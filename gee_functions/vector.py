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


def split_region(region):
    bounding_box = region.geometry().bounds()
    centroid = bounding_box.centroid(1)
    point_1 = ee.Geometry.Point(ee.List(bounding_box.coordinates().get(0)).get(0)).coordinates()
    point_2 = ee.Geometry.Point(ee.List(bounding_box.coordinates().get(0)).get(1)).coordinates()
    point_3 = ee.Geometry.Point(ee.List(bounding_box.coordinates().get(0)).get(2)).coordinates()
    point_4 = ee.Geometry.Point(ee.List(bounding_box.coordinates().get(0)).get(3)).coordinates()

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

    bottom_left_poly = new_poly_1.intersection(region)
    bottom_right_poly = new_poly_2.intersection(region)
    top_right_poly = new_poly_3.intersection(region)
    top_left_poly = new_poly_4.intersection(region)

    return {
        'top_left': top_left_poly,
        'top_right': top_right_poly,
        'bottom_right': bottom_right_poly,
        'bottom_left': bottom_left_poly
    }
