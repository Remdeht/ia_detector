import ee

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA

import plotly.graph_objects as go

from typing import List

try:
    from constants import PALETTE_RF
except ImportError:
    from .constants import PALETTE_RF


def take_strat_sample(
        calibration_maps,
        feature_data,
        lc_classes,
        aoi: ee.FeatureCollection,
        samplesize: int = 5000,
        scale: int = 30,
        tilescale: int = 16,
        classband: str = 'lc',
        file_name: str = 'sample_collection',
        dir_name: str = 'sample_directory',
        min_connected_pixels: int = 60) -> (ee.batch.Task, ee.Image, ee.Image):
    """
        Selects pixels from target classes extracted from calibration maps, filters out small patches of pixels and
        performs a stratified sample from the remaining

        :param calibration_maps: Dictionary containing calibration maps loaded as Earth Engine Image objects
        :param feature_data: Collection of images containing the feature data for classification
        :param lc_classes: dict containing the calibration classes to sample
        :param aoi: GEE FeatureCollection containing the vector of the area of interest for classification, this will be
         used to mask any pixels outside of the area of interest
        :param samplesize: Number of samples to take per class
        :param scale: A nominal scale in meters of the projection to sample in. Defaults to the scale of the first band
         of the input image.
        :param tilescale: Scaling factor used to reduce aggregation tile size; using a larger tileScale (e.g. 2 or 4) may
        enable computations that run out of memory with the default.
        :param classband: The name to be used the band containing the patches of the target classes. Defaults to 'lc'
        :param file_name: Name for the CSV file in which the samples are stored on the Google Drive, Defaults to 'sample_collection'
        :param dir_name: Name for the directory in which the samples are stored on the Google Drive, Defaults to 'sample_directory'
        :param min_connected_pixels: Number of minimum connected pixels a patch needs to contain, otherwise it is not
         considered for sampling
        :return: export task, EE Image containing the masked patches, EE image containing the patches
        """

    sample_collection = None
    new_class_values = {}

    for key in calibration_maps:
        lc_map = calibration_maps[key]
        land_areas_for_sampling = ee.Image(0)  # Empty image

        pix_val = 1

        for lc_class, class_values in lc_classes.items():
            # Paints the areas for each of the specified land cover classes to sample on the empty image
            for cal_lc_val in class_values:
                land_areas_for_sampling = land_areas_for_sampling.where(lc_map.eq(cal_lc_val), pix_val)

            new_class_values[pix_val] = lc_class
            pix_val += 1

        land_areas_for_sampling = land_areas_for_sampling.clip(aoi).reproject(feature_data[key].projection())

        training_regions_mask = land_areas_for_sampling.connectedPixelCount(min_connected_pixels).gte(
            min_connected_pixels).reproject(feature_data[key].projection())
        # Removes smaller land cover patches based on the number of connected pixels
        lc_patches = land_areas_for_sampling.where(training_regions_mask.eq(0), 0).rename(classband)

        # combine the feature data and land cover patches into one image
        data_for_sampling = feature_data[key].addBands(lc_patches)

        sample = data_for_sampling.stratifiedSample(  # perform a stratified sample
            numPoints=samplesize,
            classBand=classband,
            scale=scale,
            tileScale=tilescale,
            region=aoi.geometry()
        ).filter(ee.Filter.neq(classband, 0))

        if sample_collection is None:  # combine the samples for all the years being used for calibration
            sample_collection = sample
        else:
            sample_collection = sample_collection.merge(sample)

    def add_class_name(x):

        name_dict = ee.Dictionary(new_class_values)
        return ee.Feature(x).set('class', name_dict.get(ee.Number(ee.Feature(x).get('lc')).format())).copyProperties(x)

    sample_collection = sample_collection.map(add_class_name)

    task = ee.batch.Export.table.toDrive(
        collection=sample_collection,
        description=file_name,
        fileFormat='CSV',
        folder=dir_name,
    )
    task.start()  # export to the Google drive

    return task, training_regions_mask, lc_patches


def remove_outliers(
        df: pd.DataFrame,
        bands_to_include: List[str],
        lower_quantile: float = 0.05,
        upper_quantile: float = 0.95) -> pd.DataFrame:
    """
    Removes the outliers from a pandas dataframe
    :param df: Pandas dataframe containing the data to remove
    :param bands_to_include:bands for which to remove the outliers
    :param lower_quantile: lower quantile, between 0 and 1
    :param upper_quantile: upper quantile, between 0 and 1
    :return: Pandas dataframe with outliers removed
    """

    q1 = df[bands_to_include].quantile(lower_quantile)
    q3 = df[bands_to_include].quantile(upper_quantile)
    iqr = q3 - q1
    df = df[~((df[bands_to_include] < (q1 - 1.5 * iqr)) | (df[bands_to_include] > (q3 + 1.5 * iqr))).any(axis=1)]

    return df


def get_lda_params(X, y):
    sklearn_lda = LDA(n_components=1, store_covariance=True)

    LDA_clf = sklearn_lda.fit(X, y)
    LDA_fit = sklearn_lda.fit_transform(X, y)

    if np.mean(LDA_fit[:, 0][y == 0]) > np.mean(LDA_fit[:, 0][y == 1]):
        greater_than = False
    else:
        greater_than = True

    coefficients = list(LDA_clf.scalings_.flatten())
    covariance = LDA_clf.covariance_

    pred = X.copy()

    for ind, band in enumerate(X.columns):
        pred[band] = X[band] * coefficients[ind]

    sklearn_df = pd.DataFrame(data=LDA_fit, columns=['Sklearn Prediction'])
    man_df = pd.DataFrame(data=pred.sum(1).values, columns=['Manual Prediction'])
    sklearn_df['Manual Prediction'] = man_df['Manual Prediction']
    sklearn_df['intercept'] = sklearn_df['Sklearn Prediction'] - sklearn_df['Manual Prediction']
    intercept = sklearn_df['intercept'].mode().values

    df_coefficients = pd.DataFrame({'Bandname': X.columns, 'Coefficient': coefficients})
    # df_covariance = pd.DataFrame({'Bandname': X.columns, 'Coefficient': coefficients})

    return intercept, df_coefficients, LDA_fit, greater_than, covariance


def perform_lda_scaling(
        data,
        intercept,
        coefficients,
        threshold,
        gt: bool = True,
        min_connected_pixels: int = 10):
    transformed_features = {}
    for ind, row in coefficients.iterrows():
        transformed_features[row['Bandname']] = data.select(row['Bandname']).multiply(float(row['Coefficient']))

    total_lda_1 = None

    for feat_key in transformed_features:
        if total_lda_1 is None:
            total_lda_1 = transformed_features[feat_key]
        else:
            total_lda_1 = total_lda_1.add(transformed_features[feat_key])

    total = total_lda_1.add(ee.Number(intercept[0])).rename('total')

    if gt:
        training_areas = total.gte(threshold).rename('training')
    else:
        training_areas = total.lte(threshold).rename('training')

    training_areas_mask = training_areas.connectedPixelCount(min_connected_pixels).gte(min_connected_pixels).reproject(
        data.projection())

    final_img = total.addBands(training_areas.where(training_areas_mask.eq(0), 0))

    return final_img


def get_data(data_loc, bandnames, target_class, subsample_other=True):
    def assign_bin_y(val):
        if val == target_class:
            return 1
        else:
            return 0

    df = pd.read_csv(data_loc)
    bandnames = [band for band in bandnames if band in list(df.columns)]

    df['lc_bin'] = df['class'].apply(assign_bin_y)
    df = df[bandnames + ['lc', 'lc_bin', 'class']].dropna()
    df = remove_outliers(df, bandnames)

    if subsample_other:
        df_target = df[(df['class'] == target_class)]
        df_other = df[~(df['lc'] == target_class)].groupby('lc').sample(n=2000, random_state=1)
        df = pd.concat([df_target, df_other])

    X = df[bandnames]
    y = df[['lc', 'lc_bin', 'class']]

    return X, y


def get_data(data_loc, bandnames, target_class, subsample_other=True):
    def assign_bin_y(val):
        if val == target_class:
            return 1
        else:
            return 0

    df = pd.read_csv(f'{data_loc}.csv')
    bandnames = [band for band in bandnames if band in list(df.columns)]

    df['lc_bin'] = df['class'].apply(assign_bin_y)
    df = df[bandnames + ['lc', 'lc_bin', 'class']].dropna()
    df = remove_outliers(df, bandnames)

    if subsample_other:
        df_target = df[(df['class'] == target_class)]
        df_other = df[~(df['lc'] == target_class)].groupby('lc').sample(n=2000, random_state=1)
        df = pd.concat([df_target, df_other])

    X = df[bandnames]
    y = df[['lc', 'lc_bin', 'class']]

    return X, y


def get_histogram(X, y, classes, user_threshold=None, suggested_threshold=None, fig=None, row=None, col=None):
    if fig is None:
        fig = go.Figure()

    for cl_key, cl_name in classes.items():

        if len(y.unique()) == 2:
            fig.add_trace(
                go.Histogram(
                    x=X[:, 0][y == cl_key],
                    name=classes[cl_key],
                    legendgroup=cl_key,
                    opacity=.85,
                    showlegend=False,
                ),
                row=row,
                col=col
            )
        else:

            if cl_key == 0:
                opacity = 0.90
                showlegend = True
                data_x = X[:, 0][y == cl_name['lc_val']]
                cl_name = cl_name['name']
            else:
                opacity = 0.65
                showlegend = False
                data_x = X[:, 0][y == cl_key]

            fig.add_trace(
                go.Histogram(
                    x=data_x,
                    name=cl_name,
                    legendgroup=cl_name,
                    marker_color=PALETTE_RF[cl_name],
                    opacity=opacity,
                    showlegend=showlegend,
                ),
                row=row,
                col=col
            )

    if user_threshold is not None:
        fig.add_shape(
            type="line",
            x0=user_threshold,
            y0=0,
            x1=user_threshold,
            y1=500,
            line=dict(
                color="Red",
                width=3
            ),
            name='Threshold selected by user',
            row=row,
            col=col
        )

    if suggested_threshold is not None:
        fig.add_shape(
            type="line",
            x0=suggested_threshold,
            y0=0,
            x1=suggested_threshold,
            y1=500,
            line=dict(
                color="RoyalBlue",
                width=3
            ),
            name='Suggested Threshold',
            row=row,
            col=col
        )

    # Overlay both histograms
    fig.update_layout(barmode='overlay')
    # Reduce opacity to see both histograms
    # fig.update_traces(opacity=0.75)
    return fig
