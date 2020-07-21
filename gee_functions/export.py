"""
Functions related to exporting EE assets as well as the tracking of export tasks
"""

import ee
import re
import time
import urllib3
from .constants import GEE_USER_PATH


def export_to_asset(asset, asset_type, asset_id, region, scale=30):
    """
    Exports a vector or image to the GEE asset collection
    :param asset: GEE Image or FeatureCollection
    :param asset_type: String specifying if the asset is a vector ('vector') or ('image').
    :param asset_id: ID under which the asset will be saved
    :param region: Vector representing the area of interest
    :param user_path: optional parameter to overwrite the set GEE user path
    :return task: Returns a GEE export task
    """

    # TODO - try to add a overwrite method

    user_path = GEE_USER_PATH + "/ia_classification"

    if not asset_type in ['vector', 'image']:  # in case unknwown asset type is specified
        raise ValueError('unknown asset type, please use vector or image')

    if not ee.data.getInfo(f'{user_path}'):  # creates a raster folder if needed
        ee.data.createAsset({'type': 'FOLDER'}, f'{user_path}')

    if not ee.data.getInfo(f'{user_path}/raster'):  # creates a raster folder if needed
        ee.data.createAsset({'type': 'FOLDER'}, f'{user_path}/raster')

    if not ee.data.getInfo(f'{user_path}/vector'):  # creates a vector folder if needed
        ee.data.createAsset({'type': 'FOLDER'}, f'{user_path}/vector')

    if ee.data.getInfo(f'{user_path}/raster/{asset_id}') or ee.data.getInfo(f'{user_path}/vector/{asset_id}'):
        raise FileExistsError('asset already exists')  # in case the asset already exists

    if '/' in asset_id:
        # If a "/" is present the asset is supposed to be saved in a deeper folder. The following lines make sure that
        # the folder exists before exporting the asset, if the folder does not exist a new folder is created.
        description = re.findall(pattern='.*\/([A-Za-z0-9_]*)', string=asset_id)[0]
        folders = re.findall(pattern='([A-Za-z0-9_]*)\/', string=asset_id)
        folder_str = ""
        for x in range(0, len(folders)):
            folder_str += f'/{folders[x]}'
            if asset_type == 'image':
                if not ee.data.getInfo(f'{user_path}/raster{folder_str}'):
                    ee.data.createAsset({'type':'FOLDER'}, f'{user_path}/raster{folder_str}')
            elif asset_type == 'vector':
                if not ee.data.getInfo(f'{user_path}/vector{folder_str}'):
                    ee.data.createAsset({'type':'FOLDER'}, f'{user_path}/vector{folder_str}')

    else:
        description = asset_id  # no folder structure so asset is exported with only the id

    if asset_type == 'image':
        asset = asset.regexpRename('([0-9]{1,3}_)', '')
        # removes number before each bandname
        export_task = ee.batch.Export.image.toAsset(
            image=asset,
            description=description,
            assetId=f'{user_path}/raster/{asset_id}',
            scale=scale,
            region=region,
            maxPixels=1e13,
        )
        export_task.start()
        print(f"Export started for {asset_id}")
        return export_task

    elif asset_type == 'vector':
        export_task = ee.batch.Export.table.toAsset(
            collection=asset,
            description=description,
            assetId=f'{user_path}/vector/{asset_id}',
        )

        export_task.start()
        print(f"Export started for {asset_id}")
        return export_task


def export_to_drive(asset, asset_type, asset_name, region, folder, crs='EPSG:4326'):
    """
    Exports a EE FeatureCollection of Image to user's drive account

    :param asset: EE Image or FeatureCollection
    :param asset_type: String specifying if the asset is a vector ('vector') or ('image').
    :param asset_name: filename for the asset to be saved under on the Google drive
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


def track_task(task):
    """
    Function for the tracking of a EE export task

    :param task: Either a single EE task or a dictionary with tasknames as keys and EE tasks as values.
    """
    if task == True:  # in case an asset already exists a new task is not started. Instead the existing asset is used.
        return True

    starttime = time.time()  # set the starttime, to track the runtime of the task

    if type(task) == dict:  # If a dictionary is used for input all the tasks in the dic will be tracked
        while True:
            mins_running = round((time.time() - starttime) / 60)  # calculates the # of minutes the task is running
            for t in task:
                if task[t] == True:
                    continue
                try:
                    status = task[t].status()  # get the task status
                except (ConnectionResetError, urllib3.exceptions.ProtocolError):  # in case the connection fails
                    time.sleep(30)
                    status = task[t].status()
                if status['state'] == 'COMPLETED':  # if the task is completed
                    print(f'\rTask "{t}" Completed, runtime: {mins_running} minutes')
                    task[t] = True
                elif status['state'] == 'CANCELLED':
                    raise RuntimeError(f'Export task {t} canceled')
                elif status['state'] == 'FAILED':  # if the task has failed
                    if 'Cannot overwrite asset' in status['error_message']:  # in case the asset already exists
                        print('\rAsset Already Exists')
                        return True
                    raise RuntimeError(f'Export task failed: {status["error_message"]}')
            if all(value == True for value in task.values()):
                print('All tasks completed!')
                return True
            else:
                print(f'\rRunning tasks: ({mins_running} min)')
                time.sleep(60.0 - ((time.time() - starttime) % 60.0))  # pause the loop for 60 seconds
    else:  # single ee task is used
        while True:
            mins_running = round((time.time() - starttime) / 60)  # calculates the # of minutes the task is running
            try:
                status = task.status()  # get the task status
            except (ConnectionResetError, urllib3.exceptions.ProtocolError):  # in case the connection fails
                time.sleep(30)
                status = task.status()
            if status['state'] == 'COMPLETED':  # if the task is completed
                print(f'\rTask Completed, runtime: {mins_running} minutes')
                return True
            elif status['state'] == 'CANCELLED':
                raise RuntimeError(f'Export task canceled')
            elif status['state'] == 'FAILED':  # if the task has failed
                if 'Cannot overwrite asset' in status['error_message']:  # in case the asset already exists
                    print('\rAsset Already Exists')
                    return True
                raise RuntimeError(f'Export task failed: {status["error_message"]}')
            print(f'\rRunning task: ({mins_running} min)')
            time.sleep(60.0 - ((time.time() - starttime) % 60.0))  # pause the loop for 60 seconds

