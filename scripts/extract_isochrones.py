import os
import argparse
import math
import geopandas as gpd
import osmnx as ox
import networkx as nx
from shapely.ops import unary_union

try:
    from .utils_qgis import add_layer_to_project
except ImportError:
    from utils_qgis import add_layer_to_project


def _safe(s: str) -> str:
    return s.lower().replace(" ", "_")


def _load_polygon(base_dir, municipality):
    mun_safe = _safe(municipality)
    poly_path = os.path.join(base_dir, "output", "municipality_shapes", f"{mun_safe}_polygon.gpkg")
    if not os.path.exists(poly_path):
        return None, None
    poly = gpd.read_file(poly_path, layer="polygon")
    if poly.empty or poly.crs is None:
        return None, None
    poly = poly.to_crs(epsg=4326)
    return poly.geometry.unary_union, poly_path


def _ensure_costs(G, mode, walk_kmh=5.0):
    if mode == "drive":
        G = ox.add_edge_speeds(G)
        G = ox.add_edge_travel_times(G)
        for u, v, k, data in G.edges(keys=True, data=True):
            if "travel_time" in data:
                data["cost"] = float(data["travel_time"]) / 60.0
        return G

    speed_m_s = (walk_kmh * 1000.0) / 3600.0
    for u, v, k, data in G.edges(keys=True, data=True):
        length_m = data.get("length")
        if length_m is None:
            continue
        tt_min = (float(length_m) / speed_m_s) / 60.0 if speed_m_s > 0 else math.inf
        data["cost"] = tt_min
    return G


def _iso_polygon(G, center_node, cutoff_min, buffer_m=50):
    sub = nx.ego_graph(G, center_node, radius=cutoff_min, distance="cost")
    if sub.number_of_nodes() == 0:
        return None

    nodes = ox.graph_to_gdfs(sub, edges=False)
    if nodes.empty:
        return None

    g = nodes.geometry
    poly = unary_union(g.buffer(buffer_m))
    if poly.is_empty:
        return None
    return poly


def generate_isochrones(
    municipality,
    category,
    mode,
    pois_dir,
    output_base,
    times_min,
    walk_kmh=5.0,
    buffer_m=50,
    max_origins=2,
    add_to_qgis=False,
):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(script_dir, ".."))

    mun_safe = _safe(municipality)
    cat_safe = category.lower()

    poi_file = f"peak_pois_{cat_safe}.gpkg"
    poi_path = os.path.join(pois_dir, mun_safe, poi_file)

    if not os.path.exists(poi_path):
        return f"[ERROR] Peak POI file not found: {poi_path}"

    pois = gpd.read_file(poi_path, layer="hotspot_origins")
    if pois.empty or pois.crs is None:
        return "[ERROR] POI layer empty or missing CRS."

    boundary, _ = _load_polygon(base_dir, municipality)

    if boundary is not None:
        G = ox.graph_from_polygon(boundary, network_type=mode, simplify=True)
    else:
        place = f"{municipality}, Portugal"
        G = ox.graph_from_place(place, network_type=mode, simplify=True)

    G = ox.project_graph(G)
    G = _ensure_costs(G, mode=mode, walk_kmh=walk_kmh)

    pois = pois.to_crs(G.graph["crs"])
    centers = pois.geometry.head(max_origins).tolist()

    rows = []
    for idx, geom in enumerate(centers):
        center_node = ox.distance.nearest_nodes(G, X=float(geom.x), Y=float(geom.y))
        for t in times_min:
            poly = _iso_polygon(G, center_node, cutoff_min=float(t), buffer_m=buffer_m)
            if poly is None:
                continue
            rows.append({
                "origin_id": idx,
                "time_min": int(t),
                "mode": mode,
                "category": cat_safe,
                "geometry": poly
            })

    if not rows:
        return "[INFO] No isochrones generated."

    iso = gpd.GeoDataFrame(rows, crs=G.graph["crs"]).to_crs(epsg=4326)

    out_dir = os.path.join(output_base, "isochrones", mun_safe)
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"isochrones_{mun_safe}_{cat_safe}_{mode}.gpkg")
    layer = "isochrones"

    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except PermissionError:
            return "[ERROR] Output file is open in QGIS. Close it and retry."

    iso.to_file(out_path, layer=layer, driver="GPKG")

    if add_to_qgis:
        try:
            add_layer_to_project(out_path, layer, f"Isochrones {category} ({mode}) - {municipality}")
        except Exception:
            pass

    return f"[SUCCESS] Isochrones exported: {out_path}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--municipality", required=True, type=str)
    parser.add_argument("--category", required=True, type=str)
    parser.add_argument("--mode", choices=["walk", "drive"], default="walk")
    parser.add_argument("--times", nargs="+", type=int, default=[5, 10])
    parser.add_argument("--buffer", type=int, default=50)
    parser.add_argument("--walk_kmh", type=float, default=5.0)
    parser.add_argument("--max_origins", type=int, default=2)
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(script_dir, ".."))

    pois_dir = os.path.join(base_dir, "output", "peak_pois")
    output_base = os.path.join(base_dir, "output")

    msg = generate_isochrones(
        municipality=args.municipality,
        category=args.category,
        mode=args.mode,
        pois_dir=pois_dir,
        output_base=output_base,
        times_min=args.times,
        walk_kmh=args.walk_kmh,
        buffer_m=args.buffer,
        max_origins=args.max_origins,
        add_to_qgis=False,
    )
    print(msg)


if __name__ == "__main__":
    main()
