from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.QtCore import QTimer,QThread, pyqtSignal

import os
import sys
import geopandas as gpd
from .scripts.extract_pois import extract_filtered_pois
from .scripts.extract_polygon import export_municipality_polygon
from .scripts.extract_networks import extract_network
from .scripts.extract_cluster import extract_cluster_and_isochrones
from .scripts.extract_heatmap import extract_heatmap_from_poi
from .scripts.extract_pois_density import extract_peak_density
from .scripts.extract_isochrones import extract_isochrones_for_walk_drive, extract_isochrones_for_transit
from .scripts.utils_qgis import add_layer_to_project


class WorkerThread(QThread):
    finished = pyqtSignal(object)  
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        result = self.func(*self.args, **self.kwargs)
        self.finished.emit(result)


class SmartAccessDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), "forms", "smart_acess_dialog.ui"), self)
        self.simulated_timer = QTimer()
        self.simulated_timer.setInterval(100)  # 100ms = 0.1s
        self.simulated_timer.timeout.connect(self.advance_progress)
        self.progress_value = 0

        self.hide_progress()
        self.populate_fields()

        self.setup_tooltips()

        self.btnShowPolygon.clicked.connect(self.show_polygon)
        self.btnShowPois.clicked.connect(self.show_pois)
        self.btnShowNetworks.clicked.connect(self.show_networks)
        self.btnRunIsochrone.clicked.connect(self.run_isochrones)
        self.btnRunClustering.clicked.connect(self.run_clustering)

        self.loaded_peak_pois = None

    def start_simulated_progress(self):
        self.simulated_timer.stop()
        self.progress_value = 0
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        self.simulated_timer.start()

    def advance_progress(self):
        if self.progress_value < 100:
            self.progress_value += 5
            self.progressBar.setValue(self.progress_value)
        else:
            self.simulated_timer.stop()

    def show_progress(self, message="Processing..."):
        self.progressBar.setValue(0)
        self.start_simulated_progress()
        QApplication.processEvents()

    def hide_progress(self):
        self.simulated_timer.stop()
        self.progressBar.setVisible(False)
        QApplication.processEvents()



    def setup_tooltips(self):
        self.comboMunicipality.setToolTip("Select the municipality to analyze.")
        self.comboCategory.setToolTip("Choose the category of POIs (e.g. education, health).")
        self.comboMode.setToolTip("Select travel mode: walk, drive, or transit (only available for Coimbra).")

        self.btnShowPolygon.setToolTip("Generate and display the boundary of the selected municipality.")
        self.btnShowPois.setToolTip("Extract and filter POIs for the selected municipality and category.")
        self.btnShowNetworks.setToolTip("Download the road network for the selected municipality and travel mode.")
        self.btnRunIsochrone.setToolTip("Generate accessibility isochrones from selected POIs.")
        self.btnRunClustering.setToolTip("Group POIs into clusters and generate cluster-based isochrones.")

        self.comboSelectPoi1.setToolTip("This field will be populated after running 'Show POIs'")
        self.comboSelectPoi2.setToolTip("This field will be populated after running 'Show POIs'")

        self.spinBoxTime1.setToolTip("First time threshold (in minutes) for isochrone calculation.")
        self.spinBoxTime2.setToolTip("Second time threshold (in minutes) for isochrone calculation.")

        self.spinBoxNClusters.setToolTip("Number of clusters to divide POIs into during clustering analysis.")

    def populate_fields(self):
        self.comboMode.addItems(["walk", "drive", "transit"])
        categories = ["education", "health", "commerce", "culture", "sports"]
        self.comboCategory.addItems(categories)

        plugin_dir = os.path.dirname(__file__)
        caop_path = os.path.join(plugin_dir, "data", "caop", "continente_caop2024.gpkg")

        try:
            gdf = gpd.read_file(caop_path, layer="cont_municipios")
            gdf.columns = gdf.columns.str.lower()
            municipios = sorted(gdf["municipio"].dropna().unique())
            self.comboMunicipality.addItems(municipios)
        except Exception as e:
            print(f"[ERROR] Failed to load municipalities: {e}")

    def validate_inputs(self):
        return all([
            self.comboMunicipality.currentText().strip(),
            self.comboCategory.currentText().strip(),
            self.comboMode.currentText().strip()
        ])

    def show_message(self, title, message, success=True):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.setStandardButtons(QMessageBox.Ok)
        background = "#729859" if success else "#BA5757"
        text_color = "#9CC97F" if success else "#DC5E5E"

        box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {background};
                color: {text_color};
                font-weight: normal;
                font-size: 9pt;
            }}
            QPushButton {{
                background-color: #537E72;
                color: white;
                border-radius: 6px;
                padding: 5px 12px;
            }}
            QPushButton:hover {{
                background-color: #70b5a1;
            }}
        """)
        box.exec_()

    def show_polygon(self):
        municipality = self.comboMunicipality.currentText()
        plugin_dir = os.path.dirname(__file__)
        caop_path = os.path.join(plugin_dir, "data", "caop", "continente_caop2024.gpkg")
        output_dir = os.path.join(plugin_dir, "output", "municipality_shapes")

        self.show_progress()

        def task():
            return export_municipality_polygon(municipality, caop_path, output_dir)

        self.worker = WorkerThread(task)
        self.worker.finished.connect(self.on_polygon_extraction_finished)
        self.worker.start()

    def on_polygon_extraction_finished(self, result):
        self.hide_progress()
        self.show_message("Polygon Result", result, "[SUCCESS]" in result)
        self.worker = None


    def show_pois(self):
        municipality = self.comboMunicipality.currentText()
        category = self.comboCategory.currentText()
        plugin_dir = os.path.dirname(__file__)
        pois_path = os.path.join(plugin_dir, "output", "portugal_pois.gpkg")
        caop_path = os.path.join(plugin_dir, "data", "caop", "continente_caop2024.gpkg")
        output_base = os.path.join(plugin_dir, "output", "pois_by_municipality")

        self.show_progress()

        def task():
            result = extract_filtered_pois(municipality, category, pois_path, caop_path, output_base)
            if not result:
                return "[ERROR] No POIs extracted."

            extract_heatmap_from_poi(municipality, category)
            peak_path = extract_peak_density(municipality, category)

            if not peak_path or not os.path.exists(peak_path):
                return "[ERROR] No peak POIs found."

            try:
                peak_pois = gpd.read_file(peak_path, layer="hotspot_origins")
            except Exception as e:
                return f"[ERROR] Failed to load peak POIs: {e}"

            return {"result": result, "peak_pois": peak_pois}

        self.worker = WorkerThread(task)
        self.worker.finished.connect(self.on_pois_finished)
        self.worker.start()

    def on_pois_finished(self, result):
        self.hide_progress()

        if isinstance(result, str) and result.startswith("[ERROR]"):
            self.show_message("POIs Error", result, success=False)
            return

        self.loaded_peak_pois = result["peak_pois"]
        self.comboSelectPoi1.clear()
        self.comboSelectPoi2.clear()

        names = self.loaded_peak_pois["name"].dropna().astype(str).unique()
        self.comboSelectPoi1.addItems(sorted(names))
        self.comboSelectPoi2.addItems(sorted(names))

        self.show_message("POIs Extracted", result["result"], success=True)
        self.worker = None

    def run_heatmap(self, municipality, category):
        plugin_dir = os.path.dirname(__file__)

        heatmap_path = os.path.join(
        plugin_dir,
        "output",
        "heatmaps",
        municipality.lower().replace(" ", "_"),
        f"{category.lower()}_heatmap.tif")

        if not os.path.exists(heatmap_path):
            extract_heatmap_from_poi(municipality, category)
            print("[INFO] Heatmap generated.")
        else:
            print("[INFO] Heatmap already exists.")

    def run_peak_pois(self, municipality, category):
        return extract_peak_density(municipality, category)

    def show_networks(self):
        municipality = self.comboMunicipality.currentText()
        mode = self.comboMode.currentText().lower()
        if mode == "transit" and municipality.lower() != "coimbra":
            self.show_message(
                "Invalid Operation",
                "[ERROR] Transit networks are only available for Coimbra.",
                success=False
            )
            return

        self.show_progress()

        def task():
            return extract_network(municipality, mode)

        self.worker = WorkerThread(task)
        self.worker.finished.connect(self.on_network_extraction_finished)
        self.worker.start()

    def on_network_extraction_finished(self, result):
        self.hide_progress()
        self.show_message("Network Extraction", result, "[SUCCESS]" in result)
        self.worker = None


    def run_isochrones(self):
        try:
            mode = self.comboMode.currentText().lower()
            municipality = self.comboMunicipality.currentText()
            time1 = self.spinBoxTime1.value()
            time2 = self.spinBoxTime2.value()
            save_summary = self.checkBoxSave.isChecked()

            if time1 < 1 or time2 < 1 or time1 > 60 or time2 > 60:
                self.show_message("Invalid Time", "[ERROR] Please enter times between 1 and 60 minutes.", success=False)
                return

            if time1 == time2:
                self.show_message("Invalid Time", "[ERROR] Time values must be different.", success=False)
                return

            if not hasattr(self, 'loaded_peak_pois') or self.loaded_peak_pois is None:
                self.show_message("Isochrones", "[ERROR] No POIs loaded. Please extract POIs first.", success=False)
                return

            gdf = self.loaded_peak_pois.to_crs(epsg=4326)
            selected = gdf[gdf["name"].isin([
                self.comboSelectPoi1.currentText(),
                self.comboSelectPoi2.currentText()
            ])]

            if selected.empty:
                self.show_message("Isochrones", "[ERROR] Selected POIs not found.", success=False)
                return

            if self.comboSelectPoi1.currentText() == self.comboSelectPoi2.currentText():
                self.show_message("Invalid Selection", "[ERROR] Please select two different POIs for comparison.", success=False)
                return

            plugin_dir = os.path.dirname(__file__)
            temp_dir = os.path.join(plugin_dir, "output", "temp")
            os.makedirs(temp_dir, exist_ok=True)
            tmp_path = os.path.join(temp_dir, "tmp_selected_pois.gpkg")
            selected.to_file(tmp_path, layer="selected_pois", driver="GPKG")
            add_layer_to_project(tmp_path, "selected_pois", "Selected POIs")

            self.show_progress()

            if mode == "transit":
                if municipality.lower() != "coimbra":
                    self.hide_progress()
                    self.show_message("Isochrones", "[ERROR] Transit isochrones are only supported for Coimbra.", success=False)
                    return

                self.worker = WorkerThread(
                    extract_isochrones_for_transit,
                    municipality, tmp_path,
                    times=[time1, time2],
                    save_summary=save_summary
                )
            else:
                self.worker = WorkerThread(
                    extract_isochrones_for_walk_drive,
                    municipality, tmp_path, mode,
                    times=[time1, time2],
                    save_summary=save_summary
                )

            self.worker.finished.connect(self.on_isochrone_finished)
            self.worker.start()

        except Exception as e:
            self.hide_progress()
            self.show_message("Isochrones Error", str(e), success=False)

    def on_isochrone_finished(self, result):
        self.hide_progress()
        self.show_message("Isochrones Result", result, "[SUCCESS]" in result)
        self.worker = None

    def run_clustering(self):
        municipality = self.comboMunicipality.currentText()
        category = self.comboCategory.currentText()
        mode = self.comboMode.currentText().lower()
        n_clusters = self.spinBoxNClusters.value()

        if mode == "transit":
            self.show_message(
                "Unsupported Mode",
                "[ERROR] Clustering is not supported for 'transit' mode. Please choose 'walk' or 'drive'.",
                success=False
            )
            return

        if n_clusters < 2 or n_clusters > 10:
            self.show_message(
                "Invalid Number of Clusters",
                "[ERROR] Please select a number of clusters between 2 and 10.",
                success=False
            )
            return

        self.show_progress()

        def task():
            return extract_cluster_and_isochrones(municipality, category, mode, n_clusters)

        self.worker = WorkerThread(task)
        self.worker.finished.connect(self.on_clustering_finished)
        self.worker.start()

    def on_clustering_finished(self, result):
        self.hide_progress()

        if "[SUCCESS]" in result:
            self.show_message("Clustering", result, success=True)
        else:
            self.show_message("Clustering", result, success=False)
        self.worker = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SmartAccessDialog()
    dialog.show()
    sys.exit(app.exec_())
