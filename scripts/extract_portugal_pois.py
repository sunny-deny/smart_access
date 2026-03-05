import geopandas as gpd
import os
import pandas as pd

# === Base path for relative references ===
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(script_dir, ".."))  # root of the plugin
data_dir = os.path.join(base_dir, "data", "geofabrik")
output_dir = os.path.join(base_dir, "output")

# === Load Portugal-wide POIs ===
pois_path = os.path.join(data_dir, "gis_osm_pois_free_1.shp")
if not os.path.exists(pois_path):
    raise FileNotFoundError(f"POI file not found: {pois_path}")

pois = gpd.read_file(pois_path)

# Normalize column names
pois.columns = map(str.lower, pois.columns)

# Ensure 'fclass' exists
if 'fclass' not in pois.columns:
    raise ValueError("Column 'fclass' not found in input data.")

# === Define POI categories by OSM 'fclass' tags ===
poi_categories = {
    "education": ["school", "university", "college", "kindergarten"],
    "health": ["hospital", "clinic", "doctors", "dentist", "pharmacy"],
    "transport": ["bus_station", "train_station", "airport", "ferry_terminal", "subway_entrance"],
    "government": ["townhall", "public_building", "police", "fire_station", "courthouse"],
    "commerce": ["supermarket", "mall", "marketplace", "convenience", "bakery"],
    "culture": ["library", "cinema", "museum", "theatre", "arts_centre", "gallery"],
    "religion": ["place_of_worship", "church", "mosque", "synagogue"],
    "sports": ["stadium", "sports_centre", "gym", "pitch", "swimming_pool"]
}

# === Combine all matching POIs into one GeoDataFrame ===
filtered_frames = []

for category, tags in poi_categories.items():
    matches = pois[pois["fclass"].isin(tags)].copy()
    matches["category"] = category
    if not matches.empty:
        filtered_frames.append(matches)
        print(f"{category}: {len(matches)} features")

# === Merge all categories into one layer ===
if filtered_frames:
    combined = pd.concat(filtered_frames)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs=pois.crs)
    combined = combined.to_crs(epsg=4326)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save to GPKG
    output_path = os.path.join(output_dir, "portugal_pois.gpkg")
    combined.to_file(output_path, layer="pois_portugal", driver="GPKG")
    print(f"[SUCCESS] Combined POIs saved to {output_path}")
else:
    print("[ERROR] No POIs matched any category.")
