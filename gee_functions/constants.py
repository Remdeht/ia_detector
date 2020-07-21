"""
Contains constants used throughout the entire package
"""
import ee
ee.Initialize()


GEE_USER_PATH = ee.data.getAssetRoots()[0]['id']  # Retrieves the user's GEE path to be used for saving assets
