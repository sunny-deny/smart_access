import os
import argparse
import geopandas as gpd
from shapely.ops import unary_union

def _safe(s: str) -> str:
    return s.lower().replace(" ", "_")

def _m_per_min(speed_kmh: float) -> float:
    return speed_kmh * 1000.0 / 60.0

def _load_polygon(base_dir, municipality):
    mun_safe = _safe(municipality)
    poly_path = os.path.join(base_dir, "output", "municipality_shapes", f"{mun_safe}_polygon.gpkg")
    if not os.path.exists(poly_path):
        return None
    poly = gpd.read_file(poly_path, layer="polygon")
    if poly.empty or poly.crs is None:
        return None
    return poly.to_crs(epsg=3763).geometry.unary_union

def generate_hybrid_isochrones(
    municipality,
    category,
    times_min,
    pois_dir,
    stops_path,
    output_base,
    walk_speed_kmh=5.0,
    transit_speed_kmh=20.0,
    walk_to_stop_min=2,
    last_mile_walk_min=2,
    max_origins=2,
):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(script_dir, ".."))

    mun_safe = _safe(municipality)
    cat_safe = category.lower()

    poi_file = f"peak_pois_{cat_safe}.gpkg"
    poi_path = os.path.join(pois_dir, mun_safe, poi_file)

    if not os.path.exists(poi_path):
        return f"[ERROR] Peak POI file not found: {poi_path}"

    if not os.path.exists(stops_path):
        return f"[ERROR] Stops file not found: {stops_path}"

    pois = gpd.read_file(poi_path, layer="hotspot_origins")
    if pois.empty or pois.crs is None:
        return "[ERROR] POIs empty or missing CRS."

    stops = gpd.read_file(stops_path)
    if stops.empty or stops.crs is None:
        return "[ERROR] Stops empty or missing CRS."

    pois = pois.to_crs(epsg=3763)
    stops = stops.to_crs(epsg=3763)

    boundary = _load_polygon(base_dir, municipality)
    if boundary is not None:
        stops = stops[stops.geometry.within(boundary)].copy()
        if stops.empty:
            return "[INFO] No stops inside municipality boundary."

    walk_mpm = _m_per_min(walk_speed_kmh)
    transit_mpm = _m_per_min(transit_speed_kmh)

    origins = pois.geometry.head(max_origins).tolist()
    rows = []

    for idx, origin in enumerate(origins):
        for t_total in times_min:
            t_total = float(t_total)

            if walk_to_stop_min + last_mile_walk_min >= t_total:
                continue

            walk1_r = walk_mpm * float(walk_to_stop_min)
            walk2_r = walk_mpm * float(last_mile_walk_min)
            transit_t = t_total - float(walk_to_stop_min) - float(last_mile_walk_min)
            transit_r = transit_mpm * transit_t

            walk_to_stop_area = origin.buffer(walk1_r)
            candidate_stops = stops[stops.geometry.within(walk_to_stop_area)]
            if candidate_stops.empty:
                continue

            transit_reach = unary_union(candidate_stops.geometry).buffer(transit_r)
            hybrid_area = transit_reach.buffer(walk2_r)

            rows.append({
                "origin_id": idx,
                "time_min": int(t_total),
                "mode": "hybrid_transit",
                "category": cat_safe,
                "walk_to_stop_min": int(walk_to_stop_min),
                "transit_min": float(transit_t),
                "last_mile_walk_min": int(last_mile_walk_min),
                "geometry": hybrid_area
            })

    if not rows:
        return "[INFO] No hybrid isochrones generated."

    iso = gpd.GeoDataFrame(rows, crs="EPSG:3763").to_crs(epsg=4326)

    out_dir = os.path.join(output_base, "isochrones", mun_safe)
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"isochrones_{mun_safe}_{cat_safe}_hybrid.gpkg")

    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except PermissionError:
            return "[ERROR] Output file is open in QGIS. Close it and retry."

    iso.to_file(out_path, layer="isochrones", driver="GPKG")
    return f"[SUCCESS] Hybrid isochrones exported: {out_path}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--municipality", required=True, type=str)
    parser.add_argument("--category", required=True, type=str)
    parser.add_argument("--times", nargs="+", type=int, default=[5, 10])
    parser.add_argument("--walk_to_stop", type=int, default=2)
    parser.add_argument("--last_mile", type=int, default=2)
    parser.add_argument("--walk_kmh", type=float, default=5.0)
    parser.add_argument("--transit_kmh", type=float, default=20.0)
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(script_dir, ".."))

    pois_dir = os.path.join(base_dir, "output", "peak_pois")
    output_base = os.path.join(base_dir, "output")
    stops_path = os.path.join(base_dir, "data", "smtuc", "SMTUV_paragens.gpkg")

    print(generate_hybrid_isochrones(
        municipality=args.municipality,
        category=args.category,
        times_min=args.times,
        pois_dir=pois_dir,
        stops_path=stops_path,
        output_base=output_base,
        walk_speed_kmh=args.walk_kmh,
        transit_speed_kmh=args.transit_kmh,
        walk_to_stop_min=args.walk_to_stop,
        last_mile_walk_min=args.last_mile,
    ))

if __name__ == "__main__":
    main()
