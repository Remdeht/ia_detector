import ee
from gee_functions import vector
import os
import itertools
import pandas as pd

ee.Initialize()

CdC = ee.FeatureCollection('users/Postm087/outline_3857')  # Load the feature collection containing the area of interest
cdc_coordinates = CdC.geometry().bounds().getInfo()['coordinates']


def calc_area(image, aoi):
    """Function to calculate the area of the a binary mask in hectares"""
    area = ee.Image.pixelArea().divide(10000);
    irrigated_area = image.gt(0);
    masked_area = area.updateMask(irrigated_area);

    total_irrigated_area = masked_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=30,
        tileScale=2,
        maxPixels=1e13).get('area')

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


def calc_validation_score(mask, val_poly_ir_crops, val_poly_ir_trees, ):
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

        score = ee.Number(irrigated_pixels.get('b1')).round().divide(ee.Number(total_pixels.get('b1')))
        score = ee.Algorithms.If(score.gt(1), 1, score)

        feature = feature.set({
            'total_pixels': total_pixels.get('b1'),
            'irrigated_pixels': irrigated_pixels.get('b1'),
            'score': score
        })
        return feature

    validation_areas_ir_crops = ee.FeatureCollection(val_poly_ir_crops.geometry().intersection(
        CdC.geometry(),
        ee.ErrorMargin(1)
    ))

    validation_areas_ir_trees = ee.FeatureCollection(val_poly_ir_trees.geometry().intersection(
        CdC.geometry(),
        ee.ErrorMargin(1)
    ))

    validation_areas_ir_crops = validation_areas_ir_crops.map(convert_to_polygons).flatten()
    validation_areas_ir_trees = validation_areas_ir_trees.map(convert_to_polygons).flatten()

    validation_areas_ir_crops = validation_areas_ir_crops.map(validate_irrigated_area)
    validation_areas_ir_trees = validation_areas_ir_trees.map(validate_irrigated_area)

    final_validation_score_ir_crops = validation_areas_ir_crops.reduceColumns(
        selectors=ee.List(['score']),
        reducer=ee.Reducer.mean()
    )

    final_validation_score_ir_trees = validation_areas_ir_trees.reduceColumns(
        selectors=ee.List(['score']),
        reducer=ee.Reducer.mean()
    )

    return final_validation_score_ir_crops.getInfo()["mean"], final_validation_score_ir_trees.getInfo()["mean"]


val_maps = {
    '88': ee.Image('users/Postm087/CEBAS_RASTER/C88'),
    '97': ee.Image('users/Postm087/CEBAS_RASTER/C97'),
    '00': ee.Image('users/Postm087/CEBAS_RASTER/C00'),
    '09': ee.Image('users/Postm087/CEBAS_RASTER/C09'),
}

validation_polygons_ir_trees = {
    '97': ee.FeatureCollection('users/Postm087/vector/validation/val_it_97'),
    '00': ee.FeatureCollection('users/Postm087/vector/validation/val_it_00'),
    '09': ee.FeatureCollection('users/Postm087/vector/validation/val_it_08'),
}

validation_polygons_ir_crops = {
    '97': ee.FeatureCollection('users/Postm087/vector/validation/val_ic_97'),
    '00': ee.FeatureCollection('users/Postm087/vector/validation/val_ic_00'),
    '09': ee.FeatureCollection('users/Postm087/vector/validation/val_ic_08'),
}

years = {
    # '88': ('1987-01-01', '1989-01-01'),
    '97': ('1996-01-01', '1998-01-01'),
    # '05': ('2004-01-01', '2006-01-01'),
    '00': ('1999-01-01', '2001-01-01'),
    '09': ('2008-01-01', '2010-01-01'),
}

land_classes = {
    1: 'natural trees',
    2: 'open natural trees',
    3: 'dense scrub',
    4: 'open scrub',
    5: 'rainfed trees',
    6: 'rainfed crops',
    7: 'irrigated trees',
    8: 'irrigated crops',
    9: 'greenhouses',
    10: 'unproductive area',
    11: 'water',
    12: 'saltplanes',
}

stats = ['mean', 'min', 'max']
stats_combos = list(itertools.combinations(stats, 1)) + \
               list(itertools.combinations(stats, 2)) + \
               list(itertools.combinations(stats, 3))

if __name__ == '__main__':

    # Each map obtained via the rf classification was uploaded to the GEE as assets. The following script calculates the
    # validation score for each map and combines the results into a csv file.
    df = pd.DataFrame(columns=['run', 'year', 'area', 'score crops', 'score trees'])

    for year in years:
        print(f'Starting year: {year}')
        for combo in stats_combos:  # Combination of feature data used for classification
            print(f'Starting {"_".join(combo)}')
            for s in ['summer', 'winter', 'year']:
                FOLDER = f'users/Postm087/raster/results/random_forest/{"_".join(combo)}/{s}/'  # GEE map folder
                RUN = f'ia_random_forest_{"_".join(combo)}_{s}_250tr_2vps_60bf_{year}'  # name of the map

                classified_area = ee.Image(f'{FOLDER}{RUN}')  # load the map
                classified_area_mask = classified_area.gt(0)  # create binary mask of irrigated pixels
                total_irrigated_area = calc_area(classified_area_mask, CdC).getInfo()  # calculate irrigated area in ha
                # Next calculate the validation score based on the validation polygons already uploaded to the GEE
                val_score_crops, val_score_trees = calc_validation_score(
                    classified_area_mask,
                    validation_polygons_ir_crops[year],
                    validation_polygons_ir_trees[year]
                )

                row = [f'{" ".join(combo)} {s}', year, total_irrigated_area, val_score_crops, val_score_trees]
                df.loc[len(df)] = row  # Join data with a pandas dataframe containing all results

            # Next up the same procedure is followed only this time for irrigated areas when combining both the summer
            # and winter maps

            classified_area_summer = ee.Image(
                f'users/Postm087/raster/results/random_forest/{"_".join(combo)}/summer/ia_random_forest_{"_".join(combo)}_summer_250tr_2vps_60bf_{year}')
            classified_area_winter = ee.Image(
                f'users/Postm087/raster/results/random_forest/{"_".join(combo)}/winter/ia_random_forest_{"_".join(combo)}_winter_250tr_2vps_60bf_{year}')
            classified_area_combined_mask = classified_area_summer.gt(0) \
                .Or(classified_area_winter.gt(0))
            total_irrigated_area_combined = calc_area(classified_area_combined_mask, CdC).getInfo()
            val_score_crops, val_score_trees = calc_validation_score(classified_area_combined_mask,
                                                                     validation_polygons_ir_crops[year],
                                                                     validation_polygons_ir_trees[year])
            row = [f'{" ".join(combo)} summer/winter', year, total_irrigated_area_combined, val_score_crops,
                   val_score_trees]
            df.loc[len(df)] = row
            print(f'Ended {"_".join(combo)}')

        # if not year == '05':
        #     area = ee.Image.pixelArea().divide(10000)
        #     val_map = val_maps[year]
        #     validation_area = val_map.updateMask(classified_area_combined_mask)
        #     class_areas = area.addBands(validation_area).reduceRegion(
        #         reducer=ee.Reducer.sum().group(groupField=1,
        #                                        groupName='class',
        #                                        ),
        #         geometry=CdC,
        #         scale=30,
        #         maxPixels=1e10
        #     ).get('groups')
        # 
        #     class_area_ha = class_areas.getInfo()
        # 
        #     for i in class_area_ha:
        #         print(f'{land_classes[i["class"]]}: {(i["sum"] / total_irrigated_area_combined) * 100:.2f}%')

    # Save the df to the results folder after making sure that a results folder is present

    if not os.path.exists('results/'):
        os.mkdir('results/')

    df.to_csv(r'results/classification/classification_runs.csv', index=False)
