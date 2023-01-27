import ee
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from monthdelta import monthdelta


def s2_cloudmask(image: ee.Image) -> ee.Image:
    qa = image.select('QA60');
    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloudBitMask = 1 << 10
    cirrusBitMask = 1 << 11

    # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))

    return image.updateMask(mask).multiply(0.0001)


def rename_s2_bands(image: ee.Image) -> ee.Image:
    return image.rename(['B', 'G', 'R', 'NIR', 'SWIR2', 'SWIR', 'QA60'])


def get_s2_image_collection(begin_date, end_date, aoi=None):
    """
    Calls the GEE API to collect scenes from the Landsat 4 Tier 1 Surface Reflectance Libraries

    :param begin_date: Begin date for time period for scene selection
    :param end_date: End date for time period for scene selection
    :param aoi: Optional, only select scenes that cover this aoi
    :return: cloud masked GEE image collection
    """
    if aoi is None:
        return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')\
                 .map(s2_cloudmask)\
                 .select('B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'QA60')\
                 .filterDate(begin_date, end_date)\
                 .map(rename_s2_bands)

    else:
        return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                 .map(s2_cloudmask)\
                 .select('B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'QA60')\
                 .filterBounds(aoi)\
                 .filterDate(begin_date, end_date)\
                 .map(rename_s2_bands)


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
                                  .median()
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
