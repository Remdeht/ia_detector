import ee

def add_area(vector):
    """
    Function to add area as a property to a GEE feature collection representing a polygon or multipolygon.

    :param vector: GEE feature collection representing a polygon or multipolygon feature.
    :return: GEE feature collection of a polygon/multipolygon
    """
    area = vector.geometry().area(maxError=1)
    return vector.set('area', area)


def raster_to_vector(image, region, scale=30, max_pixels=1e8, tile_scale=1):
    """Wrapper for the ReduceToVector function that converts a raster object to a polygon"""

    vector = image.reduceToVectors(
        reducer=ee.Reducer.countEvery(),
        geometry=region,
        scale=scale,
        maxPixels=max_pixels,
        tileScale=tile_scale
    ).filter(ee.Filter.neq('label', 0))

    return vector
