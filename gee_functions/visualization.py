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

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        overlay=True,
        control=True
    ).add_to(folium_map)

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