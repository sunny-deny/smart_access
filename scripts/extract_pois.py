import geopandas as gpd
import os
from .utils_qgis import add_layer_to_project 

def extract_filtered_pois(municipality, category, pois_path, caop_path, output_base):
    print("[INFO] Loading POIs...")
    pois = gpd.read_file(pois_path, layer="pois_portugal")

    print("[INFO] Loading CAOP municipalities...")
    municipalities = gpd.read_file(caop_path, layer="cont_municipios")
    municipalities.columns = municipalities.columns.str.lower()
    pois.columns = pois.columns.str.lower()
    municipalities = municipalities.to_crs(epsg=4326)
    pois = pois.to_crs(epsg=4326)

    match = municipalities[municipalities["municipio"].str.upper() == municipality.upper()]
    if match.empty:
        print(f"[WARNING] Municipality '{municipality}' not found.")
        return None

    area = match.iloc[0].geometry
    pois_subset = pois[pois.geometry.within(area)]

    if category:
        if "category" not in pois_subset.columns:
            print("[ERROR] Column 'category' not found in POIs.")
            return None
        pois_subset = pois_subset[pois_subset["category"] == category]

    if pois_subset.empty:
        print(f"[INFO] No POIs found for {municipality} with category = '{category}'.")
        return None

    out_dir = os.path.join(output_base, municipality.lower().replace(" ", "_"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"pois_{category.lower()}.gpkg")
    pois_subset.to_file(out_path, layer="pois", driver="GPKG")
    add_layer_to_project(out_path, "pois", f"POIs {category} - {municipality}")
    print(f"[SUCCESS] Saved to: {out_path}")
    return f"[SUCCESS] POIs for '{municipality}' ({category}) extracted and added to the project."
