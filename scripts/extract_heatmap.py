import os
from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer
)
from qgis.analysis import QgsNativeAlgorithms
import processing
from .init_qgis import init_qgis

def extract_heatmap_from_poi(municipality, category):
    # === Constants ===
    HEATMAP_RADIUS = 500
    PIXEL_SIZE = 10
    LAYER_NAME = "pois"

    # Get plugin root directory
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_base = os.path.join(plugin_dir, "output")

    mun_safe = municipality.lower().replace(" ", "_")
    cat_safe = category.lower()

    input_path = os.path.join(output_base, "pois_by_municipality", mun_safe, f"pois_{cat_safe}.gpkg")
    heatmap_out_dir = os.path.join(output_base, "heatmaps", mun_safe)
    os.makedirs(heatmap_out_dir, exist_ok=True)
    heatmap_path = os.path.join(heatmap_out_dir, f"{cat_safe}_heatmap.tif")

    if os.path.exists(heatmap_path):
        return heatmap_path  # Already exists

    # === Init QGIS if needed ===
    init_qgis()
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

    layer_uri = f"{input_path}|layername={LAYER_NAME}"
    vector_layer = QgsVectorLayer(layer_uri, f"{mun_safe}_{cat_safe}_pois", "ogr")

    if not vector_layer.isValid():
        return f"[ERROR] Could not load POI layer: {input_path}"

    print(f"[INFO] Generating heatmap for {mun_safe} - {cat_safe}")

    result = processing.run("qgis:heatmapkerneldensityestimation", {
        'INPUT': vector_layer,
        'RADIUS': HEATMAP_RADIUS,
        'PIXEL_SIZE': PIXEL_SIZE,
        'WEIGHT_FIELD': '',
        'KERNEL': 0,
        'DECAY': 0,
        'OUTPUT_VALUE': 0,
        'OUTPUT': heatmap_path
    })

    # Confirm output
    raster = QgsRasterLayer(result['OUTPUT'], f"{cat_safe}_heatmap")
    if raster.isValid():
        print(f"[SUCCESS] Heatmap saved: {heatmap_path}")
        return heatmap_path
    else:
        return f"[ERROR] Failed to load generated heatmap: {heatmap_path}"
