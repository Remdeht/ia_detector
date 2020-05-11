import folium


def create_folium_map(images, name=None, coords=[20, 0], zoom=3, height=5000):
    """
    Creates a html file containing a folium map containing specified EE image

    :param images: Dictionary of EE map IDs (obtained via method .getMapId()) to add to folium map
    :param name: name of the final html file, if None the map is not saved
    :param coords: coordinates for the center of the folium map
    :param zoom:starting zoom level for the folium map
    :param height: starting height for the folium map
    """
    folium_map = folium.Map(location=coords, zoom_start=zoom, height=height, control_scale=True)

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


