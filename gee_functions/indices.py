import ee

# spectral indices
def add_ndvi(image):
    """
    Calculates the Normalized Difference Vegetation Index(NDVI) for Landsat 4,5 & 7 Scenes
    """
    ndvi = image.normalizedDifference(['NIR', 'R']).rename('NDVI');
    return image.addBands(ndvi)


def add_ndwi(image):
    """
    Calculates the Normalized Difference Water Index(NDWI) for Landsat 4,5 & 7 Scenes
    """
    ndvi = image.normalizedDifference(['NIR', 'SWIR']).rename('NDWI');
    return image.addBands(ndvi)


def add_ndwi_swir_2(image):
    """
    Calculates the Normalized Difference Water Index(NDWI) for Landsat 4,5 & 7 Scenes
    """
    ndvi = image.normalizedDifference(['NIR', 'SWIR2']).rename('NDWI2');
    return image.addBands(ndvi)


def add_ndwi_mcfeeters(image):
    ndwi = image.normalizedDifference(['G', 'SWIR']).rename('NDWIGH')
    return image.addBands(ndwi)


def add_ndbi(image):
    ndbi = image.normalizedDifference(['SWIR', 'NIR']).rename('NDBI')
    return image.addBands(ndbi)


def add_bu(image):
    bu = image.select('NDBI').subtract(image.select('NDVI')).rename('BU')
    return image.addBands(bu)


def add_evi(image):
    """
    Calculates the Enhanced Vegetation Index(EVI) for Landsat 4,5 & 7 Scenes
    """
    evi = image.expression(
        '2.5 * ((NIR-RED) / (NIR + (6 * RED) - (7.5* BLUE) + 1))', {
            'NIR': image.select('NIR'),
            'RED': image.select('R'),
            'BLUE': image.select('B')
        }).rename('EVI')

    return image.addBands(evi)


def add_savi(image):
    """
    Calculates the Soil Adjusted Vegetation Index(SAVI) for Landsat 4,5 & 7 Scenes
    """
    savi = image.expression(
        '((1 + 0.5) * (NIR-RED) / (NIR + RED + 0.5))', {
            'NIR': image.select('NIR'),
            'RED': image.select('R')
        }).rename('SAVI')

    return image.addBands(savi)


def add_gi(image):
    """
    Calculates the Greenness Index(GI) for Landsat 4,5 & 7 Scenes
    """
    gi = image.expression(
        'NIR / G', {
            'NIR': image.select('NIR'),
            'G': image.select('G'),
        }
    ).rename('GI')

    return image.addBands(gi)


def add_gcvi(image):
    """
    Calculates the Green Chlorophyll Vegetation Index (GCVI) for Landsat 4,5 & 7 Imagery
    """
    gcvi = image.expression(
        '(NIR/G) - 1', {
            'NIR': image.select('NIR'),
            'G': image.select('G'),
        }
    ).rename('GCVI')

    return image.addBands(gcvi)


def add_wgi(image):
    wgi = image.expression(
        'NDWI * GI', {
            'NDWI': image.select('NDWI'),
            'GI': image.select('GCVI'),
        }
    ).rename('WGI')

    return image.addBands(wgi)


