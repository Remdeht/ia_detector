import ee


def add_twi():
    flow_accumulation = ee.ImageCollection('users/imerg/flow_acc_3s').mosaic().select('b1')
    slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003").select('elevation'))
    slope_radians = slope.multiply(1.570796).divide(90).tan()
    twi = flow_accumulation.add(1).pow(0.016 * (30 ** 0.46)).divide(slope_radians.add(.001).tan()).log()



    return twi
