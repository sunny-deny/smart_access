import os
import osmnx as ox
import geopandas as gpd
from .utils_qgis import add_layer_to_project


def extract_network(municipality, mode):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(script_dir, ".."))

    mun_safe = municipality.lower().replace(" ", "_")
    mode_safe = mode.lower()

    output_dir = os.path.join(base_dir, "output", "networks")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{mun_safe}_{mode_safe}_network.gpkg")

    if mode_safe == "transit":
        routes_path = os.path.join(base_dir, "data", "smtuc", "SMTUC_linhas.gpkg")

        if not os.path.exists(routes_path):
            return "[ERROR] Transit data not found."

        try:
            routes = gpd.read_file(routes_path).to_crs(epsg=4326)

            routes.to_file(out_path, layer="edges", driver="GPKG")

            add_layer_to_project(out_path, "edges", f"Transit Network {municipality}")

            return f"[SUCCESS] Transit network for '{municipality}' loaded and added to the project."

        except Exception as e:
            return f"[ERROR] Failed to process transit data: {e}"

    else:
        city_name = municipality.replace("_", " ").title() + ", Portugal"
        try:
            print(f"[INFO] Downloading '{mode}' network for {city_name}...")
            graph = ox.graph_from_place(city_name, network_type=mode_safe, simplify=True)
            nodes, edges = ox.graph_to_gdfs(graph)
            edges = edges.to_crs(epsg=4326)

            edges.to_file(out_path, layer="edges", driver="GPKG")
            add_layer_to_project(out_path, "edges", f"Network {municipality} ({mode})")

            return f"[SUCCESS] Road network for '{municipality}' ({mode}) downloaded and added to the project."

        except Exception as e:
            return f"[ERROR] Failed to download or save road network: {e}"
