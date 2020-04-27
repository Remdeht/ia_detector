import ee
import itertools
from gee_functions.classification import create_features, create_training_areas, classify_irrigated_areas
from gee_functions.constants import GEE_USER_PATH

if __name__ == '__main__':

    ee.Initialize()  # Initialize the Google Earth Engine

    # Load the feature collection containing the area of interest

    # aoi = ee.FeatureCollection(f'{GEE_USER_PATH}/vector/outline/outline_region_de_murcia')
    aoi = ee.FeatureCollection(f'{GEE_USER_PATH}/vector/outline/outline_cdc_3857')

    aoi_coordinates = aoi.geometry().bounds().getInfo()['coordinates']

    # Dictionary containing the date ranges for each year, will be used to select sat. imagery
    years = {
        '88': ('1987-01-01', '1989-01-01'),
        '97': ('1996-01-01', '1998-01-01'),
        '00': ('1999-01-01', '2001-01-01'),
        '05': ('2004-01-01', '2006-01-01'),
        '09': ('2008-01-01', '2010-01-01'),
    }

    stats = ['median', 'min', 'max']
    stats_combos = list(itertools.combinations(stats, 3))

    # stats_combos = list(itertools.combinations(stats, 3)) + \
    #                list(itertools.combinations(stats, 2)) + \
    #                list(itertools.combinations(stats, 3))

    for year in years:
        name = "cdc_"
        name_string = f'{name}{year}'
        crop_data_folder = f'{GEE_USER_PATH}/raster/crop_data/cdc/'

        # GENERATE FEATURES
        create_features(years[year], aoi, name_string, season='summer')
        create_features(years[year], aoi, name_string, season='winter')

        # GENERATE TRAINING AREAS
        create_training_areas(aoi, name_string=name_string, season='summer')
        create_training_areas(aoi, name_string=name_string, season='winter')

        ##  CLASSIFICATION
        crop_data_collection = {
            'min_median_max_summer': ee.Image(f"{crop_data_folder}crop_data_summer_min_median_max_{name_string}"),
            'min_median_max_winter': ee.Image(f"{crop_data_folder}crop_data_winter_min_median_max_{name_string}"),
        }

        for key in crop_data_collection:
            for combo in stats_combos:
                crop_data_image = crop_data_collection[key]

                potential_crop_area = crop_data_image.select('classification_area')

                bands_to_select = ['red', 'green', 'blue', '.*std.*', 'slope']
                stat_bands = [f'.*{s}.*' for s in list(combo)]
                bands_to_select += stat_bands

                crop_data_image = crop_data_image.select(bands_to_select)
                classification_name = "_".join(combo)

                if 'summer' in key:
                    classification_name += '_summer'
                    training_image = ee.Image(f'{GEE_USER_PATH}/raster/training_areas/training_areas_summer_{name_string}') \
                        .select('training')
                    potential_crop_area = ee.Image(f'{GEE_USER_PATH}/raster/training_areas/training_areas_summer_{name_string}') \
                        .select('classification_area')
                elif 'winter' in key:
                    classification_name += '_winter'
                    training_image = ee.Image(f'{GEE_USER_PATH}/raster/training_areas/training_areas_winter_{name_string}') \
                        .select('training')
                    potential_crop_area = ee.Image(
                        f'{GEE_USER_PATH}/raster/training_areas/training_areas_winter_{name_string}') \
                        .select('classification_area')
                else:
                    classification_name += '_year'

                classify_irrigated_areas(crop_data_image, classification_name, training_image,
                                         potential_crop_area,
                                         aoi, name_string=year,
                                         clf='random_forest', no_trees=350, bag_fraction=.6, vps=2)
