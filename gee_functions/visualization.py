import folium
from branca.element import Template, MacroElement


def create_folium_map(images, name=None, coords=[20, 0], zoom=6, height='100%'):
    """
    Creates a html file containing a folium map containing specified EE image

    :param images: Dictionary of EE map IDs (obtained via method .getMapId()) to add to folium map
    :param name: name of the final html file, if None the map is not saved
    :param coords: coordinates for the center of the folium map
    :param zoom:starting zoom level for the folium map
    :param height: starting height for the folium map
    """
    folium_map = folium.Map(location=coords, zoom_start=zoom, height=height, control_scale=True)

    if images is None:
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google',
            name='Google Maps',
            overlay=True,
            control=True
        ).add_to(folium_map)

    else:
        for key in images:
            folium.TileLayer(
                tiles=images[key]['tile_fetcher'].url_format,
                attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
                overlay=True,
                name=key,
            ).add_to(folium_map)


    folium_map.add_child(folium.LayerControl())

    if name is not None:
        folium_map.save(f'{name}.html')

    return folium_map


# Generate visual parameters for visualization
def vis_params_cp(band, min_val, max_val, palette=None, opacity=1):
    """
    Returns a dictionary for the visual parameters for a single band color palette representation

    :param band: Name of the band to visualize
    :param min: minimum value for color range
    :param max: maximum value for color range
    :param palette: optional, color palette vor visualization. Default is red yellow green.
    :return: Returns a dictionary containing parameters for visualization
    """
    if palette is None:
        palette = ["red", "orange", "yellow", "green", "darkgreen"]

    params = {
        'bands': band,
        'min': min_val,
        'max': max_val,
        'palette': palette,
        'opacity': opacity
    }
    return params


def vis_params_rgb_ls457(bands= [], minVal=0, maxVal=3000, gamma=1.4):
    """
    Return the visual parameters for RGB maps

    :param minVal: Min Value
    :param maxVal: Max Value
    :param gamma: Gamma Value
    :return: Dictionary containing the parameters for visualization
    """
    params = {
        'bands': bands,
        'min': minVal,
        'max': maxVal,
        'gamma': gamma,
    }
    return params


def vis_irrigated_area_map(band=['ia_year']):
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
            "darkblue",
            "FFFFFF",
            "FFFFFF",
            "000000",
        ],
    }
    return params


def vis_params_ndvi():
    """
    Return the visual parameters for NDVI maps, representing the values with a red to green color palette
    """
    params = {
        'bands': ["NDVI"],
        'min': -1,
        'max': 1,
        'palette': ["red", "orange", "yellow", "green", "darkgreen"],
    }
    return params

def vis_params_pr_ndvi():
    params = {
        'bands': ["NDVI_pr"],
        'min': -1,
        'max': 1,
        'palette': ["red", "orange", "yellow", "green", "darkgreen"],
    }
    return params


def create_categorical_legend(map, palette, classnames):
    categories = ""
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

    template = template_head + styling + end
    macro = MacroElement()
    macro._template = Template(template)

    return map.get_root().add_child(macro)




