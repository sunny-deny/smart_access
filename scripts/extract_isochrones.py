import os
import geopandas as gpd
import pandas as pd
import osmnx as ox
import networkx as nx
from shapely.geometry import Point, MultiPoint
from pathlib import Path
from .utils_qgis import add_layer_to_project

def extract_isochrones_for_walk_drive(municipality, input_path, mode, times, save_summary):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(script_dir, ".."))

        if not os.path.exists(input_path):
            return f"[ERROR] Input file not found: {input_path}"

        pois = gpd.read_file(input_path, layer="selected_pois")
        if pois.empty:
            return "[WARNING] Selected POI layer is empty."

        city_name = municipality.replace("_", " ").title() + ", Portugal"
        print(f"[INFO] Downloading {mode} network for {city_name}...")
        graph = ox.graph_from_place(city_name, network_type=mode, simplify=True)
        graph = ox.project_graph(graph)

        pois = pois.to_crs(graph.graph['crs'])
        centers = pois.geometry

        def make_iso_polys(G, center_node):
            meters_per_minute = ({"walk": 5, "drive": 30}[mode] * 1000) / 60
            time_cutoffs = [t * meters_per_minute for t in times]
            polys = []
            for cutoff in time_cutoffs:
                subgraph = nx.ego_graph(G, center_node, radius=cutoff, distance='length')
                nodes = ox.graph_to_gdfs(subgraph, edges=False)
                if nodes.empty:
                    continue
                hull = nodes.geometry.unary_union.convex_hull
                polys.append(hull)
            return polys

        results = []
        for idx, geom in enumerate(centers):
            poi_name = pois.iloc[idx].get("name", f"POI_{idx}")
            node = ox.distance.nearest_nodes(graph, X=geom.x, Y=geom.y)
            polys = make_iso_polys(graph, node)
            for i, poly in enumerate(polys):
                results.append({
                    "origin_id": idx,
                    "poi_name": poi_name,
                    "time_min": times[i],
                    "mode": mode,
                    "geometry": poly
                })

        if not results:
            return "[ERROR] No isochrones were generated for the selected POIs."

        gdf = gpd.GeoDataFrame(results, crs=graph.graph['crs']).to_crs(epsg=4326)

        out_dir = os.path.join(base_dir, "output", "isochrones", municipality.lower().replace(" ", "_"))
        os.makedirs(out_dir, exist_ok=True)

        output_path = os.path.join(out_dir, f"isochrones_{mode}.gpkg")
        for t in times:
            subset = gdf[gdf["time_min"] == t]
            layer_name = f"isochrones_{t}min_{mode}"
            subset.to_file(output_path, layer=layer_name, driver="GPKG")
            print(f"[SUCCESS] {layer_name} saved to: {output_path}")
            add_layer_to_project(output_path, layer_name, f"Isochrone {municipality.title()} - {layer_name}")


        if save_summary:
            summary_df = gdf.copy()
            summary_df["area"] = summary_df.geometry.area
            summary_df["municipality"] = municipality
            home = Path.home()
            downloads_dirs = [home / "Downloads", home / "Transferências"]

            downloads_dir = next((p for p in downloads_dirs if p.exists()), None)

            summary_path = downloads_dir / "isochrone_area_summary.csv"
            #summary_path = os.path.join(base_dir, "output", "isochrones", "isochrone_area_summary.csv")
            if os.path.exists(summary_path):
                old = pd.read_csv(summary_path)
                summary_df = pd.concat([old, summary_df], ignore_index=True)
            summary_df[["poi_name", "time_min", "mode", "area", "municipality"]].to_csv(summary_path, index=False)
      
        return f"[SUCCESS] Accessibility isochrones generated and saved successfully."

    except Exception as e:
        return f"[ERROR] Failed to generate isochrones: {e}"



# === TRANSIT ISOCHRONES ===
SPEED_KMH = 20
SNAP_MAX_DIST = 150

def build_spatial_index(gdf):
    return gdf.sindex

def find_nearest_stop(stops_gdf, sindex, point, max_dist=SNAP_MAX_DIST):
    bounds = point.buffer(max_dist).bounds
    matches_idx = list(sindex.intersection(bounds))
    if not matches_idx:
        return None
    possible_matches = stops_gdf.iloc[matches_idx]
    distances = possible_matches.geometry.distance(point)
    if distances.empty or distances.min() > max_dist:
        return None
    nearest_global_idx = distances.idxmin()
    return stops_gdf.loc[nearest_global_idx, "idparagem"]

def extract_isochrones_for_transit(municipality, input_path, times, save_summary):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(script_dir, ".."))
        stops_path = os.path.join(base_dir, "data", "smtuc", "SMTUV_paragens.gpkg")
        routes_path = os.path.join(base_dir, "data", "smtuc", "SMTUC_linhas.gpkg")

        if not os.path.exists(input_path):
            return "[ERROR] POI file not found."
        if not os.path.exists(stops_path) or not os.path.exists(routes_path):
            return "[ERROR] Transit data not found."

        pois = gpd.read_file(input_path, layer="selected_pois").to_crs(epsg=3763)
        stops = gpd.read_file(stops_path).to_crs(epsg=3763)
        routes = gpd.read_file(routes_path).to_crs(epsg=3763)
        stops_sindex = build_spatial_index(stops)

        G = nx.Graph()
        for _, row in stops.iterrows():
            G.add_node(row["idparagem"], geometry=row.geometry)

        for _, row in routes.iterrows():
            geom = row.geometry
            segments = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom]
            for segment in segments:
                start_point = Point(segment.coords[0])
                end_point = Point(segment.coords[-1])
                s1 = find_nearest_stop(stops, stops_sindex, start_point)
                s2 = find_nearest_stop(stops, stops_sindex, end_point)
                if s1 and s2 and s1 != s2 and not G.has_edge(s1, s2):
                    dist = segment.length
                    G.add_edge(s1, s2, weight=dist, geometry=segment)

        meters_per_minute = SPEED_KMH * 1000 / 60
        out_dir = os.path.join(base_dir, "output", "isochrones", municipality.lower().replace(" ", "_"))
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "isochrones_transit.gpkg")

        results, network_by_time, stops_by_time = [], {t: [] for t in times}, {t: [] for t in times}

        for idx, poi in enumerate(pois.geometry):
            poi_name = pois.iloc[idx].get("name", f"POI_{idx}")
            nearest_stop_id = find_nearest_stop(stops, stops_sindex, poi)
            if not nearest_stop_id:
                print(f"[INFO] No nearby stop for POI {idx}")
                continue

            lengths = nx.single_source_dijkstra_path_length(G, nearest_stop_id, weight="weight")
            for t in times:
                max_dist = t * meters_per_minute
                reachable_nodes = {n for n, d in lengths.items() if d <= max_dist}
                reachable_points = [G.nodes[n]["geometry"] for n in reachable_nodes]
                if len(reachable_points) < 3:
                    continue
                poly = MultiPoint(reachable_points).convex_hull
                results.append({
                    "origin_id": idx,
                    "poi_name": poi_name,
                    "time_min": t,
                    "mode": "transit",
                    "geometry": poly
                })

                subgraph = G.subgraph(reachable_nodes)
                for u, v, data in subgraph.edges(data=True):
                    network_by_time[t].append({
                        "origin_id": idx, "from_stop": u, "to_stop": v,
                        "time_min": t, "geometry": data["geometry"]
                    })
                for stop_id in subgraph.nodes:
                    stops_by_time[t].append({
                        "origin_id": idx, "poi_name": poi_name,
                        "stop_id": stop_id, "time_min": t,
                        "geometry": G.nodes[stop_id]["geometry"]
                    })

        if not results:
            return "[ERROR] No isochrones were generated for the selected POIs."

        gdf = gpd.GeoDataFrame(results, crs="EPSG:3763").to_crs(epsg=4326)
        for t in times:
            subset = gdf[gdf["time_min"] == t]
            layer = f"isochrones_{t}min_transit"
            subset.to_file(out_path, layer=layer, driver="GPKG")
            add_layer_to_project(out_path, layer, f"Isochrone {municipality.title()} - {layer}")

        for t in times:
            edges = network_by_time[t]
            if edges:
                edges_gdf = gpd.GeoDataFrame(edges, crs="EPSG:3763").to_crs(epsg=4326)
                layer = f"transit_network_{t}min"
                edges_gdf.to_file(out_path, layer=layer, driver="GPKG")
                add_layer_to_project(out_path, layer, f"{municipality.title()} - Transit Network {t} min")

        for t in times:
            reachable_stops = stops_by_time[t]
            if reachable_stops:
                stops_gdf = gpd.GeoDataFrame(reachable_stops, crs="EPSG:3763").to_crs(epsg=4326)
                layer = f"accessible_stops_{t}min"
                stops_gdf.to_file(out_path, layer=layer, driver="GPKG")
                add_layer_to_project(out_path, layer, f"{municipality.title()} - Accessible Stops {t} min")

        if save_summary:
            summary_df = gdf.copy()
            summary_df["area"] = summary_df.geometry.area
            summary_df["municipality"] = municipality
            home = Path.home()
            downloads_dirs = [home / "Downloads", home / "Transferências"]

            downloads_dir = next((p for p in downloads_dirs if p.exists()), None)

            if downloads_dir is None:
                raise FileNotFoundError("Nenhuma pasta de downloads encontrada ('Downloads' ou 'Transferências').")

            summary_path = downloads_dir / "isochrone_area_summary.csv"
            #summary_path = os.path.join(base_dir, "output", "isochrones", "isochrone_area_summary.csv")
            if os.path.exists(summary_path):
                old = pd.read_csv(summary_path)
                summary_df = pd.concat([old, summary_df], ignore_index=True)
            summary_df[["poi_name", "time_min", "mode", "area", "municipality"]].to_csv(summary_path, index=False)
        return "[SUCCESS] Transit isochrones, network, and stop layers generated successfully."

    except Exception as e:
        return f"[ERROR] Transit extraction failed: {e}"