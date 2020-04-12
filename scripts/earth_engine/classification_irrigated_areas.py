import re
import ee
import ee.mapclient
import subprocess
from gee_functions import landsat, vector

ee.Initialize()  # Initialize the Google Earth Engine

GEE_USER_PATH = 'users/Postm087'

CdC = ee.FeatureCollection(f'{GEE_USER_PATH}/outline_3857')  # Load the feature collection containing the area of interest
cdc_coordinates = CdC.geometry().bounds().getInfo()['coordinates']


def add_points(feature, class_label, no_points=1000):
    """Selects desired number of training points within a given region and labels each point with the corresponding
     class label"""

    def add_class(feature):
        return feature.set({'landuse': class_label})

    training_points = ee.FeatureCollection.randomPoints(feature, no_points, 0);
    training_set = training_points.map(add_class)

    return training_set


def rename_bands_to_month_year(image):
    """Renames the bands of an imagecollection to the name of the index, and the month and year of the observation"""
    return image.rename(ee.List([image.get('date_info')]))


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
            if asset_type == 'raster':
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
        asset = asset.regexpRename('([0-9]*_)', '')  # removes number before each bandname
        export_task = ee.batch.Export.image.toAsset(
            image=asset,
            description=description,
            assetId=f'{GEE_USER_PATH}/raster/{asset_id}',
            scale=30,
            region=region,
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


def create_features(year, aoi, year_string='unknown', season='year', features=[None], single_bands=None):
    """
    Exports the features need for classification to the GEE as assets. The assets will later be loaded in
    during classification.

    :param year: Tuple containing the begin and end date for the selection of imagery.
    :param aoi: GEE Featurecollection of the area of interest.
    :param year_string: String with the last two numbers of the year being observed, e.g. '88'.
    :param season: String indicating the season for which the data is extracted, either summer, winter or year
    :param features: List of the features to export, vector refers to the polygons of the training areas and crop_data
    refers to an image containing all the features for classification, i.e. spectral indices and slope
    :param single_bands: in case the monthly data for a single band is used for classification this parameters
    can be used. Each monthly image for the selected season will be exported for the spectral index specified.
    """

    # Extract the date range for the period from the dictionary
    BEGIN = year[0]
    END = year[1]

    # Retrieve landsat 5 and 7 imagery for the period and merge them together
    ls_5 = landsat.get_ls5_image_collection(BEGIN, END, aoi)
    ls_7 = landsat.get_ls7_image_collection(BEGIN, END, aoi)
    ls = ls_5.merge(ls_7)

    # Calculate indices to be used in the classification
    ls_ndvi = ls.map(landsat.add_ndvi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDVI'))
    ls_gcvi = ls.map(landsat.add_gcvi_ls457).filter(ee.Filter.listContains('system:band_names', 'GCVI'))
    ls_ndwi = ls.map(landsat.add_ndwi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDWI'))
    ls_ndwi_greenhouses = ls.map(landsat.add_ndwi_mcfeeters_ls457).filter(
        ee.Filter.listContains('system:band_names', 'NDWIGH'))
    ls_hsv = ls.map(landsat.rgb_to_hsv)  # Hue Saturation Value

    # Create monthly images for each index, containing both the mean value and, the 10th and 90th percentile,
    # for each month

    ls_monthly_hue = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='hue',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_saturation = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='saturation',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_value = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='value',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_blue = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B1',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_green = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B2',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_red = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B3',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_ndvi = landsat.create_monthly_index_images(
        image_collection=ls_ndvi,
        band='NDVI',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_gcvi = landsat.create_monthly_index_images(
        image_collection=ls_gcvi,
        band='GCVI',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_ndwi = landsat.create_monthly_index_images(
        image_collection=ls_ndwi,
        band='NDWI',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_ndwi_greenhouses = landsat.create_monthly_index_images(
        image_collection=ls_ndwi_greenhouses,
        band='NDWIGH',
        start_date=BEGIN,
        end_date=END,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_mean_monthly_mean_hue = ls_monthly_hue.select('mean').mean().rename('hue mean')
    ls_mean_monthly_max_hue = ls_monthly_hue.select('max').mean().rename('hue max')
    ls_mean_monthly_min_hue = ls_monthly_hue.select('min').mean().rename('hue min')

    ls_mean_monthly_mean_saturation = ls_monthly_saturation.select('mean').mean().rename('saturation mean')
    ls_mean_monthly_max_saturation = ls_monthly_saturation.select('max').mean().rename('saturation max')
    ls_mean_monthly_min_saturation = ls_monthly_saturation.select('min').mean().rename('saturation min')

    ls_mean_monthly_mean_value = ls_monthly_value.select('mean').mean().rename('value mean')
    ls_mean_monthly_max_value = ls_monthly_value.select('max').mean().rename('value max')
    ls_mean_monthly_min_value = ls_monthly_value.select('min').mean().rename('value min')

    ls_mean_monthly_mean_blue = ls_monthly_blue.select('mean').mean().rename('blue mean')
    ls_mean_monthly_max_blue = ls_monthly_blue.select('max').mean().rename('blue max')
    ls_mean_monthly_min_blue = ls_monthly_blue.select('min').mean().rename('blue min')

    ls_mean_monthly_mean_green = ls_monthly_green.select('mean').mean().rename('green mean')
    ls_mean_monthly_max_green = ls_monthly_green.select('max').mean().rename('green max')
    ls_mean_monthly_min_green = ls_monthly_green.select('min').mean().rename('green min')

    ls_mean_monthly_mean_red = ls_monthly_red.select('mean').mean().rename('red mean')
    ls_mean_monthly_max_red = ls_monthly_red.select('max').mean().rename('red max')
    ls_mean_monthly_min_red = ls_monthly_red.select('min').mean().rename('red min')

    ls_mean_monthly_mean_ndvi = ls_monthly_ndvi.select('mean').mean().rename('NDVI mean')
    ls_mean_monthly_max_ndvi = ls_monthly_ndvi.select('max').mean().rename('NDVI max')
    ls_mean_monthly_min_ndvi = ls_monthly_ndvi.select('min').mean().rename('NDVI min')

    ls_mean_monthly_mean_gcvi = ls_monthly_gcvi.select('mean').mean().rename('GCVI mean')
    ls_mean_monthly_max_gcvi = ls_monthly_gcvi.select('max').mean().rename('GCVI max')
    ls_mean_monthly_min_gcvi = ls_monthly_gcvi.select('min').mean().rename('GCVI min')

    ls_mean_monthly_mean_ndwi = ls_monthly_ndwi.select('mean').mean().rename('NDWI mean')
    ls_mean_monthly_max_ndwi = ls_monthly_ndwi.select('max').mean().rename('NDWI max')
    ls_mean_monthly_min_ndwi = ls_monthly_ndwi.select('min').mean().rename('NDWI min')

    ls_mean_monthly_mean_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('mean').mean().rename('NDWIGH mean')
    ls_mean_monthly_max_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('max').mean().rename('NDWIGH max')
    ls_mean_monthly_min_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('min').mean().rename('NDWIGH min')

    ls_monthly_value_summer = ls_monthly_value.filter(ee.Filter.rangeContains('month', 4, 9))
    ls_monthly_blue_summer = ls_monthly_blue.filter(ee.Filter.rangeContains('month', 4, 9))
    ls_monthly_green_summer = ls_monthly_green.filter(ee.Filter.rangeContains('month', 4, 9))
    ls_monthly_red_summer = ls_monthly_red.filter(ee.Filter.rangeContains('month', 4, 9))
    ls_monthly_ndvi_summer = ls_monthly_ndvi.filter(ee.Filter.rangeContains('month', 4, 9))
    ls_monthly_gcvi_summer = ls_monthly_gcvi.filter(ee.Filter.rangeContains('month', 4, 9))
    ls_monthly_ndwi_summer = ls_monthly_ndwi.filter(ee.Filter.rangeContains('month', 4, 9))
    ls_monthly_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses.filter(ee.Filter.rangeContains('month', 4, 9))

    # Same principle only now for the summer months
    ls_mean_monthly_max_value_summer = ls_monthly_value_summer.select('max').mean().rename('value max')

    ls_mean_monthly_mean_blue_summer = ls_monthly_blue_summer.select('mean').mean().rename('blue mean')
    ls_mean_monthly_max_blue_summer = ls_monthly_blue_summer.select('max').mean().rename('blue max')
    ls_mean_monthly_min_blue_summer = ls_monthly_blue_summer.select('min').mean().rename('blue min')

    ls_mean_monthly_mean_green_summer = ls_monthly_green_summer.select('mean').mean().rename('green mean')
    ls_mean_monthly_max_green_summer = ls_monthly_green_summer.select('max').mean().rename('green max')
    ls_mean_monthly_min_green_summer = ls_monthly_green_summer.select('min').mean().rename('green min')

    ls_mean_monthly_mean_red_summer = ls_monthly_red_summer.select('mean').mean().rename('red mean')
    ls_mean_monthly_max_red_summer = ls_monthly_red_summer.select('max').mean().rename('red max')
    ls_mean_monthly_min_red_summer = ls_monthly_red_summer.select('min').mean().rename('red min')

    ls_mean_monthly_mean_ndvi_summer = ls_monthly_ndvi_summer.select('mean').mean().rename('NDVI mean')
    ls_mean_monthly_max_ndvi_summer = ls_monthly_ndvi_summer.select('max').mean().rename('NDVI max')
    ls_mean_monthly_min_ndvi_summer = ls_monthly_ndvi_summer.select('min').mean().rename('NDVI min')

    ls_mean_monthly_mean_gcvi_summer = ls_monthly_gcvi_summer.select('mean').mean().rename('GCVI mean')
    ls_mean_monthly_max_gcvi_summer = ls_monthly_gcvi_summer.select('max').mean().rename('GCVI max')
    ls_mean_monthly_min_gcvi_summer = ls_monthly_gcvi_summer.select('min').mean().rename('GCVI min')

    ls_mean_monthly_mean_ndwi_summer = ls_monthly_ndwi_summer.select('mean').mean().rename('NDWI mean')
    ls_mean_monthly_max_ndwi_summer = ls_monthly_ndwi_summer.select('max').mean().rename('NDWI max')
    ls_mean_monthly_min_ndwi_summer = ls_monthly_ndwi_summer.select('min').mean().rename('NDWI min')

    ls_mean_monthly_mean_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select('mean').mean().rename(
        'NDWIGH mean')
    ls_mean_monthly_max_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select('max').mean().rename(
        'NDWIGH max')
    ls_mean_monthly_min_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select('min').mean().rename(
        'NDWIGH min')

    early_filter = ee.Filter.rangeContains('month', 1, 3)
    late_filter = ee.Filter.rangeContains('month', 10, 12)

    ls_monthly_blue_winter = ls_monthly_blue.filter(ee.Filter.Or(early_filter, late_filter))
    ls_monthly_green_winter = ls_monthly_green.filter(ee.Filter.Or(early_filter, late_filter))
    ls_monthly_red_winter = ls_monthly_red.filter(ee.Filter.Or(early_filter, late_filter))
    ls_monthly_ndvi_winter = ls_monthly_ndvi.filter(ee.Filter.Or(early_filter, late_filter))
    ls_monthly_gcvi_winter = ls_monthly_gcvi.filter(ee.Filter.Or(early_filter, late_filter))
    ls_monthly_ndwi_winter = ls_monthly_ndwi.filter(ee.Filter.Or(early_filter, late_filter))
    ls_monthly_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses.filter(ee.Filter.Or(early_filter, late_filter))

    # And Winter
    ls_mean_monthly_mean_blue_winter = ls_monthly_blue_winter.select('mean').mean().rename('blue mean')
    ls_mean_monthly_max_blue_winter = ls_monthly_blue_winter.select('max').mean().rename('blue max')
    ls_mean_monthly_min_blue_winter = ls_monthly_blue_winter.select('min').mean().rename('blue min')

    ls_mean_monthly_mean_green_winter = ls_monthly_green_winter.select('mean').mean().rename('green mean')
    ls_mean_monthly_max_green_winter = ls_monthly_green_winter.select('max').mean().rename('green max')
    ls_mean_monthly_min_green_winter = ls_monthly_green_winter.select('min').mean().rename('green min')

    ls_mean_monthly_mean_red_winter = ls_monthly_red_winter.select('mean').mean().rename('red mean')
    ls_mean_monthly_max_red_winter = ls_monthly_red_winter.select('max').mean().rename('red max')
    ls_mean_monthly_min_red_winter = ls_monthly_red_winter.select('min').mean().rename('red min')

    ls_mean_monthly_mean_ndvi_winter = ls_monthly_ndvi_winter.select('mean').mean().rename('NDVI mean')
    ls_mean_monthly_max_ndvi_winter = ls_monthly_ndvi_winter.select('max').mean().rename('NDVI max')
    ls_mean_monthly_min_ndvi_winter = ls_monthly_ndvi_winter.select('min').mean().rename('NDVI min')

    ls_mean_monthly_mean_gcvi_winter = ls_monthly_gcvi_winter.select('mean').mean().rename('GCVI mean')
    ls_mean_monthly_max_gcvi_winter = ls_monthly_gcvi_winter.select('max').mean().rename('GCVI max')
    ls_mean_monthly_min_gcvi_winter = ls_monthly_gcvi_winter.select('min').mean().rename('GCVI min')

    ls_mean_monthly_mean_ndwi_winter = ls_monthly_ndwi_winter.select('mean').mean().rename('NDWI mean')
    ls_mean_monthly_max_ndwi_winter = ls_monthly_ndwi_winter.select('max').mean().rename('NDWI max')
    ls_mean_monthly_min_ndwi_winter = ls_monthly_ndwi_winter.select('min').mean().rename('NDWI min')

    ls_mean_monthly_mean_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select('mean').mean().rename(
        'NDWIGH mean')
    ls_mean_monthly_max_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select('max').mean().rename(
        'NDWIGH max')
    ls_mean_monthly_min_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select('min').mean().rename(
        'NDWIGH min')

    # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
    yearly_std_ndvi = landsat.get_yearly_band_std(
        ls_ndvi,
        ['NDVI'],
        BEGIN,
        END,
        aoi
    )

    yearly_std_ndwi = landsat.get_yearly_band_std(
        ls_ndwi,
        ['NDWI'],
        BEGIN,
        END,
        aoi
    )

    yearly_std_gcvi = landsat.get_yearly_band_std(
        ls_gcvi,
        ['GCVI'],
        BEGIN,
        END,
        aoi
    )

    # Take the mean for the periods that will be used during thresholding.
    yearly_ndvi_std_mean = yearly_std_ndvi.select('NDVI_std').mean()
    yearly_ndwi_std_mean = yearly_std_ndwi.select('NDWI_std').mean()
    yearly_gcvi_std_mean = yearly_std_gcvi.select('GCVI_std').mean()

    # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
    summer_std_ndvi = landsat.get_yearly_band_std(
        ls_ndvi,
        ['NDVI'],
        BEGIN,
        END,
        aoi,
        season='summer'
    )

    summer_std_ndwi = landsat.get_yearly_band_std(
        ls_ndwi,
        ['NDWI'],
        BEGIN,
        END,
        aoi,
        season='summer'
    )

    summer_std_gcvi = landsat.get_yearly_band_std(
        ls_gcvi,
        ['GCVI'],
        BEGIN,
        END,
        aoi,
        season='summer'
    )

    summer_ndvi_std_mean = summer_std_ndvi.select('NDVI_std').mean()
    summer_ndwi_std_mean = summer_std_ndwi.select('NDWI_std').mean()
    summer_gcvi_std_mean = summer_std_gcvi.select('GCVI_std').mean()

    winter_std_ndvi = landsat.get_yearly_band_std(
        ls_ndvi,
        ['NDVI'],
        BEGIN,
        END,
        aoi,
        season='winter'
    )

    winter_std_ndwi = landsat.get_yearly_band_std(
        ls_ndwi,
        ['NDWI'],
        BEGIN,
        END,
        aoi,
        season='winter'
    )

    winter_std_gcvi = landsat.get_yearly_band_std(
        ls_gcvi,
        ['GCVI'],
        BEGIN,
        END,
        aoi,
        season='winter'
    )

    winter_ndvi_std_mean = winter_std_ndvi.select('NDVI_std').mean()
    winter_ndwi_std_mean = winter_std_ndwi.select('NDWI_std').mean()
    winter_gcvi_std_mean = winter_std_gcvi.select('GCVI_std').mean()

    # Dictionaries with the imagecollections contaning the monthly values for each month, the are used in case
    # a single band imagecollection is exported.
    band_collection = {
        'NDVI': {'min': ls_monthly_ndvi.select('min'),
                 'mean': ls_monthly_ndvi.select('mean'),
                 'max': ls_monthly_ndvi.select('max'), },
        'GCVI': {'min': ls_monthly_gcvi.select('min'),
                 'mean': ls_monthly_gcvi.select('mean'),
                 'max': ls_monthly_gcvi.select('max'), },
        'NDWI': {'min': ls_monthly_ndwi.select('min'),
                 'mean': ls_monthly_ndwi.select('mean'),
                 'max': ls_monthly_ndwi.select('max'), },
        'NDWIGH': {'min': ls_monthly_ndwi_greenhouses.select('min'),
                   'mean': ls_monthly_ndwi_greenhouses.select('mean'),
                   'max': ls_monthly_ndwi_greenhouses.select('max'), },
    }

    band_collection_summer = {
        'NDVI': {'min': ls_monthly_ndvi_summer.select('min'),
                 'mean': ls_monthly_ndvi_summer.select('mean'),
                 'max': ls_monthly_ndvi_summer.select('max'), },
        'GCVI': {'min': ls_monthly_gcvi_summer.select('min'),
                 'mean': ls_monthly_gcvi_summer.select('mean'),
                 'max': ls_monthly_gcvi_summer.select('max'), },
        'NDWI': {'min': ls_monthly_ndwi_summer.select('min'),
                 'mean': ls_monthly_ndwi_summer.select('mean'),
                 'max': ls_monthly_ndwi_summer.select('max'), },
        'NDWIGH': {'min': ls_monthly_ndwi_greenhouses_summer.select('min'),
                   'mean': ls_monthly_ndwi_greenhouses_summer.select('mean'),
                   'max': ls_monthly_ndwi_greenhouses_summer.select('max'), },
    }

    band_collection_winter = {
        'NDVI': {'min': ls_monthly_ndvi_winter.select('min'),
                 'mean': ls_monthly_ndvi_winter.select('mean'),
                 'max': ls_monthly_ndvi_winter.select('max'), },
        'GCVI': {'min': ls_monthly_gcvi_winter.select('min'),
                 'mean': ls_monthly_gcvi_winter.select('mean'),
                 'max': ls_monthly_gcvi_winter.select('max'), },
        'NDWI': {'min': ls_monthly_ndwi_winter.select('min'),
                 'mean': ls_monthly_ndwi_winter.select('mean'),
                 'max': ls_monthly_ndwi_winter.select('max'), },
        'NDWIGH': {'min': ls_monthly_ndwi_greenhouses_winter.select('min'),
                   'mean': ls_monthly_ndwi_greenhouses_winter.select('mean'),
                   'max': ls_monthly_ndwi_greenhouses_winter.select('max'), },
    }

    # Finally calculate the slope for the area of interest
    elevation = ee.Image('JAXA/ALOS/AW3D30/V2_2').select('AVE_DSM')
    slope = ee.Terrain.slope(elevation).clip(aoi).rename('slope')

    if 'vector' in features:
        # Based on class analysis the pixels for classes can be obtained by applying thresholds.
        # Next up the masks for each class will be created.
        mask_irrigated_crops = slope.lte(4) \
            .And(ls_mean_monthly_max_gcvi_summer.gt(1.05)) \
            .And(ls_mean_monthly_min_ndvi_summer.gte(.13)) \
            .And(ls_mean_monthly_min_ndvi_summer.lte(.31)) \
            .And(ls_mean_monthly_max_ndwi_greenhouses_summer.lt(-.26)) \
            .And(yearly_ndvi_std_mean.gt(.14))
        vector_irrigated_crops_mask = vector.raster_to_vector(
            mask_irrigated_crops,
            aoi,
            tile_scale=2
        )
        export_to_asset(vector_irrigated_crops_mask, 'vector',
                        f'training_areas/vector_irrigated_crops_mask_{year_string}',
                        cdc_coordinates)

        mask_irrigated_trees = slope.lte(4) \
            .And(ls_mean_monthly_max_gcvi_summer.gt(1.05)) \
            .And(ls_mean_monthly_min_ndvi_summer.gt(.31)) \
            .And(ls_mean_monthly_max_ndwi_greenhouses_summer.lt(-.26))
        vector_irrigated_trees_mask = vector.raster_to_vector(
            mask_irrigated_trees,
            aoi,
            tile_scale=2
        )
        export_to_asset(vector_irrigated_trees_mask, 'vector',
                        f'training_areas/vector_irrigated_trees_mask_{year_string}',
                        cdc_coordinates)

        mask_greenhouses = slope.lte(5) \
            .And(ls_mean_monthly_max_ndwi_greenhouses.gt(-.23)) \
            .And(ls_mean_monthly_max_ndwi.gt(.06)) \
            .And(ls_mean_monthly_max_value_summer.gt(.27))
        vector_greenhouses_mask = vector.raster_to_vector(
            mask_greenhouses,
            aoi,
            tile_scale=2
        )
        export_to_asset(vector_greenhouses_mask, 'vector', f'training_areas/vector_greenhouses_mask_{year_string}',
                        cdc_coordinates)

        mask_potential_crops = slope.lte(5) \
            .And(ls_mean_monthly_max_gcvi_summer.gt(.7))
        vector_potential_crops_mask = vector.raster_to_vector(
            mask_potential_crops,
            aoi,
            tile_scale=2
        )
        export_to_asset(vector_potential_crops_mask, 'vector',
                        f'training_areas/vector_potential_crops_mask_{year_string}',
                        cdc_coordinates)

        mask_rainfed_trees_crops = slope.lte(4) \
            .And(ls_mean_monthly_max_gcvi_summer.lte(1.05)) \
            .And(ls_mean_monthly_max_gcvi_summer.gte(.6))
        vector_rainfed_trees_crops_mask = vector.raster_to_vector(
            mask_rainfed_trees_crops,
            aoi,
            tile_scale=2
        )
        export_to_asset(vector_rainfed_trees_crops_mask, 'vector',
                        f'training_areas/vector_rainfed_trees_crops_mask_{year_string}',
                        cdc_coordinates)
        mask_natural_trees = slope.gte(10) \
            .And(ls_mean_monthly_min_red.lt(1000)) \
            .And(ls_mean_monthly_max_ndvi.gt(.3))
        vector_natural_trees_mask = vector.raster_to_vector(
            mask_natural_trees,
            aoi,
            tile_scale=2
        )
        export_to_asset(vector_natural_trees_mask, 'vector', f'training_areas/vector_natural_trees_mask_{year_string}',
                        cdc_coordinates)

        if 'training' in features:
            training_area = ee.Image(0).where(
                mask_natural_trees.eq(1), 1).where(
                mask_rainfed_trees_crops.eq(1), 2).where(
                mask_irrigated_crops.eq(1), 3).where(
                mask_greenhouses.eq(1), 4).where(
                mask_potential_crops.eq(1), 5)

            export_task_4 = ee.batch.Export.image.toDrive(
                image=training_area,
                description=f'training_areas_rf_{year_string}',
                folder='training_areas',
                scale=30,
                region=cdc_coordinates,
            )
            export_task_4.start()
            print(
                f'Export task started for year: {year_string}.')
            return 0

    if 'crop_data' in features:
        # Create an image out of all the feature maps created. This Image will be used for classification and training
        if season == 'year':
            crop_data_min_mean_max = ee.ImageCollection([
                ls_mean_monthly_mean_blue.rename('blue'),
                ls_mean_monthly_mean_green.rename('green'),
                ls_mean_monthly_mean_red.rename('red'),
                ls_mean_monthly_min_gcvi.rename('min_GCVI'),
                ls_mean_monthly_mean_gcvi.rename('mean_GCVI'),
                ls_mean_monthly_max_gcvi.rename('max_GCVI'),
                ls_mean_monthly_min_ndvi.rename('min_NDVI'),
                ls_mean_monthly_mean_ndvi.rename('mean_NDVI'),
                ls_mean_monthly_max_ndvi.rename('max_NDVI'),
                ls_mean_monthly_min_ndwi.rename('min_NDWI'),
                ls_mean_monthly_mean_ndwi.rename('mean_NDWI'),
                ls_mean_monthly_max_ndwi.rename('max_NDWI'),
                ls_mean_monthly_min_ndwi_greenhouses.rename('min_NDWIGH'),
                ls_mean_monthly_mean_ndwi_greenhouses.rename('mean_NDWIGH'),
                ls_mean_monthly_max_ndwi_greenhouses.rename('max_NDWIGH'),
                yearly_ndvi_std_mean.rename('NDVI_std'),
                yearly_gcvi_std_mean.rename('GCVI_std'),
                yearly_ndwi_std_mean.rename('NDWI_std'),
                slope
            ]).toBands()
            export_to_asset(crop_data_min_mean_max, 'image', f"crop_data_min_mean_max_{year_string}", cdc_coordinates)
        elif season == 'summer':
            crop_data_min_mean_max = ee.ImageCollection([
                ls_mean_monthly_mean_blue_summer.rename('blue'),
                ls_mean_monthly_mean_green_summer.rename('green'),
                ls_mean_monthly_mean_red_summer.rename('red'),
                ls_mean_monthly_min_gcvi_summer.rename('min_GCVI'),
                ls_mean_monthly_mean_gcvi_summer.rename('mean_GCVI'),
                ls_mean_monthly_max_gcvi_summer.rename('max_GCVI'),
                ls_mean_monthly_min_ndvi_summer.rename('min_NDVI'),
                ls_mean_monthly_mean_ndvi_summer.rename('mean_NDVI'),
                ls_mean_monthly_max_ndvi_summer.rename('max_NDVI'),
                ls_mean_monthly_min_ndwi_summer.rename('min_NDWI'),
                ls_mean_monthly_mean_ndwi_summer.rename('mean_NDWI'),
                ls_mean_monthly_max_ndwi_summer.rename('max_NDWI'),
                ls_mean_monthly_min_ndwi_greenhouses_summer.rename('min_NDWIGH'),
                ls_mean_monthly_mean_ndwi_greenhouses_summer.rename('mean_NDWIGH'),
                ls_mean_monthly_max_ndwi_greenhouses_summer.rename('max_NDWIGH'),
                summer_ndvi_std_mean.rename('NDVI_std'),
                summer_gcvi_std_mean.rename('GCVI_std'),
                summer_ndwi_std_mean.rename('NDWI_std'),
                slope
            ]).toBands()
            export_to_asset(crop_data_min_mean_max, 'image', f"crop_data_summer_min_mean_max_{year_string}",
                            cdc_coordinates)
        elif season == 'winter':
            crop_data_min_mean_max = ee.ImageCollection([
                ls_mean_monthly_mean_blue_winter.rename('blue'),
                ls_mean_monthly_mean_green_winter.rename('green'),
                ls_mean_monthly_mean_red_winter.rename('red'),
                ls_mean_monthly_min_gcvi_winter.rename('min_GCVI'),
                ls_mean_monthly_mean_gcvi_winter.rename('mean_GCVI'),
                ls_mean_monthly_max_gcvi_winter.rename('max_GCVI'),
                ls_mean_monthly_min_ndvi_winter.rename('min_NDVI'),
                ls_mean_monthly_mean_ndvi_winter.rename('mean_NDVI'),
                ls_mean_monthly_max_ndvi_winter.rename('max_NDVI'),
                ls_mean_monthly_min_ndwi_winter.rename('min_NDWI'),
                ls_mean_monthly_mean_ndwi_winter.rename('mean_NDWI'),
                ls_mean_monthly_max_ndwi_winter.rename('max_NDWI'),
                ls_mean_monthly_min_ndwi_greenhouses_winter.rename('min_NDWIGH'),
                ls_mean_monthly_mean_ndwi_greenhouses_winter.rename('mean_NDWIGH'),
                ls_mean_monthly_max_ndwi_greenhouses_winter.rename('max_NDWIGH'),
                winter_ndvi_std_mean.rename('NDVI_std'),
                winter_gcvi_std_mean.rename('GCVI_std'),
                winter_ndwi_std_mean.rename('NDWI_std'),
                slope
            ]).toBands()
            export_to_asset(
                crop_data_min_mean_max,
                'image',
                f"crop_data_winter_min_mean_max_{year_string}",
                cdc_coordinates,
            )

    if single_bands is not None:
        # Exports each monthly image for the specified index
        for band in single_bands:
            band_name = band[0]
            stat = band[1]
            if season == 'year':
                monthly_images = band_collection[band_name][stat]
            elif season == 'summer':
                monthly_images = band_collection_summer[band_name][stat]
            elif season == 'winter':
                monthly_images = band_collection_winter[band_name][stat]

            monthly_images = monthly_images.map(rename_bands_to_month_year)

            export_to_asset(monthly_images.toBands(),
                            'image',
                            f"crop_data/single_bands/{season}/crop_data_{season}_{band_name}_{stat}_{year_string}",
                            cdc_coordinates)


def classify_irrigated_areas(training_image, data_info, vector_collection, aoi_coordinates, year_string='unknown', clf='random_forest',
                             no_trees=500, bag_fraction=.5, vps=2):
    """
    Performs a classification using pixels within the class regions obtained via thresholding as training data.
    Classification is performed on the GEE servers and results are exported to Google Drive connected to the GEE
    user account.

    :param training_image: GEE image containing all the feature data for classification.
    :param data_info: metadata regarding the feature data, used for naming the classification.
    :param vector_collection: dictionary containing the assetIds of the vector of each class.
    :param aoi_coordinates: Featurecollection representing the area of interest.
    :param year_string: year of observation, used for naming of the results.
    :param clf: classifier type, either bayes or random forest.
    :param no_trees: In case of random forest the number of trees to use for classificaiton.
    :param bag_fraction: In case of random forest the bag fraction to use for classificaiton.
    :param vps: In case of random forest the variables per split to use for classificaiton.
    """

    bands = training_image.bandNames()  # Extracts the name of each band in the training image
    class_property = 'landuse'

    # Create Training Areas for Multiclass classification
    rainfed_crops_trees = add_points(ee.FeatureCollection(
        f'{GEE_USER_PATH}/vector/{vector_collection["rainfed_trees_crops"]}'), 1)
    natural_trees = add_points(ee.FeatureCollection(
        f'{GEE_USER_PATH}/vector/{vector_collection["natural_trees"]}'), 2)
    greenhouses = add_points(ee.FeatureCollection(
        f'{GEE_USER_PATH}/vector/{vector_collection["greenhouses"]}'), 3)
    irrigated_crops = add_points(ee.FeatureCollection(
        f'{GEE_USER_PATH}/vector/{vector_collection["irrigated_crops"]}'), 4)
    irrigated_trees = add_points(ee.FeatureCollection(
        f'{GEE_USER_PATH}/vector/{vector_collection["irrigated_trees"]}'), 5)

    training_regions_multiclass = rainfed_crops_trees \
        .merge(natural_trees) \
        .merge(greenhouses) \
        .merge(irrigated_crops) \
        .merge(irrigated_trees)

    training_multiclass = training_image.select(bands).sampleRegions(
        collection=training_regions_multiclass,
        properties=[class_property],
        scale=30,
        tileScale=2,
    )

    if clf == 'bayes':
        # Train classifier for the multiclass classification
        classifier_naivebayes = ee.Classifier.smileNaiveBayes().train(training_multiclass, class_property)

        # Classify the unknown area based on the crop data using the multiclass classifiers
        irrigated_area_classified_multiclass = training_image \
            .clip(ee.FeatureCollection(f'{GEE_USER_PATH}/vector/{vector_collection["potential_crops"]}')) \
            .classify(classifier_naivebayes)

        irrigated_area_multiclass = ee.Image(0) \
            .where(irrigated_area_classified_multiclass.select('classification').eq(4), 1) \
            .where(irrigated_area_classified_multiclass.select('classification').eq(5), 2)

        export_task = ee.batch.Export.image.toDrive(
            image=irrigated_area_multiclass,
            description=f'ia_{clf}_{data_info}_{year_string}',
            folder=f'{clf}_{data_info}',
            scale=30,
            region=aoi_coordinates,
        )

        export_task.start()
        print(f'Export started. Year: {year_string}. Classification method: {clf}. Features used {data_info}')

    elif clf == 'random_forest':
        # Train classifier for the multiclass classification
        classifier_multiclass = ee.Classifier.smileRandomForest(
            no_trees,
            variablesPerSplit=vps,
            bagFraction=bag_fraction
        ).train(
            training_multiclass,
            class_property
        )

        # Classify the unknown area based on the crop data using the multiclass classifiers
        irrigated_area_classified_multiclass = training_image \
            .clip(ee.FeatureCollection(f'{GEE_USER_PATH}/vector/{vector_collection["potential_crops"]}')) \
            .classify(classifier_multiclass)

        irrigated_area_multiclass = ee.Image(0) \
            .where(irrigated_area_classified_multiclass.select('classification').eq(4), 1) \
            .where(irrigated_area_classified_multiclass.select('classification').eq(5), 2)

        export_task = ee.batch.Export.image.toDrive(
            image=irrigated_area_multiclass,
            description=f'ia_{clf}_{data_info}_{no_trees}tr_{vps}vps_{int(bag_fraction * 100)}bf_{year_string}',
            folder=f'{clf}_{data_info}',
            scale=30,
            region=aoi_coordinates,
        )

        export_task.start()
        print(f'Export started. Year: {year_string}. Classification method: {clf}. Features used {data_info}')


if __name__ == '__main__':
    import itertools

    # Dictionary containing the date ranges for each year, will be used to select sat. imagery
    years = {
        '88': ('1987-01-01', '1989-01-01'),
        '97': ('1996-01-01', '1998-01-01'),
        '00': ('1999-01-01', '2001-01-01'),
        '05': ('2004-01-01', '2006-01-01'),
        '09': ('2008-01-01', '2010-01-01'),
    }

    stats = ['mean', 'min', 'max']
    stats_combos = list(itertools.combinations(stats, 1)) + \
                   list(itertools.combinations(stats, 2)) + \
                   list(itertools.combinations(stats, 3))

    for year in years:
        crop_data_folder = f'{GEE_USER_PATH}/raster/crop_data/'

        crop_data_collection = {
            'min_mean_max': ee.Image(f"{crop_data_folder}crop_data_min_mean_max_{year}"),
            'min_mean_max_summer': ee.Image(f"{crop_data_folder}crop_data_summer_min_mean_max_{year}"),
            'min_mean_max_winter': ee.Image(f"{crop_data_folder}crop_data_winter_min_mean_max_{year}"),
        }

        vector_collection = {
            'irrigated_crops': f'training_areas/vector_irrigated_crops_mask_{year}',
            'irrigated_trees': f'training_areas/vector_irrigated_trees_mask_{year}',
            'greenhouses': f'training_areas/vector_greenhouses_mask_{year}',
            'potential_crops': f'training_areas/vector_potential_crops_mask_{year}',
            'rainfed_trees_crops': f'training_areas/vector_rainfed_trees_crops_mask_{year}',
            'natural_trees': f'training_areas/vector_natural_trees_mask_{year}',
        }

        for key in crop_data_collection:
            for combo in stats_combos:
                crop_data_image = crop_data_collection[key]

                bands_to_select = ['red', 'green', 'blue', '.*std.*', 'slope']
                stat_bands = [f'.*{s}.*' for s in list(combo)]
                bands_to_select += stat_bands

                crop_data_image = crop_data_image.select(bands_to_select)
                classification_name = "_".join(combo)

                if 'summer' in key:
                    classification_name += '_summer'
                elif 'winter' in key:
                    classification_name += '_winter'
                else:
                    classification_name += '_year'

                classify_irrigated_areas(crop_data_image, classification_name, vector_collection, cdc_coordinates, year_string=year,
                                     clf='random_forest', no_trees=250, bag_fraction=.6, vps=2)


