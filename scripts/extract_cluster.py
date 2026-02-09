import os
import numpy as np
import geopandas as gpd
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from .utils_qgis import add_layer_to_project
from pathlib import Path


def extract_cluster_and_isochrones(municipality, category, mode, n_clusters=3):
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    POIS_BASE = os.path.join(plugin_dir, "output", "pois_by_municipality")
    OUTPUT_BASE = os.path.join(plugin_dir, "output", "clusters")
    TRAVEL_TIMES = [5, 10]
    SPEEDS = {"walk": 5, "drive": 30}

    mun_safe = municipality.lower().replace(" ", "_")
    cat_safe = category.lower()
    poi_path = os.path.join(POIS_BASE, mun_safe, f"pois_{cat_safe}.gpkg")

    if not os.path.exists(poi_path):
        return f"[ERROR] POI file not found: {poi_path}"

    pois = gpd.read_file(poi_path, layer="pois").to_crs(epsg=4326)
    if pois.empty:
        return "[ERROR] No POIs found."

    # === Clustering ===
    coords = np.array([[geom.x, geom.y] for geom in pois.geometry])
    kmeans = KMeans(n_clusters=n_clusters, random_state=42).fit(coords)
    pois["cluster"] = kmeans.labels_

    clustered_gdf = pois.to_crs(epsg=4326)
    cluster_dir = os.path.join(OUTPUT_BASE, mun_safe)
    os.makedirs(cluster_dir, exist_ok=True)
    cluster_file = os.path.join(cluster_dir, f"pois_clusters_{cat_safe}.gpkg")
    clustered_gdf.to_file(cluster_file, layer="clusters", driver="GPKG")

    # === Find sparsest cluster ===
    cluster_counts = pois["cluster"].value_counts().sort_index()
    sparsest = cluster_counts.idxmin()
    sparse_cluster = pois[pois["cluster"] == sparsest].copy()
    origins = sparse_cluster.geometry[:2]

    if origins.empty:
        return "[ERROR] No origins found in sparsest cluster."

    # === Network download ===
    city_name = municipality.replace("_", " ").title() + ", Portugal"
    try:
        graph = ox.graph_from_place(city_name, network_type=mode, simplify=True)
        graph = ox.project_graph(graph)
    except Exception as e:
        return f"[ERROR] Failed to download network: {e}"

    # === Isochrone function ===
    def make_iso_polys(G, center_node, trip_times, speed_kmh):
        meters_per_minute = (speed_kmh * 1000) / 60
        cutoffs = [t * meters_per_minute for t in trip_times]
        polys = []
        for cutoff in cutoffs:
            subgraph = nx.ego_graph(G, center_node, radius=cutoff, distance='length')
            nodes = ox.graph_to_gdfs(subgraph, edges=False)
            if nodes.empty:
                continue
            hull = nodes.geometry.unary_union.convex_hull
            polys.append(hull)
        return polys

    # === Compute isochrones ===
    all_isochrones = []
    speed = SPEEDS[mode]
    origins = origins.to_crs(graph.graph['crs'])

    for idx, geom in enumerate(origins):
        node = ox.distance.nearest_nodes(graph, X=geom.x, Y=geom.y)
        polys = make_iso_polys(graph, node, TRAVEL_TIMES, speed)
        for i, poly in enumerate(polys):
            all_isochrones.append({
                "origin_id": idx,
                "time_min": TRAVEL_TIMES[i],
                "geometry": poly,
                "mode": mode,
                "category": category,
                "cluster": int(sparsest)
            })

    if not all_isochrones:
        return "[INFO] No isochrones could be generated from the clustered POIs."

    # === Save isochrones ===
    gdf = gpd.GeoDataFrame(all_isochrones, crs=graph.graph['crs']).to_crs(epsg=4326)
    output_path = os.path.join(cluster_dir, f"isochrones_cluster_{cat_safe}_{mode}.gpkg")
    gdf.to_file(output_path, layer="isochrones_cluster", driver="GPKG")

    # === Add to QGIS project ===
    add_layer_to_project(cluster_file, "clusters", f"Clusters {category}")
    add_layer_to_project(output_path, "isochrones_cluster", f"Isochrones {category} ({mode})")

    # === Plot cluster bar chart ===
    plt.figure(figsize=(6, 4))
    cluster_counts.plot(kind="bar", color="skyblue")
    plt.title("POIs per Cluster")
    plt.xlabel("Cluster")
    plt.ylabel("Number of POIs")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.grid(axis="y", linestyle="--", alpha=0.5)

    home = Path.home()
    downloads_dirs = [home / "Downloads", home / "Transferências"]

    downloads_dir = next((p for p in downloads_dirs if p.exists()), None)
    cluster_dir = downloads_dir / "qgis_clusters" / mun_safe
    cluster_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(os.path.join(cluster_dir, f"cluster_distribution_{cat_safe}.png"))
    plt.close()
    return "[SUCCESS] POIs clustered and isochrones generated successfully."