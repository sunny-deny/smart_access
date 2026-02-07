import os
import numpy as np
import geopandas as gpd

from .utils_qgis import add_layer_to_project

def _safe(s: str) -> str:
    return s.lower().replace(" ", "_")


def _make_grid(bounds, cell_size):
    minx, miny, maxx, maxy = bounds
    xs = np.arange(minx, maxx, cell_size)
    ys = np.arange(miny, maxy, cell_size)

    polys = []
    for x in xs:
        for y in ys:
            polys.append(
                gpd.GeoSeries.from_wkt(
                    [f"POLYGON(({x} {y},{x+cell_size} {y},{x+cell_size} {y+cell_size},{x} {y+cell_size},{x} {y}))"]
                ).iloc[0]
            )
    return polys


def extract_heatmap(
    municipality: str,
    category: str | None,
    pois_gpkg: str,
    pois_layer: str,
    polygon_gpkg: str,
    polygon_layer: str,
    output_base: str,
    cell_size_m: int = 250,
    epsg_work: int = 3763,
    add_to_qgis: bool = True,
):
    if not os.path.exists(pois_gpkg):
        return f"[ERROR] POIs file not found: {pois_gpkg}"

    if not os.path.exists(polygon_gpkg):
        return f"[ERROR] Polygon file not found: {polygon_gpkg}"

    pois = gpd.read_file(pois_gpkg, layer=pois_layer)
    poly = gpd.read_file(polygon_gpkg, layer=polygon_layer)

    pois.columns = pois.columns.str.lower()
    poly.columns = poly.columns.str.lower()

    if pois.empty:
        return "[ERROR] POIs layer is empty."

    if poly.empty:
        return "[ERROR] Polygon layer is empty."

    if pois.crs is None or poly.crs is None:
        return "[ERROR] Missing CRS in POIs or polygon."

    pois = pois.to_crs(epsg=epsg_work)
    poly = poly.to_crs(epsg=epsg_work)

    if category:
        c = category.lower()
        if "category" not in pois.columns:
            return "[ERROR] Column 'category' not found in POIs."
        pois = pois[pois["category"] == c].copy()
        if pois.empty:
            return f"[INFO] No POIs for category '{category}'."
    else:
        c = "all"

    area_geom = poly.geometry.unary_union
    bounds = area_geom.bounds

    grid_geoms = _make_grid(bounds, cell_size_m)
    grid = gpd.GeoDataFrame({"cell_id": range(len(grid_geoms))}, geometry=grid_geoms, crs=pois.crs)

    grid = grid[grid.intersects(area_geom)].copy()
    grid["geometry"] = grid.geometry.intersection(area_geom)

    join = gpd.sjoin(pois[["geometry"]], grid[["cell_id", "geometry"]], predicate="within", how="left")
    counts = join.groupby("cell_id").size()

    grid["poi_count"] = grid["cell_id"].map(counts).fillna(0).astype(int)
    grid["area_m2"] = grid.geometry.area
    grid["density_km2"] = (grid["poi_count"] / (grid["area_m2"] / 1_000_000)).replace([np.inf, -np.inf], 0).fillna(0)

    grid = grid.to_crs(epsg=4326)

    mun_safe = _safe(municipality)
    out_dir = os.path.join(output_base, "heatmaps", mun_safe)
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"heatmap_{mun_safe}_{c}_{cell_size_m}m.gpkg")
    out_layer = "heatmap"

    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except PermissionError:
            return "[ERROR] Output file is open in QGIS. Close it and retry."

    grid.to_file(out_path, layer=out_layer, driver="GPKG")

    if add_to_qgis:
        try:
            add_layer_to_project(out_path, out_layer, f"Heatmap {c} - {municipality} ({cell_size_m}m)")
        except Exception:
            pass

    return f"[SUCCESS] Heatmap exported: {out_path}"


if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    municipality = "Coimbra"
    mun_safe = municipality.lower().replace(" ", "_")

    pois_gpkg = os.path.join(base_dir, "output", mun_safe, "pois_all.gpkg")
    polygon_gpkg = os.path.join(base_dir, "output", "municipality_shapes", f"{mun_safe}_polygon.gpkg")

    print(
        extract_heatmap(
            municipality=municipality,
            category="health",
            pois_gpkg=pois_gpkg,
            pois_layer="pois",
            polygon_gpkg=polygon_gpkg,
            polygon_layer="polygon",
            output_base=os.path.join(base_dir, "output"),
            cell_size_m=250,
            add_to_qgis=False,
        )
    )
