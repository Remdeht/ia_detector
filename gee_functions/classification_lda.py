"""
All the functions used in the classification process of the irrigated area detector
"""

# Local imports
import ee
import pandas as pd

try:
    import landsat
    import sentinel
    import indices
    from export import export_to_asset, track_task
    from hydrology import add_mti

except ImportError:
    from . import landsat
    from . import sentinel
    from . import indices
    from .export import export_to_asset, track_task
    from .hydrology import add_mti


def create_feature_data(
        date_range: tuple,
        aoi: ee.FeatureCollection,
        creation_method: str,
        aoi_name: str = 'undefined',
        sensor: str = 'landsat',
        custom_name: str = None,
        overwrite: bool = False ) -> ee.batch.Task or bool:
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

        col = ls_5.merge(ls_7).merge(ls_8).merge(ls_9).map(landsat.remove_edges)  # merge all the landsat scenes into single col.

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

    tc = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE').select(['pdsi', 'soil', 'pr']).filter(
        ee.Filter.date(begin, end))

    if creation_method in ['monthly_composites_reduced', 'all_scenes_reduced']:

        col_mean = col.mean().regexpRename('(.*)', '$1_mean', False)
        col_median = col.median().regexpRename('(.*)', '$1_median', False)
        col_min = col.min().regexpRename('(.*)', '$1_min', False)
        col_max = col.max().regexpRename('(.*)', '$1_max', False)
        col_p85 = col.reduce(ee.Reducer.percentile([85]))
        col_p15 = col.reduce(ee.Reducer.percentile([15]))
        col_std_dev = col.reduce(ee.Reducer.stdDev())

        col_tc_mean = tc.mean().regexpRename('(.*)', '$1_mean', False)
        col_tc_median = tc.median().regexpRename('(.*)', '$1_median', False)
        col_tc_min = tc.min().regexpRename('(.*)', '$1_min', False)
        col_tc_max = tc.max().regexpRename('(.*)', '$1_max', False)
        col_tc_p85 = tc.reduce(ee.Reducer.percentile([85]))
        col_tc_p15 = tc.reduce(ee.Reducer.percentile([15]))
        col_tc_std_dev = tc.reduce(ee.Reducer.stdDev())

        feature_data = ee.ImageCollection(
                [
                    col_mean,
                    col_median,
                    col_max,
                    col_min,
                    col_p85,
                    col_p15,
                    col_std_dev,
                    col_tc_mean,
                    col_tc_median,
                    col_tc_min,
                    col_tc_max,
                    col_tc_p85,
                    col_tc_p15,
                    col_tc_std_dev,
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
        :param lc_classes: dict containing the calibration classes to sample
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
    new_class_values = {}

    for key in calibration_maps:
        lc_map = calibration_maps[key]
        land_areas_for_sampling = ee.Image(0)  # Empty image

        pix_val = 1

        for lc_class, class_values in lc_classes.items():
            # Paints the areas for each of the specified land cover classes to sample on the empty image
            for cal_lc_val in class_values:
                land_areas_for_sampling = land_areas_for_sampling.where(lc_map.eq(cal_lc_val), pix_val)

            new_class_values[pix_val] = lc_class
            pix_val += 1

        land_areas_for_sampling = land_areas_for_sampling.clip(aoi).reproject(feature_data[key].projection())

        training_regions_mask = land_areas_for_sampling.connectedPixelCount(min_connected_pixels).gte(
            min_connected_pixels).reproject(feature_data[key].projection())
        # Removes smaller land cover patches based on the number of connected pixels
        lc_patches = land_areas_for_sampling.where(training_regions_mask.eq(0), 0).rename(classband)

        # combine the feature data and land cover patches into one image
        data_for_sampling = feature_data[key].addBands(lc_patches)

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

    def add_class_name(x):

        name_dict = ee.Dictionary(new_class_values)
        return ee.Feature(x).set('class', name_dict.get(ee.Number(ee.Feature(x).get('lc')).format())).copyProperties(x)

    sample_collection = sample_collection.map(add_class_name)

    task = ee.batch.Export.table.toDrive(
        collection=sample_collection,
        description=file_name,
        fileFormat='CSV',
        folder=dir_name,
    )
    task.start()  # export to the Google drive

    return task, training_regions_mask, lc_patches


def remove_outliers(
        df: pd.DataFrame,
        bands_to_include: list['str'],
        lower_quantile: float=0.05,
        upper_quantile: float=0.95):
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


if __name__ == '__main__':
    aoi = ee.Geometry.Polygon(
        [[[-1.4572492923062508, 37.93351644908467],
          [-1.4572492923062508, 37.51205504786782],
          [-0.6401411380093758, 37.51205504786782],
          [-0.6401411380093758, 37.93351644908467]]],
        None,
        False
    )

    task = create_feature_data(
        (f'{2020}-04-01', f'{2020}-10-01'),
        aoi,
        aoi_name='undefined',
        sensor='sentinel',
        custom_name=None,
        overwrite=False
    )

    track_task(task)
