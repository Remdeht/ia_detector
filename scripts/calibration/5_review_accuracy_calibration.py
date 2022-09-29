"""
Main description

Author: Thedmer Postma
Date: 12/09/2022
"""

import ee
from gee_functions.constants import AOI, AOI_NAME, CLF_RUN, CALIBRATION_MAPS, PROJECT_PATH
from gee_functions.validation import calc_area, calc_validation_score


def load_validation_polygons(year):
    pol_ic = ee.FeatureCollection(f'users/Postm087/vector/validation/cdc/val_ic_{str(year)[2:]}')
    pol_it = ee.FeatureCollection(f'users/Postm087/vector/validation/cdc/val_it_{str(year)[2:]}')

    pol_ic = ee.FeatureCollection(pol_ic.geometry().intersection(AOI.geometry()), ee.ErrorMargin(1))
    pol_it = ee.FeatureCollection(pol_it.geometry().intersection(AOI.geometry()), ee.ErrorMargin(1))

    pol_ia = pol_ic.merge(pol_it)

    return {
        'irrigated_crops' : pol_ic,
        'irrigated_trees': pol_it,
        'irrigated_areas' : pol_ia
    }


def main():

    for year, cal_map in CALIBRATION_MAPS.items():

        irrigated_area = ee.Image(
            f'{PROJECT_PATH}/raster/results/irrigated_area/{AOI_NAME}/{CLF_RUN}/irrigated_areas_{AOI_NAME}_{year}'
        ).select('ia_year')

        ia_binary = irrigated_area.gt(0)  # .where(irrigated_area.eq(4), 0).where(irrigated_area.eq(6), 0)
        cal_binary = ee.Image(0).where(cal_map.eq(7),1).where(cal_map.eq(8),1).reproject(irrigated_area.projection())
        area = round(calc_area(ia_binary, AOI).getInfo())
        area_cal = round(calc_area(cal_binary, AOI).getInfo())

        val_polygons = load_validation_polygons(year)

        val_score_ia = round(calc_validation_score(
            ia_binary,
            val_polygons['irrigated_areas'],
            export=False
        ).get('mean').getInfo(), 2)

        val_score_ic = round(calc_validation_score(
            ia_binary,
            val_polygons['irrigated_crops'],
            export=False
        ).get('mean').getInfo(), 2)

        val_score_it = round(calc_validation_score(
            ia_binary,
            val_polygons['irrigated_trees'],
            export=False
        ).get('mean').getInfo(), 2)

        print(f'{year}:\nvalidation score: {val_score_ia} (crops: {val_score_ic} & trees: {val_score_it})'
              f'\ntotal irrigated area: {area} hectares\ntotal irrigated area calibration: {area_cal} hectares')


if __name__ == '__main__':
    print(CLF_RUN)
    main()


