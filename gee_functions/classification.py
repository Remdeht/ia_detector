"""
All the functions used in the classification process of the irrigated area detector
"""

import ee

try:
    import landsat
    import sentinel
    import indices
    from export import export_to_asset
    from hydrology import add_mti
except ImportError:
    from . import landsat
    from . import sentinel
    from . import indices
    from .export import export_to_asset
    from .hydrology import add_mti

from typing import Union


def get_fraction_training_pixels(obj):
    """Calculates a fraction of the total number of pixels for the all the patches generated for a land cover class"""
    fraction = .20
    return ee.Number(ee.Dictionary(obj).get('count')).multiply(fraction).toInt()


def get_count(obj):
    """Returns the number of pixels of the patches per land cover class"""
    return ee.Number(ee.Dictionary(obj).get('count'))


def create_feature_data(
        date_range: tuple,
        aoi: ee.FeatureCollection,
        creation_method: str='all_scenes_reduced',
        aoi_name: str = 'undefined',
        sensor: str = 'landsat',
        custom_name: str = None,
        overwrite: bool = False) -> ee.batch.Task or bool:
    """
    Creates and exports the feature data for classification to the GEE as two image assets (feature data for summer and
    winter).

    :param date_range: tuple containing the begin and end date for the selection of imagery. Date format: YYYY-MM-DD.
    :param aoi: EE FeatureCollection of the vector representing the area of interest
    :param aoi_name: name of the aoi, this is used for the naming of the results
    :param sensor: string indicating which satellite to use, landsat or sentinel
    :param custom_name: Optional, provide a name for the asset. If no custom name is given the year of the start date
    will be used
    :param overwrite: Optional, provide a name for the asset. If no custom name is given the year of the start date
    will be used
    :return: dictionary containing two GEE export tasks
    """

    # Extract the date range for the period from the tuple
    begin = date_range[0]
    end = date_range[1]

    year_string = end[0:4]  # string with the year for the naming of the assets

    aoi_info = aoi.geometry().getInfo()

    if 'coordinates' in aoi_info.keys():
        aoi_coordinates = aoi_info['coordinates']  # aoi coordinates

        if len(aoi_coordinates) > 1:
            aoi_coordinates = ee.Geometry.MultiPolygon(aoi_coordinates)
        else:
            aoi_coordinates = ee.Geometry.Polygon(aoi_coordinates)

    else:
        return None

    if sensor == 'landsat':
        scale = 30
        # Retrieve landsat 5 and 7 imagery for the period and merge them together
        ls_5 = landsat.get_ls_image_collection('5', begin, end, aoi)
        ls_7 = landsat.get_ls_image_collection('7', begin, end, aoi)
        ls_8 = landsat.get_ls_image_collection('8', begin, end, aoi)
        ls_9 = landsat.get_ls_image_collection('9', begin, end, aoi)

        col = ls_5.merge(ls_7).merge(ls_8).merge(ls_9).map(
            landsat.remove_edges)  # merge all the landsat scenes into single col.

        if creation_method in ['monthly_composites_reduced', 'monthly_composites']:
            # create monthly band composites
            col = landsat.create_monthly_index_images(
                image_collection=col,
                start_date=begin,
                end_date=end,
                aoi=aoi,
                stats=['median'],
            )

    elif sensor == 'sentinel':
        scale = 10
        col = sentinel.get_s2_image_collection(begin, end, aoi)

        # col = sentinel.create_monthly_index_images(
        #     image_collection=col,
        #     start_date=begin,
        #     end_date=end,
        #     aoi=aoi,
        #     stats=['median'],
        # )
    else:
        raise ValueError(f'Provided unknown sensor: {sensor}')

    col = col.select(['R_*', 'G_*', 'B_*', 'NIR_*', 'SWIR_*'])  # Select these RGB, NIR and SWIR bands

    col = col.map(indices.add_gcvi).filter(
        ee.Filter.listContains('system:band_names', 'GCVI')) \
        .map(indices.add_ndvi).filter(ee.Filter.listContains('system:band_names', 'NDVI')) \
        .map(indices.add_ndwi).filter(ee.Filter.listContains('system:band_names', 'NDWI')) \
        .map(indices.add_ndwi_mcfeeters).filter(ee.Filter.listContains('system:band_names', 'NDWBI')) \
        .map(indices.add_ndbi).filter(ee.Filter.listContains('system:band_names', 'NDBI')) \
        .map(indices.add_wgi).filter(ee.Filter.listContains('system:band_names', 'WGI')) \
        .map(indices.add_evi).filter(ee.Filter.listContains('system:band_names', 'EVI')) \
        .map(indices.add_savi).filter(ee.Filter.listContains('system:band_names', 'SAVI'))

    mti = add_mti()
    slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003").select('elevation')).rename('slope')

    if creation_method in ['monthly_composites_reduced', 'all_scenes_reduced']:

        col_mean = col.mean().regexpRename('(.*)', '$1_mean', False)
        col_median = col.median().regexpRename('(.*)', '$1_median', False)
        col_min = col.min().regexpRename('(.*)', '$1_min', False)
        col_max = col.max().regexpRename('(.*)', '$1_max', False)
        col_p85 = col.reduce(ee.Reducer.percentile([85]))
        col_p15 = col.reduce(ee.Reducer.percentile([15]))
        col_std_dev = col.reduce(ee.Reducer.stdDev())

        feature_data = ee.ImageCollection(
            [
                col_mean,
                col_median,
                col_max,
                col_min,
                col_p85,
                col_p15,
                col_std_dev,
                mti.rename('MTI'),
                slope
            ]
        )
    else:

        def rename_all_bands(image):
            month = image.get('month')
            stat = image.get('stat')
            new_name = ee.String('$1_').cat(stat).cat('_').cat(month)
            return image.regexpRename('(.*)', new_name, False)

        feature_data = col.map(rename_all_bands)

    # flatten all the maps to a single GEE image
    # crop_data_min_mean_max = ee.ImageCollection(feature_bands).toBands().set('sensor', sensor).set('scale', scale)
    feature_data = feature_data.toBands().set(
        'sensor', sensor).set(
        'scale', scale).set(
        'start_date', begin).set(
        'end_date', end).set(
        'aoi', aoi_name)

    if custom_name:
        asset_id = f"data/{aoi_name}/{sensor}/{creation_method}/feature_data_{aoi_name}_{custom_name}"
        feature_data.set('name', custom_name)
    else:
        asset_id = f"data/{aoi_name}/{sensor}/{creation_method}/feature_data_{aoi_name}_{year_string}"
        feature_data.set('name', year_string)

    try:
        task = export_to_asset(  # Export to the GEE account of the user
            asset=feature_data,
            asset_type='image',
            asset_id=asset_id,
            region=aoi_coordinates,
            scale=scale,
            overwrite=overwrite
        )
    except FileExistsError as e:  # if the asset already exists the user is notified and no error is generated
        print(e)
        task = True

    return task  # returns the dictionary with the export tasks


def create_training_areas(aoi, data_loc, aoi_name, year_string, clf_folder=None, hb=True, ft=True):
    """
    Creates a map containing the training areas for classification using thresholding.

    :param aoi: GEE FeatureCollection containing a polygon of the area of interest
    :param aoi_name: name of the area of interest
    :param year_string: year for which the traninig areas are selected
    :param clf_folder: Optional folder for storing the training areas
    :return: GEE export task
    """

    #  Get the coordinates of the area of interest. Will be used for the exporting of results later
    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']

    if hb:  # Creates a mask from WDPA - Habitats Directive for the masking of irrigated land area patches
        habitats = ee.FeatureCollection('WCMC/WDPA/current/polygons') \
            .filterBounds(aoi) \
            .filter(ee.Filter.eq('DESIG_ENG', 'Site of Community Importance (Habitats Directive)'))
        habitats_mask = ee.Image(1).paint(habitats, 0)

    mask_aoi = ee.Image(0).paint(aoi, 1)  # mask of the area of interest

    tasks = {}

    for season in ['summer', 'winter']:

        if clf_folder is None:  # sets the classification folder for export
            loc = f"training_areas/{aoi_name}/training_areas_{season}_{aoi_name}_{year_string}"
        else:
            loc = f"training_areas/{aoi_name}/{clf_folder}/training_areas_{season}_{aoi_name}_{year_string}"

        data_image = ee.Image(data_loc.replace('season', season))

        if season == 'summer':
            # Creates binary images for all land cover classes, named masks, containing pixels that will be used for
            # training the classifier.

            # mask_irrigated_crops = data_image.select('slope').lte(4).And(
            #         data_image.select('WGI_min').lt(0)).And(
            #         data_image.select('WGI_std').gte(.25)).And(
            #         data_image.select('NDWBI_mean').lt(-.28)).And(
            #         data_image.select('NDWBI_mean').gt(-.45)).And(
            #         data_image.select('NDWBI_min').gt(-.5))
            #
            # mask_irrigated_trees = data_image.select('slope').lte(4).And(
            #         data_image.select('WGI_min').gt(-.05)).And(
            #         data_image.select('NDBI_min').lt(-.1)).And(
            #         data_image.select('NDWI_std').lte(.1)).And(
            #         data_image.select('NDWBI_mean').lt(-.3)).And(
            #         data_image.select('NDWBI_mean').gt(-.4))
            #
            # if hb:
            #     # Removes training patches of irrigated land areas from areas within Habitats Sites
            #     # of Community Importance. This is done to remove wetlands from the training patches.
            #     habitats = ee.FeatureCollection('WCMC/WDPA/current/polygons') \
            #         .filterBounds(aoi) \
            #         .filter(ee.Filter.eq('DESIG_ENG', 'Site of Community Importance (Habitats Directive)'))
            #     habitats_mask = ee.Image(1).paint(habitats, 0)
            #
            #     mask_irrigated_crops = mask_irrigated_crops.updateMask(habitats_mask)
            #     mask_irrigated_trees = mask_irrigated_trees.updateMask(habitats_mask)
            #
            # mask_greenhouses = data_image.select('slope').lte(5).And(
            #     data_image.select('NDWBI_mean').gt(-.22)).And(
            #     data_image.select('NDWBI_mean').lt(-.06)).And(
            #     data_image.select('blue').gte(1800)).And(
            #     data_image.select('NDWI_mean').gt(.04)
            # )
            #
            # mask_natural_trees = data_image.select('slope').gt(8).And(
            #     data_image.select('NDVI_min').gt(.2)).And(
            #     data_image.select('WGI_min').lt(0.1))
            #
            # mask_rainfed_trees_crops = data_image.select('slope').lte(4).And(
            #     data_image.select('NDBI_min').gte(0)).And(
            #     data_image.select('NDBI_min').lte(0.1)).And(
            #     data_image.select('WGI_std').gte(.1)).And(
            #     data_image.select('WGI_std').lte(.4)).And(
            #     data_image.select('WGI_min').lt(-.05)).And(
            #     data_image.select('NDWI_std').lt(.15))
            #
            # mask_scrubs = data_image.select('slope').gt(5).And(
            #     data_image.select('NDWI_std').gte(.05)).And(
            #     data_image.select('NDWI_std').lte(.18)).And(
            #     data_image.select('WGI_mean').gte(-.1)).And(
            #     data_image.select('WGI_mean').lte(0)
            # )
            #
            # mask_water = data_image.select('NDWBI_mean').gt(.4)
            #
            # mask_urban = data_image.select('slope').lte(4).And(
            #         data_image.select('NDWBI_min').gt(-.4)).And(
            #         data_image.select('NDWBI_min').lt(-.25)).And(
            #         data_image.select('swir1').gt(2000)).And(
            #         data_image.select('swir1').lt(3500)).And(
            #         data_image.select('NDBI_min').lt(0)).And(
            #         data_image.select('NDBI_min').gt(-.2)).And(
            #         data_image.select('WGI_std').lt(.25))

            mask_irrigated_crops = data_image.select('slope').lte(4).And(
                data_image.select('WGI_min').lt(-.05)).And(
                data_image.select('WGI_std').gte(.1)).And(
                data_image.select('NDWBI_mean').lt(-.28)).And(
                data_image.select('NDWBI_mean').gt(-.45)).And(
                data_image.select('NDWBI_min').gt(-.5))

            mask_irrigated_trees = data_image.select('slope').lte(4).And(
                data_image.select('WGI_min').gt(0.05)).And(
                data_image.select('NDWBI_mean').lt(-.28)).And(
                data_image.select('NDWBI_mean').gt(-.4))

            if hb:
                # Removes training patches of irrigated land areas from areas within Habitats Sites
                # of Community Importance. This is done to remove wetlands from the training patches.
                habitats = ee.FeatureCollection('WCMC/WDPA/current/polygons') \
                    .filterBounds(aoi) \
                    .filter(ee.Filter.eq('DESIG_ENG', 'Site of Community Importance (Habitats Directive)'))
                habitats_mask = ee.Image(1).paint(habitats, 0)

                mask_irrigated_crops = mask_irrigated_crops.updateMask(habitats_mask)
                mask_irrigated_trees = mask_irrigated_trees.updateMask(habitats_mask)

            mask_greenhouses = data_image.select('slope').lte(5).And(
                data_image.select('NDWBI_mean').gt(-.25)).And(
                data_image.select('NDWBI_mean').lt(-.06)).And(
                data_image.select('blue').gte(1800)).And(
                data_image.select('NDWI_mean').gt(0)
            )

            mask_natural_trees = data_image.select('slope').gt(8).And(
                data_image.select('NDVI_min').gt(.2)).And(
                data_image.select('WGI_min').lt(0.1))

            mask_rainfed_trees_crops = data_image.select('slope').lte(4).And(
                data_image.select('NDBI_min').gte(0.05)).And(
                data_image.select('NDBI_min').lte(0.15)).And(
                data_image.select('WGI_std').lte(.05)).And(
                data_image.select('WGI_min').lt(-.05)).And(
                data_image.select('NDWI_std').lt(.05))

            mask_scrubs = data_image.select('slope').gt(5).And(
                data_image.select('NDWI_std').gte(0)).And(
                data_image.select('NDWI_std').lte(.05)).And(
                data_image.select('WGI_mean').gte(-.15)).And(
                data_image.select('WGI_mean').lte(0)).And(
                data_image.select('nir').gte(1700)).And(
                data_image.select('nir').lte(2700))

            mask_water = data_image.select('NDWBI_mean').gt(.4)

            mask_urban = data_image.select('slope').lte(4).And(
                data_image.select('NDWBI_min').gt(-.4)).And(
                data_image.select('NDWBI_min').lt(-.25)).And(
                data_image.select('swir1').gt(2000)).And(
                data_image.select('swir1').lt(4000)).And(
                data_image.select('NDBI_min').lt(0.1)).And(
                data_image.select('NDBI_min').gt(-.05)).And(
                data_image.select('WGI_std').lt(.05))

            corine_lc = ee.Image('COPERNICUS/CORINE/V20/100m/2018').select('landcover')  # mask of urban areas in Corine
            mask_urban = mask_urban.updateMask(corine_lc.eq(111))  # removes patches outside of urban areas
        else:
            # mask_irrigated_crops = data_image.select('slope').lte(4).And(
            #     data_image.select('WGI_min').lte(0.05)).And(
            #     data_image.select('WGI_std').gte(.2)).And(
            #     data_image.select('NDWBI_mean').lt(-.28)
            # )
            #
            # mask_irrigated_trees = data_image.select('slope').lte(4).And(
            #     data_image.select('WGI_min').gt(.1)).And(
            #     data_image.select('NDWBI_mean').lt(-.28))
            #
            # if hb:
            #     mask_irrigated_crops = mask_irrigated_crops.updateMask(habitats_mask)
            #     mask_irrigated_trees = mask_irrigated_trees.updateMask(habitats_mask)
            #
            # mask_greenhouses = data_image.select('slope').lte(5).And(
            #     data_image.select('NDWBI_mean').gt(-.2)).And(
            #     data_image.select('NDWBI_mean').lt(.1)).And(
            #     data_image.select('blue').gte(2000)).And(
            #     data_image.select('NDWI_mean').gt(.04))
            #
            # mask_rainfed_trees_crops = data_image.select('slope').lte(4).And(
            #     data_image.select('NDBI_min').gte(-.35)).And(
            #     data_image.select('NDBI_min').lte(0.05)).And(
            #     data_image.select('WGI_std').gte(0)).And(
            #     data_image.select('WGI_std').lte(.2)).And(
            #     data_image.select('WGI_min').lt(-.05)).And(
            #     data_image.select('WGI_min').gte(-.13)).And(
            #     data_image.select('NDWI_std').lt(.07))
            #
            # mask_natural_trees = data_image.select('slope').gt(5).And(
            #     data_image.select('NDVI_min').gt(.2))
            #
            # mask_scrubs = data_image.select('slope').gt(5).And(
            #     data_image.select('NDWI_std').gte(0)).And(
            #     data_image.select('NDWI_std').lte(.08)).And(
            #     data_image.select('WGI_mean').gte(-.1)).And(
            #     data_image.select('WGI_mean').lte(0.05)
            # )
            #
            # mask_water = data_image.select('NDWBI_mean').gt(.4)
            #
            # mask_urban = data_image.select('NDWBI_min').gt(-.4).And(
            #     data_image.select('NDWBI_min').lt(-.25)).And(
            #     data_image.select('swir1').gt(1500)).And(
            #     data_image.select('NDBI_mean').gt(0))

            mask_irrigated_crops = data_image.select('slope').lte(4).And(
                data_image.select('WGI_min').lte(0)).And(
                data_image.select('WGI_std').gte(.2)).And(
                data_image.select('NDWBI_mean').lt(-.25)
            )

            mask_irrigated_trees = data_image.select('slope').lte(4).And(
                data_image.select('WGI_min').gt(0.1)).And(
                data_image.select('NDWBI_mean').lt(-.25))

            if hb:
                mask_irrigated_crops = mask_irrigated_crops.updateMask(habitats_mask)
                mask_irrigated_trees = mask_irrigated_trees.updateMask(habitats_mask)

            mask_greenhouses = data_image.select('slope').lte(5).And(
                data_image.select('NDWBI_mean').gt(-.25)).And(
                data_image.select('NDWBI_mean').lt(.1)).And(
                data_image.select('blue').gte(1500)).And(
                data_image.select('NDWI_mean').gt(.04))

            mask_rainfed_trees_crops = data_image.select('slope').lte(4).And(
                data_image.select('NDBI_min').gte(-0.05)).And(
                data_image.select('NDBI_min').lte(0.06)).And(
                data_image.select('WGI_std').gte(0)).And(
                data_image.select('WGI_std').lte(.2)).And(
                data_image.select('WGI_min').lt(-.05)).And(
                data_image.select('WGI_min').gte(-.13)).And(
                data_image.select('NDWI_std').lt(.1))

            mask_natural_trees = data_image.select('slope').gt(8).And(
                data_image.select('NDVI_min').gt(.2)).And(
                data_image.select('nir').lt(2000))

            mask_scrubs = data_image.select('slope').gt(5).And(
                data_image.select('NDWI_std').gte(0)).And(
                data_image.select('NDWI_std').lte(.08)).And(
                data_image.select('WGI_mean').gte(-.1)).And(
                data_image.select('WGI_mean').lte(0.05)
            )

            mask_water = data_image.select('NDWBI_mean').gt(.4)

            mask_urban = data_image.select('NDWBI_min').gt(-.35).And(
                data_image.select('NDWBI_min').lt(-.25)).And(
                data_image.select('swir1').gt(2000)).And(
                data_image.select('NDBI_mean').gt(-.05))

            corine_lc = ee.Image('COPERNICUS/CORINE/V20/100m/2018').select('landcover')
            mask_urban = mask_urban.updateMask(corine_lc.eq(111))

        # Creates an image where pixels belonging to different patches are indicated with a class specific label
        training_regions_image = ee.Image(0).where(
            mask_scrubs.eq(1), 2).where(
            mask_natural_trees.eq(1), 1).where(
            mask_rainfed_trees_crops.eq(1), 3).where(
            mask_greenhouses.eq(1), 4).where(
            mask_irrigated_crops.eq(1), 5).where(
            mask_irrigated_trees.eq(1), 6).where(
            mask_water.eq(1), 7).where(
            mask_urban.eq(1), 8).clip(aoi).rename('training')

        if ft:
            # filters the training patches based on the number of connected pixels. Only patches with 25 connected
            # pixels within a 5-by-5 window are selected. This removes small pixel patches and edge pixels.
            training_regions_mask = training_regions_image.connectedPixelCount(25) \
                .reproject(data_image.projection()).gte(25)

            training_regions_image = training_regions_image.where(training_regions_mask.eq(0), 0)

        training_regions_image = training_regions_image.addBands(
            mask_aoi.rename('area_of_interest'))
        try:
            task = export_to_asset(
                asset=training_regions_image,
                asset_type='image',
                asset_id=loc,
                region=aoi_coordinates,
                scale=data_image.get('scale').getInfo()
            )
        except FileExistsError as e:  # if the asset already exists the user is notified and no error is generated
            print(e)
            tasks[season] = True
        else:
            tasks[season] = task

    return tasks


def classify_irrigated_areas(
        input_features: ee.Image,
        training_areas: ee.Image,
        aoi: ee.FeatureCollection,
        aoi_name: str,
        season: str,
        year: Union[int, str],
        it_cl: int = 1,
        ic_cl: int = 2,
        clf_folder: str = None,
        filename: str = None,
        min_tp: int = 1000,
        max_tp: int = 60000,
        tile_scale: int = 16,
        no_trees: int = 500,
        bag_fraction: float = .5,
        vps: int = 5,
        overwrite: bool = False):
    """
    Performs a RF classification and postprocessing of irrigated land areas as determined by the RF.

    :param input_features: EE Image, feature data used for training and classfication
    :param training_areas: EE Image, map with land cover patches to serve as training sites for the classifier
    :param aoi: EE FeatureCollection, area of interest
    :param aoi_name: string, name of the area of interest, used when saving the results
    :param year: string, year of classification, is used when naming the results
    :param it_cl: int, integer representing pixels belonging to irrigated trees
    :param ic_cl: int, integer representing pixels belonging to irrigated crops
    :param season: string, name of the season being classified
    :param clf_folder: string, name of the folder where the results are to be saved on the GEE, defaults to None
    :param filename: string, name of the asset, if None the default name is used
    :param min_tp: int, minimum number of training points per land cover class to use for classification
    :param max_tp: int, maximum number of training points per land cover class to use for classification
    :param tile_scale: int, A scaling factor used to reduce aggregation tile size, defaults to 16.
    :param no_trees: int, number of trees to use in the random forest, defaults to 500
    :param bag_fraction: float, fraction of training pixels to be left out of the bag for each tree, defaults to 0.5
    :param vps: int, variables per split, indicates how many variables to use per split. Defaults to 5.
    :param overwrite: Boolean, if True it overwrites previous classification result with the same parameters/aoi
    :return: EE task for the export of the classification results to an EE asset & the trained RF Classifier
    """

    # sets up the location where the results of the classification are saved.
    if clf_folder is None and filename is None:  # in case no folder/custom filename have been given
        loc = f"results/random_forest/{aoi_name}/ia_random_forest_{no_trees}tr_{vps}vps_{int(bag_fraction * 100)}bf_{aoi_name}_{season}_{year}"
    elif clf_folder is None:  # only custom filename is given
        loc = f"results/random_forest/{aoi_name}/{filename}"
    else:  # only a folder is given
        loc = f"results/random_forest/{aoi_name}/{clf_folder}/ia_random_forest_{no_trees}tr_{vps}vps_{int(bag_fraction * 100)}bf_{aoi_name}_{season}_{year}"

    class_property = 'training'  # bandname of the band containing the patches from which the training pixels are sampled
    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']  # coordinates of the aoi, needed for export
    scale = input_features.get('scale').getInfo()

    # select the land cover patches for all the land cover classes
    training_areas_masked = training_areas.select('training').updateMask(training_areas.select('training').gt(0))

    # check the class values present in the training image, in case thresholding did not separate patches for a lc class
    # the RF classifier does not consider  it for training
    freq_histogram = training_areas_masked.reduceRegion(ee.Reducer.frequencyHistogram(), aoi, 30, maxPixels=1e15)
    class_values = ee.Dictionary(freq_histogram.get('training')).keys().getInfo()  # gets the unique class labels
    class_values = [int(x) for x in class_values]  # converts the strings to int

    min_training_pixels = ee.Array([min_tp for i in range(0, len(class_values))])  # Array with min
    max_training_pixels = ee.Array([max_tp for i in range(0, len(class_values))])  # and max tps

    class_count = ee.List(training_areas.updateMask(training_areas.select('training').gt(0)).reduceRegion(
        reducer=ee.Reducer.count().group(
            groupField=0,
            groupName='class',
        ),
        geometry=aoi,
        scale=30,
        maxPixels=1e14
    ).get('groups'))  # counts the number of pixels in the patches for each land cover class

    class_points = class_count.map(get_fraction_training_pixels)  # select 20 percent of the pixels per lc class

    # in case the number of pixels is lower or higher than the minimum/maximum number of training pixels, they are
    # replaced by the max/min number of training pixels
    class_points = ee.Array(class_points).min(max_training_pixels)
    class_points = ee.Array(class_points).max(min_training_pixels)

    bands = input_features.bandNames()  # bands to be used as inputs for the classifier
    # adds the map with the training areas as band to the image with the input features.
    input_features = input_features.addBands(training_areas)

    # stratified sample for from the land cover patches for each land cover class.
    training_multiclass = input_features.updateMask(input_features.select('training').gt(0)) \
        .stratifiedSample(
        numPoints=1000,
        classBand=class_property,
        scale=scale,
        classValues=ee.List(class_values),
        classPoints=class_points.toList(),
        region=aoi.geometry(),
        tileScale=tile_scale
    )

    # create and train classifier for the land cover classification
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

    # get the map indicating forest loss from the Hansen Global Forest Change Map.
    forest_change = ee.Image("UMD/hansen/global_forest_change_2018_v1_6").select('lossyear').clip(aoi)

    if int(year[-2:]) in range(1, 19):  # checks if a forest loss map is available for the year of classification
        forest_change_mask = forest_change.eq(ee.Number(int(year[-2:])))
        # Classify the unknown area based on the crop data using the multiclass classifiers
        irrigated_area_classified_multiclass = input_features \
            .classify(classifier_multiclass) \
            .where(forest_change_mask.eq(1), 10) \
            .toByte()
    else:
        # Classify the unknown area based on the crop data using the multiclass classifiers
        irrigated_area_classified_multiclass = input_features \
            .classify(classifier_multiclass) \
            .toByte()

    # Post-processing
    # select the irrigated areas and paint them on an image
    irrigated_areas = ee.Image(0).toByte() \
        .where(irrigated_area_classified_multiclass.select('classification').eq(it_cl), 1) \
        .where(irrigated_area_classified_multiclass.select('classification').eq(ic_cl), 2)

    # remove small speckles
    mask_small_patches_removed = irrigated_areas.updateMask(irrigated_areas.gt(0)) \
        .connectedPixelCount(4).reproject(input_features.projection()).gte(4)
    irrigated_areas = irrigated_areas.where(mask_small_patches_removed.eq(0), 0)

    # fill small isolated pixels in irrigated land areas
    non_ia_connected_pixels = irrigated_areas.gt(0).where(mask_small_patches_removed.eq(0), 0).Not() \
        .connectedPixelCount(8).reproject(input_features.projection()).lte(5)

    mean_ia = irrigated_areas.updateMask(irrigated_areas.gt(0)).focal_mean(
        kernelType='square',
        radius=2.5).reproject(input_features.projection())

    mean_ia_assigned = mean_ia.where(mean_ia.gte(1.5), 2).where(mean_ia.lt(1.5).And(mean_ia.gt(0)), 1) \
        .updateMask(non_ia_connected_pixels)

    irrigated_areas = irrigated_areas.where(mean_ia_assigned.eq(2), 2).where(mean_ia_assigned.eq(1), 1)

    # creates an image that incorporates the irrigated areas, the result of the rf classification and the training areas
    # that were used

    irrigated_results = ee.ImageCollection([
        irrigated_areas.rename('irrigated_area'),
        irrigated_area_classified_multiclass.rename('rf_all_classes'),
        input_features.select('training'),
    ]).toBands().regexpRename('([0-9]{1,3}_)', '').set(
        'area_of_interest', aoi_name).set(
        'number_or_trees', no_trees).set(
        'variables_per_split', vps).set(
        'bagging_fraction', bag_fraction).set(
        'scale', scale)

    class_points = class_points.getInfo()

    for ind, val in enumerate(class_values):
        irrigated_results = irrigated_results.set(
            f'training_pixels_cl_{class_values[ind]}',
            class_points[ind]
        )

    try:  # export the results to asset
        task = export_to_asset(
            asset=irrigated_results,
            asset_type='image',
            asset_id=loc,
            region=aoi_coordinates,
            scale=scale,
            overwrite=overwrite
        )
    except FileExistsError as e:
        print(e)
        return True, classifier_multiclass
    else:
        return task, classifier_multiclass


def join_seasonal_irrigated_areas(
        irrigated_area_summer: ee.Image,
        irrigated_area_winter: ee.Image,
        aoi_name: str,
        year: Union[int, str],
        aoi: ee.FeatureCollection,
        export_method: str = 'drive',
        clf_folder: str = None,
        filename: str = None,
        scale: int = 30,
        overwrite: bool = False) -> Union[ee.batch.Task, bool]:
    """
    Combines the irrigated land areas determined by the RF for the summer and winter season into a single overview map.

    :param irrigated_area_summer: GEE image, classification result for the summer season
    :param irrigated_area_winter: GEE image, classification result for the winter season
    :param aoi_name: string, name of the area of interest, will be used for the naming of the result
    :param year: string, string of the year being classified
    :param aoi: EE FeatureCollection, vector of the aoi
    :param export_method: string, 'asset' to export results as asset or 'drive' to export the results to drive
    :param clf_folder: string, name of the folder to store the results, defaults to None
    :param filename: string, overwrites the default filename
    :param scale: pixel resolution tp use for export (meter per pixel)
    :param overwrite: Boolean, if True it overwrites previous classification result with the same parameters/aoi
    :return: returns an GEE task, or True if asset already exists.
    """
    # sets up the location where the results of the classification are saved
    if clf_folder is None and filename is None:
        loc = f"results/irrigated_area/{aoi_name}/irrigated_areas_{aoi_name}_{year}"
        filename = f"irrigated_areas_{aoi_name}_{year}"
    elif clf_folder is None:
        loc = f"results/irrigated_area/{aoi_name}/{filename}"
    else:
        loc = f"results/irrigated_area/{aoi_name}/{clf_folder}/irrigated_areas_{aoi_name}_{year}"

    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']  # coordinates of the aoi, needed for export

    # Get the irrigated areas from the classification results
    summer = ee.Image().constant(1).where(irrigated_area_summer.eq(1), 3).where(irrigated_area_summer.eq(2),
                                                                                2).reproject(
        irrigated_area_summer.projection())
    winter = ee.Image().constant(1).where(irrigated_area_winter.eq(1), 4).where(irrigated_area_winter.eq(2),
                                                                                5).reproject(
        irrigated_area_winter.projection())

    # multiply the seasonal irrigation maps with each other
    combined_irrigated_area_map = summer.multiply(winter)

    # assign the type of seasonal irrigated area class to the map
    combined_irrigated_area_map = ee.Image(0).where(
        combined_irrigated_area_map.eq(10), 1).where(
        combined_irrigated_area_map.eq(12), 2).where(
        combined_irrigated_area_map.eq(2), 3).where(
        combined_irrigated_area_map.eq(3), 4).where(
        combined_irrigated_area_map.eq(5), 5).where(
        combined_irrigated_area_map.eq(4), 6).where(
        combined_irrigated_area_map.eq(8), 7).where(
        combined_irrigated_area_map.eq(15), 7)

    # create a results image with the seasonal results and the total overview map
    results = ee.ImageCollection([
        combined_irrigated_area_map.rename('ia_year'),
        irrigated_area_summer.rename('ia_summer'),
        irrigated_area_winter.rename('ia_winter'),
    ]).toBands()

    # export the results
    if export_method == 'drive':
        export_task_ext = ee.batch.Export.image.toDrive(
            image=results,
            description=filename,
            folder=clf_folder,
            scale=scale,
            region=aoi_coordinates,
        )
        task = export_task_ext.start()
        return task
    elif export_method == 'asset':
        try:
            task = export_to_asset(
                asset=results,
                asset_type='image',
                asset_id=loc,
                region=aoi_coordinates,
                scale=scale,
                overwrite=overwrite
            )
        except FileExistsError as e:
            print(e)
            return True
        else:
            return task


def min_distance_classification(
        training: ee.Image,
        data: ee.Image,
        aoi: ee.FeatureCollection,
        training_points: int = 20000,
        scale: int = 30,
        tilescale: int = 4,
        classband: str = 'training') -> Union[ee.batch.Task, bool]:
    """
    Function that samples training data and trains a Mahalanobis distance classifier with a regression output mode
    and classifies the feature data provided

    :param training: EE Image containing the areas with the target class
    :param data:EE Image contaning the feature data for classification
    :param aoi: GEE FeatureCollection containing the vector of the area of interest for classification, this will be
     used to mask any pixels outside of the area of interest
    :param training_points: Number of training points to sample
    :param scale: A nominal scale in meters of the projection to sample in. Defaults to the scale of the first band
     of the input image. Defaults to 30
    :param tilescale: Scaling factor used to reduce aggregation tile size; using a larger tileScale (e.g. 2 or 4) may
    enable computations that run out of memory with the default. Defaults to 4
    :param classband: The name to be used the band containing the patches of the target classes. Defaults to 'training'
    :return: EE Image containing the result of the Mahalanobis distance classification
    """
    bandnames = data.bandNames()

    data = data.addBands(training)

    training_data = data.stratifiedSample(
        numPoints=training_points,
        classBand=classband,
        scale=scale,
        region=aoi.geometry(),
        tileScale=tilescale
    ).filter(ee.Filter.neq(classband, 0))

    distance_classifier = ee.Classifier.minimumDistance(metric='mahalanobis').train(
        features=training_data,
        classProperty=classband,
        inputProperties=bandnames
    ).setOutputMode('REGRESSION')

    return data.classify(distance_classifier).rename('classification')


def combine_training_areas(img_training_areas, classes):
  # Combine the training areas in to single image

  img_training_areas_summed = img_training_areas.reduce('sum')
  img_training_areas_combined = ee.Image(0)

  for ind, cl in enumerate(classes):
    img_training_areas_combined = img_training_areas_combined.where(img_training_areas.select(cl).eq(1).And(img_training_areas_summed.eq(1)), classes[cl])

  return img_training_areas_combined