import ee
from monthdelta import monthdelta
import json
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
import folium
import pandas as pd
import time


def get_tc_image_collection(begin_date, end_date, region=None):
    if region is None:
        return (ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE')
                .select('tmmn', 'tmmx', 'soil', 'aet', 'pr')
                .filterDate(begin_date, end_date))
    else:
        return (ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE')
                .select('tmmn', 'tmmx', 'soil', 'aet', 'pr')
                .filterBounds(region)
                .filterDate(begin_date, end_date))


def getMaxTempVisParams(minTemp, maxTemp):

    params = {
        'min': minTemp,
        'max': maxTemp,
        'palette': [
            '1a3678', '2955bc', '5699ff', '8dbae9', 'acd1ff', 'caebff', 'e5f9ff',
            'fdffb4', 'ffe6a2', 'ffc969', 'ffa12d', 'ff7c1f', 'ca531a', 'ff0000',
            'ab0000'
        ],
    }

    return params


def get_tc_statistics(imageCollection, region):

    def set_property(image):
        dict = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=30
        )
        return ee.Feature(None, dict).set('system:time_start', image.date())

    tc_stats = ee.FeatureCollection(imageCollection.map(set_property))
    return tc_stats


