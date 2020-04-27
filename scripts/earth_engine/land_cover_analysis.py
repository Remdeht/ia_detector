import ee
from gee_functions import vector, landsat

ee.Initialize()

GEE_USER_PATH = 'users/Postm087'


def get_data(begin, end, aoi, stat, season='yearly'):
    """
    Function to gather all the spectral imagery to be analysed.

    :param begin: Begin date of the period for which the analysis is to be done
    :param end: End date of the period for which the analysis is to be done
    :param aoi: Area of interest
    :param season: Season to be analysed, currently supports winter, summer or the whole year.
    :return: Image containing all the spectral indexes added as bands.
    """
    # Calculate the slope for the area of interest
    elevation = ee.Image('JAXA/ALOS/AW3D30/V2_2').select('AVE_DSM')
    slope = ee.Terrain.slope(elevation).clip(aoi).rename('slope')

    # Select Landsat imagery for the period of interest and join the collections
    ls_5 = landsat.get_ls5_image_collection(begin, end, aoi)
    ls_7 = landsat.get_ls7_image_collection(begin, end, aoi)
    ls = ls_5.merge(ls_7)

    # Convert the RGB bands in the landsat collection to Hue, Saturation and Value
    ls_hsv = ls.map(landsat.rgb_to_hsv)

    # Calculate spectral indices to be analysed.
    ls_ndvi = ls.map(landsat.add_ndvi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDVI'))
    ls_gcvi = ls.map(landsat.add_gcvi_ls457).filter(ee.Filter.listContains('system:band_names', 'GCVI'))
    ls_ndwi = ls.map(landsat.add_ndwi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDWI'))
    ls_ndbi = ls_ndvi.map(landsat.add_ndbi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDBI'))
    ls_bu = ls_ndbi.map(landsat.add_bu_ls457).filter(ee.Filter.listContains('system:band_names', 'BU'))
    ls_pr = landsat.join_precipitation(ls_ndvi, begin, end, aoi).filter(ee.Filter.listContains('system:band_names', 'pr'))

    ls_wgi = ls_gcvi.map(landsat.add_ndwi_ls457).filter(ee.Filter.listContains('system:band_names', 'NDWI'))\
        .map(landsat.add_wgi_ls457).filter(ee.Filter.listContains('system:band_names', 'WGI'))
    ls_ndwi_greenhouses = ls.map(landsat.add_ndwi_mcfeeters_ls457)\
        .filter(ee.Filter.listContains('system:band_names', 'NDWIGH'))

    # # Calculate the monthly values per spectral index
    ls_monthly_hue = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='hue',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_saturation = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='saturation',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    ls_monthly_value = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='value',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

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

    ls_monthly_ndvi_pr = ls_ndvi_pr = ls_pr.map(landsat.ndvi_precipitation_correction)\
        .filter(ee.Filter.listContains('system:band_names', 'NDVI_pr')).select('NDVI_pr')

    ls_monthly_ndwi_greenhouses = landsat.create_monthly_index_images(
        image_collection=ls_ndwi_greenhouses,
        band='NDWIGH',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'median']
    )

    # Finally cobine all the data layers into a single image for the desired season

    if season == 'yearly':
        # Create images containing the mean monthly median and max value for the period on interest
        ls_mean_monthly_mean_hue = ls_monthly_hue.select('mean').mean().rename('hue mean')
        ls_mean_monthly_max_hue = ls_monthly_hue.select('mean').max().rename('hue max')
        ls_mean_monthly_min_hue = ls_monthly_hue.select('mean').min().rename('hue min')

        ls_mean_monthly_mean_saturation = ls_monthly_saturation.select('mean').mean().rename('saturation mean')
        ls_mean_monthly_max_saturation = ls_monthly_saturation.select('mean').max().rename('saturation max')
        ls_mean_monthly_min_saturation = ls_monthly_saturation.select('mean').min().rename('saturation min')

        ls_mean_monthly_mean_value = ls_monthly_value.select('mean').mean().rename('value mean')
        ls_mean_monthly_max_value = ls_monthly_value.select('mean').max().rename('value max')
        ls_mean_monthly_min_value = ls_monthly_value.select('mean').min().rename('value min')

        ls_mean_monthly_mean_blue = ls_monthly_blue.select('mean').mean().rename('blue mean')
        ls_mean_monthly_max_blue = ls_monthly_blue.select('mean').max().rename('blue max')
        ls_mean_monthly_min_blue = ls_monthly_blue.select('mean').min().rename('blue min')

        ls_mean_monthly_mean_green = ls_monthly_green.select('mean').mean().rename('green mean')
        ls_mean_monthly_max_green = ls_monthly_green.select('mean').max().rename('green max')
        ls_mean_monthly_min_green = ls_monthly_green.select('mean').min().rename('green min')

        ls_mean_monthly_mean_red = ls_monthly_red.select('mean').mean().rename('red mean')
        ls_mean_monthly_max_red = ls_monthly_red.select('mean').max().rename('red max')
        ls_mean_monthly_min_red = ls_monthly_red.select('mean').min().rename('red min')

        ls_mean_monthly_mean_ndvi = ls_monthly_ndvi.select('mean').mean().rename('NDVI mean')
        ls_mean_monthly_max_ndvi = ls_monthly_ndvi.select('mean').max().rename('NDVI max')
        ls_mean_monthly_min_ndvi = ls_monthly_ndvi.select('mean').min().rename('NDVI min')

        ls_mean_monthly_mean_gcvi = ls_monthly_gcvi.select('mean').mean().rename('GCVI mean')
        ls_mean_monthly_max_gcvi = ls_monthly_gcvi.select('mean').max().rename('GCVI max')
        ls_mean_monthly_min_gcvi = ls_monthly_gcvi.select('mean').min().rename('GCVI min')

        ls_mean_monthly_mean_ndwi = ls_monthly_ndwi.select('mean').mean().rename('NDWI mean')
        ls_mean_monthly_max_ndwi = ls_monthly_ndwi.select('mean').max().rename('NDWI max')
        ls_mean_monthly_min_ndwi = ls_monthly_ndwi.select('mean').min().rename('NDWI min')

        ls_mean_monthly_mean_wgi = ls_monthly_wgi.select('mean').mean().rename('WGI mean')
        ls_mean_monthly_max_wgi = ls_monthly_wgi.select('mean').max().rename('WGI max')
        ls_mean_monthly_min_wgi = ls_monthly_wgi.select('mean').min().rename('WGI min')

        ls_mean_monthly_mean_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('mean').mean().rename('NDWIGH mean')
        ls_mean_monthly_max_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('mean').max().rename('NDWIGH max')
        ls_mean_monthly_min_ndwi_greenhouses = ls_monthly_ndwi_greenhouses.select('mean').min().rename('NDWIGH min')

        # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
        yearly_std_ndvi = landsat.get_yearly_band_std(
            ls_monthly_ndvi,
            [stat],
            begin,
            end,
            aoi
        )

        yearly_std_ndwi = landsat.get_yearly_band_std(
            ls_monthly_ndwi,
            [stat],
            begin,
            end,
            aoi
        )

        yearly_std_gcvi = landsat.get_yearly_band_std(
            ls_monthly_gcvi,
            [stat],
            begin,
            end,
            aoi
        )

        yearly_std_wgi = landsat.get_yearly_band_std(
            ls_monthly_wgi,
            [stat],
            begin,
            end,
            aoi
        )

        # Take the mean for the periods that will be used during thresholding.
        yearly_ndvi_std_mean = yearly_std_ndvi.select(f'{stat}_std').mean()
        yearly_ndwi_std_mean = yearly_std_ndwi.select(f'{stat}_std').mean()
        yearly_gcvi_std_mean = yearly_std_gcvi.select(f'{stat}_std').mean()
        yearly_wgi_std_mean = yearly_std_wgi.select(f'{stat}_std').mean()

        crop_data = ee.ImageCollection([
            ls_mean_monthly_mean_hue,
            ls_mean_monthly_max_hue,
            ls_mean_monthly_min_hue,
            ls_mean_monthly_mean_saturation,
            ls_mean_monthly_max_saturation,
            ls_mean_monthly_min_saturation,
            ls_mean_monthly_mean_value,
            ls_mean_monthly_max_value,
            ls_mean_monthly_min_value,
            ls_mean_monthly_mean_blue,
            ls_mean_monthly_max_blue,
            ls_mean_monthly_min_blue,
            ls_mean_monthly_mean_green,
            ls_mean_monthly_max_green,
            ls_mean_monthly_min_green,
            ls_mean_monthly_mean_red,
            ls_mean_monthly_max_red,
            ls_mean_monthly_min_red,
            ls_mean_monthly_mean_ndvi,
            ls_mean_monthly_max_ndvi,
            ls_mean_monthly_min_ndvi,
            ls_mean_monthly_mean_gcvi,
            ls_mean_monthly_max_gcvi,
            ls_mean_monthly_min_gcvi,
            ls_mean_monthly_mean_ndwi,
            ls_mean_monthly_max_ndwi,
            ls_mean_monthly_min_ndwi,
            ls_mean_monthly_mean_ndwi_greenhouses,
            ls_mean_monthly_max_ndwi_greenhouses,
            ls_mean_monthly_min_ndwi_greenhouses,
            ls_mean_monthly_mean_wgi,
            ls_mean_monthly_max_wgi,
            ls_mean_monthly_min_wgi,
            yearly_ndvi_std_mean.rename('NDVI_std'),
            yearly_ndwi_std_mean.rename('NDWI_std'),
            yearly_gcvi_std_mean.rename('GCVI_std'),
            yearly_wgi_std_mean.rename('WGI_std'),
            slope,
        ])

        return crop_data.toBands().regexpRename('([0-9]*_)', '')

    elif season == 'summer':
        # # Create separate image collections containing only data for the summer months
        ls_monthly_hue_summer = ls_monthly_hue.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_saturation_summer = ls_monthly_saturation.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_value_summer = ls_monthly_value.filter(ee.Filter.rangeContains('month', 4, 9))
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
        ls_monthly_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses.filter(ee.Filter.rangeContains('month', 4, 9))

        # # Same principle only now for the summer months
        ls_mean_monthly_mean_hue_summer = ls_monthly_hue_summer.select('mean').mean().rename('hue mean')
        ls_mean_monthly_max_hue_summer = ls_monthly_hue_summer.select('mean').max().rename('hue max')
        ls_mean_monthly_min_hue_summer = ls_monthly_hue_summer.select('mean').min().rename('hue min')
        ls_mean_monthly_mean_saturation_summer = ls_monthly_saturation_summer.select('mean').mean().rename('saturation mean')
        ls_mean_monthly_max_saturation_summer = ls_monthly_saturation_summer.select('mean').max().rename('saturation max')
        ls_mean_monthly_min_saturation_summer = ls_monthly_saturation_summer.select('mean').min().rename('saturation min')
        ls_mean_monthly_mean_value_summer = ls_monthly_value_summer.select('mean').mean().rename('value mean')
        ls_mean_monthly_max_value_summer = ls_monthly_value_summer.select('mean').max().rename('value max')
        ls_mean_monthly_min_value_summer = ls_monthly_value_summer.select('mean').min().rename('value min')
        ls_mean_monthly_mean_blue_summer = ls_monthly_blue_summer.select('mean').mean().rename('blue mean')
        ls_mean_monthly_max_blue_summer = ls_monthly_blue_summer.select('mean').max().rename('blue max')
        ls_mean_monthly_min_blue_summer = ls_monthly_blue_summer.select('mean').min().rename('blue min')
        ls_mean_monthly_mean_green_summer = ls_monthly_green_summer.select('mean').mean().rename('green mean')
        ls_mean_monthly_max_green_summer = ls_monthly_green_summer.select('mean').max().rename('green max')
        ls_mean_monthly_min_green_summer = ls_monthly_green_summer.select('mean').min().rename('green min')
        ls_mean_monthly_mean_red_summer = ls_monthly_red_summer.select('mean').mean().rename('red mean')
        ls_mean_monthly_max_red_summer = ls_monthly_red_summer.select('mean').max().rename('red max')
        ls_mean_monthly_min_red_summer = ls_monthly_red_summer.select('mean').min().rename('red min')
        ls_mean_monthly_mean_ndvi_summer = ls_monthly_ndvi_summer.select('mean').mean().rename('NDVI mean')
        ls_mean_monthly_max_ndvi_summer = ls_monthly_ndvi_summer.select('mean').max().rename('NDVI max')
        ls_mean_monthly_min_ndvi_summer = ls_monthly_ndvi_summer.select('mean').min().rename('NDVI min')
        ls_mean_monthly_mean_gcvi_summer = ls_monthly_gcvi_summer.select('mean').mean().rename('GCVI mean')
        ls_mean_monthly_max_gcvi_summer = ls_monthly_gcvi_summer.select('mean').max().rename('GCVI max')
        ls_mean_monthly_min_gcvi_summer = ls_monthly_gcvi_summer.select('mean').min().rename('GCVI min')
        ls_mean_monthly_mean_ndwi_summer = ls_monthly_ndwi_summer.select('mean').mean().rename('NDWI mean')
        ls_mean_monthly_max_ndwi_summer = ls_monthly_ndwi_summer.select('mean').max().rename('NDWI max')
        ls_mean_monthly_min_ndwi_summer = ls_monthly_ndwi_summer.select('mean').min().rename('NDWI min')
        ls_mean_monthly_mean_wgi_summer = ls_monthly_wgi_summer.select('mean').mean().rename('WGI mean')
        ls_mean_monthly_max_wgi_summer = ls_monthly_wgi_summer.select('mean').max().rename('WGI max')
        ls_mean_monthly_min_wgi_summer = ls_monthly_wgi_summer.select('mean').min().rename('WGI min')

        ls_mean_monthly_mean_ndbi_summer = ls_monthly_ndbi_summer.select('mean').mean().rename('NDBI mean')
        ls_mean_monthly_max_ndbi_summer = ls_monthly_ndbi_summer.select('mean').max().rename('NDBI max')
        ls_mean_monthly_min_ndbi_summer = ls_monthly_ndbi_summer.select('mean').min().rename('NDBI min')

        ls_mean_monthly_mean_bu_summer = ls_monthly_bu_summer.select('mean').mean().rename('BU mean')
        ls_mean_monthly_max_bu_summer = ls_monthly_bu_summer.select('mean').max().rename('BU max')
        ls_mean_monthly_min_bu_summer = ls_monthly_bu_summer.select('mean').min().rename('BU min')

        ls_mean_monthly_mean_ndvi_pr_summer = ls_monthly_ndvi_pr_summer.select('NDVI_pr').mean().rename('NDVI_pr mean')
        ls_mean_monthly_max_ndvi_pr_summer = ls_monthly_ndvi_pr_summer.select('NDVI_pr').max().rename('NDVI_pr max')
        ls_mean_monthly_min_ndvi_pr_summer = ls_monthly_ndvi_pr_summer.select('NDVI_pr').min().rename('NDVI_pr min')

        ls_mean_monthly_mean_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select('mean').mean().rename(
            'NDWIGH mean')
        ls_mean_monthly_max_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select('mean').max().rename(
            'NDWIGH max')
        ls_mean_monthly_min_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses_summer.select('mean').min().rename(
            'NDWIGH min')

        # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
        summer_std_ndvi = landsat.get_yearly_band_std(
            ls_monthly_ndvi,
            [stat],
            begin,
            end,
            aoi,
            season='summer'
        )
        summer_std_ndwi = landsat.get_yearly_band_std(
            ls_monthly_ndwi,
            [stat],
            begin,
            end,
            aoi,
            season='summer'
        )
        summer_std_gcvi = landsat.get_yearly_band_std(
            ls_monthly_gcvi,
            [stat],
            begin,
            end,
            aoi,
            season='summer'
        )
        summer_std_wgi = landsat.get_yearly_band_std(
            ls_monthly_wgi,
            [stat],
            begin,
            end,
            aoi,
            season='summer'
        )

        summer_ndvi_std_mean = summer_std_ndvi.select(f'{stat}_std').mean()
        summer_ndwi_std_mean = summer_std_ndwi.select(f'{stat}_std').mean()
        summer_gcvi_std_mean = summer_std_gcvi.select(f'{stat}_std').mean()
        summer_wgi_std_mean = summer_std_wgi.select(f'{stat}_std').mean()

        crop_data = ee.ImageCollection([
            ls_mean_monthly_mean_hue_summer,
            ls_mean_monthly_max_hue_summer,
            ls_mean_monthly_min_hue_summer,
            ls_mean_monthly_mean_saturation_summer,
            ls_mean_monthly_max_saturation_summer,
            ls_mean_monthly_min_saturation_summer,
            ls_mean_monthly_mean_value_summer,
            ls_mean_monthly_max_value_summer,
            ls_mean_monthly_min_value_summer,
            ls_mean_monthly_mean_blue_summer,
            ls_mean_monthly_max_blue_summer,
            ls_mean_monthly_min_blue_summer,
            ls_mean_monthly_mean_green_summer,
            ls_mean_monthly_max_green_summer,
            ls_mean_monthly_min_green_summer,
            ls_mean_monthly_mean_red_summer,
            ls_mean_monthly_max_red_summer,
            ls_mean_monthly_min_red_summer,
            ls_mean_monthly_mean_ndvi_summer,
            ls_mean_monthly_max_ndvi_summer,
            ls_mean_monthly_min_ndvi_summer,
            ls_mean_monthly_mean_gcvi_summer,
            ls_mean_monthly_max_gcvi_summer,
            ls_mean_monthly_min_gcvi_summer,
            ls_mean_monthly_mean_ndwi_summer,
            ls_mean_monthly_max_ndwi_summer,
            ls_mean_monthly_min_ndwi_summer,
            ls_mean_monthly_mean_wgi_summer,
            ls_mean_monthly_max_wgi_summer,
            ls_mean_monthly_min_wgi_summer,
            ls_mean_monthly_mean_ndbi_summer,
            ls_mean_monthly_max_ndbi_summer,
            ls_mean_monthly_min_ndbi_summer,
            ls_mean_monthly_mean_bu_summer,
            ls_mean_monthly_max_bu_summer,
            ls_mean_monthly_min_bu_summer,
            ls_mean_monthly_mean_ndvi_pr_summer,
            ls_mean_monthly_max_ndvi_pr_summer,
            ls_mean_monthly_min_ndvi_pr_summer,
            ls_mean_monthly_mean_ndwi_greenhouses_summer,
            ls_mean_monthly_max_ndwi_greenhouses_summer,
            ls_mean_monthly_min_ndwi_greenhouses_summer,
            summer_ndvi_std_mean.rename('NDVI_std'),
            summer_ndwi_std_mean.rename('NDWI_std'),
            summer_gcvi_std_mean.rename('GCVI_std'),
            summer_wgi_std_mean.rename('WGI_std'),
            slope,
        ])

        return crop_data.toBands().regexpRename('([0-9]*_)', '')

    elif season == 'winter':
        early_filter = ee.Filter.rangeContains('month', 1, 3)
        late_filter = ee.Filter.rangeContains('month', 10, 12)

        ls_monthly_hue_winter = ls_monthly_hue.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_saturation_winter = ls_monthly_saturation.filter(ee.Filter.Or(early_filter, late_filter))
        ls_monthly_value_winter = ls_monthly_value.filter(ee.Filter.Or(early_filter, late_filter))
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
        ls_monthly_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses.filter(ee.Filter.Or(early_filter, late_filter))

        # And Winter
        ls_mean_monthly_mean_hue_winter = ls_monthly_hue_winter.select('mean').mean().rename('hue mean')
        ls_mean_monthly_max_hue_winter = ls_monthly_hue_winter.select('mean').max().rename('hue max')
        ls_mean_monthly_min_hue_winter = ls_monthly_hue_winter.select('mean').min().rename('hue min')
        ls_mean_monthly_mean_saturation_winter = ls_monthly_saturation_winter.select('mean').mean().rename('saturation mean')

        ls_mean_monthly_max_saturation_winter = ls_monthly_saturation_winter.select('mean').max().rename(
            'saturation max')
        ls_mean_monthly_min_saturation_winter = ls_monthly_saturation_winter.select('mean').min().rename(
            'saturation min')
        ls_mean_monthly_mean_value_winter = ls_monthly_value_winter.select('mean').mean().rename('value mean')

        ls_mean_monthly_max_value_winter = ls_monthly_value_winter.select('mean').max().rename('value max')
        ls_mean_monthly_min_value_winter = ls_monthly_value_winter.select('mean').min().rename('value min')
        ls_mean_monthly_mean_blue_winter = ls_monthly_blue_winter.select('mean').mean().rename('blue mean')
        ls_mean_monthly_max_blue_winter = ls_monthly_blue_winter.select('mean').max().rename('blue max')
        ls_mean_monthly_min_blue_winter = ls_monthly_blue_winter.select('mean').min().rename('blue min')
        ls_mean_monthly_mean_green_winter = ls_monthly_green_winter.select('mean').mean().rename('green mean')
        ls_mean_monthly_max_green_winter = ls_monthly_green_winter.select('mean').max().rename('green max')
        ls_mean_monthly_min_green_winter = ls_monthly_green_winter.select('mean').min().rename('green min')
        ls_mean_monthly_mean_red_winter = ls_monthly_red_winter.select('mean').mean().rename('red mean')
        ls_mean_monthly_max_red_winter = ls_monthly_red_winter.select('mean').max().rename('red max')
        ls_mean_monthly_min_red_winter = ls_monthly_red_winter.select('mean').min().rename('red min')
        ls_mean_monthly_mean_ndvi_winter = ls_monthly_ndvi_winter.select('mean').mean().rename('NDVI mean')
        ls_mean_monthly_max_ndvi_winter = ls_monthly_ndvi_winter.select('mean').max().rename('NDVI max')
        ls_mean_monthly_min_ndvi_winter = ls_monthly_ndvi_winter.select('mean').min().rename('NDVI min')
        ls_mean_monthly_mean_gcvi_winter = ls_monthly_gcvi_winter.select('mean').mean().rename('GCVI mean')
        ls_mean_monthly_max_gcvi_winter = ls_monthly_gcvi_winter.select('mean').max().rename('GCVI max')
        ls_mean_monthly_min_gcvi_winter = ls_monthly_gcvi_winter.select('mean').min().rename('GCVI min')
        ls_mean_monthly_mean_ndwi_winter = ls_monthly_ndwi_winter.select('mean').mean().rename('NDWI mean')
        ls_mean_monthly_max_ndwi_winter = ls_monthly_ndwi_winter.select('mean').max().rename('NDWI max')
        ls_mean_monthly_min_ndwi_winter = ls_monthly_ndwi_winter.select('mean').min().rename('NDWI min')
        ls_mean_monthly_mean_wgi_winter = ls_monthly_wgi_winter.select('mean').mean().rename('WGI mean')
        ls_mean_monthly_max_wgi_winter = ls_monthly_wgi_winter.select('mean').max().rename('WGI max')
        ls_mean_monthly_min_wgi_winter = ls_monthly_wgi_winter.select('mean').min().rename('WGI min')

        ls_mean_monthly_mean_ndbi_winter = ls_monthly_ndbi_winter.select('mean').mean().rename('NDBI mean')
        ls_mean_monthly_max_ndbi_winter = ls_monthly_ndbi_winter.select('mean').max().rename('NDBI max')
        ls_mean_monthly_min_ndbi_winter = ls_monthly_ndbi_winter.select('mean').min().rename('NDBI min')

        ls_mean_monthly_mean_bu_winter = ls_monthly_bu_winter.select('mean').mean().rename('BU mean')
        ls_mean_monthly_max_bu_winter = ls_monthly_bu_winter.select('mean').max().rename('BU max')
        ls_mean_monthly_min_bu_winter = ls_monthly_bu_winter.select('mean').min().rename('BU min')

        ls_mean_monthly_mean_ndvi_pr_winter = ls_monthly_ndvi_pr_winter.select('NDVI_pr').mean().rename('NDVI_pr mean')
        ls_mean_monthly_max_ndvi_pr_winter = ls_monthly_ndvi_pr_winter.select('NDVI_pr').max().rename('NDVI_pr max')
        ls_mean_monthly_min_ndvi_pr_winter = ls_monthly_ndvi_pr_winter.select('NDVI_pr').min().rename('NDVI_pr min')

        ls_mean_monthly_mean_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select('mean').mean().rename(
            'NDWIGH mean')
        ls_mean_monthly_max_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select('mean').max().rename(
            'NDWIGH max')
        ls_mean_monthly_min_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses_winter.select('mean').min().rename(
            'NDWIGH min')


        # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
        winter_std_ndvi = landsat.get_yearly_band_std(
            ls_monthly_ndvi,
            [f'{stat}'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_std_ndwi = landsat.get_yearly_band_std(
            ls_monthly_ndwi,
            [f'{stat}'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_std_gcvi = landsat.get_yearly_band_std(
            ls_monthly_gcvi,
            [f'{stat}'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_std_wgi = landsat.get_yearly_band_std(
            ls_monthly_wgi,
            [f'{stat}'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_ndvi_std_mean = winter_std_ndvi.select(f'{stat}_std').mean()
        winter_ndwi_std_mean = winter_std_ndwi.select(f'{stat}_std').mean()
        winter_gcvi_std_mean = winter_std_gcvi.select(f'{stat}_std').mean()
        winter_wgi_std_mean = winter_std_wgi.select(f'{stat}_std').mean()

        crop_data = ee.ImageCollection([
            ls_mean_monthly_mean_hue_winter,
            ls_mean_monthly_max_hue_winter,
            ls_mean_monthly_min_hue_winter,
            ls_mean_monthly_mean_saturation_winter,
            ls_mean_monthly_max_saturation_winter,
            ls_mean_monthly_min_saturation_winter,
            ls_mean_monthly_mean_value_winter,
            ls_mean_monthly_max_value_winter,
            ls_mean_monthly_min_value_winter,
            ls_mean_monthly_mean_blue_winter,
            ls_mean_monthly_max_blue_winter,
            ls_mean_monthly_min_blue_winter,
            ls_mean_monthly_mean_green_winter,
            ls_mean_monthly_max_green_winter,
            ls_mean_monthly_min_green_winter,
            ls_mean_monthly_mean_red_winter,
            ls_mean_monthly_max_red_winter,
            ls_mean_monthly_min_red_winter,
            ls_mean_monthly_mean_ndvi_winter,
            ls_mean_monthly_max_ndvi_winter,
            ls_mean_monthly_min_ndvi_winter,
            ls_mean_monthly_mean_gcvi_winter,
            ls_mean_monthly_max_gcvi_winter,
            ls_mean_monthly_min_gcvi_winter,
            ls_mean_monthly_mean_ndwi_winter,
            ls_mean_monthly_max_ndwi_winter,
            ls_mean_monthly_min_ndwi_winter,
            ls_mean_monthly_mean_wgi_winter,
            ls_mean_monthly_max_wgi_winter,
            ls_mean_monthly_min_wgi_winter,

            ls_mean_monthly_mean_ndbi_winter,
            ls_mean_monthly_max_ndbi_winter,
            ls_mean_monthly_min_ndbi_winter,
            ls_mean_monthly_mean_bu_winter,
            ls_mean_monthly_max_bu_winter,
            ls_mean_monthly_min_bu_winter,

            ls_mean_monthly_mean_ndvi_pr_winter,
            ls_mean_monthly_max_ndvi_pr_winter,
            ls_mean_monthly_min_ndvi_pr_winter,

            ls_mean_monthly_mean_ndwi_greenhouses_winter,
            ls_mean_monthly_max_ndwi_greenhouses_winter,
            ls_mean_monthly_min_ndwi_greenhouses_winter,
            winter_ndvi_std_mean.rename('NDVI_std'),
            winter_ndwi_std_mean.rename('NDWI_std'),
            winter_gcvi_std_mean.rename('GCVI_std'),
            winter_wgi_std_mean.rename('WGI_std'),
            slope,
        ])

        return crop_data.toBands().regexpRename('([0-9]*_)', '')


aoi = ee.FeatureCollection(f'{GEE_USER_PATH}/vector/outline/outline_cdc_3857')  # Load the feature collection containing the area of interest
cdc_coordinates = aoi.geometry().bounds().getInfo()['coordinates']

val_maps = {  # Validation Maps, previously uploaded to the GEE
    '88': ee.Image(f'{GEE_USER_PATH}/CEBAS_RASTER/C88'),
    '97': ee.Image(f'{GEE_USER_PATH}/CEBAS_RASTER/C97'),
    '00': ee.Image(f'{GEE_USER_PATH}/CEBAS_RASTER/C00'),
    '09': ee.Image(f'{GEE_USER_PATH}/CEBAS_RASTER/C09'),
}

years = {  # Time periods
    '88': ('1987-01-01', '1989-01-01'),
    '97': ('1996-01-01', '1998-01-01'),
    '00': ('1999-01-01', '2001-01-01'),
    '09': ('2008-01-01', '2010-01-01'),
}

land_classes = {  # land classes to be analysed
    1: 'natural trees',
    2: 'open trees',
    3: 'dense scrub',
    4: 'open scrub',
    5: 'rainfed trees',
    6: 'rainfed crops',
    7: 'irrigated trees',
    8: 'irrigated crops',
    9: 'greenhouses',
    10: 'unproductive area',
}

season = [
    # 'yearly',
    'summer',
    'winter',
]

for key in val_maps:
    BEGIN = years[key][0]
    END = years[key][1]

    validation_map = val_maps[key] # load validation map

    elevation = ee.Image('JAXA/ALOS/AW3D30/V2_2').select('AVE_DSM')
    slope = ee.Terrain.slope(elevation).clip(aoi).rename('slope')
    slope_mask = slope.lte(5)

    validation_map = validation_map.updateMask(slope_mask)

    stat = 'median'

    for s in season:
        crop_data = get_data(BEGIN, END, aoi, stat,s) # prepare the seasonal data

        all_stats = []

        for cl in land_classes:
            # For each of the classes to be analyses, first select all the pixels in the validation map that correspond
            # to the class. Then convert the pixels into a multipolygon.
            land_class_vector = vector.raster_to_vector(validation_map.eq(cl), aoi)
            land_class_vector = land_class_vector.map(vector.add_area)  # calculate the areas of the created polygons
            land_class_vector = land_class_vector.filter(ee.Filter.gt('area', 10000))  # Filter out any small polygons
            # Sample points within the class area, i.e. the area that falls within the vector just created
            sample_points = ee.FeatureCollection.randomPoints(land_class_vector, 500, 0)

            # For each point the corresponding seasonal data is then retrieved
            sample_data = crop_data.select(crop_data.bandNames()).sampleRegions(
                collection=sample_points,
                scale=30,
                tileScale=16,
            )

            def get_point_data(name):
                """Function that calculates simple statistics for the overall point collection"""

                reducer = ee.Reducer.mean().combine(
                    reducer2= ee.Reducer.percentile([10,90]),sharedInputs= True)

                sample_data_results = sample_data.reduceColumns(
                selectors=ee.List([name]),
                reducer= reducer
                ).set('band', ee.String(name)).set('class', land_classes[cl])

                return ee.Feature(None, sample_data_results)

            sample_stats = ee.FeatureCollection(crop_data.bandNames().map(get_point_data))  # calculate stats per class

            all_stats += [sample_stats]

        export_task = ee.batch.Export.table.toDrive(  # Export the statitics to personal google drive account
            collection=ee.FeatureCollection(all_stats).flatten(),
            description=f'sample_data_{s}_{key}',
            folder=f'sample_data_validation_classes_{s}_ndbi_{stat}',
            fileFormat='CSV'
        )

        export_task.start()

    print(f'Finished year: {key}')

