import ee
import re
import subprocess
from .constants import GEE_USER_PATH


def export_to_asset(asset, asset_type, asset_id, region):
    """
    Exports a vector or image to the GEE asset collection
    :param asset: GEE Image or FeatureCollection
    :param asset_type: String specifying if the asset is a vector ('vector') or ('image').
    :param asset_id: ID under which the asset will be saved
    :param region: Vector representing the area of interest
    """
    if not asset_type in ['vector', 'image']:
        raise Exception('unknown asset type, please use vector or image')

    if '/' in asset_id:
        # If a "/" is present the asset is supposed to be saved in a deeper folder. The following lines make sure that
        # the folder exists before exporting the asset, if the folder does not exist a new folder is created.
        description = re.findall(pattern='.*\/([A-Za-z0-9_]*)', string=asset_id)[0]
        folders = re.findall(pattern='([A-Za-z0-9_]*)\/', string=asset_id)
        folder_str = ""
        for x in range(0, len(folders)):
            folder_str += f'/{folders[x]}'
            if asset_type == 'image':
                subprocess.check_call(  # calls the earthengine command line tool to create a folder
                    f'earthengine create folder {GEE_USER_PATH}/raster{folder_str}'
                )
            elif asset_type == 'vector':
                subprocess.check_call(
                    f'earthengine create folder {GEE_USER_PATH}/vector{folder_str}'
                )

    else:
        description = asset_id

    if asset_type == 'image':
        asset = asset.regexpRename('([0-9]{1,3}_)', '')  # removes number before each bandname
        export_task = ee.batch.Export.image.toAsset(
            image=asset,
            description=description,
            assetId=f'{GEE_USER_PATH}/raster/{asset_id}',
            scale=30,
            region=region,
            maxPixels=1e13,
        )
        export_task.start()

    elif asset_type == 'vector':
        export_task = ee.batch.Export.table.toAsset(
            collection=asset,
            description=description,
            assetId=f'{GEE_USER_PATH}/vector/{asset_id}',
        )

        export_task.start()

    print(f"Export started for {asset_id}")
