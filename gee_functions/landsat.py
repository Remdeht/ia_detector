import ee
from monthdelta import monthdelta
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
import folium
from .gap_fill import gap_fill
import pandas as pd


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
    return image.clip(image.geometry().buffer(-6000))


def rename_ls_bands(image):
    return image.rename(['B', 'G', 'R', 'NIR', 'SWIR', 'THERMAL', 'SWIR2', 'pixel_qa'])


# Preprocessing
def cloud_mask_ls457(image):  # Cloud masking function
    """
    Perform cloud correction for Landsat 4,5 & 7 scenes based on the pixel quality.
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


# spectral indices
def add_ndvi_ls457(image):
    """
    Calculates the Normalized Difference Vegetation Index(NDVI) for Landsat 4,5 & 7 Scenes
    """
    ndvi = image.normalizedDifference(['B4', 'B3']).rename('NDVI');
    return image.addBands(ndvi)


def add_ndwi_ls457(image):
    """
    Calculates the Normalized Difference Water Index(NDWI) for Landsat 4,5 & 7 Scenes
    """
    ndvi = image.normalizedDifference(['B4', 'B5']).rename('NDWI');
    return image.addBands(ndvi)


def add_ndwi_mcfeeters_ls457(image):
    ndwi = image.normalizedDifference(['B2', 'B5']).rename('NDWIGH')
    return image.addBands(ndwi)


def add_ndbi_ls457(image):
    ndbi = image.normalizedDifference(['B5', 'B4']).rename('NDBI')
    return image.addBands(ndbi)


def add_bu_ls457(image):
    bu = image.select('NDBI').subtract(image.select('NDVI')).rename('BU')
    return image.addBands(bu)


def add_ndvi_ls123(image):
    ndvi = image.normalizedDifference(['B6', 'B5']).rename('NDVI')
    return image.addBands(ndvi)


def add_evi_ls457(image):
    """
    Calculates the Enhanced Vegetation Index(EVI) for Landsat 4,5 & 7 Scenes
    """
    evi = image.expression(
        '2.5 * ((NIR-RED) / (NIR + (6 * RED) - (7.5* BLUE) + 1))', {
            'NIR': image.select('B4'),
            'RED': image.select('B3'),
            'BLUE': image.select('B1')
        }).rename('EVI')

    return image.addBands(evi)


def add_savi_ls457(image):
    """
    Calculates the Soil Adjusted Vegetation Index(SAVI) for Landsat 4,5 & 7 Scenes
    """
    savi = image.expression(
        '((1 + 0.5) * (NIR-RED) / (NIR + RED + 0.5))', {
            'NIR': image.select('B4'),
            'RED': image.select('B3')
        }).rename('SAVI')

    return image.addBands(savi)


def add_gi_ls457(image):
    """
    Calculates the Greenness Index(GI) for Landsat 4,5 & 7 Scenes
    """
    gi = image.expression(
        'NIR / G', {
            'NIR': image.select('B4'),
            'G': image.select('B2'),
        }
    ).rename('GI')

    return image.addBands(gi)


def add_gcvi_ls457(image):
    """
    Calculates the Green Chlorophyll Vegetation Index (GCVI) for Landsat 4,5 & 7 Imagery
    """
    gcvi = image.expression(
        '(NIR/G) - 1', {
            'NIR': image.select('B4'),
            'G': image.select('B2'),
        }
    ).rename('GCVI')

    return image.addBands(gcvi)


def add_wgi_ls457(image):
    wgi = image.expression(
        'NDWI * GI', {
            'NDWI': image.select('NDWI'),
            'GI': image.select('GCVI'),
        }
    ).rename('WGI')

    return image.addBands(wgi)


def rgb_to_hsv(image):
    """
    Wrapper to convert a landsat 4,5 or 5 image from RGB to HSV.

    :param image: Landsat Image to convert to the HSV color space
    :return: Image containing three bands, representing the hue, saturation and value.
    """
    image_hsv = image.select(['B3', 'B2', 'B1']).multiply(0.0001).rgbToHsv()

    return image_hsv.copyProperties(image).set('system:time_start', image.get('system:time_start'))


def create_monthly_index_images(image_collection, band, start_date, end_date, aoi, stats=['mean'], bimonthly=False):
    """
    Generate monthly NDVI images for a aoi
    :param image_collection: EE imagecollection of NDVI images to be used for the calculation of monthly median NDVI
    :param band: name of the band to select
    :param start_date: Date at which the image collection begins
    :param end_date: Date at which the image Collection ends
    :param aoi: Area of interest
    :param stat: list of statistics to calculate, possibilities are: 'mean', 'max', 'min', 'median'
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

        ls_5 = get_ls5_image_collection(start_month - monthdelta(1), start_month, aoi).merge(
            get_ls5_image_collection(end_month, end_month + monthdelta(1))
        )
        ls_7 = get_ls7_image_collection(start_month - monthdelta(1), start_month, aoi).merge(
            get_ls7_image_collection(end_month, end_month + monthdelta(1))
        )
        ls_8 = get_ls8_image_collection(start_month - monthdelta(1), start_month, aoi).merge(
            get_ls8_image_collection(end_month, end_month + monthdelta(1))
        )

        filler_data = ls_5.merge(ls_7).merge(ls_8)

        monthly_stats = []

        for stat in stats:
            if stat == 'mean':
                monthly_mean = (image_collection.filter(
                        ee.Filter.date(start_month, end_month))
                                    .select(band)
                                    .mean()
                                    .rename(f'mean')
                                    .set('month', start_month.month)
                                    .set('year', start_month.year)
                                    .set('date_info',
                                         ee.String(f'{band}_{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                    .set('system:time_start', ee.Date(start_month).millis())
                                    )
                monthly_mean = monthly_mean.unmask(filler_data, True).clip(aoi)
                monthly_stats += [monthly_mean]
            elif stat == 'min':
                monthly_min = (image_collection.filter(
                        ee.Filter.date(start_month, end_month))
                                   .select(band)
                                   .reduce(ee.Reducer.percentile(ee.List([10])))
                                   .rename(f'min')
                                   .set('month', start_month.month)
                                   .set('year', start_month.year)
                                   .set('date_info',
                                        ee.String(f'{band}_{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                   .set('system:time_start', ee.Date(start_month).millis())
                                   )
                monthly_min = monthly_min.unmask(filler_data.reduce(ee.Reducer.percentile(ee.List([10]))), True).clip(aoi)
                monthly_stats += [monthly_min]
            elif stat == 'max':
                monthly_max = (image_collection.filter(
                        ee.Filter.date(start_month, end_month))
                                   .select(band)
                                   .reduce(ee.Reducer.percentile(ee.List([90])))
                                   .rename(f'max')
                                   .set('month', start_month.month)
                                   .set('year', start_month.year)
                                   .set('date_info',
                                        ee.String(f'{band}_{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                   .set('system:time_start', ee.Date(start_month).millis())
                                   )

                monthly_max = monthly_max.unmask(filler_data.reduce(ee.Reducer.percentile(ee.List([90]))), True).clip(aoi)
                monthly_stats += [monthly_max]
            elif stat == 'median':
                monthly_median = (image_collection.filter(
                    ee.Filter.date(start_month, end_month))
                                  .select(band)
                                  .map(remove_edges)
                                  .median()
                                  .clip(aoi)
                                  .rename(f'median')
                                  .set('month', start_month.month)
                                  .set('year', start_month.year)
                                  .set('date_info',
                                       ee.String(f'{band}_{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                  .set('system:time_start', ee.Date(start_month).millis())
                                  )



                monthly_median = gap_fill(monthly_median, filler_data.median().rename('median'), 17, False).clip(aoi)
                monthly_median = monthly_median.unmask(filler_data.median(), True).clip(aoi)



                monthly_stats += [monthly_median]

            else:
                raise ValueError("Unknown statistic entered, please pick from: ['mean', 'max', 'min', 'median'].")

        for ind, st in enumerate(monthly_stats):
            if bimonthly:
                img = st
            else:
                if ind == 0:
                    img = monthly_stats[0]
                else:
                    img = img.addBands(st)

        images = images.add(img)

    return ee.ImageCollection(images)



def create_monthly_index_images_v2(image_collection, start_date, end_date, aoi, stats=['mean'], bimonthly=False):
    """
    Generate monthly images for a aoi
    :param image_collection: EE imagecollection of NDVI images to be used for the calculation of monthly median NDVI
    :param band: name of the band to select
    :param start_date: Date at which the image collection begins
    :param end_date: Date at which the image Collection ends
    :param aoi: Area of interest
    :param stat: list of statistics to calculate, possibilities are: 'mean', 'max', 'min', 'median'
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
                                  # .regexpRename('(.*[A-Z0-9])$', 'median_$1')
                                  .set('month', start_month.month)
                                  .set('year', start_month.year)
                                  .set('date_info',
                                       ee.String(f'{datetime.strftime(start_month, "%b")}_{start_month.year}'))
                                  .set('system:time_start', ee.Date(start_month).millis())
                                  )

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


def create_yearly_ndvi_images(image_collection, start_date, end_date, aoi, folium_map):
    if not str(type(start_date)) == 'datetime.datetime' or str(type(end_date) == 'datetime.datetime'):
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            print('Please use following date format: YYYY-MM-DD')

    images = ee.List([])

    time_dif = relativedelta(end_date, start_date)
    year_dif = time_dif.years
    if time_dif.months != 0:
        year_dif + 1

    for i in range(year_dif + 1):
        if i == 0:
            start_year = start_date
            end_year = datetime(start_date.year, 12, 31, 23, 59, 59)
        else:
            start_year = datetime(start_date.year + i, 1, 1, 0, 0, 0)
            end_year = datetime(start_date.year + i, 12, 31, 23, 59, 59)

        yearly_ndvi = image_collection.filter(
            ee.Filter.date(start_year, end_year)) \
            .select('NDVI') \
            .mean() \
            .clip(aoi) \
            .set('year', start_year.year).set(
            'system:time_start', ee.Date(start_year).millis())

        images = images.add(yearly_ndvi)

        image = yearly_ndvi.getMapId(get_vis_params_ndvi())
        folium.TileLayer(
            tiles=image['tile_fetcher'].url_format,
            attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
            overlay=True,
            name='%i' % start_year.year,
        ).add_to(folium_map)

    return ee.ImageCollection(images), folium_map


def get_yearly_band_std(image_collection, band_names, start_date, end_date, aoi, season=None):
    """
    Calculates the standard deviation for each pixel for each image in an GEE ImageCollection per year or
    summer/winter season

    :param image_collection: GEE image_collection object
    :param band_names: image bands for which to calculate the yearly standard deviation
    :param start_date: begin date for period of interest
    :param end_date: end date for period of interest
    :param aoi: area of interest for which to calculate the standard deviation
    :return: three GEE image_collection objects containing yearly std maps for the entire year, summer and winter
    """

    # Convert the start and end date to datetime objects if they are not already.
    if not str(type(start_date)) == 'datetime.datetime' or str(type(end_date) == 'datetime.datetime'):
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            print('Please use following date format: YYYY-MM-DD')

    # Initiate empty GEE arrays to store std maps in
    images_year = []
    images_summer = []
    images_winter = []

    time_dif = relativedelta(end_date, start_date)  # Calculate the no of years, a map will be created for each year

    for i in range(time_dif.years):
        for band_name in band_names:  # Std Maps should be calculated for each specified band
            begin_year = start_date.replace(year=start_date.year + i)
            end_year = start_date.replace(year=start_date.year + i + 1)

            if season is None:
                # collect all images within a year
                yearly_images = image_collection.filter(
                    ee.Filter.date(begin_year, end_year)) \
                    .select(band_name)

                # Calculate std deviation maps using the GEE Reducer, and then clip it to the area of interest.
                std_image = yearly_images.reduce(ee.Reducer.stdDev()).clip(aoi).set(
                    'year', begin_year.year).set(
                    'system:time_start', ee.Date(begin_year).millis()).rename(
                    f'{band_name}_std'
                )
                # Add the std. deviation maps to the corresponding arrays
                # finally the arrays are converted to ImageCollections
                images_year += [std_image]

            # collect all images for the summer season
            elif season == 'summer':
                summer_images = image_collection.filter(
                    ee.Filter.date(
                        begin_year.replace(month=4),
                        end_year.replace(month=10))
                ).select(band_name)

                std_image_summer = summer_images.reduce(ee.Reducer.stdDev()).clip(aoi).set(
                    'year', start_date.year).set(
                    'season', f'summer {begin_year.year}').set(
                    'system:time_start', ee.Date(begin_year.replace(month=7)).millis()).rename(
                    f'{band_name}_std'
                )
                images_summer += [std_image_summer]

            # collect all images for the winter season
            elif season == 'winter':
                winter_images = image_collection.filter(
                    ee.Filter.date(
                        begin_year.replace(month=10),
                        end_year.replace(year=end_year.year + 1, month=4))
                ).select(band_name)

                std_image_winter = winter_images.reduce(ee.Reducer.stdDev()).clip(aoi).set(
                    'year', start_date.year).set(
                    'season', f'winter {begin_year.year} - {begin_year.year + 1}').set(
                    'system:time_start', ee.Date(begin_year).millis()).rename(
                    f'{band_name}_std'
                )

                images_winter += [std_image_winter]

    if season is None:
        return ee.ImageCollection(images_year)
    elif season is 'summer':
        return ee.ImageCollection(images_summer)
    elif season == 'winter':
        return ee.ImageCollection(images_winter)


def get_ic_statistics(image_collection, aoi):
    """
    Calculates the pixel statistics for pixels within a given area of interest for each image in the image collection

    :param image_collection: GEE image collection containing the images for which the statistics will be calculated
    :param aoi: GEE feature or feature collection providing the extent within which the statistics will be calculated
    :return: GEE feature collection containing the mean, 10th & 90th percentile(min, max), median, std Dev and pix count
    for pixels within the specified area of interest
    """

    # Functions to calculate feature statistics using the GEE API
    def get_mean(image):
        dict = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=30
        )
        return ee.Feature(None, dict).set('system:time_start', image.date()).set('stat', 'mean')

    def get_min(image):
        dict = image.reduceRegion(
            reducer=ee.Reducer.percentile(ee.List([10])),
            geometry=aoi,
            scale=30
        )
        return ee.Feature(None, dict).set('system:time_start', image.date()).set('stat', 'min')

    def get_max(image):
        dict = image.reduceRegion(
            reducer=ee.Reducer.percentile(ee.List([90])),
            geometry=aoi,
            scale=30
        )
        return ee.Feature(None, dict).set('system:time_start', image.date()).set('stat', 'max')

    def get_median(image):
        dict = image.reduceRegion(
            reducer=ee.Reducer.median(),
            geometry=aoi,
            scale=30
        )
        return ee.Feature(None, dict).set('system:time_start', image.date()).set('stat', 'median')

    def get_stdDev(image):
        dict = image.reduceRegion(
            reducer=ee.Reducer.stdDev(),
            geometry=aoi,
            scale=30
        )
        return ee.Feature(None, dict).set('system:time_start', image.date()).set('stat', 'stdDev')

    def get_count(image):
        dict = image.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=aoi,
            scale=30
        )
        return ee.Feature(None, dict).set('system:time_start', image.date()).set('stat', 'count')

    # Calculate aoi statistics for all images in image collection
    ic_mean = ee.FeatureCollection(image_collection.map(get_mean))
    ic_max = ee.FeatureCollection(image_collection.map(get_max))
    ic_min = ee.FeatureCollection(image_collection.map(get_min))
    ic_median = ee.FeatureCollection(image_collection.map(get_median))
    ic_stdDev = ee.FeatureCollection(image_collection.map(get_stdDev))
    ic_count = ee.FeatureCollection(image_collection.map(get_count))

    # Combine all statistics into a single feature collection
    ic_stats = ee.FeatureCollection([
        ic_mean,
        ic_max,
        ic_min,
        ic_median,
        ic_stdDev,
        ic_count,
    ]).flatten()

    return ic_stats


def get_monthly_ic(image_collection, band_name, start_date, end_date, aoi):
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
        print(f'Starting iteration {i}')

        start_month = start_date + monthdelta(i)
        end_month = start_date + monthdelta(i + 1) - timedelta(days=1)

        monthly_stats = image_collection.filter(
            ee.Filter.date(start_month, end_month)) \
            .select(band_name) \
            .mean() \
            .clip(aoi) \
            .set('month', start_month.month) \
            .set('year', start_month.year). \
            set('system:time_start', ee.Date(start_month).millis())

        images = images.add(monthly_stats)

    return ee.ImageCollection(images)


def get_yearly_ndvi_statistics(image_collection, start_date, end_date, aoi):
    if not str(type(start_date)) == 'datetime.datetime' or str(type(end_date) == 'datetime.datetime'):
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            print('Please use following date format: YYYY-MM-DD')

    df = pd.DataFrame(columns=['Year',
                               'mean NDVI',
                               'min NDVI',
                               'max NDVI',
                               'median NDVI'
                               ])

    images = ee.List([])

    time_dif = relativedelta(end_date, start_date)
    year_dif = time_dif.years
    if time_dif.months != 0:
        year_dif + 1

    for i in range(year_dif + 1):
        if i == 0:
            start_year = start_date
            end_year = datetime(start_date.year, 12, 31, 23, 59, 59)
        else:
            start_year = datetime(start_date.year + i, 1, 1, 0, 0, 0)
            end_year = datetime(start_date.year + i, 12, 31, 23, 59, 59)

        yearly_ndvi = image_collection.filter(ee.Filter.date(start_year, end_year)) \
            .select('NDVI') \
            .mean() \
            .clip(aoi) \
            .set('year', start_year.year).set(
            'system:time_start', ee.Date(start_year).millis())

        images = images.add(yearly_ndvi)

        mean_ndvi = yearly_ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=30
        )

        try:
            value_check = mean_ndvi.getInfo()['NDVI']
        except KeyError:
            df.loc[i] = [start_year.year,
                         'NaN',
                         'NaN',
                         'NaN',
                         'NaN'
                         ]
        else:

            min_ndvi = yearly_ndvi.reduceRegion(
                reducer=ee.Reducer.percentile(ee.List([10])),
                geometry=aoi,
                scale=30
            )

            max_ndvi = yearly_ndvi.reduceRegion(
                reducer=ee.Reducer.percentile(ee.List([90])),
                geometry=aoi,
                scale=30
            )

            median_ndvi = yearly_ndvi.reduceRegion(
                reducer=ee.Reducer.median(),
                geometry=aoi,
                scale=30
            )

            df.loc[i] = [start_year.year,
                         mean_ndvi.getInfo()['NDVI'],
                         min_ndvi.getInfo()['NDVI'],
                         max_ndvi.getInfo()['NDVI'],
                         median_ndvi.getInfo()['NDVI']
                         ]

    return ee.ImageCollection(images), df


def join_precipitation(image_collection, start_date, end_date, aoi):
    if not str(type(start_date)) == 'datetime.datetime' or str(type(end_date) == 'datetime.datetime'):
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            print('Please use following date format: YYYY-MM-DD')

    time_dif = relativedelta(end_date, start_date)

    pr_added = ee.List([])

    for year in range(0, time_dif.years):
        adj_start_date = ee.Date(start_date).advance(year, 'years')

        begin_year = ee.Date(adj_start_date).advance(-1, 'months')
        end_year = ee.Date(adj_start_date).advance(1, 'years')

        yearly_pr = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE').filterDate(begin_year, end_year) \
            .filterBounds(aoi).select('pr').sum()

        for m in range(0, 12):
            start_date_ndvi = adj_start_date.advance(m, 'months')
            start_date_pr = start_date_ndvi.advance(-1, 'months')
            filtered_image = image_collection.filterDate(start_date_ndvi, start_date_ndvi.advance(1, 'months')).median()
            pr = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE').filterDate(start_date_pr, start_date_ndvi) \
                .filterBounds(aoi).select('pr').mean()
            pr = pr.divide(yearly_pr)

            filtered_image = filtered_image.addBands(pr).set('system:time_start', ee.Date(start_date_ndvi).millis())\
                .set('month', (m+1))
            pr_added = pr_added.add(filtered_image.clip(aoi))

    return ee.ImageCollection(pr_added)


def ndvi_precipitation_correction(image):
    pr_img = image.select('NDVI').multiply(
        image.select('NDVI').subtract(image.select('pr')).divide(
            image.select('NDVI').add(image.select('pr')))) \
        .rename('NDVI_pr')

    return image.addBands(pr_img)

def create_folium_map(images, name=None, coords=[20, 0], zoom=3, height=5000):
    """
    Creates a html file containing a folium map containing specified EE image

    :param images: Dictionary of EE images to add to folium map
    :param name: name of the final html file, if None the map is not saved
    :param coords: coordinates for the center of the folium map
    :param zoom:starting zoom level for the folium map
    :param height: starting height for the folium map
    """
    folium_map = folium.Map(location=coords, zoom_start=zoom, height=height, control_scale=True)

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        overlay=True,
        control=True
    ).add_to(folium_map)

    for key in images:
        folium.TileLayer(
            tiles=images[key]['tile_fetcher'].url_format,
            attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
            overlay=True,
            name=key,
        ).add_to(folium_map)

    folium_map.add_child(folium.LayerControl())

    if name is not None:
        folium_map.save(f'{name}.html')

    return folium_map
