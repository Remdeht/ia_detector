"""
Contains constants used throughout the entire package

TODO - Maybe rename this file classification config?
"""
import os
import httplib2
from pathlib import Path

from typing import Dict

import ee

try:
    ee.Initialize(http_transport=httplib2.Http())
except AttributeError:
    ee.Authenticate()
    ee.Initialize(http_transport=httplib2.Http())

GEE_USER_PATH = ee.data.getAssetRoots()[0]['id']  # Retrieves the user's GEE path to be used for saving assets
PROJECT_PATH = f'{GEE_USER_PATH}/ia_classification'  # The project path

AOI = ee.FeatureCollection(f'users/Postm087/vector/outline/outline_cdc')  # Polygon of the AOI uploaded to the EE
AOI_NAME: str = 'cdc'  # AOI name to use for files, asset names etc.

aoi_info = AOI.geometry().getInfo()

if 'coordinates' in aoi_info.keys():

    aoi_coordinates = aoi_info['coordinates']  # aoi coordinates

    if len(aoi_coordinates) > 1:
        AOI_COORDINATES = ee.Geometry.MultiPolygon(aoi_coordinates)
    else:
        AOI_COORDINATES = ee.Geometry.Polygon(aoi_coordinates)

AOI_BOUNDS_COORDINATES = AOI.geometry().bounds().getInfo()['coordinates']

CALIBRATION_LC_CLASSES = {
    'irrigated_trees': [7],
    'irrigated_crops': [8],
    'forest': [1, 2],
    'shrub': [3, 4],
    'rainfed_agriculture': [5, 6],
    'greenhouses': [9],
    'urban_fallow': [10],
    'water_bodies': [11],
}

CALIBRATION_MAPS = {  # Load the Land cover maps for the calibration
    1997: ee.Image('users/Postm087/raster/validation/cdc/C97'),
    2000: ee.Image('users/Postm087/raster/validation/cdc/C00'),
    2009: ee.Image('users/Postm087/raster/validation/cdc/C09'),
}

RF_CLASSES = {
    0: 'NA',
    1: 'Irrigated Trees',
    2: 'Irrigated Crops',
    3: 'Forest',
    4: 'Shrub',
    5: 'Rainfed Agriculture',
    6: 'Greenhouses',
    7: 'Urban Fallow',
    8: 'Water Bodies',
}

IRRIGATED_AREA_CLASSES = {
    'Not Irrigated': 0,
    'Year Round Irrigated Crops': 1,
    'Year Round Irrigated Trees': 2,
    'Summer Irrigated Crops': 3,
    'Summer Irrigated Trees': 4,
    'Winter Irrigated Crops': 5,
    'Winter Irrigated Trees': 6,
    'Uncertain Areas': 7,
}

VALIDATION_MAPS = {
    2005: {
        'type': 'vector',
        'irrigated_area': {
            'asset': ee.FeatureCollection('users/Postm087/vector/validation/cdc/val_ia_05'),
            'val_ia_classes': [
                'Year Round Irrigated Crops',
                'Year Round Irrigated Trees',
                'Summer Irrigated Crops',
                'Summer Irrigated Trees',
                'Winter Irrigated Crops',
                'Winter Irrigated Trees',
                'Uncertain Areas',
            ],
        },
        'irrigated_crops': {
            'asset': ee.FeatureCollection('users/Postm087/vector/validation/cdc/val_ia_05').filter(
                ee.Filter.inList('USO_SUELO', [6, 12, 14])
            ),
            'val_ia_classes': [
                'Year Round Irrigated Crops',
                'Summer Irrigated Crops',
                'Winter Irrigated Crops',
                'Uncertain Areas',
            ],
        },
        'irrigated_trees': {
            'asset': ee.FeatureCollection('users/Postm087/vector/validation/cdc/val_ia_05').filter(
                ee.Filter.inList('USO_SUELO', [16])
            ),
            'val_ia_classes': [
                'Year Round Irrigated Trees',
                'Summer Irrigated Trees',
                'Winter Irrigated Trees',
                'Uncertain Areas',
            ],
        }
    },
    2014: {
        'type': 'vector',
        'irrigated_area': {
            'asset': ee.FeatureCollection('users/Postm087/vector/validation/rdm/val_ic_14'),
            'val_ia_classes': [
                'Year Round Irrigated Crops',
                'Year Round Irrigated Trees',
                'Summer Irrigated Crops',
                'Summer Irrigated Trees',
                'Winter Irrigated Crops',
                'Winter Irrigated Trees',
                'Uncertain Areas',
            ],
        },
        'irrigated_crops': {
            'asset': ee.FeatureCollection('users/Postm087/vector/validation/rdm/val_ic_14'),
            'val_ia_classes': [
                'Year Round Irrigated Crops',
                'Summer Irrigated Crops',
                'Winter Irrigated Crops',
                'Uncertain Areas',
            ],
        },
    },
    2017: {
        'type': 'raster',
        'irrigated_crops': {
            'asset': ee.Image(f"users/Postm087/raster/validation/cds/C17").select('b1'),
            'irrigated_pixel_values': [6],
            'val_ia_classes': [
                'Year Round Irrigated Crops',
                'Summer Irrigated Crops',
                'Winter Irrigated Crops',
                'Uncertain Areas',
            ],
        },
        'irrigated_area': {
            'asset': ee.Image(f"users/Postm087/raster/validation/cds/C17").select('b1'),
            'irrigated_pixel_values': [6],
            'val_ia_classes': [
                'Year Round Irrigated Crops',
                'Year Round Irrigated Trees',
                'Summer Irrigated Crops',
                'Summer Irrigated Trees',
                'Winter Irrigated Crops',
                'Winter Irrigated Trees',
                'Uncertain Areas',
            ],
        },

    },
}

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.getcwd())))
DATA_DIR = BASE_DIR.joinpath('data')

CLF_RUN: str = 'all_scenes_p15_p85_evi_savi'
# Number of Trees
TREES: int = 500
# Variables per Split
VPS: int = 6
# Bagging Fraction
BF: float = 0.25
# Minimum Number of Training Points
MIN_TP: int = 1000
# Maximum Number of Training Points
MAX_TP: int = 10000

DATA_CREATION_METHOD: str = 'all_scenes_reduced'   # 'all_scenes_reduced', 'monthly_composites_reduced'

CLASSIFICATION_BANDS: Dict[str, bool] = {
    'R_max': False,
    'R_mean': True,
    'R_median': True,
    'R_min': False,
    'R_p15': True,
    'R_p85': True,
    'R_stdDev': True,
    'G_max': False,
    'G_mean': True,
    'G_median': True,
    'G_min': False,
    'G_p15': True,
    'G_p85': True,
    'G_stdDev': True,
    'B_max': False,
    'B_mean': True,
    'B_median': True,
    'B_min': False,
    'B_p15': True,
    'B_p85': True,
    'B_stdDev': True,
    'NIR_max': False,
    'NIR_mean': True,
    'NIR_median': True,
    'NIR_min': False,
    'NIR_p15': True,
    'NIR_p85': True,
    'NIR_stdDev': True,
    'SWIR_max': False,
    'SWIR_mean': True,
    'SWIR_median': True,
    'SWIR_min': False,
    'SWIR_p15': True,
    'SWIR_p85': True,
    'SWIR_stdDev': True,
    'GCVI_min': False,
    'GCVI_p15': True,
    'GCVI_p85': True,
    'GCVI_mean': True,
    'GCVI_max': False,
    'NDVI_min': False,
    'NDVI_p15': True,
    'NDVI_p85': True,
    'NDVI_mean': True,
    'NDVI_max': False,
    'NDWI_min': False,
    'NDWI_p15': True,
    'NDWI_p85': True,
    'NDWI_mean': True,
    'NDWI_max': False,
    'WGI_min': False,
    'WGI_p15': True,
    'WGI_p85': True,
    'WGI_mean': True,
    'WGI_max': False,
    'NDWBI_min': False,
    'NDWBI_p15': True,
    'NDWBI_p85': True,
    'NDWBI_mean': True,
    'NDWBI_max': False,
    'NDBI_min': False,
    'NDBI_p15': True,
    'NDBI_p85': True,
    'NDBI_mean': True,
    'NDBI_max': False,
    'EVI_min': False,
    'EVI_p15': True,
    'EVI_p85': True,
    'EVI_mean': True,
    'EVI_max': False,
    'SAVI_min': False,
    'SAVI_p15': True,
    'SAVI_p85': True,
    'SAVI_mean': True,
    'SAVI_max': False,
    'NDBI_stdDev': True,
    'NDVI_stdDev': True,
    'GCVI_stdDev': True,
    'NDWI_stdDev': True,
    'WGI_stdDev': True,
    'EVI_stdDev': True,
    'SAVI_stdDev': True,
    'pdsi_min': False,
    'pdsi_p15': False,
    'pdsi_p85': False,
    'pdsi_mean': False,
    'pdsi_max': False,
    'pdsi_stdDev': False,
    'soil_min': False,
    'soil_p15': False,
    'soil_p85': False,
    'soil_mean': False,
    'soil_max': False,
    'soil_stdDev': False,
    'pr_min': False,
    'pr_p15': False,
    'pr_p85': False,
    'pr_mean': False,
    'pr_max': False,
    'pr_stdDev': False,
    'MTI': True,
    'slope': True,
}

BANDNAMES = [key for key, value in CLASSIFICATION_BANDS.items() if value]
