"""
Functions related to the processing of landsat satellite scenes
"""

import ee
from monthdelta import monthdelta
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta


# Functions to get Image Collections
def get_ls4_image_collection(begin_date, end_date, aoi=None):
    """
    Calls the GEE API to collect scenes from the Landsat 4 Tier 1 Surface Reflectance Libraries

    :param begin_date: Begin date for time period for scene selection
    :param end_date: End date for time period for scene selection
    :param aoi: Optional, only select scenes that cover this aoi
    :return: cloud masked GEE image collection
    """
    if aoi is None:
        return (ee.ImageCollection('LANDSAT/LT04/C01/T1_SR')
                .select('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'pixel_qa')
                .filterDate(begin_date, end_date)
                .map(rename_ls_bands)
                .map(cloud_mask_ls457))
    else:
        return (ee.ImageCollection('LANDSAT/LT04/C01/T1_SR')
                .select('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'pixel_qa')
                .filterBounds(aoi)
                .filterDate(begin_date, end_date)
                .map(rename_ls_bands)
                .map(cloud_mask_ls457))


def get_ls5_image_collection(begin_date, end_date, aoi=None):
    """
        Calls the GEE API to collect scenes from the Landsat 5 Tier 1 Surface Reflectance Libraries

        :param begin_date: Begin date for time period for scene selection
        :param end_date: End date for time period for scene selection
        :param aoi: Optional, only select scenes that cover this aoi
        :return: cloud masked GEE image collection
        """
    if aoi is None:
        return (ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')
                .select('B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'pixel_qa')
                .filterDate(begin_date, end_date)
                .map(rename_ls_bands)
                .map(cloud_mask_ls457))
    else:
        return (ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')
                .select('B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'pixel_qa')
                .filterBounds(aoi)
                .filterDate(begin_date, end_date)
                .map(rename_ls_bands)
                .map(cloud_mask_ls457))


def get_ls7_image_collection(begin_date, end_date, aoi=None):
    """
        Calls the GEE API to collect scenes from the Landsat 7 Tier 1 Surface Reflectance Libraries

        :param begin_date: Begin date for time period for scene selection
        :param end_date: End date for time period for scene selection
        :param aoi: Optional, only select scenes that cover this aoi
        :return: cloud masked GEE image collection
        """
    if aoi is None:
        return (ee.ImageCollection('LANDSAT/LE07/C01/T1_SR')
                .select('B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'pixel_qa')
                .filterDate(begin_date, end_date)
                .map(rename_ls_bands)
                .map(cloud_mask_ls457))
    else:
        return (ee.ImageCollection('LANDSAT/LE07/C01/T1_SR')
                .select('B1', 'B2', 'B3', 'B4', 'B5', 'B6','B7', 'pixel_qa')
                .filterBounds(aoi)
                .filterDate(begin_date, end_date)
                .map(rename_ls_bands)
                .map(cloud_mask_ls457))


def get_ls8_image_collection(begin_date, end_date, aoi=None):
    """
        Calls the GEE API to collect scenes from the Landsat 7 Tier 1 Surface Reflectance Libraries

        :param begin_date: Begin date for time period for scene selection
        :param end_date: End date for time period for scene selection
        :param aoi: Optional, only select scenes that cover this aoi
        :return: cloud masked GEE image collection
        """
    if aoi is None:
        return (ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')
                .filterDate(begin_date, end_date)
                .select('B2', 'B3', 'B4', 'B5', 'B6', 'B10', 'B7', 'pixel_qa')
                .map(rename_ls_bands)
                .map(cloud_mask_ls8))
    else:
        return (ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')
                .select('B2', 'B3', 'B4', 'B5', 'B6', 'B10', 'B7', 'pixel_qa')
                .filterDate(begin_date, end_date).filterBounds(aoi)
                .map(rename_ls_bands)
                .map(cloud_mask_ls8))


def remove_edges(image):
    """Applies a negative buffer of 6 km to sat. scenes to remove the edges."""
    return image.clip(image.geometry().buffer(-6000))


def rename_ls_bands(image):
    """Renames the landsat bands"""
    return image.rename(['B', 'G', 'R', 'NIR', 'SWIR', 'THERMAL', 'SWIR2', 'pixel_qa'])

# Preprocessing
def cloud_mask_ls457(image):  # Cloud masking function
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


def cloud_mask_ls8(image):
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


def rgb_to_hsv(image):
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

    for i in range(month_dif):
        start_month = start_date + monthdelta(i)
        end_month = start_date + monthdelta(i + 1) - timedelta(days=1)

        filler_data = image_collection.filter(ee.Filter.date(start_month - monthdelta(1), start_month)).merge(
            image_collection.filter(ee.Filter.date(end_month, end_month + monthdelta(1))))


        monthly_stats = []

        for stat in stats:
            if stat == 'mean':
                monthly_mean = (image_collection.filter(
                        ee.Filter.date(start_month, end_month))
                                    .mean()
                                    .set('month', start_month.month)
                                    .set('year', start_month.year)
                                    .set('date_info',
                                         ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                    .set('system:time_start', ee.Date(start_month).millis())
                                    )
                monthly_mean = monthly_mean.unmask(filler_data, True).clip(aoi)
                monthly_stats += [monthly_mean]
            elif stat == 'min':
                monthly_min = (image_collection.filter(
                        ee.Filter.date(start_month, end_month))
                                   .reduce(ee.Reducer.percentile(ee.List([10])))
                                   .rename(f'min')
                                   .set('month', start_month.month)
                                   .set('year', start_month.year)
                                   .set('date_info',
                                        ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                   .set('system:time_start', ee.Date(start_month).millis())
                                   )
                monthly_min = monthly_min.unmask(filler_data.reduce(ee.Reducer.percentile(ee.List([10]))), True).clip(aoi)
                monthly_stats += [monthly_min]
            elif stat == 'max':
                monthly_max = (image_collection.filter(
                        ee.Filter.date(start_month, end_month))
                                   .reduce(ee.Reducer.percentile(ee.List([90])))
                                   .rename(f'max')
                                   .set('month', start_month.month)
                                   .set('year', start_month.year)
                                   .set('date_info',
                                        ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                   .set('system:time_start', ee.Date(start_month).millis())
                                   )

                monthly_max = monthly_max.unmask(filler_data.reduce(ee.Reducer.percentile(ee.List([90]))), True).clip(aoi)
                monthly_stats += [monthly_max]
            elif stat == 'median':

                monthly_median = (image_collection.filter(
                    ee.Filter.date(start_month, end_month))
                                  .qualityMosaic('pixel_qa')
                                  .clip(aoi)
                                  .set('month', start_month.month)
                                  .set('year', start_month.year)
                                  .set('date_info',
                                       ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                  .set('system:time_start', ee.Date(start_month).millis())
                                  )

                if monthly_median.bandNames().size().getInfo() == 0:
                    print(f'No data available for: {datetime.strftime(start_month, "%b")} {start_month.year}')
                    continue

                monthly_median = monthly_median.unmask(filler_data.median(), True).clip(aoi)

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





