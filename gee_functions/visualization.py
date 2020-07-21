"""
Functions for visualizing EE layers
"""

import folium
from branca.element import Template, MacroElement


def create_folium_map(images=None, name=None, coords=[20, 0], zoom=6, height='100%'):
    """
    Creates a html file containing a folium map visualizing EE image

    :param images: dict. w/ name as key and EE map IDs (via method .getMapId()) as value
    :param name: name of the final html file, if 'None' the folium map is not saved
    :param coords: coordinates for the center of the folium map
    :param zoom: starting zoom level for the folium map
    :param height: starting height for the folium map
    """

    folium_map = folium.Map(location=coords, zoom_start=zoom, height=height, control_scale=True)  # create a folium map

    # If no dictionary with EE Image id's have been provided an folium map with Google satellite basemap is returned
    if images is None:
        folium.TileLayer(
            tiles='http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google',
            name='Google Sat',
            overlay=True,
            control=True,
            subdomains= ['mt0', 'mt1', 'mt2', 'mt3'],
            max_zoom=20
        ).add_to(folium_map)

    else:
        # first add the Google satellite basemap
        folium.TileLayer(
            tiles='http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google',
            name='Google Sat',
            overlay=True,
            control=True,
            subdomains=['mt0', 'mt1', 'mt2', 'mt3'],
            max_zoom=20
        ).add_to(folium_map)

        for key in images:  # loop through the dict. and add all map id's as layer
            folium.TileLayer(
                tiles=images[key]['tile_fetcher'].url_format,
                attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
                overlay=True,
                name=key,
            ).add_to(folium_map)

    folium_map.add_child(folium.LayerControl())  # add layer control

    if name is not None:  # if a name is specified the map is saved as an HTML file
        folium_map.save(f'{name}.html')

    return folium_map


def vis_params_cp(band, min_val, max_val, palette=None, opacity=1):
    """
    Returns a dictionary for the visual parameters for a single band color palette representation

    :param band: name of the band to visualize
    :param min_val: minimum value
    :param max_val: maximum value
    :param palette: optional, color palette vor visualization. Default is red yellow green.
    :return: returns a dictionary containing parameters for visualization
    """
    if palette is None:
        palette = ["red", "orange", "yellow", "green", "darkgreen"]  # default colot palette

    params = {
        'bands': band,
        'min': min_val,
        'max': max_val,
        'palette': palette,
        'opacity': opacity
    }
    return params


def vis_params_rgb(bands=['R', 'G', 'B'], minVal=0, maxVal=3000, gamma=1.4, opacity=None):
    """
    Returns visual parameters for a RGB visualization
    :param bands: list of RGB bandnames, defaults to ['R', 'G', 'B']
    :param minVal: value to map to RGB value 0, defaults to 0
    :param maxVal: value to map to RGB8 value 255, defaults to 3000
    :param gamma: gamma value, defaults to 1.4
    :param opacity: opacity value, defaults to None
    :return: dictionary containing the parameters for visualization
    """
    params = {
        'bands': bands,
        'min': minVal,
        'max': maxVal,
        'gamma': gamma,
        'opacity': opacity
    }
    return params


def vis_irrigated_area_map(band=['ia_year']):
    """
    Returns dictionary containing visual parameters for the visualization of the irrigated area overview map

    :param band: list with the bandname of the overview map with irrigated areas, default name is 'ia_year'
    :return: dictionary containing visual parameters for the visualization of the irrigated area overview map
    """
    params = {
        'bands': band,
        'min': 0,
        'max': 7,
        'palette':[
            '000000',
            '20b407',
            '211cff',
            '86ffa7',
            '64d3ff',
            '5bff0a',
            '0aaeff',
            'ff7e9b',
        ],
    }
    return params


def vis_rf_classification(band=['rf_all_classes']):
    """
    Returns dictionary containing visual parameters for the visualization of land cover maps obtained from random forest
    classification

    :param band: list with the bandname of the lc map, default name is 'rf_all_classes'
    :return: dictionary containing visual parameters for the visualization of the irrigated area overview map
    """
    params = {
        'bands': band,
        'min': 0,
        'max': 10,
        'palette': [
            "FFFFFF",
            "009600",
            "824B32",
            "F5D7A5",
            "FAFA05",
            "6464FE",
            "64C3FF",
            "00008b",
            "AA0F6E",
            "F5A555",
            "000000",
        ],
    }
    return params


def vis_params_ndvi(band=["NDVI"]):
    """
    Return the visual parameters for NDVI maps, representing the values with a red to green color palette
    """
    params = {
        'bands': band,
        'min': -1,
        'max': 1,
        'palette': ["red", "orange", "yellow", "green", "darkgreen"],
    }
    return params


def create_categorical_legend(map, palette, classnames):
    """
    Function to create and add a categorical legend to a folium map.

    :param map: folium map to which the legend will be added
    :param palette: list with color codes for each class
    :param classnames: list with class names, matching the palette list
    :return: folium map with categorical legend
    """
    categories = ""
    # creates class category label to add to legend
    for ind, cl in enumerate(classnames):
        categories += f"<li><span style='background:#{palette[ind]};opacity:0.85;'></span>{classnames[cl]}</li>"

    template_head = """
    {% macro html(this, kwargs) %}

    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>jQuery UI Draggable - Default functionality</title>
      <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">

      <script src="https://code.jquery.com/jquery-1.12.4.js"></script>
      <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>

      <script>
      $( function() {
        $( "#maplegend" ).draggable({
                        start: function (event, ui) {
                            $(this).css({
                                right: "auto",
                                top: "auto",
                                bottom: "auto"
                            });
                        }
                    });
    });

      </script>
    </head>
    <body>
    """

    styling = f"""
    <div id='maplegend' class='maplegend' 
        style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.8);
         border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px;'>

    <div class='legend-title'>Legend</div>
    <div class='legend-scale'>
      <ul class='legend-labels'>
        {categories}
      </ul>
    </div>
    </div>

    </body>
    </html>
    """
    end = """
    <style type='text/css'>
      .maplegend .legend-title {
        text-align: left;
        margin-bottom: 5px;
        font-weight: bold;
        font-size: 90%;
        }
      .maplegend .legend-scale ul {
        margin: 0;
        margin-bottom: 5px;
        padding: 0;
        float: left;
        list-style: none;
        }
      .maplegend .legend-scale ul li {
        font-size: 80%;
        list-style: none;
        margin-left: 0;
        line-height: 18px;
        margin-bottom: 2px;
        }
      .maplegend ul.legend-labels li span {
        display: block;
        float: left;
        height: 16px;
        width: 30px;
        margin-right: 5px;
        margin-left: 0;
        border: 1px solid #999;
        }
      .maplegend .legend-source {
        font-size: 80%;
        color: #777;
        clear: both;
        }
      .maplegend a {
        color: #777;
        }
    </style>
    {% endmacro %}"""

    template = template_head + styling + end  # Combine all the parts into a single templace docstring
    macro = MacroElement()
    macro._template = Template(template)  # create an element

    return map.get_root().add_child(macro)  # add element to the map and return the map




