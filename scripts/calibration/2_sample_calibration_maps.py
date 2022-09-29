"""
Script used to sample the feature data based on the land cover classes of the Campo de Cartagena calibration maps
developed by TODO(Source)

The samples are exported to google drive as a csv file.

Author: Thedmer Postma
Date: 07/09/2022
"""

# standard libs
import ee

# local imports
from gee_functions.constants import PROJECT_PATH, AOI, AOI_NAME, CALIBRATION_MAPS, CALIBRATION_LC_CLASSES, \
    DATA_CREATION_METHOD
from gee_functions.lda import take_strat_sample
from gee_functions.export import track_task


def main():
    training_data_summer = {}
    training_data_winter = {}

    for year in CALIBRATION_MAPS.keys():
        training_data_summer[year] = ee.Image(
            f'{PROJECT_PATH}/raster/data/{AOI_NAME}/landsat/{DATA_CREATION_METHOD}/feature_data_{AOI_NAME}_summer_{year}')
        training_data_winter[year] = ee.Image(
            f'{PROJECT_PATH}/raster/data/{AOI_NAME}/landsat/{DATA_CREATION_METHOD}/feature_data_{AOI_NAME}_winter_{year}')

    tasks = {}

    task_summer, _, _ = take_strat_sample(
        CALIBRATION_MAPS,
        training_data_summer,
        CALIBRATION_LC_CLASSES,
        AOI,
        file_name=f'calibration_samples_summer',
        dir_name=f'ia_classification/{DATA_CREATION_METHOD}'
    )

    tasks[f'sample_summer'] = task_summer

    task_winter, _, _ = take_strat_sample(
        CALIBRATION_MAPS,
        training_data_winter,
        CALIBRATION_LC_CLASSES,
        AOI,
        file_name=f'calibration_samples_winter',
        dir_name=f'ia_classification/{DATA_CREATION_METHOD}'
    )

    tasks[f'sample_winter'] = task_winter

    track_task(tasks)


if __name__ == '__main__':
    main()
