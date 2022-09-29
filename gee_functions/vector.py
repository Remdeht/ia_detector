"""
Functions related to EE vectors
"""
import ee

from typing import Union, Dict


def add_area(vector: ee.FeatureCollection) -> ee.FeatureCollection:
    """
    Function to add area as a property to a GEE feature collection representing a polygon or multipolygon.

    :param vector: GEE feature collection representing a polygon or multipolygon feature.
    :return: GEE feature collection of a polygon/multipolygon with an area property for each feature
    """
    area = vector.geometry().area(maxError=1)
    return vector.set('area', area)


def raster_to_vector(
        image: ee.Image,
        region: ee.FeatureCollection,
        scale: int = 30,
        max_pixels: int = 1e8,
        tile_scale: int = 1) -> ee.FeatureCollection:
    """
    Wrapper for the EE ReduceToVector function that converts a raster object to a vector. Removes features belonging to
    pixels with the value 0 by default.

    :param image: EE Image to convert, the first band is expected to be an integer type; adjacent pixels will be
     in the same segment if they have the same value in this band
    :param region: the region over which to reduce data, defaults to the footprint of the image's first band
    :param scale: a nominal scale in meters of the projection to work in
    :param max_pixels: the maximum number of pixels to reduce
    :param tile_scale: a scaling factor used to reduce aggregation tile size
    :return: EE FeatureCollection of the first band of the input image
    """

    vector = image.reduceToVectors(
        reducer=ee.Reducer.countEvery(),
        geometry=region,
        scale=scale,
        maxPixels=max_pixels,
        tileScale=tile_scale
    ).filter(ee.Filter.neq('label', 0))

    return vector


def split_region(region: Union[ee.FeatureCollection, ee.Feature]) -> Dict[str, ee.Geometry]:
    """
    Splits a EE FeatureCollection/Feature into four equal parts
    :param region: EE FeatureCollection/Feature to split
    :return: dictionary containing the four parts of FeatureCollection
    """

    bounding_box = region.geometry().bounds()  # gets the bounding box of the region
    centroid = bounding_box.centroid(1)  # get the centroid
    # select the four corner coordinates of the bounding box
    point_1 = ee.Geometry.Point(ee.List(bounding_box.coordinates().get(0)).get(0)).coordinates()
    point_2 = ee.Geometry.Point(ee.List(bounding_box.coordinates().get(0)).get(1)).coordinates()
    point_3 = ee.Geometry.Point(ee.List(bounding_box.coordinates().get(0)).get(2)).coordinates()
    point_4 = ee.Geometry.Point(ee.List(bounding_box.coordinates().get(0)).get(3)).coordinates()

    # split the original bounding box into four equal bounding boxes
    new_poly_1 = ee.Geometry.Polygon(
        coords=[
            point_1,
            [centroid.coordinates().get(0), point_1.get(1)],
            centroid.coordinates(),
            [point_1.get(0), centroid.coordinates().get(1)],
            point_1
        ],
        proj='EPSG:4326',
        evenOdd=False,
    )

    new_poly_2 = ee.Geometry.Polygon(
        coords=[
            point_2,
            [point_2.get(0), centroid.coordinates().get(1)],
            centroid.coordinates(),
            [centroid.coordinates().get(0), point_2.get(1)],
            point_2
        ],
        proj='EPSG:4326',
        evenOdd=False,
    )

    new_poly_3 = ee.Geometry.Polygon(
        coords=[
            point_3,
            [centroid.coordinates().get(0), point_3.get(1)],
            centroid.coordinates(),
            [point_3.get(0), centroid.coordinates().get(1)],
            point_3
        ],
        proj='EPSG:4326',
        evenOdd=False,
    )

    new_poly_4 = ee.Geometry.Polygon(
        coords=[
            point_4,
            [point_4.get(0), centroid.coordinates().get(1)],
            centroid.coordinates(),
            [centroid.coordinates().get(0), point_4.get(1)],
            point_4
        ],
        proj='EPSG:4326',
        evenOdd=False,
    )

    # clip the original region using the each part of the bounding box
    bottom_left_poly = new_poly_1.intersection(region, maxError=1)
    bottom_right_poly = new_poly_2.intersection(region, maxError=1)
    top_right_poly = new_poly_3.intersection(region, maxError=1)
    top_left_poly = new_poly_4.intersection(region, maxError=1)

    return {
        'top_left': top_left_poly,
        'top_right': top_right_poly,
        'bottom_right': bottom_right_poly,
        'bottom_left': bottom_left_poly
    }
