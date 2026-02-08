import os
import pandas as pd
import geopandas as gpd
import rasterio
import numpy as np
from shapely.geometry import Point
from rasterio.transform import xy

def extract_peak_density(municipality, category):
    # === Define base directory relative to the plugin ===
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(script_dir, ".."))

    mun_safe = municipality.lower().replace(" ", "_")
    cat_safe = category.lower()

    # === Construct file paths ===
    pois_path = os.path.join(base_dir, "output", "pois_by_municipality", mun_safe, f"pois_{cat_safe}.gpkg")
    heatmap_path = os.path.join(base_dir, "output", "heatmaps", mun_safe, f"{cat_safe}_heatmap.tif")
    output_dir = os.path.join(base_dir, "output", "peak_pois", mun_safe)
    output_path = os.path.join(output_dir, f"peak_pois_{cat_safe}.gpkg")

    os.makedirs(output_dir, exist_ok=True)

    # === Validate input files ===
    if not os.path.exists(pois_path):
        return f"[ERROR] POI file not found: {pois_path}"
    if not os.path.exists(heatmap_path):
        return f"[ERROR] Heatmap file not found: {heatmap_path}"

    # === Load POIs ===
    pois = gpd.read_file(pois_path, layer="pois")
    if pois.empty:
        return "[ERROR] POI layer is empty."

    # === Extract top density locations from heatmap ===
    with rasterio.open(heatmap_path) as src:
        data = src.read(1)
        transform = src.transform

        flat = data.flatten()
        nonzero = flat.nonzero()[0]
        if len(nonzero) == 0:
            return "[ERROR] Heatmap contains only zeros."

        top_n = min(10, len(nonzero))
        top_indices = np.argpartition(flat, -top_n)[-top_n:]
        top_indices = top_indices[np.argsort(flat[top_indices])[::-1]]

        selected_coords = []
        for idx in top_indices:
            row, col = np.unravel_index(idx, data.shape)
            x, y = xy(transform, row, col)
            selected_coords.append(Point(x, y))

    # === Find nearest POIs to density points, avoiding duplicates ===
    def nearest_poi(target_point, pois_gdf, exclude_ids=None):
        if exclude_ids:
            pois_gdf = pois_gdf[~pois_gdf.index.isin(exclude_ids)]
        if pois_gdf.empty:
            return None
        distances = pois_gdf.geometry.distance(target_point)
        nearest_idx = distances.idxmin()
        return pois_gdf.loc[[nearest_idx]]

    used_ids = set()
    selected_pois = []
    for point in selected_coords:
        poi = nearest_poi(point, pois, exclude_ids=used_ids)
        if poi is not None:
            used_ids.update(poi.index)
            selected_pois.append(poi)
        if len(selected_pois) >= 10:
            break

    if not selected_pois:
        return "[ERROR] No POIs could be selected."

    # === Save selected POIs to output ===
    result = gpd.GeoDataFrame(pd.concat(selected_pois), geometry="geometry", crs=pois.crs)
    result.to_file(output_path, layer="hotspot_origins", driver="GPKG")
    return output_path
