import ee

def calc_area(image, aoi, scale=30, tile_scale=2, max_pixels=1e13):
    """Function to calculate the area of the a binary mask in hectares"""
    area = ee.Image.pixelArea().divide(10000);
    irrigated_area = image.gt(0);
    masked_area = area.updateMask(irrigated_area);

    total_irrigated_area = masked_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=scale,
        tileScale=tile_scale,
        maxPixels=max_pixels).get('area')

    return total_irrigated_area


def convert_to_polygons(feat):
    """
    Converts a GEE Multipolygon Featurecollection into a FeatureCollection of separate polygons
    """
    feat = ee.Feature(feat)
    geometries = feat.geometry().geometries()

    def poly(feat):
        poly = ee.Geometry.Polygon(ee.Geometry(feat).coordinates())
        return ee.Feature(poly).copyProperties(feat)

    extractPolys = ee.FeatureCollection(geometries.map(poly))
    return extractPolys


def buffer_polygon(ft):
    """Applies a buffer to a polygon"""
    return ft.buffer(-30, 1)


def add_area(ft):
    "Add the area as a property to each feature"
    return ft.set('area', ft.area(1))


def calc_validation_score(mask, validation_polygons, mask_name='irrigated_area', export=False):
    """Calculates the validation score for a mask layer using validation polygons that were uploaded as assets to GEE
    beforehand"""

    def validate_irrigated_area(feature):
        total_pixels = mask.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=feature.geometry(),
            scale=30
        )

        irrigated_pixels = mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=feature.geometry(),
            scale=30
        )

        score = ee.Number(irrigated_pixels.get(mask_name)).round().divide(ee.Number(total_pixels.get(mask_name)))
        score = ee.Algorithms.If(score.gt(1), 1, score)

        feature = feature.set({
            'total_pixels': total_pixels.get(mask_name),
            'irrigated_pixels': irrigated_pixels.get(mask_name),
            'score': score
        })
        return feature

    mask = mask.rename(mask_name)
    # validation_polygons = validation_polygons.map(convert_to_polygons).flatten()
    validation_polygons_scored = validation_polygons.map(validate_irrigated_area)

    validation_score = validation_polygons_scored.reduceColumns(
        selectors=ee.List(['score']),
        reducer=ee.Reducer.mean()
    )

    result = ee.FeatureCollection(ee.Feature(None, validation_score))

    if export is True:
        export_task = ee.batch.Export.table.toDrive(
            collection=validation_polygons_scored,
            description=f'validation_polygons',
            folder=f'accuracy_polygons_kml',
            fileFormat='KML'
        )
        export_task.start()

        export_task = ee.batch.Export.table.toDrive(
            collection=result,
            description=f'validation_score',
            folder=f'accuracy_scores',
            fileFormat='CSV'
        )
        export_task.start()
        return export_task

    else:
        return validation_score


def sample_featurecollection(fc, fraction=.2, max_area=1000000, min_area=50000, seed=0):
    """Samples features from a featurecollection"""
    fc = fc.randomColumn(seed=seed)
    filter_max_area = ee.Filter.lte('area', max_area)
    filter_min_area = ee.Filter.gte('area', min_area)
    filter_random = ee.Filter.lte('random', fraction)

    return fc.filter(filter_max_area).filter(filter_min_area).filter(filter_random).map(buffer_polygon)