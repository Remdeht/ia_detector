"""
Main description

Author: Thedmer Postma
Date: 08/09/2022
"""

# standard libs
import ee

# local imports
from gee_functions.constants import GEE_USER_PATH, PROJECT_PATH, AOI, AOI_NAME, BANDNAMES, CLF_RUN, \
    DATA_CREATION_METHOD, VALIDATION_MAPS
from gee_functions.classification import classify_irrigated_areas, join_seasonal_irrigated_areas
from gee_functions.export import track_task

# Number of Trees
TREES = 500
# Variables per Split
VPS = 6
# Bagging Fraction
BF = 0.25
# Minimum Number of Training Points
MIN_TP = 1000
# Maximum Number of Training Points
MAX_TP = 10000


def main():
    classification_data = {}

    for year in VALIDATION_MAPS:
        classification_data[year] = {
            'summer': {
                'feature_data': ee.Image(
                    f'{GEE_USER_PATH}/ia_classification/raster/data/{AOI_NAME}/landsat/{DATA_CREATION_METHOD}/feature_data_{AOI_NAME}_summer_{year}'
                ),
                'training_data': ee.Image(
                    f'{GEE_USER_PATH}/ia_classification/raster/results/random_forest/{AOI_NAME}/{CLF_RUN}/training/training_summer_{year}'
                ).select('combined_training_areas').rename('training'),
            },
            'winter': {
                'feature_data': ee.Image(
                    f'{GEE_USER_PATH}/ia_classification/raster/data/{AOI_NAME}/landsat/{DATA_CREATION_METHOD}/feature_data_{AOI_NAME}_winter_{year}'
                ),
                'training_data': ee.Image(
                    f'{GEE_USER_PATH}/ia_classification/raster/results/random_forest/{AOI_NAME}/{CLF_RUN}/training/training_winter_{year}'
                ).select('combined_training_areas').rename('training'),
            },
        }

    classification_tasks = {}
    classifiers = {}

    for year, season_dict in classification_data.items():

        for season, asset_dict in season_dict.items():

            asset_bands = asset_dict['feature_data'].bandNames().getInfo()

            bands_to_select = [band for band in BANDNAMES if band in list(asset_bands)]

            feature_data = asset_dict['feature_data'].select(bands_to_select)

            training = asset_dict['training_data'].reproject(feature_data.projection())
            training = training.addBands(training)

            try:

                classification_task, _ = classify_irrigated_areas(
                    feature_data,
                    training,
                    AOI,
                    aoi_name=AOI_NAME,
                    clf_folder=CLF_RUN,
                    season=season,
                    year=str(year),
                    no_trees=TREES,
                    bag_fraction=BF,
                    vps=VPS,
                    min_tp=MIN_TP,
                    max_tp=MAX_TP,
                    overwrite=False
                )

                classification_tasks[f'{season}_{year}'] = classification_task

            except FileExistsError as e:
                classification_tasks[f'{season}_{year}'] = True
                print(e)
                continue

    if track_task(classification_tasks):

        tasks = {}

        for year in VALIDATION_MAPS:
            ia_summer = ee.Image(
                f'{PROJECT_PATH}/raster/results/random_forest/{AOI_NAME}/{CLF_RUN}/ia_random_forest_{TREES}tr_{VPS}vps_{int(BF * 100)}bf_{AOI_NAME}_summer_{year}'
            ).select('irrigated_area')
            ia_winter = ee.Image(
                f'{PROJECT_PATH}/raster/results/random_forest/{AOI_NAME}/{CLF_RUN}/ia_random_forest_{TREES}tr_{VPS}vps_{int(BF * 100)}bf_{AOI_NAME}_winter_{year}'
            ).select('irrigated_area')

            task = join_seasonal_irrigated_areas(
                ia_summer,
                ia_winter,
                AOI_NAME,
                year,
                AOI,
                clf_folder=CLF_RUN,
                overwrite=False,
                export_method='asset',
            )

            tasks[year] = task

        track_task(tasks)


if __name__ == '__main__':
    main()