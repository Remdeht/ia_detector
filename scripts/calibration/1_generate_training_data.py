"""
Script to generate the training data for calibration

The first step in the methodology is to generate the summer and winter feature data, which are later used to determine
training areas via LDA for the RF classifier. By running this script the


Author: Thedmer Postma
Date: 06/09/2022
"""

#  TODO Training areas are generated using the landsat libraries, but also important to test if Sentinel 2 can be used
#  TODO - fix the naming of the feature data assets

# standard libs

# local imports
from gee_functions.constants import AOI, AOI_NAME, DATA_CREATION_METHOD
from gee_functions.classification import create_feature_data
from gee_functions.export import track_task

# globals

CALIBRATION_YEARS = [
    1997,
    2000,
    2009,
]

SENSOR = 'landsat'  # 'sentinel'

def main():

    tasks = {}

    for year in CALIBRATION_YEARS:
        # Date ranges are selected to match the dates shown in table 2.3, pg 17 of the thesis document found here:
        # https://zenodo.org/record/237068
        summer_dates = (f'{year}-04-01', f'{year}-09-30')
        winter_dates = (f'{year}-10-01', f'{year + 1}-03-31')

        task = create_feature_data(
            summer_dates,
            aoi=AOI,
            aoi_name=AOI_NAME,
            creation_method=DATA_CREATION_METHOD,
            sensor=SENSOR,
            custom_name=f'summer_{year}',
            overwrite=True,
        )
        tasks[f'summer_{year}'] = task

        task = create_feature_data(
            winter_dates,
            aoi=AOI,
            aoi_name=AOI_NAME,
            creation_method=DATA_CREATION_METHOD,
            sensor=SENSOR,
            custom_name=f'winter_{year}',
            overwrite=True,
        )
        tasks[f'winter_{year}'] = task

    track_task(tasks)


if __name__ == '__main__':
    main()
