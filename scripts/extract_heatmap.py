import os
import sys
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer
from qgis.analysis import QgsNativeAlgorithms
import processing

try:
    from .init_qgis import init_qgis
except ImportError:
    from init_qgis import init_qgis


def extract_heatmap_qgis(
    municipality,
    category,
    pois_gpkg,
    pois_layer,
    output_base,
    project_path=None,
    radius=500,
    pixel_size=10,
    add_to_project=True,
):
    if not os.path.exists(pois_gpkg):
        return f"[ERROR] POIs not found: {pois_gpkg}"

    out_dir = os.path.join(output_base, "heatmaps", municipality.lower().replace(" ", "_"))
    os.makedirs(out_dir, exist_ok=True)

    suffix = category.lower() if category else "all"
    heatmap_path = os.path.join(out_dir, f"{suffix}_heatmap.tif")

    qgs = init_qgis()
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

    project = QgsProject.instance()
    if project_path:
        if not os.path.exists(project_path):
            qgs.exitQgis()
            return f"[ERROR] Project not found: {project_path}"
        project.read(project_path)

    uri = f"{pois_gpkg}|layername={pois_layer}"
    layer = QgsVectorLayer(uri, f"pois_{municipality}", "ogr")
    if not layer.isValid():
        qgs.exitQgis()
        return f"[ERROR] Could not load POIs layer: {pois_gpkg} ({pois_layer})"

    if category:
        if "category" not in [f.name() for f in layer.fields()]:
            qgs.exitQgis()
            return "[ERROR] Field 'category' not found in POIs."
        layer.setSubsetString(f"\"category\" = '{category.lower()}'")

    try:
        processing.run("qgis:heatmapkerneldensityestimation", {
            "INPUT": layer,
            "RADIUS": radius,
            "PIXEL_SIZE": pixel_size,
            "WEIGHT_FIELD": "",
            "KERNEL": 0,
            "DECAY": 0,
            "OUTPUT_VALUE": 0,
            "OUTPUT": heatmap_path,
        })
    except Exception as e:
        qgs.exitQgis()
        return f"[ERROR] Heatmap processing failed: {e}"

    if add_to_project:
        raster = QgsRasterLayer(heatmap_path, f"heatmap_{suffix}_{municipality}")
        if raster.isValid():
            project.addMapLayer(raster)

    if project_path:
        project.write()

    qgs.exitQgis()
    return f"[SUCCESS] Heatmap exported: {heatmap_path}"


if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    municipality = "Coimbra"
    mun_safe = municipality.lower().replace(" ", "_")

    pois_gpkg = os.path.join(base_dir, "output", mun_safe, "pois_all.gpkg")
    output_base = os.path.join(base_dir, "output")

    project_path = os.path.join(base_dir, "portugal_project.qgz")
    if not os.path.exists(project_path):
        project_path = None

    print(
        extract_heatmap_qgis(
            municipality=municipality,
            category="education",
            pois_gpkg=pois_gpkg,
            pois_layer="pois",
            output_base=output_base,
            project_path=project_path,
            radius=500,
            pixel_size=10,
            add_to_project=True,
        )
    )
