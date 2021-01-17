"""
All the functions used in the classification process of the irrigated area detector
"""

import ee
from . import landsat
from . import sentinel
from . import indices
from .export import export_to_asset
from .hydrology import add_mti


def create_feature_data(year, aoi, aoi_name='undefined', sensor='landsat'):
    """
    Creates and exports the feature data for classification to the GEE as two image assets (feature data for summer and
     winter).

    :param year: tuple containing the begin and end date for the selection of imagery. Date format: YYYY-MM-DD.
    :param aoi: GEE FeatureCollection of the area of interest
    :param aoi_name: name of the aoi, this is used for the naming of the results
    :param sensor: string indicating which satellite to use, landsat or sentinel
    :param gap_fill: boolean indicating whether to use histogram matching fill algorithm
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
        .map(indices.add_wgi).filter(ee.Filter.listContains('system:band_names', 'WGI'))

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
        col_std_dev_monthly_median_ndvi.rename('NDVI_std'),
        col_std_dev_monthly_median_gcvi.rename('GCVI_std'),
        col_std_dev_monthly_median_ndwi.rename('NDWI_std'),
        col_std_dev_monthly_median_wgi.rename('WGI_std'),
        mti.rename('MTI'),
        slope
    ]

    # flatten all the maps to a single GEE image
    crop_data_min_mean_max = ee.ImageCollection(feature_bands).toBands().set('sensor', sensor).set('scale', scale)

    try:
        task = export_to_asset(  # Export to the GEE account of the user
            asset=crop_data_min_mean_max,
            asset_type='image',
            asset_id=f"data/{aoi_name}/{sensor}/feature_data_lda_{aoi_name}_{year_string}",
            region=aoi_coordinates,
            scale=scale
        )
    except FileExistsError as e:  # if the asset already exists the user is notified and no error is generated
        print(e)
        task = True

    return task  # returns the dictionary with the export tasks