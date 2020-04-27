import ee
from . import landsat
from .export import export_to_asset
from .constants import GEE_USER_PATH
from .vector import split_region


def create_features(year, aoi, name_string='unknown', season='year'):
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

    # Retrieve landsat 5 and 7 imagery for the period and merge them together
    ls_5 = landsat.get_ls5_image_collection(begin, end, aoi)
    ls_7 = landsat.get_ls7_image_collection(begin, end, aoi)
    ls = ls_5.merge(ls_7).map(landsat.remove_edges)

    # Calculate indices to be used in the classification
    ls_gcvi = ls.map(landsat.add_gcvi_ls457).filter(ee.Filter.listContains('system:band_names', 'GCVI'))
    ls_ndvi = ls.map(landsat.add_ndvi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDVI'))
    ls_ndwi = ls.map(landsat.add_ndwi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDWI'))
    ls_ndwi_greenhouses = ls.map(landsat.add_ndwi_mcfeeters_ls457).filter(
        ee.Filter.listContains('system:band_names', 'NDWIGH'))
    ls_ndbi = ls_ndvi.map(landsat.add_ndbi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDBI'))
    ls_bu = ls_ndbi.map(landsat.add_bu_ls457).filter(ee.Filter.listContains('system:band_names', 'BU'))
    ls_pr = landsat.join_precipitation(ls_ndvi, begin, end, aoi).filter(
        ee.Filter.listContains('system:band_names', 'pr'))
    ls_wgi = ls_gcvi.map(landsat.add_ndwi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDWI')) \
        .map(landsat.add_wgi_ls457).filter(ee.Filter.listContains('system:band_names', 'WGI'))

    # Create monthly images for each index, containing both the mean value and, the 10th and 90th percentile,
    # for each month

    ls_monthly_blue = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B1',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_green = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B2',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_red = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B3',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_ndvi = landsat.create_monthly_index_images(
        image_collection=ls_ndvi,
        band='NDVI',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_gcvi = landsat.create_monthly_index_images(
        image_collection=ls_gcvi,
        band='GCVI',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_ndwi = landsat.create_monthly_index_images(
        image_collection=ls_ndwi,
        band='NDWI',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_wgi = landsat.create_monthly_index_images(
        image_collection=ls_wgi,
        band='WGI',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_ndwi_greenhouses = landsat.create_monthly_index_images(
        image_collection=ls_ndwi_greenhouses,
        band='NDWIGH',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_ndbi = landsat.create_monthly_index_images(
        image_collection=ls_ndbi,
        band='NDBI',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_bu = landsat.create_monthly_index_images(
        image_collection=ls_bu,
        band='BU',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_ndvi_pr = ls_ndvi_pr = ls_pr.map(landsat.ndvi_precipitation_correction) \
        .filter(ee.Filter.listContains('system:band_names', 'NDVI_pr')).select('NDVI_pr')

    # Finally calculate the slope for the area of interest
    elevation = ee.Image('JAXA/ALOS/AW3D30/V2_2').select('AVE_DSM')
    slope = ee.Terrain.slope(elevation).clip(aoi).rename('slope')

    # Based on class analysis the pixels for classes can be obtained by applying thresholds.
    # Next up the masks for each class will be created.

    # Create an image out of all the feature maps created. This Image will be used for classification and training
    if season == 'year':

        ls_mean_monthly_median_blue = ls_monthly_blue.select('mean').mean().rename('blue')
        ls_mean_monthly_median_green = ls_monthly_green.select('mean').mean().rename('green median')
        ls_mean_monthly_median_red = ls_monthly_red.select('mean').mean().rename('red median')

        ls_mean_monthly_median_ndvi = ls_monthly_ndvi.select('mean').mean().rename('NDVI median')
        ls_mean_monthly_max_ndvi = ls_monthly_ndvi.select('mean').max().rename('NDVI max')
        ls_mean_monthly_min_ndvi = ls_monthly_ndvi.select('mean').min().rename('NDVI min')

        ls_mean_monthly_median_gcvi = ls_monthly_gcvi.select('mean').mean().rename('GCVI median')
        ls_mean_monthly_max_gcvi = ls_monthly_gcvi.select('mean').max().rename('GCVI max')
        ls_mean_monthly_min_gcvi = ls_monthly_gcvi.select('mean').min().rename('GCVI min')

        ls_mean_monthly_median_ndwi = ls_monthly_ndwi.select('mean').mean().rename('NDWI median')
        ls_mean_monthly_max_ndwi = ls_monthly_ndwi.select('mean').max().rename('NDWI max')
        ls_mean_monthly_min_ndwi = ls_monthly_ndwi.select('mean').min().rename('NDWI min')

        ls_mean_monthly_median_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('mean').mean().rename(
            'NDWIGH median')
        ls_mean_monthly_max_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('mean').max().rename('NDWIGH max')
        ls_mean_monthly_min_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('mean').min().rename('NDWIGH min')

        # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.

        yearly_std_ndvi = landsat.get_yearly_band_std(
            ls_monthly_ndvi,
            ['median'],
            begin,
            end,
            aoi
        )

        yearly_std_ndwi = landsat.get_yearly_band_std(
            ls_monthly_ndwi,
            ['median'],
            begin,
            end,
            aoi
        )

        yearly_std_gcvi = landsat.get_yearly_band_std(
            ls_monthly_gcvi,
            ['median'],
            begin,
            end,
            aoi
        )

        yearly_std_wgi = landsat.get_yearly_band_std(
            ls_monthly_wgi,
            ['median'],
            begin,
            end,
            aoi
        )

        # Take the median for the periods that will be used during thresholding.
        yearly_ndvi_std_mean = yearly_std_ndvi.select('median_std').mean()
        yearly_ndwi_std_mean = yearly_std_ndwi.select('median_std').mean()
        yearly_gcvi_std_mean = yearly_std_gcvi.select('median_std').mean()
        yearly_wgi_std_mean = yearly_std_wgi.select('median_std').mean()

        crop_data_min_mean_max = ee.ImageCollection([
            ls_mean_monthly_median_blue.rename('blue'),
            ls_mean_monthly_median_green.rename('green'),
            ls_mean_monthly_median_red.rename('red'),
            ls_mean_monthly_min_gcvi.rename('min_GCVI'),
            ls_mean_monthly_median_gcvi.rename('median_GCVI'),
            ls_mean_monthly_max_gcvi.rename('max_GCVI'),
            ls_mean_monthly_min_ndvi.rename('min_NDVI'),
            ls_mean_monthly_median_ndvi.rename('median_NDVI'),
            ls_mean_monthly_max_ndvi.rename('max_NDVI'),
            ls_mean_monthly_min_ndwi.rename('min_NDWI'),
            ls_mean_monthly_median_ndwi.rename('median_NDWI'),
            ls_mean_monthly_max_ndwi.rename('max_NDWI'),
            ls_mean_monthly_min_ndwi_greenhouses.rename('min_NDWIGH'),
            ls_mean_monthly_median_ndwi_greenhouses.rename('median_NDWIGH'),
            ls_mean_monthly_max_ndwi_greenhouses.rename('max_NDWIGH'),
            yearly_ndvi_std_mean.rename('NDVI_std'),
            yearly_gcvi_std_mean.rename('GCVI_std'),
            yearly_ndwi_std_mean.rename('NDWI_std'),
            yearly_wgi_std_mean.rename('WGI_std'),
            slope
        ]).toBands()
        export_to_asset(crop_data_min_mean_max, 'image', f"crop_data/crop_data_min_mean_max_{name_string}",
                        aoi_coordinates)

    elif season == 'summer':
        # ls_monthly_value_summer = ls_monthly_value.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_blue_summer = ls_monthly_blue.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_green_summer = ls_monthly_green.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_red_summer = ls_monthly_red.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_ndvi_summer = ls_monthly_ndvi.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_gcvi_summer = ls_monthly_gcvi.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_ndwi_summer = ls_monthly_ndwi.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_wgi_summer = ls_monthly_wgi.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_ndbi_summer = ls_monthly_ndbi.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_bu_summer = ls_monthly_bu.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_ndvi_pr_summer = ls_monthly_ndvi_pr.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses.filter(
            ee.Filter.rangeContains('month', 4, 9))

        # Same principle only now for the summer months

        ls_mean_monthly_median_blue_summer = ls_monthly_blue_summer.select('mean').mean().rename('blue')
        ls_mean_monthly_median_green_summer = ls_monthly_green_summer.select('mean').mean().rename('green')
        ls_mean_monthly_median_red_summer = ls_monthly_red_summer.select('mean').mean().rename('red')

        ls_mean_monthly_median_ndvi_summer = ls_monthly_ndvi_summer.select('mean').mean().rename('NDVI median')
        ls_mean_monthly_max_ndvi_summer = ls_monthly_ndvi_summer.select('mean').max().rename('NDVI max')
        ls_mean_monthly_min_ndvi_summer = ls_monthly_ndvi_summer.select('mean').min().rename('NDVI min')

        ls_mean_monthly_median_gcvi_summer = ls_monthly_gcvi_summer.select('mean').mean().rename('GCVI median')
        ls_mean_monthly_max_gcvi_summer = ls_monthly_gcvi_summer.select('mean').max().rename('GCVI max')
        ls_mean_monthly_min_gcvi_summer = ls_monthly_gcvi_summer.select('mean').min().rename('GCVI min')

        ls_mean_monthly_median_ndwi_summer = ls_monthly_ndwi_summer.select('mean').mean().rename('NDWI median')
        ls_mean_monthly_max_ndwi_summer = ls_monthly_ndwi_summer.select('mean').max().rename('NDWI max')
        ls_mean_monthly_min_ndwi_summer = ls_monthly_ndwi_summer.select('mean').min().rename('NDWI min')

        ls_mean_monthly_median_wgi_summer = ls_monthly_wgi_summer.select('mean').mean().rename('WGI median')
        ls_mean_monthly_max_wgi_summer = ls_monthly_wgi_summer.select('mean').max().rename('WGI max')
        ls_mean_monthly_min_wgi_summer = ls_monthly_wgi_summer.select('mean').min().rename('WGI min')

        ls_mean_monthly_mean_ndbi_summer = ls_monthly_ndbi_summer.select('mean').mean().rename('NDBI mean')
        ls_mean_monthly_max_ndbi_summer = ls_monthly_ndbi_summer.select('mean').max().rename('NDBI max')
        ls_mean_monthly_min_ndbi_summer = ls_monthly_ndbi_summer.select('mean').min().rename('NDBI min')

        ls_mean_monthly_mean_bu_summer = ls_monthly_bu_summer.select('mean').mean().rename('BU mean')
        ls_mean_monthly_max_bu_summer = ls_monthly_bu_summer.select('mean').max().rename('BU max')
        ls_mean_monthly_min_bu_summer = ls_monthly_bu_summer.select('mean').min().rename('BU min')

        ls_mean_monthly_mean_ndvi_pr_summer = ls_monthly_ndvi_pr_summer.select('NDVI_pr').mean().rename(
            'NDVI_pr mean')
        ls_mean_monthly_max_ndvi_pr_summer = ls_monthly_ndvi_pr_summer.select('NDVI_pr').max().rename('NDVI_pr max')
        ls_mean_monthly_min_ndvi_pr_summer = ls_monthly_ndvi_pr_summer.select('NDVI_pr').min().rename('NDVI_pr min')

        ls_mean_monthly_median_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select(
            'mean').mean().rename(
            'NDWIGH median')
        ls_mean_monthly_max_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select(
            'mean').max().rename(
            'NDWIGH max')
        ls_mean_monthly_min_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select(
            'mean').min().rename(
            'NDWIGH min')

        # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
        summer_std_ndvi = landsat.get_yearly_band_std(
            ls_monthly_ndvi,
            ['median'],
            begin,
            end,
            aoi,
            season='summer'
        )

        summer_std_ndwi = landsat.get_yearly_band_std(
            ls_monthly_ndwi,
            ['median'],
            begin,
            end,
            aoi,
            season='summer'
        )

        summer_std_gcvi = landsat.get_yearly_band_std(
            ls_monthly_gcvi,
            ['median'],
            begin,
            end,
            aoi,
            season='summer'
        )

        summer_std_wgi = landsat.get_yearly_band_std(
            ls_monthly_wgi,
            ['median'],
            begin,
            end,
            aoi,
            season='summer'
        )

        summer_ndvi_std_mean = summer_std_ndvi.select('median_std').mean()
        summer_ndwi_std_mean = summer_std_ndwi.select('median_std').mean()
        summer_gcvi_std_mean = summer_std_gcvi.select('median_std').mean()
        summer_wgi_std_mean = summer_std_wgi.select('median_std').mean()

        crop_data_min_mean_max = ee.ImageCollection([
            ls_mean_monthly_median_blue_summer.rename('blue'),
            ls_mean_monthly_median_green_summer.rename('green'),
            ls_mean_monthly_median_red_summer.rename('red'),
            ls_mean_monthly_min_gcvi_summer.rename('min_GCVI'),
            ls_mean_monthly_median_gcvi_summer.rename('median_GCVI'),
            ls_mean_monthly_max_gcvi_summer.rename('max_GCVI'),
            ls_mean_monthly_min_ndvi_summer.rename('min_NDVI'),
            ls_mean_monthly_median_ndvi_summer.rename('median_NDVI'),
            ls_mean_monthly_max_ndvi_summer.rename('max_NDVI'),
            ls_mean_monthly_min_ndwi_summer.rename('min_NDWI'),
            ls_mean_monthly_median_ndwi_summer.rename('median_NDWI'),
            ls_mean_monthly_max_ndwi_summer.rename('max_NDWI'),
            ls_mean_monthly_min_wgi_summer.rename('min_WGI'),
            ls_mean_monthly_median_wgi_summer.rename('median_WGI'),
            ls_mean_monthly_max_wgi_summer.rename('max_WGI'),
            ls_mean_monthly_min_ndwi_greenhouses_summer.rename('min_NDWIGH'),
            ls_mean_monthly_median_ndwi_greenhouses_summer.rename('median_NDWIGH'),
            ls_mean_monthly_max_ndwi_greenhouses_summer.rename('max_NDWIGH'),
            ls_mean_monthly_mean_ndbi_summer.rename('median_NDBI'),
            ls_mean_monthly_max_ndbi_summer.rename('max_NDBI'),
            ls_mean_monthly_min_ndbi_summer.rename('min_NDBI'),
            ls_mean_monthly_mean_bu_summer.rename('median_BU'),
            ls_mean_monthly_max_bu_summer.rename('max_BU'),
            ls_mean_monthly_min_bu_summer.rename('min_BU'),
            ls_mean_monthly_mean_ndvi_pr_summer.rename('median_NDVI_pr'),
            ls_mean_monthly_max_ndvi_pr_summer.rename('max_NDVI_pr'),
            ls_mean_monthly_min_ndvi_pr_summer.rename('min_NDVI_pr'),
            summer_ndvi_std_mean.rename('NDVI_std'),
            summer_gcvi_std_mean.rename('GCVI_std'),
            summer_ndwi_std_mean.rename('NDWI_std'),
            summer_wgi_std_mean.rename('WGI_std'),
            slope
        ]).toBands()
        export_to_asset(crop_data_min_mean_max, 'image',
                        f"crop_data/cdc/crop_data_summer_min_median_max_{name_string}",
                        aoi_coordinates)

    elif season == 'winter':
        early_filter = ee.Filter.rangeContains('month', 1, 3)
        late_filter = ee.Filter.rangeContains('month', 10, 12)

        ls_monthly_blue_winter = ls_monthly_blue.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_green_winter = ls_monthly_green.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_red_winter = ls_monthly_red.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_ndvi_winter = ls_monthly_ndvi.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_gcvi_winter = ls_monthly_gcvi.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_ndwi_winter = ls_monthly_ndwi.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_wgi_winter = ls_monthly_wgi.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_ndbi_winter = ls_monthly_ndbi.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_bu_winter = ls_monthly_bu.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_ndvi_pr_winter = ls_monthly_ndvi_pr.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses.filter(
            ee.Filter.Or(early_filter, late_filter))

        # And Winter
        ls_mean_monthly_median_blue_winter = ls_monthly_blue_winter.select('mean').mean().rename('blue')
        ls_mean_monthly_median_green_winter = ls_monthly_green_winter.select('mean').mean().rename('green median')
        ls_mean_monthly_median_red_winter = ls_monthly_red_winter.select('mean').mean().rename('red median')

        ls_mean_monthly_median_ndvi_winter = ls_monthly_ndvi_winter.select('mean').mean().rename('NDVI median')
        ls_mean_monthly_max_ndvi_winter = ls_monthly_ndvi_winter.select('mean').max().rename('NDVI max')
        ls_mean_monthly_min_ndvi_winter = ls_monthly_ndvi_winter.select('mean').min().rename('NDVI min')

        ls_mean_monthly_median_gcvi_winter = ls_monthly_gcvi_winter.select('mean').mean().rename('GCVI median')
        ls_mean_monthly_max_gcvi_winter = ls_monthly_gcvi_winter.select('mean').max().rename('GCVI max')
        ls_mean_monthly_min_gcvi_winter = ls_monthly_gcvi_winter.select('mean').min().rename('GCVI min')

        ls_mean_monthly_median_ndwi_winter = ls_monthly_ndwi_winter.select('mean').mean().rename('NDWI median')
        ls_mean_monthly_max_ndwi_winter = ls_monthly_ndwi_winter.select('mean').max().rename('NDWI max')
        ls_mean_monthly_min_ndwi_winter = ls_monthly_ndwi_winter.select('mean').min().rename('NDWI min')

        ls_mean_monthly_median_wgi_winter = ls_monthly_wgi_winter.select('mean').mean().rename('WGI median')
        ls_mean_monthly_max_wgi_winter = ls_monthly_wgi_winter.select('mean').max().rename('WGI max')
        ls_mean_monthly_min_wgi_winter = ls_monthly_wgi_winter.select('mean').min().rename('WGI min')

        ls_mean_monthly_mean_ndbi_winter = ls_monthly_ndbi_winter.select('mean').mean().rename('NDBI mean')
        ls_mean_monthly_max_ndbi_winter = ls_monthly_ndbi_winter.select('mean').max().rename('NDBI max')
        ls_mean_monthly_min_ndbi_winter = ls_monthly_ndbi_winter.select('mean').min().rename('NDBI min')

        ls_mean_monthly_mean_bu_winter = ls_monthly_bu_winter.select('mean').mean().rename('BU mean')
        ls_mean_monthly_max_bu_winter = ls_monthly_bu_winter.select('mean').max().rename('BU max')
        ls_mean_monthly_min_bu_winter = ls_monthly_bu_winter.select('mean').min().rename('BU min')

        ls_mean_monthly_mean_ndvi_pr_winter = ls_monthly_ndvi_pr_winter.select('NDVI_pr').mean().rename(
            'NDVI_pr mean')
        ls_mean_monthly_max_ndvi_pr_winter = ls_monthly_ndvi_pr_winter.select('NDVI_pr').max().rename('NDVI_pr max')
        ls_mean_monthly_min_ndvi_pr_winter = ls_monthly_ndvi_pr_winter.select('NDVI_pr').min().rename('NDVI_pr min')

        ls_mean_monthly_median_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select(
            'mean').mean().rename(
            'NDWIGH median')
        ls_mean_monthly_max_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select(
            'mean').max().rename(
            'NDWIGH max')
        ls_mean_monthly_min_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select(
            'mean').min().rename(
            'NDWIGH min')

        winter_std_ndvi = landsat.get_yearly_band_std(
            ls_monthly_ndvi,
            ['median'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_std_ndwi = landsat.get_yearly_band_std(
            ls_monthly_ndwi,
            ['median'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_std_gcvi = landsat.get_yearly_band_std(
            ls_monthly_gcvi,
            ['median'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_std_wgi = landsat.get_yearly_band_std(
            ls_monthly_wgi,
            ['median'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_ndvi_std_mean = winter_std_ndvi.select('median_std').mean()
        winter_ndwi_std_mean = winter_std_ndwi.select('median_std').mean()
        winter_gcvi_std_mean = winter_std_gcvi.select('median_std').mean()
        winter_wgi_std_mean = winter_std_wgi.select('median_std').mean()

        crop_data_min_mean_max = ee.ImageCollection([
            ls_mean_monthly_median_blue_winter.rename('blue'),
            ls_mean_monthly_median_green_winter.rename('green'),
            ls_mean_monthly_median_red_winter.rename('red'),
            ls_mean_monthly_min_gcvi_winter.rename('min_GCVI'),
            ls_mean_monthly_median_gcvi_winter.rename('median_GCVI'),
            ls_mean_monthly_max_gcvi_winter.rename('max_GCVI'),
            ls_mean_monthly_min_ndvi_winter.rename('min_NDVI'),
            ls_mean_monthly_median_ndvi_winter.rename('median_NDVI'),
            ls_mean_monthly_max_ndvi_winter.rename('max_NDVI'),
            ls_mean_monthly_min_ndwi_winter.rename('min_NDWI'),
            ls_mean_monthly_median_ndwi_winter.rename('median_NDWI'),
            ls_mean_monthly_max_ndwi_winter.rename('max_NDWI'),
            ls_mean_monthly_min_wgi_winter.rename('min_WGI'),
            ls_mean_monthly_median_wgi_winter.rename('median_WGI'),
            ls_mean_monthly_max_wgi_winter.rename('max_WGI'),
            ls_mean_monthly_min_ndwi_greenhouses_winter.rename('min_NDWIGH'),
            ls_mean_monthly_median_ndwi_greenhouses_winter.rename('median_NDWIGH'),
            ls_mean_monthly_max_ndwi_greenhouses_winter.rename('max_NDWIGH'),
            ls_mean_monthly_mean_ndbi_winter.rename('median_NDBI'),
            ls_mean_monthly_max_ndbi_winter.rename('max_NDBI'),
            ls_mean_monthly_min_ndbi_winter.rename('min_NDBI'),
            ls_mean_monthly_mean_bu_winter.rename('median_BU'),
            ls_mean_monthly_max_bu_winter.rename('max_BU'),
            ls_mean_monthly_min_bu_winter.rename('min_BU'),
            ls_mean_monthly_mean_ndvi_pr_winter.rename('median_NDVI_pr'),
            ls_mean_monthly_max_ndvi_pr_winter.rename('max_NDVI_pr'),
            ls_mean_monthly_min_ndvi_pr_winter.rename('min_NDVI_pr'),
            winter_ndvi_std_mean.rename('NDVI_std'),
            winter_gcvi_std_mean.rename('GCVI_std'),
            winter_ndwi_std_mean.rename('NDWI_std'),
            winter_wgi_std_mean.rename('WGI_std'),
            slope
        ]).toBands()

        export_to_asset(
            crop_data_min_mean_max,
            'image',
            f"crop_data/cdc/crop_data_winter_min_median_max_{name_string}",
            aoi_coordinates,
        )


def create_training_areas(aoi, name_string='unknown', season=None):
    if not season in ['summer', 'winter']:
        raise ValueError('unknown season string, please enter either "winter" or "summer"')

    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']
    if season == 'summer':
        data_image = ee.Image(f"{GEE_USER_PATH}/raster/crop_data/cdc/crop_data_{season}_min_median_max_{name_string}")

        mask_potential_crops = data_image.select('slope').lte(5).And(
            data_image.select('median_NDVI').gt(.2))

        mask_irrigated_crops = data_image.select('slope').lte(4).And(
            data_image.select('median_WGI').gte(.04)).And(
            data_image.select('WGI_std').gte(.25)).And(
            data_image.select('median_NDWIGH').lt(-.28)
        )

        mask_irrigated_trees = data_image.select('slope').lte(4).And(
            data_image.select('min_WGI').gt(-.05)).And(
            data_image.select('min_NDBI').lt(-.1)).And(
            data_image.select('NDWI_std').lt(.1)).And(
            data_image.select('median_NDWIGH').lt(-.3)).And(
            data_image.select('median_NDWIGH').gt(-.4))

        blue_threshold = ee.Number(data_image.select('blue').reduceRegion(
            ee.Reducer.percentile([97]),
            aoi,
            30,
        ).get('blue'))

        mask_greenhouses = data_image.select('slope').lte(5).And(
            data_image.select('median_NDWIGH').gt(-.2)).And(
            data_image.select('blue').gte(blue_threshold)).And(
            data_image.select('median_NDWI').gt(.04)
        )

        mask_rainfed_trees_and_crops = data_image.select('slope').lte(4).And(
            data_image.select('WGI_std').gte(0)).And(
            data_image.select('WGI_std').lte(.12)).And(
            data_image.select('min_WGI').lt(-.1)).And(
            data_image.select('NDWI_std').lt(.05))

        mask_natural_trees = data_image.select('slope').gt(5).And(
            data_image.select('min_NDVI').gt(.2)
        )

        mask_scrubs = data_image.select('slope').gt(5).And(
            data_image.select('NDWI_std').gte(.05)).And(
            data_image.select('NDWI_std').lte(.18)).And(
            data_image.select('median_WGI').gte(-.1)).And(
            data_image.select('median_WGI').lte(0)
        )

        training_regions_image = ee.Image(0).where(
            mask_scrubs.eq(1), 2).where(
            mask_natural_trees.eq(1), 1).where(
            mask_rainfed_trees_and_crops.eq(1), 3).where(
            mask_greenhouses.eq(1), 4).where(
            mask_irrigated_crops.eq(1), 5).where(
            mask_irrigated_trees.eq(1), 6).clip(aoi).rename('training')

        training_regions_image = training_regions_image.addBands(
            mask_potential_crops.rename('classification_area'))

        export_to_asset(training_regions_image, 'image', f"training_areas/training_areas_summer_{name_string}",
                        aoi_coordinates)
        print(
            f'Export task started for year: {name_string}.')
        return 0

    elif season == 'winter':

        data_image = ee.Image(f"{GEE_USER_PATH}/raster/crop_data/cdc/crop_data_winter_min_median_max_{name_string}")

        mask_potential_crops = data_image.select('slope').lte(5).And(
            data_image.select('max_NDVI').gte(.28))

        mask_irrigated_crops = data_image.select('slope').lte(4).And(
            data_image('median_WGI').gte(.29)).And(
            data_image.select('NDVI_std').gte(.1)).And(
            data_image.select('median_NDWIGH').lt(-.28)
        )

        mask_irrigated_trees = data_image.select('slope').lte(4).And(
            data_image.select('min_WGI').gt(0)).And(
            data_image.select('median_NDWIGH').lt(-.28)
        )

        blue_threshold = ee.Number(data_image.slect('blue').reduceRegion(
            ee.Reducer.percentile([97]),
            aoi,
            30,
        ).get('blue'))

        mask_greenhouses = data_image.select('slope').lte(5).And(
            data_image.select('median_NDWIGH').gt(-.2)).And(
            data_image.select('median_NDWIGH').lt(.1)).And(
            data_image.slect('blue').gte(blue_threshold)).And(
            data_image.select('median_NDWI').gt(.04)
        )

        mask_rainfed_trees_and_crops = data_image.select('slope').lte(4).And(
            data_image.select('WGI_std').gte(0)).And(
            data_image.select('WGI_std').lte(.18)).And(
            data_image.select('min_WGI').lt(-.1)).And(
            data_image.select('NDWI_std').lt(.07))

        mask_natural_trees = data_image.select('slope').gt(5).And(
            data_image.select('min_NDVI').gt(.2)
        )

        mask_scrubs = data_image.select('slope').gt(5).And(
            data_image.select('NDWI_std').gte(0)).And(
            data_image.select('NDWI_std').lte(.08)).And(
            data_image('median_WGI').gte(-.1)).And(
            data_image('median_WGI').lte(0.05)
        )

        training_regions_image = ee.Image(0).where(
            mask_scrubs.eq(1), 2).where(
            mask_natural_trees.eq(1), 1).where(
            mask_rainfed_trees_and_crops, 3).where(
            mask_greenhouses.eq(1), 4).where(
            mask_irrigated_crops.eq(1), 5).where(
            mask_irrigated_trees.eq(1), 6).clip(aoi).rename('training')

        training_regions_image = training_regions_image.addBands(
            mask_potential_crops.rename('classification_area'))

        export_to_asset(training_regions_image, 'image', f"training_areas/training_areas_winter_{name_string}",
                        aoi_coordinates)
        print(f'Export task started for year: {name_string}.')
        return 0


def classify_irrigated_areas(training_image, data_info, training_areas, mask, aoi, name_string='unknown',
                             clf='random_forest', no_trees=500, bag_fraction=.5, vps=2):
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

    class_property = 'training'
    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']
    training_image = training_image.addBands(training_areas)

    training_multiclass = training_image.updateMask(training_image.select('training').gt(0)) \
        .stratifiedSample(
        numPoints=1000,
        classBand='training',
        scale=30,
        region=aoi.geometry()
    )

    if clf == 'random_forest':
        # Train classifier for the multiclass classification
        classifier_multiclass = ee.Classifier.smileRandomForest(
            no_trees,
            variablesPerSplit=vps,
            bagFraction=bag_fraction
        ).train(
            training_multiclass,
            class_property
        )

        # region_tiles = vector.split_region(ee.FeatureCollection(f'{GEE_USER_PATH}/vector/{vector_collection["potential_crops"]}'))
        # for tile in region_tiles:

        # Classify the unknown area based on the crop data using the multiclass classifiers
        irrigated_area_classified_multiclass = training_image \
            .classify(classifier_multiclass).toByte()

        irrigated_area_classified_multiclass_masked = training_image \
            .classify(classifier_multiclass) \
            .updateMask(mask).toByte()

        irrigated_area_multiclass = ee.Image(0).toByte() \
            .where(irrigated_area_classified_multiclass.select('classification').eq(5), 1) \
            .where(irrigated_area_classified_multiclass.select('classification').eq(6), 2)

        irrigated_results = ee.ImageCollection([
            irrigated_area_multiclass.rename('irrigated_area'),
            irrigated_area_classified_multiclass.rename('rf_all_classes'),
            training_image.select('training'),
        ]).toBands().regexpRename('([0-9]{1,3}_)', '')

        export_task_ext = ee.batch.Export.image.toDrive(
            image=irrigated_results,
            description=f'ia_{clf}_{data_info}_{no_trees}tr_{vps}vps_{int(bag_fraction * 100)}bf_{name_string}',
            folder=f'{clf}_{data_info}',
            scale=30,
            region=aoi_coordinates,
            maxPixels=1e13,
        )
        export_task_ext.start()

        export_to_asset(
            irrigated_results,
            'image',
            f"results/random_forest/cdc/ia_{clf}_{data_info}_{no_trees}tr_{vps}vps_{int(bag_fraction * 100)}bf_{name_string}",
            aoi_coordinates,
        )

        print(
            f'Export started. Year: {name_string}. \nClassification method: {clf}.\nFeatures used {data_info}.\n.')
