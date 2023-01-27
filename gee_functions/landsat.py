"""
Functions related to the processing of landsat satellite scenes
"""

import ee
from monthdelta import monthdelta
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

from typing import Union


def preprocess_landsat(image: ee.Image) -> ee.Image:
    """
    TODO - check if the cloud masking is working properly
    A function that scales and masks Landsat surface reflectance images

    Based on the following post on stackoverflow, linked from the official GEE docs:
    https://gis.stackexchange.com/questions/425159/how-to-make-a-cloud-free-composite-for-landsat-8-collection-2-surface-reflectanc/425160#425160

    """
    # Develop masks for unwanted pixels (fill, cloud, cloud shadow).
    qa_mask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
    saturation_mask = image.select('QA_RADSAT').eq(0)

    #  Apply the scaling factors to the appropriate bands.
    def get_factor_img(factor_names):
        factor_list = image.toDictionary().select(factor_names).values()
        return ee.Image.constant(factor_list)

    scale_img = get_factor_img(['REFLECTANCE_MULT_BAND_.|TEMPERATURE_MULT_BAND_ST_B.*'])
    offset_img = get_factor_img(['REFLECTANCE_ADD_BAND_.|TEMPERATURE_ADD_BAND_ST_B.*'])

    scaled = image.select('SR_B.|ST_B.*').multiply(scale_img).add(offset_img)

    #  Replace original bands with scaled bands and apply masks.
    return image.addBands(scaled, None, True).updateMask(qa_mask).updateMask(saturation_mask)


# Functions to get Image Collections
def get_ls_image_collection(
        col: Union[int, str],
        begin_date: str,
        end_date: str,
        aoi: ee.FeatureCollection = None) -> ee.ImageCollection:
    """
    Calls the GEE API to collect scenes from the Landsat 4 Tier 1 Surface Reflectance Libraries

    :param col: String/Int indicating the landsat collection to use. Options: '4','5','7','8'&'9'
    :param begin_date: Begin date for time period for scene selection
    :param end_date: End date for time period for scene selection
    :param aoi: Optional, only select scenes that cover this aoi
    :return: cloud masked GEE image collection
    """

    collection_parameters = {
        '4': {
            'name': 'LANDSAT/LT04/C02/T1_L2',
            'bands': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'ST_B6'],
        },
        '5': {
            'name': 'LANDSAT/LT05/C02/T1_L2',
            'bands': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'ST_B6'],
        },
        '7': {
            'name': 'LANDSAT/LE07/C02/T1_L2',
            'bands': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'ST_B6'],
        },
        '8': {
            'name': 'LANDSAT/LC08/C02/T1_L2',
            'bands': ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'ST_B10'],
        },
        '9': {
            'name': 'LANDSAT/LC09/C02/T1_L2',
            'bands': ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'ST_B10'],
        },
    }

    col_string = collection_parameters[col]['name']
    col_bands = collection_parameters[col]['bands']

    if aoi is None:
        return ee.ImageCollection(col_string).filterDate(
            begin_date,
            end_date
        ).map(
            preprocess_landsat
        ).select(
            col_bands,
            ['B', 'G', 'R', 'NIR', 'SWIR', 'SWIR2', 'THERMAL'],
        )

    else:
        return ee.ImageCollection(col_string).filterBounds(
            aoi
        ).filterDate(
            begin_date,
            end_date
        ).map(
            preprocess_landsat
        ).select(
            col_bands,
            ['B', 'G', 'R', 'NIR', 'SWIR', 'SWIR2', 'THERMAL'],
        )


def get_ls89_image_collection(
        col: Union[int, str],
        begin_date: str,
        end_date: str,
        aoi=None) -> ee.ImageCollection:
    """
        Calls the GEE API to collect scenes from the Landsat 7 Tier 1 Surface Reflectance Libraries

        :param begin_date: Begin date for time period for scene selection
        :param end_date: End date for time period for scene selection
        :param aoi: Optional, only select scenes that cover this aoi
        :return: cloud masked GEE image collection
        """
    collection_strings = {
        '8': 'LANDSAT/LC08/C02/T1_L2',
        '9': 'LANDSAT/LC09/C02/T1_L2',
    }

    col_string = collection_strings[col]

    if aoi is None:
        return ee.ImageCollection(col_string).filterDate(
            begin_date,
            end_date
        ).map(
            preprocess_landsat
        ).select(
            ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'ST_B10'],
            ['B', 'G', 'R', 'NIR', 'SWIR', 'SWIR2', 'THERMAL'],
        )
    else:
        return ee.ImageCollection(col_string).filterBounds(
            aoi
        ).filterDate(
            begin_date,
            end_date
        ).map(
            preprocess_landsat
        ).select(
            ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'ST_B10'],
            ['B', 'G', 'R', 'NIR', 'SWIR', 'SWIR2', 'THERMAL'],
        )


def remove_edges(image: ee.Image):
    """Applies a negative buffer of 6 km to sat. scenes to remove the edges."""
    return image.clip(image.geometry().buffer(-6000))


def rename_ls_bands(image: ee.Image):
    """Renames the landsat bands"""
    return image.rename(['B', 'G', 'R', 'NIR', 'SWIR', 'THERMAL', 'SWIR2', 'pixel_qa'])


# Preprocessing
def cloud_mask_ls457(image: ee.Image):  # Cloud masking function
    """
    Performs cloud correction for Landsat 4,5 & 7 scenes based on the pixel quality.
    :param image: Landsat Scene
    :return: Cloud Corrected Landsat Scene
    """
    qa = image.select('pixel_qa')

    #  If the cloud bit (5) is set and the cloud confidence (7) is high
    #  or the cloud shadow bit is set (3), then it's a bad pixel.
    cloud = qa.bitwiseAnd(1 << 5).And(qa.bitwiseAnd(1 << 7)).Or(qa.bitwiseAnd(1 << 3))

    # Remove edge pixels that don't occur in all bands
    mask2 = image.mask().reduce(ee.Reducer.min())

    mask3 = qa.neq(96)

    return image.updateMask(cloud.Not()).updateMask(mask2).updateMask(mask3)


def cloud_mask_ls8(image: ee.Image):
    """
    Function to mask clouds based on the pixel_qa band of Landsat 8 SR data

    :param {ee.Image} image input Landsat 8 SR image
    :return {ee.Image} cloudmasked Landsat 8 image
    """

    # Bits 3 and 5 are cloud shadow and cloud, respectively.
    cloudShadowBitMask = (1 << 3)
    cloudsBitMask = (1 << 5)
    # Get the pixel QA band.
    qa = image.select('pixel_qa')
    # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0).And(qa.bitwiseAnd(cloudsBitMask).eq(0))

    return image.updateMask(mask)


def rgb_to_hsv(image: ee.Image):
    """
    Wrapper function to convert a landsat 4,5 or 5 image from RGB to HSV.

    :param image: Landsat Image to convert to the HSV color space
    :return: Image containing three bands, representing the hue, saturation and value.
    """
    image_hsv = image.select(['B3', 'B2', 'B1']).multiply(0.0001).rgbToHsv()

    return image_hsv.copyProperties(image).set('system:time_start', image.get('system:time_start'))


def create_monthly_index_images(image_collection, start_date, end_date, aoi, stats=['median']):
    """
    Generates a monthly composite for an imagecollection

    :param image_collection: EE imagecollection with satellite scenes from which the composites are to be created
    :param start_date: Date at which the image collection begins
    :param end_date: Date at which the image Collection ends
    :param aoi: Area of interest
    :param stats: list of statistics to use for the monthly composite, possibilities are: 'mean', 'max', 'min', 'median'
    :return: Returns an EE imagecollection contaning monthly NDVI Images
    """

    if not str(type(start_date)) == 'datetime.datetime' or str(type(end_date) == 'datetime.datetime'):
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            print('Please use following date format: YYYY-MM-DD')

    images = ee.List([])

    time_dif = relativedelta(end_date, start_date)
    month_dif = time_dif.years * 12 + time_dif.months

    # start_date = ee.Date(start_date)
    # end_date = ee.Date(end_date)

    for i in range(month_dif):
        start_month = start_date + monthdelta(i)
        end_month = start_date + monthdelta(i + 1) - timedelta(days=1)

        filler_data = image_collection.filter(ee.Filter.date(start_month - monthdelta(1), start_month)).merge(
            image_collection.filter(ee.Filter.date(end_month, end_month + monthdelta(1))))

        monthly_stats = []

        for stat in stats:
            if stat == 'mean':
                monthly_mean = image_collection.filter(
                    ee.Filter.date(start_month, end_month)
                ).mean().set(
                    'stat',
                    'mean'
                ).set(
                    'month',
                    start_month.month
                ).set(
                    'year',
                    start_month.year
                ).set(
                    'date_info',
                    ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}')
                ).set(
                    'system:time_start',
                    ee.Date(start_month).millis()
                )

                # monthly_mean = monthly_mean.unmask(filler_data, True).clip(aoi)
                monthly_stats += [monthly_mean]

            elif stat == 'min':
                monthly_min = image_collection.filter(
                    ee.Filter.date(
                        start_month,
                        end_month
                    )).reduce(
                    ee.Reducer.percentile(ee.List([10]))
                ).set(
                    'stat',
                    'min'
                ).set(
                    'month',
                    start_month.month
                ).set(
                    'year',
                    start_month.year
                ).set(
                    'date_info',
                    ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}')
                ).set(
                    'system:time_start',
                    ee.Date(start_month).millis()
                )

                # monthly_min = monthly_min.unmask(filler_data.reduce(ee.Reducer.percentile(ee.List([10]))), True).clip(
                #     aoi)
                monthly_stats += [monthly_min]
            elif stat == 'max':
                monthly_max = image_collection.filter(
                    ee.Filter.date(start_month, end_month)).reduce(
                    ee.Reducer.percentile(ee.List([90]))
                ).set(
                    'stat',
                    'max'
                ).set(
                    'month',
                    start_month.month
                ).set(
                    'year',
                    start_month.year
                ).set(
                    'date_info',
                    ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}')
                ).set(
                    'system:time_start',
                    ee.Date(start_month).millis()
                )

                # monthly_max = monthly_max.unmask(filler_data.reduce(ee.Reducer.percentile(ee.List([90]))), True).clip(
                #     aoi)
                monthly_stats += [monthly_max]
            elif stat == 'median':
                monthly_median = image_collection.filter(
                    ee.Filter.date(
                        start_month,
                        end_month
                    )).median().set(
                    'stat',
                    'median'
                ).set(
                    'month',
                    datetime.strftime(start_month, "%b")
                ).set(
                    'year',
                    start_month.year
                ).set(
                    'date_info',
                    ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}')
                ).set(
                    'system:time_start',
                    ee.Date(start_month).millis()
                )

                if monthly_median.bandNames().size().getInfo() == 0:
                    print(f'No data available for: {datetime.strftime(start_month, "%b")} {start_month.year}')
                    continue

                # monthly_median = monthly_median.unmask(filler_data.median(), True).clip(aoi)

                monthly_stats += [monthly_median]

            else:
                raise ValueError("Unknown statistic entered, please pick from: ['mean', 'max', 'min', 'median'].")

        for ind, st in enumerate(monthly_stats):
            if ind == 0:
                img = monthly_stats[0]
            else:
                img = img.addBands(st)

        images = images.add(img)

    return ee.ImageCollection(images)


if __name__ == '__main__':
    import httplib2

    ee.Initialize(http_transport=httplib2.Http())

    aoi = ee.Geometry.Polygon(
        [[[-1.4572492923062508, 37.93351644908467],
          [-1.4572492923062508, 37.51205504786782],
          [-0.6401411380093758, 37.51205504786782],
          [-0.6401411380093758, 37.93351644908467]]],
        None,
        False
    )
    images = {}

    dates = {
        '4': ['1990-04-01', '1990-10-01'],
        '5': ['2001-05-01', '2001-10-01'],
        '7': ['2017-04-01', '2017-10-01'],
        '8': ['2019-04-01', '2019-10-01'],
        '9': ['2022-04-01', '2022-06-01'],
    }

    for ls in ['4', '5', '7', '8', '9']:
        test = get_ls_image_collection(
            ls,
            dates[ls][0],
            dates[ls][1],
            aoi=aoi
        ).median()

        min_val = test.reduceRegion(
            reducer=ee.Reducer.min(),
            geometry=aoi,
            scale=30,
            maxPixels=1e14,
        ).getInfo()

        max_val = test.reduceRegion(
            reducer=ee.Reducer.max(),
            geometry=aoi,
            scale=30,
            maxPixels=1e14,

        ).getInfo()

        print(min_val)
        print(max_val)

        # min_val = min(min_val.values())
        # max_val = max(max_val.values())
        #
        # print(min_val, max_val)
    #
    #     images[f'LS_{ls}'] = test.visualize(**{'bands': ['R', 'G', 'B'], 'min': min_val, 'max': max_val}).getMapId()

    # for ls in ['5']:
    #     test = get_ls_image_collection(
    #         ls,
    #         dates[ls][0],
    #         dates[ls][1],
    #         aoi=aoi
    #     )
    #
    #     monthly = create_monthly_index_images(test, dates[ls][0], dates[ls][1], aoi, stats=['median', 'min', 'max'])
    #
    # images[f'LS_{ls}'] = monthly.first().visualize(**{'bands': ['R', 'G', 'B'], 'min': 0.0015794864205896308, 'max': 0.29098365367301077}).getMapId()
    #
    # create_folium_map(
    #     images=images,
    #     name='monthly'
    # )
