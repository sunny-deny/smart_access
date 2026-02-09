# Smart Access – QGIS Plugin for Urban Accessibility Analysis

## Overview

Smart Access is a QGIS plugin developed in Python for analyzing urban accessibility using Points of Interest (POIs), transport networks, and spatial analysis techniques.

The plugin supports accessibility analysis for walking, driving, and public transport, including heatmaps, isochrones, and clustering of underserved areas.

This project was developed for the course *Ambient Intelligence* in the MSc in Computer Engineering.

---

## Features

- **POI Extraction** – Extract Points of Interest by municipality and category
- **Boundary Generation** – Generate municipality boundaries automatically
- **Network Download** – Download road and public transport networks
- **Kernel Density Heatmaps** – Visualize POI density across areas
- **Peak Detection** – Identify locations with highest accessibility
- **Isochrone Generation** – Create accessibility zones for:
  - Walking
  - Driving
  - Public transport (Coimbra – SMTUC)
- **Hybrid Accessibility Analysis** – Combine multiple transport modes
- **K-Means Clustering** – Cluster POIs and identify patterns
- **Low-Coverage Detection** – Identify underserved areas
- **Accessibility Summaries** – Export analysis results to CSV
- **QGIS Integration** – Seamless integration with QGIS graphical interface

---

## Project Structure

```
smart_access/
│
├── data/                      # External datasets (not tracked in Git)
├── output/                    # Generated results
├── scripts/                   # Processing modules
├── forms/                     # Qt Designer interface
├── tests/                     # Unit tests
├── smart_access_dialog.py     # Main plugin dialog
├── smart_acess_plugin.py      # QGIS plugin loader
├── metadata.txt               # QGIS plugin metadata
├── requirements.txt
└── README.md
```

---

## Requirements

### Software

- **QGIS** 3.28 or higher
- **Python** 3.9+ (included with QGIS)

### Python Libraries

Install dependencies if running outside QGIS:

```bash
pip install -r requirements.txt
```

Main libraries used:

- `geopandas`
- `osmnx`
- `networkx`
- `rasterio`
- `scikit-learn`
- `numpy`
- `matplotlib`
- `pandas`

---

## Required Datasets

Due to size and licensing restrictions, datasets are not included in this repository.

Users must manually download the required data from the official sources below and place them in the appropriate folders.

---

### 1. CAOP – Administrative Boundaries (DGT)

**Source:**  
https://www.dgterritorio.gov.pt/cartografia/cartografia-tematica/caop

**Steps:**

1. Access the CAOP download page
2. Download the latest version of CAOP for Mainland Portugal (GeoPackage format preferred)
3. Extract the file
4. Copy the main `.gpkg` file into:
   ```
   smart_access/data/caop/
   ```

**Expected file example:**
```
continente_caop2024.gpkg
```

---

### 2. OpenStreetMap POIs (Geofabrik)

**Source:**  
https://download.geofabrik.de/europe/portugal.html

**Steps:**

1. Open the Portugal Geofabrik page
2. Download: `gis_osm_pois_free_1.zip`
3. Extract the contents
4. Copy all extracted files into:
   ```
   smart_access/data/geofabrik/
   ```

**Expected files:**
```
gis_osm_pois_free_1.shp
gis_osm_pois_free_1.dbf
gis_osm_pois_free_1.shx
gis_osm_pois_free_1.prj
```

---

### 3. SMTUC – Coimbra Public Transport Data

**Source:**  
Official SMTUC website or by request

**Steps:**

1. Obtain the transport network and stops data from SMTUC
2. Ensure the data is in GeoPackage format (`.gpkg`) or compatible GIS format
3. Place the files into:
   ```
   smart_access/data/smtuc/
   ```

**Expected files:**
```
SMTUC_linhas.gpkg
SMTUC_paragens.gpkg
```

---

### 4. Final Directory Structure

After downloading and extracting all datasets, the folder structure should be:

```
data/
├── caop/
│   └── continente_caop2024.gpkg
├── geofabrik/
│   └── gis_osm_pois_free_1.*
└── smtuc/
    ├── SMTUC_linhas.gpkg
    └── SMTUC_paragens.gpkg
```

---

## Installation as QGIS Plugin

### 1. Locate QGIS Plugins Directory

**Windows**
```
C:\Users\<USER>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\
```

**Linux**
```
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

**macOS**
```
~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
```

### 3. Clone the Repository

Clone the project repository and rename the folder to `Smart Access`:

```bash
git clone https://github.com/sunny-deny/smart_access.git
```

### 4. Enable Plugin

1. Open QGIS
2. Go to **Plugins → Manage and Install Plugins**
3. Enable **Smart Access**
4. The plugin will appear in the toolbar

---

## How to Use

### 1. Open Plugin

Click the **Smart Access** icon in QGIS.

### 2. Select Parameters

Choose:
- Municipality
- POI category
- Walk mode
- Time thresholds
- Number of clusters (optional)

### 3. Generate Municipality Boundary

Click: **Show Polygon**

### 4. Extract POIs and Heatmap

Click: **Show POIs**

This will:
- Filter POIs
- Generate heatmap
- Extract peak density locations
- Load peak POIs for analysis

### 5. Download Networks

Click: **Show Networks**

### 6. Generate Isochrones

Select two POIs and click: **Run Isochrones**

Supported modes:
- Walk
- Drive
- Transit (Coimbra only)

### 7. Run Clustering (Optional)

Click: **Run Clustering**

This identifies underserved clusters and generates isochrones.

### 8. Export Summary (Optional)

Enable: **Save Summary**

A CSV file with accessibility areas will be exported to the Downloads folder.

---

## Output

All generated data is stored in:

```
output/
```

Examples:
- `output/isochrones/`
- `output/heatmaps/`
- `output/clusters/`

Files are saved in GeoPackage format (`.gpkg`).

---

## Limitations

- Public transport isochrones are approximations (no GTFS routing)
- Network download requires internet access
- Large municipalities may require longer processing time
- Driving mode uses simplified speed models

These limitations are discussed in the project report.

---

## Author

Developed by:

**[Denise Taúla]**  
MSc in Computer Engineering
2025

---

## License

This project is developed for academic purposes.  
All datasets belong to their respective owners.
