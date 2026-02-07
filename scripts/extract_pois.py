import os
import geopandas as gpd


def main():
    # === Base path (project root) ===
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(script_dir, ".."))

    data_dir = os.path.join(base_dir, "data")
    output_dir = os.path.join(base_dir, "output")

    # === File paths ===
    pois_path = os.path.join(
        output_dir,
        "portugal_pois_filtered_3763.gpkg"
    )

    caop_path = os.path.join(
        data_dir,
        "caop",
        "Cont_AAD_CAOP2023.shp"
    )

    out_path = os.path.join(
        output_dir,
        "coimbra_pois_3763.gpkg"
    )

    pois_layer = "pois_all_categories"
    out_layer = "pois_coimbra"

    # === Check files ===
    if not os.path.exists(pois_path):
        raise FileNotFoundError(f"POI file not found: {pois_path}")

    if not os.path.exists(caop_path):
        raise FileNotFoundError(f"CAOP file not found: {caop_path}")

    # === Load data ===
    print("[INFO] Loading filtered Portugal POIs...")
    pois = gpd.read_file(pois_path, layer=pois_layer)

    print("[INFO] Loading CAOP boundaries...")
    caop = gpd.read_file(caop_path)

    # === CRS normalization (target: EPSG:3763) ===
    target_crs = "EPSG:3763"

    if pois.crs is None:
        raise ValueError("POI file has no CRS defined.")

    if pois.crs.to_string() != target_crs:
        print(f"[INFO] Reprojecting POIs to {target_crs}")
        pois = pois.to_crs(target_crs)

    if caop.crs is None:
        raise ValueError("CAOP file has no CRS defined.")

    if caop.crs.to_string() != target_crs:
        print(f"[INFO] Reprojecting CAOP to {target_crs}")
        caop = caop.to_crs(target_crs)

    # === Filter Coimbra municipality ===
    print("[INFO] Extracting Coimbra boundary...")

    if "CONCELHO" not in caop.columns:
        raise ValueError("Column 'CONCELHO' not found in CAOP shapefile.")

    coimbra = caop[caop["CONCELHO"].str.upper() == "COIMBRA"]

    if coimbra.empty:
        raise ValueError("No geometry found for municipality: Coimbra")

    # Merge multipart polygons
    coimbra_geom = coimbra.geometry.unary_union

    # === Spatial filter ===
    print("[INFO] Filtering POIs within Coimbra boundary...")

    pois_coimbra = pois[pois.geometry.within(coimbra_geom)].copy()

    print(f"[RESULT] {len(pois_coimbra)} POIs found inside Coimbra")

    # === Export ===
    os.makedirs(output_dir, exist_ok=True)

    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except PermissionError:
            print("[ERROR] Output file is open in QGIS. Close it and retry.")
            raise

    print(f"[INFO] Writing output to {out_path}")

    pois_coimbra.to_file(
        out_path,
        layer=out_layer,
        driver="GPKG"
    )

    print("[SUCCESS] Coimbra POIs exported successfully")


if __name__ == "__main__":
    main()
