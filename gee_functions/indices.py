"""
All the functions for calculating vegetation indices based on satellite imagery
"""
import ee


def add_ndvi(image: ee.Image):
    """
    Calculates the Normalized Difference Vegetation Index (NDVI)
    """
    ndvi = image.normalizedDifference(['NIR', 'R']).rename('NDVI');
    return image.addBands(ndvi)


def add_ndwi(image: ee.Image):
    """
    Calculates the Normalized Difference Water Content Index (NDWI) as proposed by Gao (1996)
    """
    ndvi = image.normalizedDifference(['NIR', 'SWIR']).rename('NDWI');
    return image.addBands(ndvi)


def add_ndwi_mcfeeters(image: ee.Image):
    """
    Calculates the Normalized Difference Water Index (NDWI) as proposed by McFeeters (1996)
    """
    ndwi = image.normalizedDifference(['G', 'SWIR']).rename('NDWBI')
    return image.addBands(ndwi)


def add_ndbi(image: ee.Image):
    """
    Calculates the Normalized Difference Built-up Index (NDBI) as proposed by McFeeters (1996)
    """
    ndbi = image.normalizedDifference(['SWIR', 'NIR']).rename('NDBI')
    return image.addBands(ndbi)


def add_evi(image: ee.Image):
    """
    Calculates the Enhanced Vegetation Index (EVI)
    """
    evi = image.expression(
        '2.5 * ((NIR-RED) / (NIR + (6 * RED) - (7.5* BLUE) + 1))', {
            'NIR': image.select('NIR'),
            'RED': image.select('R'),
            'BLUE': image.select('B')
        }).rename('EVI')

    return image.addBands(evi)


def add_savi(image: ee.Image):
    """
    Calculates the Soil Adjusted Vegetation Index (SAVI)
    """
    savi = image.expression(
        '((1 + 0.5) * (NIR-RED) / (NIR + RED + 0.5))', {
            'NIR': image.select('NIR'),
            'RED': image.select('R')
        }).rename('SAVI')

    return image.addBands(savi)


def add_gi(image: ee.Image):
    """
    Calculates the Greenness Index (GI)
    """
    gi = image.expression(
        'NIR / G', {
            'NIR': image.select('NIR'),
            'G': image.select('G'),
        }
    ).rename('GI')

    return image.addBands(gi)


def add_gcvi(image: ee.Image):
    """
    Calculates the Green Chlorophyll Vegetation Index (GCVI)
    """
    gcvi = image.expression(
        '(NIR/G) - 1', {
            'NIR': image.select('NIR'),
            'G': image.select('G'),
        }
    ).rename('GCVI')

    return image.addBands(gcvi)


def add_wgi(image: ee.Image):
    """
    Calculates the Water Adjusted Green Index (WGI)
    """
    wgi = image.expression(
        'NDWI * GI', {
            'NDWI': image.select('NDWI'),
            'GI': image.select('GCVI'),
        }
    ).rename('WGI')

    return image.addBands(wgi)


