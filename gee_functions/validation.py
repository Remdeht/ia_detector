"""
Functions used for validation using validation polygons
"""

import ee

try:
    from constants import AOI
except ImportError:
    from .constants import AOI


def calc_area(
        image: ee.Image,
        region: ee.FeatureCollection,
        scale: int = 30,
        tile_scale: int = 2,
        max_pixels: int = 1e13,
        crs: str='EPSG:32630'
    ):
    """
    Function to calculate the area of the objects on a binary map in hectares
    :param image: EE image with areas for which to calculate the area having values larger then 0
    :param region: EE Geometry acting as extent for the calculation
    :param scale: a nominal scale in meters of the projection to work in
    :param tile_scale: a scaling factor used to reduce aggregation tile size; using a larger tileScale (e.g. 2 or 4)
    may enable computations that run out of memory with the default
    :param max_pixels: the maximum number of pixels to reduce.
    :return: area in hectares
    """
    area = ee.Image.pixelArea().divide(10000)
    irrigated_area = image.gt(0)
    masked_area = area.updateMask(irrigated_area)

    total_irrigated_area = masked_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        tileScale=tile_scale,
        maxPixels=max_pixels,
        crs=crs,
    ).get('area')

    return total_irrigated_area


def convert_to_polygons(feature: ee.Feature) -> ee.FeatureCollection:
    """
    Converts an EE Multipolygon Feature into a FeatureCollection of single polygons
    """
    feature = ee.Feature(feature)
    geometries = feature.geometry().geometries()

    def to_poly(f):
        poly = ee.Geometry.Polygon(ee.Geometry(f).coordinates())
        return ee.Feature(poly).copyProperties(f)

    return ee.FeatureCollection(geometries.map(to_poly))


def buffer_polygon(feature: ee.Feature):
    """Applies a buffer to a polygon"""
    return feature.buffer(-30, 1)


def add_area(feature: ee.Feature):
    """Add the area as a property to each feature"""
    return feature.set('area', feature.area(1))


def calc_validation_score(
        binary: ee.Image,
        validation_polygons: ee.FeatureCollection,
        binary_name: str = 'irrigated_area',
        export: bool = False,
        export_polygons: bool = False,
        name: str = None):
    """
    Calculates an accuracy score for the classification of irrigated areas for a binary layer using validation polygons

    :param binary: binary EE Image, with 1 pixel values representing target irrigated areas, and 0 pixel values
    representing non-irrigated areas
    :param validation_polygons: EE FeatureCollection containing validation polygons
    :param binary_name: name of the band containing the binary values
    :param export: if True the an export of the accuracy score to the users Google drive will be started
    :param export_polygons: if True a kml file containing the polygons used for validation will be exported
    to the Google Drive of the user
    :param name: name for the export task, if None no name is added to the task
    :return: depending on input a task or feature containing the accuracy score
    """

    def validate_irrigated_area(feature):
        total_pixels = binary.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=feature.geometry(),
            scale=30
        )

        irrigated_pixels = binary.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=feature.geometry(),
            scale=30
        )

        score = ee.Number(irrigated_pixels.get(binary_name)).round().divide(ee.Number(total_pixels.get(binary_name)))
        score = ee.Algorithms.If(score.gt(1), 1, score)

        feature = feature.set({
            'total_pixels': total_pixels.get(binary_name),
            'irrigated_pixels': irrigated_pixels.get(binary_name),
            'score': score
        })
        return feature

    binary = binary.rename(binary_name)

    validation_polygons_scored = validation_polygons.map(validate_irrigated_area)

    validation_score = validation_polygons_scored.reduceColumns(
        selectors=ee.List(['score']),
        reducer=ee.Reducer.mean()
    )

    result = ee.FeatureCollection(ee.Feature(None, validation_score))

    # TODO - this is sloppy
    if export is True:

        if name is None:
            description = 'validation_score'
        else:
            description = f'validation_score_{name}'

        if export_polygons is True:
            export_task = ee.batch.Export.table.toDrive(
                collection=validation_polygons_scored,
                description=description,
                folder=f'accuracy_polygons',
                fileFormat='GEO_JSON'
            )
            export_task.start()

        export_task = ee.batch.Export.table.toDrive(
            collection=result,
            description=description,
            folder=f'accuracy_scores',
            fileFormat='CSV'
        )
        export_task.start()
        return validation_score, export_task

    else:
        return validation_score


def sample_feature_collection(
        feature_collection: ee.FeatureCollection,
        fraction: float = .2,
        max_area: int = 100000,
        min_area: int = 10000,
        seed: int = 0,
        intersect_aoi: bool = False) -> ee.FeatureCollection:
    """
    Samples features from an EE FeatureCollection based on a random column value

    :param feature_collection: EE FeatureCollection containing polygons to be sampled
    :param fraction: fraction of the total number of features to extract
    :param max_area: maximum size limit for polygons in square meters
    :param min_area: minimum size limit for polygons in square meters
    :param seed: seed for randomColumn function
    :param intersect_aoi: to intersect the feature collection with the AOI, removing parts outside the aoi
    :return: feature collection containing a sample of the original feature collection
    """

    feature_collection = feature_collection.map(add_area)

    # Filter features based on area size
    filter_max_area = ee.Filter.lte('area', max_area)
    filter_min_area = ee.Filter.gte('area', min_area)
    feature_collection = feature_collection.filter(filter_max_area).filter(filter_min_area)

    # Assign a random value between 0 and 1 to each feature
    feature_collection = feature_collection.randomColumn(seed=seed)

    # Select features with a lower random value than the fraction
    feature_collection = feature_collection.filter(ee.Filter.lte('random', fraction))

    if intersect_aoi:
        feature_collection = ee.FeatureCollection(
            feature_collection.geometry().intersection(AOI.geometry(), ee.ErrorMargin(1))
        )

    return feature_collection
