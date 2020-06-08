import ee
from . import landsat
from . import sentinel
from . import indices
from .export import export_to_asset
from .hydrology import add_twi
from .constants import GEE_USER_PATH
from .vector import split_region
from . import visualization
from gee_functions import thresholds

FRACTION = .20


def get_fraction_training_pixels(obj):
    return ee.Number(ee.Dictionary(obj).get('count')).multiply(FRACTION).toInt()


def get_count(obj):
    return ee.Number(ee.Dictionary(obj).get('count'))


def create_features(year, aoi, aoi_name, year_string, season='year', collection='Landsat'):
    """
    Exports the features need for classification to the GEE as assets. The assets will later be loaded in
    during classification.

    :param year: Tuple containing the begin and end date for the selection of imagery.
    :param aoi: GEE Featurecollection of the area of interest.
    :param name_string: String with the last two numbers of the year being observed, e.g. '88'.
    :param season: String indicating the season for which the data is extracted, either summer, winter or year
    refers to an image containing all the features for classification, i.e. spectral indices and slope
    """

    # Extract the date range for the period from the dictionary
    begin = year[0]
    end = year[1]

    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']

    if collection == 'landsat':
        scale = 30
        # Retrieve landsat 5 and 7 imagery for the period and merge them together
        ls_5 = landsat.get_ls5_image_collection(begin, end, aoi)
        ls_7 = landsat.get_ls7_image_collection(begin, end, aoi)
        ls_8 = landsat.get_ls8_image_collection(begin, end, aoi)

        col = ls_5.merge(ls_7).merge(ls_8).map(landsat.remove_edges)

    elif collection == 'sentinel':
        scale = 10
        col = sentinel.get_s2_image_collection(begin, end, aoi)

    col_monthly = landsat.create_monthly_index_images_v2(
        image_collection=col,
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['median']
    )

    col_monthly = col_monthly.select(
        ['R', 'G', 'B', 'NIR', 'SWIR', 'THERMAL', 'SWIR2'])

    col_monthly = col_monthly.map(indices.add_gcvi).filter(ee.Filter.listContains('system:band_names', 'GCVI')) \
        .map(indices.add_ndvi).filter(ee.Filter.listContains('system:band_names', 'NDVI')) \
        .map(indices.add_ndwi).filter(ee.Filter.listContains('system:band_names', 'NDWI')) \
        .map(indices.add_ndwi_swir_2).filter(ee.Filter.listContains('system:band_names', 'NDWI2')) \
        .map(indices.add_ndwi_mcfeeters).filter(ee.Filter.listContains('system:band_names', 'NDWIGH')) \
        .map(indices.add_ndbi).filter(ee.Filter.listContains('system:band_names', 'NDBI')) \
        .map(indices.add_wgi).filter(ee.Filter.listContains('system:band_names', 'WGI')) \
        .map(indices.add_savi).filter(ee.Filter.listContains('system:band_names', 'SAVI'))

    twi = add_twi().clip(aoi)

    # Finally calculate the slope for the area of interest
    slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003").select('elevation')).clip(aoi).rename('slope')

    # Based on class analysis the pixecol for classes can be obtained by applying thresholds.
    # Next up the masks for each class will be created.

    # Create an image out of all the feature maps created. This Image will be used for classification and training
    if season == 'summer':
        col_monthly_season = col_monthly.filter(ee.Filter.rangeContains('month', 4, 9))
    elif season == 'winter':
        early_filter = ee.Filter.rangeContains('month', 1, 3)
        late_filter = ee.Filter.rangeContains('month', 10, 12)
        col_monthly_season = col_monthly.filter(ee.Filter.Or(early_filter, late_filter))

    col_mean_monthly_median_blue = col_monthly_season.select('B').mean().rename('blue')
    col_mean_monthly_median_green = col_monthly_season.select('G').mean().rename('green')
    col_mean_monthly_median_red = col_monthly_season.select('R').mean().rename('red')
    col_mean_monthly_median_nir = col_monthly_season.select('NIR').mean().rename('nir')
    col_mean_monthly_median_swir_1 = col_monthly_season.select('SWIR').mean().rename('swir1')
    col_mean_monthly_median_swir_2 = col_monthly_season.select('SWIR2').mean().rename('swir2')

    col_mean_monthly_median_ndvi = col_monthly_season.select('NDVI').mean()
    col_max_monthly_median_ndvi = col_monthly_season.select('NDVI').max()
    col_min_monthly_median_ndvi = col_monthly_season.select('NDVI').reduce(ee.Reducer.percentile([20]))

    col_mean_monthly_median_gcvi = col_monthly_season.select('GCVI').mean()
    col_max_monthly_median_gcvi = col_monthly_season.select('GCVI').max()
    col_min_monthly_median_gcvi = col_monthly_season.select('GCVI').reduce(ee.Reducer.percentile([20]))

    col_mean_monthly_median_ndwi = col_monthly_season.select('NDWI').mean()
    col_max_monthly_median_ndwi = col_monthly_season.select('NDWI').max()
    col_min_monthly_median_ndwi = col_monthly_season.select('NDWI').reduce(ee.Reducer.percentile([20]))

    col_mean_monthly_median_ndwi2 = col_monthly_season.select('NDWI2').mean()
    col_max_monthly_median_ndwi2 = col_monthly_season.select('NDWI2').max()
    col_min_monthly_median_ndwi2 = col_monthly_season.select('NDWI2').reduce(ee.Reducer.percentile([20]))

    col_mean_monthly_median_wgi = col_monthly_season.select('WGI').mean()
    col_max_monthly_median_wgi = col_monthly_season.select('WGI').max()
    col_min_monthly_median_wgi = col_monthly_season.select('WGI').reduce(ee.Reducer.percentile([20]))

    col_mean_monthly_median_savi = col_monthly_season.select('SAVI').mean()
    col_max_monthly_median_savi = col_monthly_season.select('SAVI').max()
    col_min_monthly_median_savi = col_monthly_season.select('SAVI').reduce(ee.Reducer.percentile([20]))

    col_mean_monthly_mean_ndbi = col_monthly_season.select('NDBI').mean()
    col_max_monthly_median_ndbi = col_monthly_season.select('NDBI').max()
    col_min_monthly_median_ndbi = col_monthly_season.select('NDBI').reduce(ee.Reducer.percentile([20]))

    col_mean_monthly_median_ndwi_greenhouses = col_monthly_season.select('NDWIGH').mean()
    col_max_monthly_median_ndwi_greenhouses = col_monthly_season.select('NDWIGH').max()
    col_min_monthly_median_ndwi_greenhouses = col_monthly_season.select('NDWIGH').min()

    # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
    std_ndvi = landsat.get_yearly_band_std(
        col_monthly,
        ['NDVI'],
        begin,
        end,
        aoi,
        season=season
    )

    std_ndwi = landsat.get_yearly_band_std(
        col_monthly,
        ['NDWI'],
        begin,
        end,
        aoi,
        season=season
    )

    std_gcvi = landsat.get_yearly_band_std(
        col_monthly,
        ['GCVI'],
        begin,
        end,
        aoi,
        season=season
    )

    std_wgi = landsat.get_yearly_band_std(
        col_monthly,
        ['WGI'],
        begin,
        end,
        aoi,
        season=season
    )

    ndvi_std_mean = std_ndvi.select('NDVI_std').mean()
    ndwi_std_mean = std_ndwi.select('NDWI_std').mean()
    gcvi_std_mean = std_gcvi.select('GCVI_std').mean()
    wgi_std_mean = std_wgi.select('WGI_std').mean()

    feature_bands = [
        col_mean_monthly_median_blue,
        col_mean_monthly_median_green,
        col_mean_monthly_median_red,
        col_mean_monthly_median_nir,
        col_mean_monthly_median_swir_1,
        col_mean_monthly_median_swir_2,
        col_min_monthly_median_gcvi.rename('GCVI_min'),
        col_mean_monthly_median_gcvi.rename('GCVI_median'),
        col_max_monthly_median_gcvi.rename('GCVI_max'),
        col_min_monthly_median_ndvi.rename('NDVI_min'),
        col_mean_monthly_median_ndvi.rename('NDVI_median'),
        col_max_monthly_median_ndvi.rename('NDVI_max'),
        col_min_monthly_median_ndwi.rename('NDWI_min'),
        col_mean_monthly_median_ndwi.rename('NDWI_median'),
        col_max_monthly_median_ndwi.rename('NDWI_max'),
        # col_mean_monthly_median_ndwi2.rename('NDWI2_min'),
        # col_max_monthly_median_ndwi2.rename('NDWI2_median'),
        # col_min_monthly_median_ndwi2.rename('NDWI2_max'),
        col_min_monthly_median_wgi.rename('WGI_min'),
        col_mean_monthly_median_wgi.rename('WGI_median'),
        col_max_monthly_median_wgi.rename('WGI_max'),
        col_min_monthly_median_ndwi_greenhouses.rename('NDWIGH_min'),
        col_mean_monthly_median_ndwi_greenhouses.rename('NDWIGH_median'),
        col_max_monthly_median_ndwi_greenhouses.rename('NDWIGH_max'),
        col_min_monthly_median_ndbi.rename('NDBI_min'),
        col_mean_monthly_mean_ndbi.rename('NDBI_median'),
        col_max_monthly_median_ndbi.rename('NDBI_max'),
        # col_min_monthly_median_savi.rename('SAVI_min'),
        # col_mean_monthly_median_savi.rename('SAVI_median'),
        # col_max_monthly_median_savi.rename('SAVI_max'),
        ndvi_std_mean.rename('NDVI_std'),
        gcvi_std_mean.rename('GCVI_std'),
        ndwi_std_mean.rename('NDWI_std'),
        wgi_std_mean.rename('WGI_std'),
        twi.rename('TWI'),
        slope
    ]

    # if collection == 'landsat':
    #     col_mean_monthly_median_thermal = col_monthly_season.select('THERMAL').mean().rename('thermal')
    #     feature_bands += [col_mean_monthly_median_thermal]

    crop_data_min_mean_max = ee.ImageCollection(feature_bands).toBands()

    try:
        task = export_to_asset(
            crop_data_min_mean_max,
            'image',
            f"data/{aoi_name}/{collection}/crop_data_{season}_{aoi_name}_{year_string}",
            aoi_coordinates,
            scale=scale
        )
    except FileExistsError as e:
        print(e)
        return True
    else:
        return task


def create_training_areas(aoi, data_image, aoi_name, year_string, season=None, clf_folder=None, hb=False, vt=False, ft=False):
    """
    Creates a map containing the training areas for classification using thresholding.

    :param aoi: GEE FeatureCollection containing a polygon of the area of interest
    :param data_image: GEE Image containing the feature data from used to select the traning areas
    :param aoi_name: name of the area of interest
    :param year_string: year for which the traninig areas are selected
    :param season: season for which the training areas are selected
    :param user_path: GEE user path to which the training areas will be exported
    :param clf_folder: Optional folder for storing the training areas
    :return: GEE export task
    """
    if not season in ['summer', 'winter']:
        raise ValueError('unknown season string, please enter either "winter" or "summer"')

    if clf_folder is None:
        loc = f"training_areas/{aoi_name}/training_areas_{season}_{aoi_name}_{year_string}"
    else:
        loc = f"training_areas/{aoi_name}/{clf_folder}/training_areas_{season}_{aoi_name}_{year_string}"

    habitats = ee.FeatureCollection('WCMC/WDPA/current/polygons') \
        .filterBounds(aoi) \
        .filter(ee.Filter.eq('DESIG_ENG', 'Site of Community Importance (Habitats Directive)'))
    habitats_mask = ee.Image(1).paint(habitats, 0)

    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']
    if season == 'summer':

        mask_potential_crops = data_image.select('slope').lte(5).And(
            data_image.select('NDVI_median').gt(.2))

        if vt:
            mask_irrigated_crops = data_image.select('slope').lte(4).And(
                data_image.select('WGI_median').gte(.04)).And(
                data_image.select('WGI_std').gte(.25)).And(
                data_image.select('NDWIGH_median').lt(-.28)).And(
                data_image.select('NDWIGH_median').gt(-.45)).And(
                data_image.select('NDWIGH_min').gt(-.5))

            mask_irrigated_trees = data_image.select('slope').lte(4).And(
                data_image.select('WGI_min').gt(-.05)).And(
                data_image.select('NDBI_min').lt(-.1)).And(
                data_image.select('NDWI_std').lt(.1)).And(
                data_image.select('NDWIGH_median').lt(-.3)).And(
                data_image.select('NDWIGH_median').gt(-.4))
        else:
            mask_irrigated_crops = data_image.select('slope').lte(4).And(
                data_image.select('WGI_median').gte(.04)).And(
                data_image.select('WGI_std').gte(.25))

            mask_irrigated_trees = data_image.select('slope').lte(4).And(
                data_image.select('WGI_min').gt(-.05)).And(
                data_image.select('NDBI_min').lt(-.1)).And(
                data_image.select('NDWI_std').lt(.1))

        if hb:
            mask_irrigated_crops = mask_irrigated_crops.updateMask(habitats_mask)
            mask_irrigated_trees = mask_irrigated_trees.updateMask(habitats_mask)

        blue_threshold = ee.Number(data_image.select('blue').reduceRegion(
            reducer=ee.Reducer.percentile([97]),
            geometry=aoi,
            scale=30,
            tileScale=4,
            maxPixels=1e13
        ).get('blue'))

        mask_greenhouses = data_image.select('slope').lte(5).And(
            data_image.select('NDWIGH_median').gt(-.22)).And(
            data_image.select('NDWIGH_median').lt(-.06)).And(
            data_image.select('blue').gte(blue_threshold)).And(
            data_image.select('NDWI_median').gt(.04)
        )

        # mask_rainfed_trees = data_image.select('slope').lte(5).And(
        #     data_image.select('swir').gt(2500)).And(
        #     data_image.select('NDWI_std').lt(.1)).And(
        #     data_image.select('WGI_min').lt(-.05)).And(
        #     data_image.select('WGI_std').lt(.3))
        #
        # mask_rainfed_crops = data_image.select('slope').lte(5).And(
        #     data_image.select('swir').gt(3000)).And(
        #     data_image.select('NDWI_std').gt(.1)).And(
        #     data_image.select('WGI_min').lt(-.05)).And(
        #     data_image.select('WGI_std').lt(.3))

        mask_rainfed_trees_crops = data_image.select('slope').lte(4).And(
            data_image.select('NDBI_min').gte(0)).And(
            data_image.select('NDBI_min').lte(0.1)).And(
            data_image.select('WGI_std').gte(.1)).And(
            data_image.select('WGI_std').lte(.4)).And(
            data_image.select('WGI_min').lt(-.05)).And(
            data_image.select('NDWI_std').lt(.15))

        mask_natural_trees = data_image.select('slope').gt(5).And(
            data_image.select('NDVI_min').gt(.2))

        mask_scrubs = data_image.select('slope').gt(5).And(
            data_image.select('NDWI_std').gte(.05)).And(
            data_image.select('NDWI_std').lte(.18)).And(
            data_image.select('WGI_median').gte(-.1)).And(
            data_image.select('WGI_median').lte(0)
        )

        mask_water = data_image.select('NDWIGH_median').gt(.4)

        mask_urban = data_image.select('slope').lte(4).And(
                data_image.select('NDWIGH_min').gt(-.4)).And(
                data_image.select('NDWIGH_min').lt(-.25)).And(
                data_image.select('swir2').gt(2000)).And(
                data_image.select('swir2').lt(3500)).And(
                data_image.select('NDBI_median').gt(0)).And(
                data_image.select('NDBI_median').lt(.2)).And(
                data_image.select('WGI_std').lt(.25))

        landCover = ee.Image('COPERNICUS/CORINE/V20/100m/2018').select('landcover')
        mask_urban = mask_urban.updateMask(landCover.eq(111))

        training_regions_image = ee.Image(0).where(
            mask_urban.eq(1), 8).where(
            mask_scrubs.eq(1), 2).where(
            mask_natural_trees.eq(1), 1).where(
            mask_rainfed_trees_crops.eq(1), 3).where(
            mask_greenhouses.eq(1), 4).where(
            mask_irrigated_crops.eq(1), 5).where(
            mask_irrigated_trees.eq(1), 6).where(
            mask_water.eq(1), 7).clip(aoi).rename('training')

        if ft:
            training_regions_mask = training_regions_image.connectedPixelCount(25) \
                .reproject(data_image.projection()).gte(25)

            training_regions_image = training_regions_image.where(training_regions_mask.eq(0), 0)

        training_regions_image = training_regions_image.addBands(
            mask_potential_crops.rename('classification_area'))

        try:
            task = export_to_asset(
                training_regions_image,
                'image',
                loc,
                aoi_coordinates
            )
        except FileExistsError as e:
            print(e)
            return True
        else:
            return task

    elif season == 'winter':

        mask_potential_crops = data_image.select('slope').lte(5).And(
            data_image.select('NDVI_max').gte(.28))

        mask_irrigated_crops = data_image.select('slope').lte(4).And(
            data_image.select('WGI_median').gte(.29)).And(
            data_image.select('NDVI_std').gte(.1)).And(
            data_image.select('NDWIGH_median').lt(-.28)
        )

        mask_irrigated_trees = data_image.select('slope').lte(4).And(
            data_image.select('WGI_min').gt(.1)).And(
            data_image.select('NDWIGH_median').lt(-.28)).And(
            data_image.select('swir2').gt(900)
        )

        if hb:
            mask_irrigated_crops = mask_irrigated_crops.updateMask(habitats_mask)
            mask_irrigated_trees = mask_irrigated_trees.updateMask(habitats_mask)

        blue_threshold = ee.Number(data_image.select('blue').reduceRegion(
            reducer=ee.Reducer.percentile([97]),
            geometry=aoi,
            scale=30,
            tileScale=4,
            maxPixels=1e13
        ).get('blue'))

        mask_greenhouses = data_image.select('slope').lte(5).And(
            data_image.select('NDWIGH_median').gt(-.2)).And(
            data_image.select('NDWIGH_median').lt(.1)).And(
            data_image.select('blue').gte(blue_threshold)).And(
            data_image.select('NDWI_median').gt(.04))

        mask_rainfed_trees_and_crops = data_image.select('slope').lte(4).And(
            data_image.select('WGI_std').gte(0)).And(
            data_image.select('WGI_std').lte(.18)).And(
            data_image.select('WGI_min').lt(-.1)).And(
            data_image.select('NDWI_std').lt(.07))

        mask_natural_trees = data_image.select('slope').gt(5).And(
            data_image.select('NDVI_min').gt(.2)
        )

        mask_scrubs = data_image.select('slope').gt(5).And(
            data_image.select('NDWI_std').gte(0)).And(
            data_image.select('NDWI_std').lte(.08)).And(
            data_image.select('WGI_median').gte(-.1)).And(
            data_image.select('WGI_median').lte(0.05)
        )

        mask_water = data_image.select('NDWIGH_median').gt(.4)

        mask_urban = data_image.select('NDWIGH_min').gt(-.4).And(
            data_image.select('NDWIGH_min').lt(-.25)).And(
            data_image.select('swir2').gt(1500)).And(
            data_image.select('NDBI_median').gt(0))

        landCover = ee.Image('COPERNICUS/CORINE/V20/100m/2018').select('landcover')
        mask_urban = mask_urban.updateMask(landCover.eq(111))

        training_regions_image = ee.Image(0).where(
            mask_urban.eq(1), 8).where(
            mask_scrubs.eq(1), 2).where(
            mask_natural_trees.eq(1), 1).where(
            mask_rainfed_trees_and_crops, 3).where(
            mask_greenhouses.eq(1), 4).where(
            mask_irrigated_crops.eq(1), 5).where(
            mask_irrigated_trees.eq(1), 6).where(
            mask_water.eq(1), 7).clip(aoi).rename('training')

        if ft:
            training_regions_mask = training_regions_image.updateMask(training_regions_image.gt(0)) \
                .connectedPixelCount(25).reproject(data_image.projection()).gte(25)

            training_regions_image = training_regions_image.where(training_regions_mask.eq(0), 0)

        training_regions_image = training_regions_image.addBands(
            mask_potential_crops.rename('classification_area'))

        try:
            task = export_to_asset(
                training_regions_image,
                'image',
                loc,
                aoi_coordinates
            )
        except FileExistsError as e:
            print(e)
            return True
        else:
            return task


def remove_outliers(sample, bandnames, classes):
    filtered_sample = None

    for cl in classes:
        class_sample = sample.filter(ee.Filter.eq('training', cl))
        mean = class_sample.reduceColumns(
            reducer=ee.Reducer.mean().repeat(bandnames.size()),
            selectors=bandnames
        ).get('mean')

        std = class_sample.reduceColumns(
            reducer=ee.Reducer.stdDev().repeat(bandnames.size()),
            selectors=bandnames
        ).get('stdDev')

        def calc_z_score(x):
            return ee.Array(x).subtract(ee.Array(mean)).divide(ee.Array(std))

        def add_z_score(feat):
            properties = ee.Feature(feat).toArray(bandnames)
            z = calc_z_score(properties)
            outlier = z.gte(3).Or(z.lte(-3)).toList().contains(1)
            return feat.set('outlier', outlier).set('z_scores', z)

        class_sample = class_sample.map(add_z_score)
        if filtered_sample is None:
            filtered_sample = class_sample
        else:
            filtered_sample = filtered_sample.merge(class_sample)

    return filtered_sample.filter(ee.Filter.eq('outlier', False)).filter(
        ee.Filter.notNull(bandnames))


def classify_irrigated_areas(training_image, training_areas, aoi, data_info, aoi_name=None, year=None,
                             clf_folder=None, min_tp=1000, max_tp=60000, tile_scale=16,
                             clf='random_forest', no_trees=500, bag_fraction=.5, vps=2, ro=False):
    """
    Performs a classification using pixels within the class regions obtained via thresholding as training data.
    Classification is performed on the GEE servers and results are exported to Google Drive connected to the GEE
    user account.

    :param training_image: GEE image containing all the feature data for classification.
    :param data_info: metadata regarding the feature data, used for naming the classification.
    :param vector_collection: dictionary containing the assetIds of the vector of each class.
    :param aoi: Featurecollection representing the area of interest.
    :param name_string: year of observation, used for naming of the results.
    :param clf: classifier type, either bayes or random forest.
    :param no_trees: In case of random forest the number of trees to use for classificaiton.
    :param bag_fraction: In case of random forest the bag fraction to use for classificaiton.
    :param vps: In case of random forest the variables per split to use for classificaiton.
    """

    if clf_folder is None:
        loc = f"results/random_forest/{aoi_name}/ia_{clf}_{data_info}_{no_trees}tr_{vps}vps_{int(bag_fraction * 100)}bf_{aoi_name}_{year}"
    else:
        loc = f"results/random_forest/{aoi_name}/{clf_folder}/ia_{clf}_{data_info}_{no_trees}tr_{vps}vps_{int(bag_fraction * 100)}bf_{aoi_name}_{year}"

    class_property = 'training'
    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']

    class_values = [1, 2, 3, 4, 5, 6, 7, 8]
    min_training_pixels = ee.Array([min_tp, min_tp, min_tp, min_tp, min_tp, min_tp, min_tp, min_tp])
    max_training_pixels = ee.Array([max_tp, max_tp, max_tp, max_tp, max_tp, max_tp, max_tp, max_tp])

    class_count = ee.List(training_areas.updateMask(training_areas.select('training').gt(0)).reduceRegion(
        reducer=ee.Reducer.count().group(
            groupField=0,
            groupName='class',
        ),
        geometry=aoi,
        scale=30,
        maxPixels=1e13
    ).get('groups'))

    class_points = class_count.map(get_fraction_training_pixels)

    # total_pixels = training_areas.select('training').updateMask(training_areas.select('training').gt(0)).reduceRegion(
    #     reducer=ee.Reducer.count(),
    #     geometry=aoi,
    #     scale=30,
    #     maxPixels=1e13
    # ).get('training')

    # max_pixels = ee.Number(26214400).divide(ee.Number(training_image.bandNames().length())).multiply(.95).toInt()
    # max_pixels_per_class = ee.Array(class_count.map(get_count)).divide(total_pixels).multiply(max_pixels).toInt()

    class_points = ee.Array(class_points).min(max_training_pixels)
    class_points = ee.Array(class_points).max(min_training_pixels)

    bands = training_image.bandNames()
    training_image = training_image.addBands(training_areas)

    training_multiclass = training_image.updateMask(training_image.select('training').gt(0)) \
        .stratifiedSample(
        numPoints=1000,
        classBand=class_property,
        scale=30,
        classValues=ee.List(class_values),
        classPoints=class_points.toList(),
        region=aoi.geometry(),
        tileScale=tile_scale
    )

    if ro:
        training_multiclass = remove_outliers(training_multiclass, training_image.bandNames(), class_values)

    if clf == 'random_forest':
        # Train classifier for the multiclass classification
        classifier_multiclass = ee.Classifier.smileRandomForest(
            no_trees,
            variablesPerSplit=vps,
            bagFraction=bag_fraction,
            minLeafPopulation=10,
        ).train(
            training_multiclass,
            class_property,
            bands
        )

        # ee.batch.Export.table.toDrive(
        #     collection=ee.FeatureCollection(ee.Feature(None, classifier_multiclass.confusionMatrix())),
        #     description=f'confusion_matrix_tf_hb_vt_slope',
        #     fileFormat='CSV'
        # ).start()

        # region_tiles = vector.split_region(ee.FeatureCollection(f'{GEE_USER_PATH}/vector/{vector_collection["potential_crops"]}'))
        # for tile in region_tiles:

    if clf == 'cart':
        # Train classifier for the multiclass classification
        classifier_multiclass = ee.Classifier.smileCart(
            minLeafPopulation=10,
        ).train(
            training_multiclass,
            class_property,
            training_image.bandNames()
        )

    if clf == 'bayes':
        # Train classifier for the multiclass classification
        classifier_multiclass = ee.Classifier.smileNaiveBayes(
        ).train(
            training_multiclass,
            class_property
        )

    # Get mask of areas were forest loss has occurred in the period.
    forest_change = ee.Image("UMD/hansen/global_forest_change_2018_v1_6").select('lossyear').clip(aoi)

    if int(year[-2:]) in range(1, 19):
        forest_change_mask = forest_change.eq(ee.Number(int(year[-2:])))
        # Classify the unknown area based on the crop data using the multiclass classifiers
        irrigated_area_classified_multiclass = training_image \
            .classify(classifier_multiclass) \
            .where(forest_change_mask.eq(1), 10) \
            .toByte()
    else:
        # Classify the unknown area based on the crop data using the multiclass classifiers
        irrigated_area_classified_multiclass = training_image \
            .classify(classifier_multiclass) \
            .toByte()

    irrigated_areas = ee.Image(0).toByte() \
        .where(irrigated_area_classified_multiclass.select('classification').eq(5), 1) \
        .where(irrigated_area_classified_multiclass.select('classification').eq(6), 2)

    mask_small_patches_removed = irrigated_areas.updateMask(irrigated_areas.gt(0)) \
        .connectedPixelCount(4).reproject(training_image.projection()).gte(4)

    irrigated_areas = irrigated_areas.where(mask_small_patches_removed.eq(0), 0)

    irrigated_results = ee.ImageCollection([
        irrigated_areas.rename('irrigated_area'),
        irrigated_area_classified_multiclass.rename('rf_all_classes'),
        training_image.select('training'),
    ]).toBands().regexpRename('([0-9]{1,3}_)', '')

    # export_task_ext = ee.batch.Export.image.toDrive(
    #     image=irrigated_results,
    #     description=f'ia_{clf}_{data_info}_{no_trees}tr_{vps}vps_{int(bag_fraction * 100)}bf_{aoi_name}_{year}',
    #     folder=f'{clf}_{aoi_name}_{year}',
    #     scale=30,
    #     region=aoi_coordinates,
    #     maxPixels=1e13,
    # )
    # export_task_ext.start()

    try:

        task = export_to_asset(
            irrigated_results,
            'image',
            loc,
            aoi_coordinates
        )
    except FileExistsError as e:
        print(e)
        return True
    else:
        return task


def join_seasonal_irrigated_areas(irrigated_area_summer, irrigated_area_winter, aoi_name, year, aoi_coordinates,
                                  export_method='drive', clf_folder=None, info=''):
    if clf_folder is None:
        loc = f"results/irrigated_area/{aoi_name}/irrigated_areas_{aoi_name}_{year}"
    else:
        loc = f"results/irrigated_area/{aoi_name}/{clf_folder}/irrigated_areas_{aoi_name}_{year}"

    summer = ee.Image().constant(1).where(irrigated_area_summer.eq(1), 3).where(irrigated_area_summer.eq(2), 2)
    winter = ee.Image().constant(1).where(irrigated_area_winter.eq(1), 4).where(irrigated_area_winter.eq(2), 5)

    combined_irrigated_area_map = summer.multiply(winter)

    combined_irrigated_area_map = ee.Image(0) \
        .where(combined_irrigated_area_map.eq(10), 1) \
        .where(combined_irrigated_area_map.eq(12), 2) \
        .where(combined_irrigated_area_map.eq(2), 3) \
        .where(combined_irrigated_area_map.eq(3), 4) \
        .where(combined_irrigated_area_map.eq(5), 5) \
        .where(combined_irrigated_area_map.eq(4), 6) \
        .where(combined_irrigated_area_map.eq(8), 7) \
        .where(combined_irrigated_area_map.eq(15), 7)

    results = ee.ImageCollection([
        combined_irrigated_area_map.rename('ia_year'),
        irrigated_area_summer.rename('ia_summer'),
        irrigated_area_winter.rename('ia_winter'),
    ]).toBands()

    if export_method == 'drive':
        export_task_ext = ee.batch.Export.image.toDrive(
            image=results,
            description=f'ia_{info}{year}',
            folder=loc.replace('/', '_'),
            scale=30,
            region=aoi_coordinates,
        )
        task = export_task_ext.start()
        return task
    elif export_method == 'asset':
        try:
            task = export_to_asset(
                results,
                'image',
                loc,
                aoi_coordinates
            )
        except FileExistsError as e:
            print(e)
            return True
        else:
            return task
