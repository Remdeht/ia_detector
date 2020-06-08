import ee

def s2_cloudmask(image):

    qa = image.select('QA60');
    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloudBitMask = 1 << 10
    cirrusBitMask = 1 << 11

    # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))

    return image.updateMask(mask)


def rename_s2_bands(image):
    return image.rename(['B', 'G', 'R', 'NIR', 'SWIR', 'SWIR2', 'QA60'])


def get_s2_image_collection(begin_date, end_date, aoi=None):
    """
    Calls the GEE API to collect scenes from the Landsat 4 Tier 1 Surface Reflectance Libraries

    :param begin_date: Begin date for time period for scene selection
    :param end_date: End date for time period for scene selection
    :param aoi: Optional, only select scenes that cover this aoi
    :return: cloud masked GEE image collection
    """
    if aoi is None:
        return (ee.ImageCollection('COPERNICUS/S2_SR')
                .select('B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'QA60')
                .filterDate(begin_date, end_date)
                .map(rename_s2_bands)
                .map(s2_cloudmask))
    else:
        return (ee.ImageCollection('COPERNICUS/S2_SR')
                .select('B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'QA60')
                .filterBounds(aoi)
                .filterDate(begin_date, end_date)
                .map(rename_s2_bands)
                .map(s2_cloudmask))