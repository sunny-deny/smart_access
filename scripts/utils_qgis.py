from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsProject

def add_layer_to_project(file_path, layer_name, custom_name=None):
    if file_path.lower().endswith(('.gpkg', '.shp', '.geojson')):
        uri = f"{file_path}|layername={layer_name}"
        layer = QgsVectorLayer(uri, custom_name or layer_name, "ogr")
    elif file_path.lower().endswith(('.tif', '.tiff')):
        layer = QgsRasterLayer(file_path, custom_name or layer_name)
    else:
        print(f"[ERROR] Unsupported file type: {file_path}")
        return False

    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        print(f"[INFO] Layer added: {custom_name or layer_name}")
        return True
    else:
        print(f"[ERROR] Failed to load layer: {file_path}")
        return False
