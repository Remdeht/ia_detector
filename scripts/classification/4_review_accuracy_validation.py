"""
Main description

Author: Thedmer Postma
Date: 12/09/2022
"""

import ee
from gee_functions.constants import AOI, AOI_NAME, CLF_RUN, VALIDATION_MAPS, PROJECT_PATH, IRRIGATED_AREA_CLASSES
from gee_functions.validation import calc_area, calc_validation_score, sample_feature_collection
from gee_functions.vector import raster_to_vector


def load_validation_polygons(asset: ee.FeatureCollection):
    return asset.filterBounds(AOI)


def load_validation_raster(val_map: ee.Image, target_classes: list[int]):
    val_binary = val_map.eq(target_classes).reduce('sum').rename('binary_irrigated_area')

    return val_map.addBands(val_binary)


def main():
    for year, val_map_info in VALIDATION_MAPS.items():
        print(f'starting validation for year {year}')

        irrigated_area = ee.Image(
            f'{PROJECT_PATH}/raster/results/irrigated_area/{AOI_NAME}/{CLF_RUN}/irrigated_areas_{AOI_NAME}_{year}'
        ).select('ia_year')

        if val_map_info['type'] == 'vector':
            # Need to load the polygons, transform to binary raster to calculate the total area
            # sample polygons to perform the accuracy score

            for key, value in [(k, v) for (k, v) in val_map_info.items() if k != 'type']:

                ia_to_validate = [IRRIGATED_AREA_CLASSES[val] for val in value['val_ia_classes']]
                ia_binary = irrigated_area.eq(ia_to_validate).reduce('sum').gt(0).rename('ia_year')
                area = round(calc_area(ia_binary, AOI).getInfo())

                val_polygons = load_validation_polygons(value['asset'])

                # TODO - test out painting the FC on an image, might be quicker

                def add_column(x):
                    return ee.Feature(x).set('to_reduce', 1).copyProperties(x)

                val_polygons = val_polygons.map(add_column)

                val_binary = val_polygons.reduceToImage(
                    reducer=ee.Reducer.first(),
                    properties=['to_reduce'],
                )

                area_val = round(calc_area(val_binary, AOI).getInfo())

                val_polygons = sample_feature_collection(
                    feature_collection=val_polygons,
                    min_area=50000,
                    max_area=500000,
                    fraction=.3,
                    intersect_aoi=False
                )

                val_score, _= calc_validation_score(
                    ia_binary,
                    val_polygons,
                    export=True,
                    export_polygons=True,
                    name=f'{key}_{year}',
                )

                val_score = round(val_score.get('mean').getInfo(), 2)

                print(f'{year}:\nvalidation score {key}: {val_score}\ntotal irrigated area: {area} hectares'
                      f'\ntotal irrigated area validation: {area_val} hectares'
                      )
        else:
            for key, value in [(k, v) for (k, v) in val_map_info.items() if k != 'type']:

                ia_to_validate = [IRRIGATED_AREA_CLASSES[val] for val in value['val_ia_classes']]
                ia_binary = irrigated_area.eq(ia_to_validate).reduce('sum').gt(0).rename('ia_year')

                area = round(calc_area(ia_binary, AOI).getInfo())

                val_map = load_validation_raster(value['asset'], value['irrigated_pixel_values'])

                area_val = round(calc_area(val_map.select('binary_irrigated_area'), AOI).getInfo())

                val_polygons = raster_to_vector(
                    val_map.select('binary_irrigated_area'),
                    AOI,
                    tile_scale=8
                )

                val_polygons = sample_feature_collection(
                    feature_collection=val_polygons,
                    fraction=.3,
                    min_area=50000,
                    max_area=500000,
                )

                val_score, _ = calc_validation_score(
                    ia_binary,
                    val_polygons,
                    export=True,
                    export_polygons=True,
                    name=f'{key}_{year}',
                )

                val_score = round(val_score.get('mean').getInfo(), 2)

                print(f'{year}:\nvalidation score {key}: {val_score}\ntotal irrigated area: {area} hectares'
                      f'\ntotal irrigated area validation: {area_val} hectares'
                      )

        # calculate the area


if __name__ == '__main__':
    main()
