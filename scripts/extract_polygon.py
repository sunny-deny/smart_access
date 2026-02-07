import os
import geopandas as gpd

try:
    from .utils_qgis import add_layer_to_project
except ImportError:
    from utils_qgis import add_layer_to_project


def _read_caop(path, layer=None):
    ext = os.path.splitext(path)[1].lower()

    if not os.path.exists(path):
        raise FileNotFoundError(f"CAOP file not found: {path}")

    if ext == ".shp":
        return gpd.read_file(path)

    if ext == ".gpkg":
        if layer:
            return gpd.read_file(path, layer=layer)
        return gpd.read_file(path)

    raise ValueError(f"Unsupported file type: {ext}")


def extract_polygon(
    municipality,
    caop_path,
    output_base,
    caop_layer=None,
    name_col="concelho",
    epsg=4326,
    add_to_qgis=True,
):

    print("[INFO] Loading CAOP...")
    gdf = _read_caop(caop_path, caop_layer)

    gdf.columns = gdf.columns.str.lower()
    name_col = name_col.lower()

    if name_col not in gdf.columns:
        print(f"[ERROR] Column '{name_col}' not found.")
        return None

    if gdf.crs is None:
        print("[ERROR] CAOP has no CRS.")
        return None

    target_crs = f"EPSG:{epsg}"

    if gdf.crs.to_string() != target_crs:
        gdf = gdf.to_crs(target_crs)

    print(f"[INFO] Searching municipality: {municipality}")

    match = gdf[
        gdf[name_col].astype(str).str.upper() == municipality.upper()
    ]

    if match.empty:
        print(f"[WARNING] Municipality '{municipality}' not found.")
        return None

    poly = match.dissolve(by=name_col).reset_index()

    safe_name = municipality.lower().replace(" ", "_")

    out_dir = os.path.join(output_base, "municipality_shapes")
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(
        out_dir,
        f"{safe_name}_polygon_{epsg}.gpkg"
    )

    out_layer = f"{safe_name}_polygon"

    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except PermissionError:
            print("[ERROR] Close file in QGIS and retry.")
            return None

    print(f"[INFO] Writing: {out_path}")

    poly.to_file(out_path, layer=out_layer, driver="GPKG")

    if add_to_qgis:
        try:
            add_layer_to_project(
                out_path,
                out_layer,
                f"{municipality} polygon"
            )
        except Exception as e:
            print(f"[INFO] QGIS add skipped: {e}")

    msg = f"[SUCCESS] Polygon saved: {out_path}"
    print(msg)

    return msg


if __name__ == "__main__":

    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    caop = os.path.join(
        base_dir,
        "data",
        "caop",
        "Cont_AAD_CAOP2023.shp"
    )

    out = os.path.join(base_dir, "output")

    extract_polygon(
        municipality="Coimbra",
        caop_path=caop,
        output_base=out,
        name_col="concelho",
        epsg=4326,
        add_to_qgis=True,
    )
