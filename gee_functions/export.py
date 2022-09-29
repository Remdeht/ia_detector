"""
Functions related to exporting EE assets as well as the tracking of export tasks
"""

import ee
import re
import time
import urllib3

from typing import Literal

try:
    from constants import PROJECT_PATH
except ImportError:
    from .constants import PROJECT_PATH


def export_to_asset(
        asset: ee.Image | ee.FeatureCollection,
        asset_type: Literal['vector', 'image'],  # TODO Maybe better to go with EE terms such as table and image
        asset_id: str,
        region: ee.FeatureCollection,
        scale: int = 30,
        max_pixels: int = 1e13,
        overwrite: bool = False) -> ee.batch.Task:
    """
    Exports a vector or image to the GEE asset collection
    :param asset: GEE Image or FeatureCollection
    :param asset_type: String specifying if the asset is a vector ('vector') or ('image').
    :param asset_id: ID under which the asset will be saved
    :param region: Vector representing the area of interest
    :param scale: pixel resolution tp use for export (meter per pixel)
    :param max_pixels: maximum number of pixels to allow for a raster asset
    :param overwrite: Boolean, if True it overwrites previous classification result with the same parameters/aoi
    :return task: Returns a GEE export task
    """

    # TODO - set the ACL for the asset? Need to check if asset can be set as viewable for everyone

    if not asset_type in ['vector', 'image']:  # in case unknwown asset type is specified
        raise ValueError('unknown asset type, please use vector or image')

    if not ee.data.getInfo(f'{PROJECT_PATH}'):  # creates a raster folder if needed
        ee.data.createAsset({'type': 'FOLDER'}, f'{PROJECT_PATH}')

    # TODO - dont create the folder if not exporting the particular asset type
    if not ee.data.getInfo(f'{PROJECT_PATH}/raster'):  # creates a raster folder if needed
        ee.data.createAsset({'type': 'FOLDER'}, f'{PROJECT_PATH}/raster')

    if not ee.data.getInfo(f'{PROJECT_PATH}/vector'):  # creates a vector folder if needed
        ee.data.createAsset({'type': 'FOLDER'}, f'{PROJECT_PATH}/vector')

    if ee.data.getInfo(f'{PROJECT_PATH}/raster/{asset_id}') or ee.data.getInfo(f'{PROJECT_PATH}/vector/{asset_id}'):
        if overwrite is True:  # In case overwriting is enabled delete the existing asset before continuing
            if asset_type == 'image':
                ee.data.deleteAsset(f'{PROJECT_PATH}/raster/{asset_id}')
            else:
                ee.data.deleteAsset(f'{PROJECT_PATH}/vector/{asset_id}')
        else:
            raise FileExistsError('asset already exists')  # in case the asset already exists and overwrite is disabled

    if '/' in asset_id:
        # If a "/" is present the asset is supposed to be saved in a deeper folder. The following lines make sure that
        # the folder exists before exporting the asset, if the folder does not exist a new folder is created.
        description = re.findall(pattern='.*\/([A-Za-z0-9_]*)', string=asset_id)[0]
        folders = re.findall(pattern='([A-Za-z0-9_]*)\/', string=asset_id)
        folder_str = ""
        for x in range(0, len(folders)):
            folder_str += f'/{folders[x]}'
            if asset_type == 'image':
                if not ee.data.getInfo(f'{PROJECT_PATH}/raster{folder_str}'):
                    ee.data.createAsset({'type': 'FOLDER'}, f'{PROJECT_PATH}/raster{folder_str}')
            elif asset_type == 'vector':
                if not ee.data.getInfo(f'{PROJECT_PATH}/vector{folder_str}'):
                    ee.data.createAsset({'type': 'FOLDER'}, f'{PROJECT_PATH}/vector{folder_str}')

    else:
        description = asset_id  # no folder structure so asset is exported with only the id

    if asset_type == 'image':
        asset = asset.regexpRename('([0-9]{1,3}_)', '')
        # removes number before each bandname
        export_task = ee.batch.Export.image.toAsset(
            image=asset,
            description=description,
            assetId=f'{PROJECT_PATH}/raster/{asset_id}',
            scale=scale,
            region=region,
            maxPixels=max_pixels,
        )
        export_task.start()
        print(f"Export started to {PROJECT_PATH}/raster/{asset_id}")
        return export_task

    elif asset_type == 'vector':
        export_task = ee.batch.Export.table.toAsset(
            collection=asset,
            description=description,
            assetId=f'{PROJECT_PATH}/vector/{asset_id}',
        )

        export_task.start()
        print(f"Export started to {PROJECT_PATH}/vector/{asset_id}")
        return export_task


def export_to_drive(
        asset: ee.Image | ee.FeatureCollection,
        asset_type: Literal['vector', 'image'],
        asset_name: str,
        region: ee.FeatureCollection,
        folder: str,
        crs: str = 'EPSG:4326') -> ee.batch.Task:
    """
    Exports an EE FeatureCollection of Image to user's drive account

    :param asset: EE Image or FeatureCollection
    :param asset_type: String specifying if the asset is a vector ('vector') or ('image').
    :param asset_name: filename for the asset to be saved under on the Google Drive
    :param region: geometry of the extent to be exported when exporting an image
    :param folder: Google Drive folder name to save the asset in
    :param crs: projection for the asset
    :return: EE export task
    """

    if asset_type == 'image':
        export_task = ee.batch.Export.image.toDrive(
            image=asset,
            description=asset_name,
            folder=folder,
            scale=30,
            region=region,
            maxPixels=1e13,
            crs=crs
        )
        export_task.start()
        print(f"Export started for {asset_name}")
        return export_task

    elif asset_type == 'vector':
        export_task = ee.batch.Export.table.toDrive(
            collection=asset,
            description=asset_name,
            folder=folder,
            fileFormat='KML'
        )

        export_task.start()
        print(f"Export started for {asset_name}")
        return export_task


def track_task(task: ee.batch.Task | dict[str, ee.batch.Task | bool]) -> bool:
    """
    Function for the tracking of a EE export task

    :param task: Either a single EE task or a dictionary with tasknames as keys and EE tasks as values.
    """
    if task == True:  # in case an asset already exists a new task is not started. Instead the existing asset is used.
        return True

    start_time = time.time()  # set the start_time, to track the runtime of the task

    if type(task) == dict:  # If a dictionary is used for input all the tasks in the dic will be tracked

        no_of_tasks = len(task.keys())
        print(f'Tasks submitted: {no_of_tasks}')  # State how many tasks are monitored

        while True:
            mins_running = round((time.time() - start_time) / 60)  # calculates the # of minutes the task is running
            for t in task:
                if task[t] == True:
                    continue
                try:
                    status = task[t].status()  # get the task status
                except (ConnectionResetError, urllib3.exceptions.ProtocolError):  # in case the connection fails
                    time.sleep(30)
                    status = task[t].status()
                if status['state'] == 'COMPLETED':  # if the task is completed
                    print(f'Task "{t}" completed, runtime: {mins_running} minutes')
                    task[t] = True
                elif status['state'] == 'CANCELLED':
                    raise RuntimeError(f'Export task {t} canceled')
                elif status['state'] == 'FAILED':  # if the task fails
                    if 'Cannot overwrite asset' in status['error_message']:  # in case the asset already exists
                        print('Asset Already Exists', end='\r')
                        return True
                    raise RuntimeError(f'Export task failed: {status["error_message"]}')
            if all(value == True for value in task.values()):
                print('All tasks completed!', end='\r')
                return True
            else:
                # TODO make it so that the output is replaced
                print(f'Running tasks ({mins_running} min)', end='\r')
                time.sleep(60.0 - ((time.time() - start_time) % 60.0))  # pause the loop for 60 seconds
    else:  # single ee task is used
        while True:
            mins_running = round((time.time() - start_time) / 60)  # calculates the # of minutes the task is running
            try:
                status = task.status()  # get the task status
            except (ConnectionResetError, urllib3.exceptions.ProtocolError):  # in case the connection fails
                time.sleep(30)
                status = task.status()
            if status['state'] == 'COMPLETED':  # if the task is completed
                sing_or_plur = ["minute" if x < 2 else "minutes" for x in [mins_running]][0]
                print(
                    f'Task completed, with a runtime of roughly {mins_running} {sing_or_plur}'
                )
                return True
            elif status['state'] == 'CANCELLED':
                raise RuntimeError(f'Export task canceled')
            elif status['state'] == 'FAILED':  # if the task has failed
                if 'Cannot overwrite asset' in status['error_message']:  # in case the asset already exists
                    print('\rAsset Already Exists')
                    return True
                raise RuntimeError(f'Export task failed: {status["error_message"]}')
            print(f'Running task ({mins_running} min)', end='\r')
            time.sleep(60.0 - ((time.time() - start_time) % 60.0))  # pause the loop for 60 seconds


def delete_folder(path_to_folder: str) -> None:
    """
    Deletes entire folder structure
    :param path_to_folder: path to the folder to delete
    :return:
    """
    folder_assets = ee.data.listAssets({'parent': path_to_folder})['assets']

    for asset in folder_assets:
        if asset['type'] == 'IMAGE' or asset['type'] == 'TABLE':
            ee.data.deleteAsset(asset['id'])
            print(f'deleted {asset["id"]}')
        elif asset['type'] == 'FOLDER':
            delete_folder(asset['name'])
            ee.data.deleteAsset(asset['id'])
        else:
            continue

        print(f'deleted {asset["id"]}')
