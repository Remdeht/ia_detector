"""
All the functions used in the classification process of the irrigated area detector
"""

import ee
from . import landsat
from . import sentinel
from . import indices
from .export import export_to_asset
from .hydrology import add_mti


def create_feature_data(year, aoi, aoi_name='undefined', sensor='landsat', custom_name=None, overwrite=False):
    """
    Creates and exports the feature data for classification to the GEE as two image assets (feature data for summer and
     winter).

    :param year: tuple containing the begin and end date for the selection of imagery. Date format: YYYY-MM-DD.
    :param aoi: GEE FeatureCollection of the area of interest
    :param aoi_name: name of the aoi, this is used for the naming of the results
    :param sensor: string indicating which satellite to use, landsat or sentinel
    :param custom_name: Optional, provide a name for the asset instead of the year
    :return: dictionary containing two GEE export tasks
    """

    # Extract the date range for the period from the tuple
    begin = year[0]
    end = year[1]

    year_string = end[0:4]  # string with the year for the naming of the assets

    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']  # aoi coordinates

    if sensor == 'landsat':
        scale = 30
        # Retrieve landsat 5 and 7 imagery for the period and merge them together
        ls_5 = landsat.get_ls5_image_collection(begin, end, aoi)
        ls_7 = landsat.get_ls7_image_collection(begin, end, aoi)
        ls_8 = landsat.get_ls8_image_collection(begin, end, aoi)

        col = ls_5.merge(ls_7).merge(ls_8).map(landsat.remove_edges)  # merge all the landsat scenes into single col.

        # create monthly band composites
        col_monthly = landsat.create_monthly_index_images(
            image_collection=col,
            start_date=begin,
            end_date=end,
            aoi=aoi,
            stats=['median'],
        )

    elif sensor == 'sentinel':
        scale = 10
        col = sentinel.get_s2_image_collection(begin, end, aoi)
        col_monthly = sentinel.create_monthly_index_images(
            image_collection=col,
            start_date=begin,
            end_date=end,
            aoi=aoi,
            stats=['median'],
        )

    col_monthly = col_monthly.select(['R', 'G', 'B', 'NIR', 'SWIR'])  # Select these RGB, NIR and SWIR bands

    col_monthly = col_monthly.map(indices.add_gcvi).filter(
        ee.Filter.listContains('system:band_names', 'GCVI')) \
        .map(indices.add_ndvi).filter(ee.Filter.listContains('system:band_names', 'NDVI')) \
        .map(indices.add_ndwi).filter(ee.Filter.listContains('system:band_names', 'NDWI')) \
        .map(indices.add_ndwi_mcfeeters).filter(ee.Filter.listContains('system:band_names', 'NDWBI')) \
        .map(indices.add_ndbi).filter(ee.Filter.listContains('system:band_names', 'NDBI')) \
        .map(indices.add_wgi).filter(ee.Filter.listContains('system:band_names', 'WGI')) \
        .map(indices.add_evi).filter(ee.Filter.listContains('system:band_names', 'EVI')) \
        .map(indices.add_savi).filter(ee.Filter.listContains('system:band_names', 'SAVI'))

    mti = add_mti().clip(aoi)
    slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003").select('elevation')).clip(aoi).rename('slope')

    # generate median band composites for each season
    col_mean_monthly_median_blue = col_monthly.select('B').median().rename('blue')
    col_mean_monthly_median_green = col_monthly.select('G').median().rename('green')
    col_mean_monthly_median_red = col_monthly.select('R').median().rename('red')
    col_mean_monthly_median_nir = col_monthly.select('NIR').median().rename('nir')
    col_mean_monthly_median_swir_1 = col_monthly.select('SWIR').median().rename('swir1')

    # generate the pixel statistic maps for the spectral indices
    col_mean_monthly_median_ndvi = col_monthly.select('NDVI').mean()
    col_max_monthly_median_ndvi = col_monthly.select('NDVI').max()
    col_min_monthly_median_ndvi = col_monthly.select('NDVI').min()
    col_std_dev_monthly_median_ndvi = col_monthly.select('NDVI').reduce(ee.Reducer.stdDev())

    col_mean_monthly_median_gcvi = col_monthly.select('GCVI').mean()
    col_max_monthly_median_gcvi = col_monthly.select('GCVI').max()
    col_min_monthly_median_gcvi = col_monthly.select('GCVI').min()
    col_std_dev_monthly_median_gcvi = col_monthly.select('GCVI').reduce(ee.Reducer.stdDev())

    col_mean_monthly_median_ndwi = col_monthly.select('NDWI').mean()
    col_max_monthly_median_ndwi = col_monthly.select('NDWI').max()
    col_min_monthly_median_ndwi = col_monthly.select('NDWI').min()
    col_std_dev_monthly_median_ndwi = col_monthly.select('NDWI').reduce(ee.Reducer.stdDev())

    col_mean_monthly_median_wgi = col_monthly.select('WGI').mean()
    col_max_monthly_median_wgi = col_monthly.select('WGI').max()
    col_min_monthly_median_wgi = col_monthly.select('WGI').min()
    col_std_dev_monthly_median_wgi = col_monthly.select('WGI').reduce(ee.Reducer.stdDev())

    col_mean_monthly_median_evi = col_monthly.select('EVI').mean()
    col_max_monthly_median_evi = col_monthly.select('EVI').max()
    col_min_monthly_median_evi = col_monthly.select('EVI').min()
    col_std_dev_monthly_median_evi = col_monthly.select('EVI').reduce(ee.Reducer.stdDev())

    col_mean_monthly_median_savi = col_monthly.select('SAVI').mean()
    col_max_monthly_median_savi = col_monthly.select('SAVI').max()
    col_min_monthly_median_savi = col_monthly.select('SAVI').min()
    col_std_dev_monthly_median_savi = col_monthly.select('SAVI').reduce(ee.Reducer.stdDev())

    col_mean_monthly_mean_ndbi = col_monthly.select('NDBI').mean()
    col_max_monthly_median_ndbi = col_monthly.select('NDBI').max()
    col_min_monthly_median_ndbi = col_monthly.select('NDBI').min()

    col_mean_monthly_median_ndwi_waterbodies = col_monthly.select('NDWBI').mean()
    col_max_monthly_median_ndwi_waterbodies = col_monthly.select('NDWBI').max()
    col_min_monthly_median_ndwi_waterbodies = col_monthly.select('NDWBI').min()

    # join all the feature data into one list
    feature_bands = [
        col_mean_monthly_median_red,
        col_mean_monthly_median_green,
        col_mean_monthly_median_blue,
        col_mean_monthly_median_nir,
        col_mean_monthly_median_swir_1,
        col_min_monthly_median_gcvi.rename('GCVI_min'),
        col_mean_monthly_median_gcvi.rename('GCVI_mean'),
        col_max_monthly_median_gcvi.rename('GCVI_max'),
        col_min_monthly_median_ndvi.rename('NDVI_min'),
        col_mean_monthly_median_ndvi.rename('NDVI_mean'),
        col_max_monthly_median_ndvi.rename('NDVI_max'),
        col_min_monthly_median_ndwi.rename('NDWI_min'),
        col_mean_monthly_median_ndwi.rename('NDWI_mean'),
        col_max_monthly_median_ndwi.rename('NDWI_max'),
        col_min_monthly_median_wgi.rename('WGI_min'),
        col_mean_monthly_median_wgi.rename('WGI_mean'),
        col_max_monthly_median_wgi.rename('WGI_max'),
        col_min_monthly_median_ndwi_waterbodies.rename('NDWBI_min'),
        col_mean_monthly_median_ndwi_waterbodies.rename('NDWBI_mean'),
        col_max_monthly_median_ndwi_waterbodies.rename('NDWBI_max'),
        col_min_monthly_median_ndbi.rename('NDBI_min'),
        col_mean_monthly_mean_ndbi.rename('NDBI_mean'),
        col_max_monthly_median_ndbi.rename('NDBI_max'),
        col_min_monthly_median_evi.rename('EVI_min'),
        col_mean_monthly_median_evi.rename('EVI_mean'),
        col_max_monthly_median_evi.rename('EVI_max'),
        col_min_monthly_median_savi.rename('SAVI_min'),
        col_mean_monthly_median_savi.rename('SAVI_mean'),
        col_max_monthly_median_savi.rename('SAVI_max'),
        col_std_dev_monthly_median_ndvi.rename('NDVI_std'),
        col_std_dev_monthly_median_gcvi.rename('GCVI_std'),
        col_std_dev_monthly_median_ndwi.rename('NDWI_std'),
        col_std_dev_monthly_median_wgi.rename('WGI_std'),
        col_std_dev_monthly_median_evi.rename('EVI_std'),
        col_std_dev_monthly_median_savi.rename('SAVI_std'),
        mti.rename('MTI'),
        slope
    ]

    # flatten all the maps to a single GEE image
    crop_data_min_mean_max = ee.ImageCollection(feature_bands).toBands().set('sensor', sensor).set('scale', scale)

    if custom_name is not None:
        asset_id = f"data/{aoi_name}/{sensor}/feature_data_lda_{aoi_name}_{custom_name}"
    else:
        asset_id = f"data/{aoi_name}/{sensor}/feature_data_lda_{aoi_name}_{year_string}"

    try:
        task = export_to_asset(  # Export to the GEE account of the user
            asset=crop_data_min_mean_max,
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


def take_strat_sample(
        calibration_maps,
        feature_data,
        lc_classes,
        aoi,
        samplesize=5000,
        scale=30,
        tilescale=16,
        classband='lc',
        file_name='sample_collection',
        dir_name='sample_directory',
        min_connected_pixels=60):
    """
        Selects pixels from target classes extracted from calibration maps, filters out small patches of pixels and
        performs a stratified sample from the remaining

        :param calibration_maps: Dictionary containing calibration maps loaded as Earth Engine Image objects
        :param feature_data: Collection of images containing the feature data for classification
        :param lc_classes: A list containing the pixel values/label representing the target land cover classes in
        the calibration maps
        :param aoi: GEE FeatureCollection containing the vector of the area of interest for classification, this will be
         used to mask any pixels outside of the area of interest
        :param samplesize: Number of samples to take per class
        :param scale: A nominal scale in meters of the projection to sample in. Defaults to the scale of the first band
         of the input image.
        :param tilescale: Scaling factor used to reduce aggregation tile size; using a larger tileScale (e.g. 2 or 4) may
        enable computations that run out of memory with the default.
        :param classband: The name to be used the band containing the patches of the target classes. Defaults to 'lc'
        :param file_name: Name for the CSV file in which the samples are stored on the Google Drive, Defaults to 'sample_collection'
        :param dir_name: Name for the directory in which the samples are stored on the Google Drive, Defaults to 'sample_directory'
        :param min_connected_pixels: Number of minimum connected pixels a patch needs to contain, otherwise it is not
         considered for sanpling
        :return: export task, EE Image containing the masked patches, EE image containing the patches
        """
    sample_collection = None

    for key in calibration_maps:
        lc_map = calibration_maps[key]
        land_areas_for_sampling = ee.Image(1)  # Empty image

        for ind, lc_class in enumerate(lc_classes):
            # Paints the areas for each of the specified land cover classes to sample on the empty image
            land_areas_for_sampling = land_areas_for_sampling.where(lc_map.eq(lc_class), 2)

        land_areas_for_sampling = land_areas_for_sampling.clip(aoi).reproject(feature_data[key].projection())

        training_regions_mask = land_areas_for_sampling.connectedPixelCount(min_connected_pixels).gte(
            min_connected_pixels).reproject(feature_data[key].projection())
        # Removes smaller land cover patches based on the number of connected pixels
        lc_patches = land_areas_for_sampling.where(training_regions_mask.eq(0), 0).rename(classband)

        data_for_sampling = feature_data[key].addBands(
            lc_patches)  # combine the feature data and land cover patches into one image

        sample = data_for_sampling.stratifiedSample(  # perform a stratified sample
            numPoints=samplesize,
            classBand=classband,
            scale=scale,
            tileScale=tilescale,
            region=aoi.geometry()
        ).filter(ee.Filter.neq(classband, 0))

        if sample_collection is None:  # combine the samples for all the years being used for calibration
            sample_collection = sample
        else:
            sample_collection = sample_collection.merge(sample)

    task = ee.batch.Export.table.toDrive(
        collection=sample_collection,
        description=file_name,
        fileFormat='CSV',
        folder=dir_name,
    )
    task.start()  # export to the Google drive

    return task, training_regions_mask, lc_patches

def remove_outliers(df, bands_to_include, lower_quantile=0.05, upper_quantile=0.95):
    """
    Removes the outliers from a pandas dataframe
    :param df: Pandas dataframe containing the data to remove
    :param bands_to_include:bands for which to remove the outliers
    :param lower_quantile: lower quantile, between 0 and 1
    :param upper_quantile: upper quantile, between 0 and 1
    :return: Pandas dataframe with outliers removed
    """

    q1 = df[bands_to_include].quantile(lower_quantile)
    q3 = df[bands_to_include].quantile(upper_quantile)
    iqr = q3 - q1
    df = df[~((df[bands_to_include] < (q1 - 1.5 * iqr)) |(df[bands_to_include] > (q3 + 1.5 * iqr))).any(axis=1)]

    return df


def min_distance_classification(training, data, aoi, training_points=20000, scale=30, tilescale=4, classband='training'):
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


def random_forest(training, data, aoi, training_points=20000, scale=30, tilescale=4, classband='training', trees=500, min_leaf_pop=10):
    """
        Function that samples training data and trains a Random Forest classifier with a probability output mode
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
        :param trees: The number of decision trees to create, defaults to 500
        :param min_leaf_pop: Only create nodes whose training set contains at least this many points, defaults to 10
        :return: EE Image containing the result of the RF classification
        """
    bandnames = data.bandNames()

    data = data.addBands(training)

    training_data = data.stratifiedSample(
        numPoints=training_points,
        classBand=classband,
        scale=scale,
        region=aoi.geometry(),
        tileScale=tilescale
    )

    rf_classifier = ee.Classifier.smileRandomForest(
        numberOfTrees=trees,
        minLeafPopulation=min_leaf_pop,
    ).train(
        features=training_data,
        classProperty=classband,
        inputProperties=bandnames
    ).setOutputMode('PROBABILITY')

    result = data.classify(rf_classifier)

    return result



def perform_lda_scaling(data, intercept, coefficients, threshold, gt=True, min_connected_pixels=10):
    transformed_features = {}
    for ind, row in coefficients.iterrows():
        transformed_features[row['Bandname']] = data.select(row['Bandname']).multiply(float(row['Coefficient']))

    total_lda_1 = None

    for feat_key in transformed_features:
        if total_lda_1 is None:
            total_lda_1 = transformed_features[feat_key]
        else:
            total_lda_1 = total_lda_1.add(transformed_features[feat_key])

    total = total_lda_1.add(ee.Number(intercept[0])).rename('total');

    if gt:
        training_areas = total.gte(threshold).rename('training');
    else:
        training_areas = total.lte(threshold).rename('training');

    training_areas_mask = training_areas.connectedPixelCount(min_connected_pixels).gte(min_connected_pixels).reproject(
        data.projection())

    final_img = total.addBands(training_areas.where(training_areas_mask.eq(0), 0))

    return final_img

