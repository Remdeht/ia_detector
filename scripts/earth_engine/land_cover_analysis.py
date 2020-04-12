import ee
from gee_functions import vector, landsat

ee.Initialize()

GEE_USER_PATH = 'users/Postm087'


def get_data(begin, end, aoi, season='yearly'):
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
    ls_ndwi_greenhouses = ls.map(landsat.add_ndwi_mcfeeters_ls457)\
        .filter(ee.Filter.listContains('system:band_names', 'NDWIGH'))

    # Calculate the monthly values per spectral index
    ls_monthly_hue = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='hue',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_saturation = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='saturation',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_value = landsat.create_monthly_index_images(
        image_collection=ls_hsv,
        band='value',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_blue = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B1',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_green = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B2',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_red = landsat.create_monthly_index_images(
        image_collection=ls,
        band='B3',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_ndvi = landsat.create_monthly_index_images(
        image_collection=ls_ndvi,
        band='NDVI',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_gcvi = landsat.create_monthly_index_images(
        image_collection=ls_gcvi,
        band='GCVI',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_ndwi = landsat.create_monthly_index_images(
        image_collection=ls_ndwi,
        band='NDWI',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    ls_monthly_ndwi_greenhouses = landsat.create_monthly_index_images(
        image_collection=ls_ndwi_greenhouses,
        band='NDWIGH',
        start_date=begin,
        end_date=end,
        aoi=aoi,
        stats=['mean', 'min', 'max']
    )

    # Finally cobine all the data layers into a single image for the desired season

    if season == 'yearly':
        # Create images containing the mean monthly median and max value for the period on interest
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

        # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
        yearly_std_ndvi = landsat.get_yearly_band_std(
            ls_ndvi,
            ['NDVI'],
            begin,
            end,
            aoi
        )

        yearly_std_ndwi = landsat.get_yearly_band_std(
            ls_ndwi,
            ['NDWI'],
            begin,
            end,
            aoi
        )

        yearly_std_gcvi = landsat.get_yearly_band_std(
            ls_gcvi,
            ['GCVI'],
            begin,
            end,
            aoi
        )

        # Take the mean for the periods that will be used during thresholding.
        yearly_ndvi_std_mean = yearly_std_ndvi.select('NDVI_std').mean()
        yearly_ndwi_std_mean = yearly_std_ndwi.select('NDWI_std').mean()
        yearly_gcvi_std_mean = yearly_std_gcvi.select('GCVI_std').mean()

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
            yearly_ndvi_std_mean,
            yearly_ndwi_std_mean,
            yearly_gcvi_std_mean,
            slope,
        ])

        return crop_data.toBands().regexpRename('([0-9]*_)', '')

    elif season == 'summer':
        # Create separate image collections containing only data for the summer months
        ls_monthly_hue_summer = ls_monthly_hue.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_saturation_summer = ls_monthly_saturation.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_value_summer = ls_monthly_value.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_blue_summer = ls_monthly_blue.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_green_summer = ls_monthly_green.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_red_summer = ls_monthly_red.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_ndvi_summer = ls_monthly_ndvi.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_gcvi_summer = ls_monthly_gcvi.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_ndwi_summer = ls_monthly_ndwi.filter(ee.Filter.rangeContains('month', 4, 9))
        ls_monthly_ndwi_greenhouses_summer = ls_monthly_ndwi_greenhouses.filter(ee.Filter.rangeContains('month', 4, 9))

        # Same principle only now for the summer months
        ls_mean_monthly_mean_hue_summer = ls_monthly_hue_summer.select('mean').mean().rename('hue mean')
        ls_mean_monthly_max_hue_summer = ls_monthly_hue_summer.select('max').mean().rename('hue max')
        ls_mean_monthly_min_hue_summer = ls_monthly_hue_summer.select('min').mean().rename('hue min')

        ls_mean_monthly_mean_saturation_summer = ls_monthly_saturation_summer.select('mean').mean().rename('saturation mean')
        ls_mean_monthly_max_saturation_summer = ls_monthly_saturation_summer.select('max').mean().rename('saturation max')
        ls_mean_monthly_min_saturation_summer = ls_monthly_saturation_summer.select('min').mean().rename('saturation min')

        ls_mean_monthly_mean_value_summer = ls_monthly_value_summer.select('mean').mean().rename('value mean')
        ls_mean_monthly_max_value_summer = ls_monthly_value_summer.select('max').mean().rename('value max')
        ls_mean_monthly_min_value_summer = ls_monthly_value_summer.select('min').mean().rename('value min')

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

        # Next create standard deviation maps for both the seasonal and yearly NDWI and NDVI values.
        summer_std_ndvi = landsat.get_yearly_band_std(
            ls_ndvi,
            ['NDVI'],
            begin,
            end,
            aoi,
            season='summer'
        )

        summer_std_ndwi = landsat.get_yearly_band_std(
            ls_ndwi,
            ['NDWI'],
            begin,
            end,
            aoi,
            season='summer'
        )

        summer_std_gcvi = landsat.get_yearly_band_std(
            ls_gcvi,
            ['GCVI'],
            begin,
            end,
            aoi,
            season='summer'
        )

        summer_ndvi_std_mean = summer_std_ndvi.select('NDVI_std').mean()
        summer_ndwi_std_mean = summer_std_ndwi.select('NDWI_std').mean()
        summer_gcvi_std_mean = summer_std_gcvi.select('GCVI_std').mean()

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
            ls_mean_monthly_mean_ndwi_greenhouses_summer,
            ls_mean_monthly_max_ndwi_greenhouses_summer,
            ls_mean_monthly_min_ndwi_greenhouses_summer,
            summer_ndvi_std_mean,
            summer_ndwi_std_mean,
            summer_gcvi_std_mean,
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
        ls_monthly_ndwi_greenhouses_winter = ls_monthly_ndwi_greenhouses.filter(ee.Filter.Or(early_filter, late_filter))

        # And Winter
        ls_mean_monthly_mean_hue_winter = ls_monthly_hue_winter.select('mean').mean().rename('hue mean')
        ls_mean_monthly_max_hue_winter = ls_monthly_hue_winter.select('max').mean().rename('hue max')
        ls_mean_monthly_min_hue_winter = ls_monthly_hue_winter.select('min').mean().rename('hue min')
        ls_mean_monthly_mean_saturation_winter = ls_monthly_saturation_winter.select('mean').mean().rename(
            'saturation mean')
        ls_mean_monthly_max_saturation_winter = ls_monthly_saturation_winter.select('max').mean().rename(
            'saturation max')
        ls_mean_monthly_min_saturation_winter = ls_monthly_saturation_winter.select('min').mean().rename(
            'saturation min')
        ls_mean_monthly_mean_value_winter = ls_monthly_value_winter.select('mean').mean().rename('value mean')
        ls_mean_monthly_max_value_winter = ls_monthly_value_winter.select('max').mean().rename('value max')
        ls_mean_monthly_min_value_winter = ls_monthly_value_winter.select('min').mean().rename('value min')

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
        winter_std_ndvi = landsat.get_yearly_band_std(
            ls_ndvi,
            ['NDVI'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_std_ndwi = landsat.get_yearly_band_std(
            ls_ndwi,
            ['NDWI'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_std_gcvi = landsat.get_yearly_band_std(
            ls_gcvi,
            ['GCVI'],
            begin,
            end,
            aoi,
            season='winter'
        )

        winter_ndvi_std_mean = winter_std_ndvi.select('NDVI_std').mean()
        winter_ndwi_std_mean = winter_std_ndwi.select('NDWI_std').mean()
        winter_gcvi_std_mean = winter_std_gcvi.select('GCVI_std').mean()

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
            ls_mean_monthly_mean_ndwi_greenhouses_winter,
            ls_mean_monthly_max_ndwi_greenhouses_winter,
            ls_mean_monthly_min_ndwi_greenhouses_winter,
            winter_ndvi_std_mean,
            winter_ndwi_std_mean,
            winter_gcvi_std_mean,
            slope,
        ])

        return crop_data.toBands().regexpRename('([0-9]*_)', '')


aoi = ee.FeatureCollection(f'{GEE_USER_PATH}/outline_3857')  # Load the feature collection containing the area of interest
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
    # '05': ('2004-01-01', '2006-01-01'),
    '09': ('2008-01-01', '2010-01-01'),
}

land_classes = {  # land classes to be analysed
    1: 'natural trees',
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
    'yearly',
    'summer',
    'winter',
]

for key in val_maps:
    BEGIN = years[key][0]
    END = years[key][1]

    validation_map = val_maps[key] # load validation map

    for s in season:
        crop_data = get_data(BEGIN, END, aoi, s) # prepare the seasonal data

        all_stats = []

        for cl in land_classes:
            # For each of the classes to be analyses, first select all the pixels in the validation map that correspond
            # to the class. Then convert the pixels into a multipolygon.
            land_class_vector = vector.raster_to_vector(validation_map.eq(cl), aoi)
            land_class_vector = land_class_vector.map(vector.add_area)  # calculate the areas of the created polygons
            land_class_vector = land_class_vector.filter(ee.Filter.gt('area', 10000))  # Filter out any small polygons
            # Sample points within the class area, i.e. the area that falls within the vector just created
            sample_points = ee.FeatureCollection.randomPoints(land_class_vector, 1000, 0)

            # For each point the corresponding seasonal data is then retrieved
            sample_data = crop_data.select(crop_data.bandNames()).sampleRegions(
                collection=sample_points,
                scale=30,
                tileScale=4,
            )

            def get_point_data(name):
                """Function that calculates some simple statistics for the seasonal data corresponding to each point"""
                sample_data_results_mean = sample_data.reduceColumns(
                selectors=ee.List([name]),
                reducer= ee.Reducer.mean()
                ).set('band', ee.String(name))

                sample_data_results_min = sample_data.reduceColumns(
                    selectors=ee.List([name]),
                    reducer=ee.Reducer.percentile([10])
                ).set('band', ee.String(name))

                sample_data_results_max = sample_data.reduceColumns(
                    selectors=ee.List([name]),
                    reducer=ee.Reducer.percentile([90])
                ).set('band', ee.String(name))

                sample_data_results = sample_data_results_mean.combine(
                    sample_data_results_min).combine(
                    sample_data_results_max).set('class', land_classes[cl])

                return ee.Feature(None, sample_data_results)

            sample_stats = ee.FeatureCollection(crop_data.bandNames().map(get_point_data))  # calculate stats per class

            all_stats += [sample_stats]

        export_task = ee.batch.Export.table.toDrive(  # Export the statitics to personal google drive account
            collection=ee.FeatureCollection(all_stats).flatten(),
            description=f'sample_data_{s}_{key}',
            folder=f'sample_data_validation_classes_{s}',
            fileFormat='CSV'
        )

        export_task.start()

    print(f'Finished year: {key}')

