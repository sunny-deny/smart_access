import geopandas as gpd
import os
from .utils_qgis import add_layer_to_project

def export_municipality_polygon(municipality_name, caop_path, output_dir):
    # Load CAOP data
    municipalities = gpd.read_file(caop_path, layer="cont_municipios")
    municipalities.columns = municipalities.columns.str.lower()
    municipalities = municipalities.to_crs(epsg=4326)

    # Filter the selected municipality
    selected = municipalities[municipalities["municipio"].str.upper() == municipality_name.upper()]
    if selected.empty:
        return f"[ERROR] Municipality '{municipality_name}' not found."

    selected = selected.copy()
    selected["label"] = municipality_name.title()

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define output path
    safe_name = municipality_name.lower().replace(" ", "_")
    output_path = os.path.join(output_dir, f"{safe_name}_polygon.gpkg")

    # Save selected municipality polygon
    selected.to_file(output_path, layer="polygon", driver="GPKG")

    # Add layer to QGIS project
    add_layer_to_project(output_path, "polygon", f"Municipality Polygon - {municipality_name}")

    return f"[SUCCESS] Municipality boundary for '{municipality_name}' generated and added to the project."
