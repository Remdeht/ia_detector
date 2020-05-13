import ee
import re
import time
from .constants import GEE_USER_PATH


def export_to_asset(asset, asset_type, asset_id, region, user_path=None):
    """
    Exports a vector or image to the GEE asset collection
    :param asset: GEE Image or FeatureCollection
    :param asset_type: String specifying if the asset is a vector ('vector') or ('image').
    :param asset_id: ID under which the asset will be saved
    :param region: Vector representing the area of interest
    :param user_path: optional parameter to overwrite the set GEE user path
    :return task: Returns a GEE export task
    """

    if user_path is None:  # if no other user path is specified set it to default user path
        user_path = GEE_USER_PATH

    if not asset_type in ['vector', 'image']:  # in case unknwown asset type is specified
        raise ValueError('unknown asset type, please use vector or image')

    if not ee.data.getInfo(f'{user_path}/raster'):
        ee.data.createAsset({'type': 'FOLDER'}, f'{user_path}/raster')

    if not ee.data.getInfo(f'{user_path}/vector'):
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
            scale=30,
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


def track_task(task):
    """ Function for the tracking of a GEE export task"""
    if task == True:  # in case an asset already exists a new task is not started. Instead the existing asset is used.
        return True

    starttime = time.time()  # set the starttime, to track the runtime of the task
    while True:
        mins_running = round((time.time() - starttime) / 60)  # calculates the # of minutes the task is running
        try:
            status = task.status()  # get the task status
        except ConnectionResetError:  # in case the connection fails
            time.sleep(15)
            status = task.status()
        if status['state'] == 'COMPLETED':  # if the task is completed
            print(f'\rTask Completed, runtime: {mins_running} minutes')
            return True
        elif status['state'] == 'FAILED':  # if the task has failed
            if 'Cannot overwrite asset' in status['error_message']:  # in case the asset already exists
                print('\rAsset Already Exists')
                return True
            raise(RuntimeError)(f'Export task failed: {status["error_message"]}')
        print(f'\rRunning Task ({mins_running} min)')
        time.sleep(60.0 - ((time.time() - starttime) % 60.0))  # pause the loop for 60 seconds

