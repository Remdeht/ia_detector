import os
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_pdf import PdfPages

RAW_CSV_DIR = r'/data/csv/single_year_thresholds/'
RESULS_DIR = r'/results/thresholds_v2'


def create_band_boxplot(df, bandname, season):
    """Creates the barchart showing the value range per class for the spectral index"""

    def autolabel(rects):
        """Attach a text label above each bar in *rects*, displaying its height."""
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    years = ['88', '97', '00', '09']  # The years examined

    fig = plt.figure(constrained_layout=True, figsize=(20, 15))
    gs = GridSpec(1, 4, figure=fig)  # , width_ratios=[2, 1.2]

    min_val = df['p10'].min()  # highest max and lowest min value to determine the value range of the y axis
    max_val = df['p90'].max()

    for ind, year in enumerate(years):  # create a plot for each year, the four plots will be added together
        ax = fig.add_subplot(gs[0, ind])
        ax.title.set_text(year)

        if max_val < 100:  # depending on the value range the max y value is set
            ax.set_ylim([min_val - .1, max_val + .1])
        else:
            ax.set_ylim([min_val - 100, max_val + 100])

        df_year = df[df['year'] == year]  # select all the values within the df belonging to the year being plotted
        class_labels = df['class'].unique()  # creates a list of the unique class labels

        low_data = df_year['p10'].to_list()  # mix and max values to plot the barchart of the spectral index value range
        high_data = (df_year['p90'] - df_year['p10']).to_list()

        # all the bars
        b1 = ax.bar(1, high_data[0], width=.6, bottom=low_data[0], color='#009600',
                    label=class_labels[0])
        b2 = ax.bar(2, high_data[1], width=.6, bottom=low_data[1], color='#824B32',
                    label=class_labels[1])
        b3 = ax.bar(3, high_data[2], width=.6, bottom=low_data[2], color='#A58755',
                    label=class_labels[2])
        b4 = ax.bar(4, high_data[3], width=.6, bottom=low_data[3], color='#F5D7A5',
                    label=class_labels[3])
        b5 = ax.bar(5, high_data[4], width=.6, bottom=low_data[4], color='#F5A555',
                    label=class_labels[4])
        b6 = ax.bar(6, high_data[5], width=.6, bottom=low_data[5], color='#64C3FF',
                    label=class_labels[5])
        b7 = ax.bar(7, high_data[6], width=.6, bottom=low_data[6], color='#6464FE',
                    label=class_labels[6])
        b8 = ax.bar(8, high_data[7], width=.6, bottom=low_data[7], color='#FAFA05',
                    label=class_labels[7])
        b9 = ax.bar(9, high_data[8], width=.6, bottom=low_data[8], color='#AA0F6E',
                    label=class_labels[8])

        ax.set_xticks(range(1, 10)) # Set the number of ticks and add shortened class labels to each tick
        class_labels = ['NT', 'DS', 'OS', 'RT', 'RC', 'IT', 'IC', 'GH', 'UA']
        ax.set_xticklabels(class_labels)

        # autolabel(b1)
        # autolabel(b2)
        # autolabel(b3)
        # autolabel(b4)
        # autolabel(b5)
        # autolabel(b6)
        # autolabel(b7)
        # autolabel(b8)
        # autolabel(b9)

    ax.legend()  # Add a legend to the plot

    if not os.path.exists(f'{RESULS_DIR}/{season}'):
        os.mkdir(f'{RESULS_DIR}/{season}')  # make sure a directory is present to save the results

    fig.savefig(f'{RESULS_DIR}/{season}/{bandname.replace(" ", "_")}.png')  # save the figure as a png
    # fig.savefig(f'results/threshold/plots/extended/pdf/{row.iloc[0]}.pdf')  # or if needed as a pdf

    plt.close()


def create_graphs(directory, season):
    """
    Processes the results obtrained from the land cover analysis and visualized them in a barchart
    :param directory: Directory in which the results of the land cover analysis are stored as a csv file
    :param season: Season for which the values are to be analysed
    :return: saves all the data into a single csv file and creates a graph for each spectral index examined
    """
    files = os.listdir(directory)

    band_data_all_years = pd.DataFrame(columns=['year', 'class', 'mean', 'p10', 'p90']) #  Create df to store results

    for csv_file in files:
        year = csv_file[-6:-4]
        df = pd.read_csv(f'{directory}{csv_file}')
        df = df.drop(['.geo', 'system:index'], 1)

        bands = df['band'].unique()  # select all the spectral index bands to analyse
        classes = df['class'].unique()

        band_data = pd.DataFrame(columns=['year', 'class', 'mean', 'p10', 'p90'])

        for band in bands:
            for cl in classes:
                row = df[(df['band'] == band) & (df['class'] == cl)]
                row['year'] = year
                band_data = pd.concat([band_data, row], sort=True)  # join all relevant data for the year into df

        band_data_all_years = pd.concat([band_data_all_years, band_data], sort=True)

    for band in bands:
        band_vals = band_data_all_years[(band_data_all_years['band'] == band)]
        create_band_boxplot(band_vals, band, season)  # create a figure per band plotting the data ranges of each class

    if not os.path.exists(f'{RAW_CSV_DIR}/combined_thresholds/'):
        os.mkdir(f'{RAW_CSV_DIR}/combined_thresholds/')

    band_data_all_years.to_csv(f'{RAW_CSV_DIR}/combined_thresholds/band_data_all_years_{season}.csv', index=False)


if __name__ == '__main__':
    create_graphs(f'{RAW_CSV_DIR}year\\', 'year')
    create_graphs(f'{RAW_CSV_DIR}summer\\', 'summer')
    create_graphs(f'{RAW_CSV_DIR}winter\\', 'winter')
