"""
Functions for topographic indices
"""

import ee


def add_mti() -> ee.Image:
    """
    Calculated the MTI based on the slope and the hydrosheds 3 arcsec flow accumulation map. See 'An automated procedure
     for the detection of flood prone areas: r. hazard. flood' by Di Leo et al. 2011 for more information.
    """
    flow_accumulation = ee.ImageCollection('users/imerg/flow_acc_3s').mosaic().select('b1')
    slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003").select('elevation'))
    slope_radians = slope.multiply(1.570796).divide(90).tan()
    twi = flow_accumulation.add(1).pow(0.016 * (30 ** 0.46)).divide(slope_radians.add(.001).tan()).log()

    return twi
