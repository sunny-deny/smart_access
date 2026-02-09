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

        self.btnShowPolygon.clicked.connect(self.show_polygon)
        self.btnShowPois.clicked.connect(self.show_pois)
        self.btnShowNetworks.clicked.connect(self.show_networks)
        self.btnRunIsochrone.clicked.connect(self.run_isochrones)
        self.btnRunClustering.clicked.connect(self.run_clustering)

        self.loaded_peak_pois = None




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
            return

        self.loaded_peak_pois = result["peak_pois"]
        self.comboSelectPoi1.clear()
        self.comboSelectPoi2.clear()

        names = self.loaded_peak_pois["name"].dropna().astype(str).unique()
        self.comboSelectPoi1.addItems(sorted(names))
        self.comboSelectPoi2.addItems(sorted(names))

        self.worker = None
    
        def show_progress(self):
        self.progress_value = 0
        if hasattr(self, "progressBar"):
            self.progressBar.setValue(0)
            self.progressBar.setVisible(True)
        self.simulated_timer.start()

    def hide_progress(self):
        self.simulated_timer.stop()
        if hasattr(self, "progressBar"):
            self.progressBar.setVisible(False)

    def advance_progress(self):
        self.progress_value = min(100, self.progress_value + 3)
        if hasattr(self, "progressBar"):
            self.progressBar.setValue(self.progress_value)
        if self.progress_value >= 100:
            self.simulated_timer.stop()

    def show_networks(self):
        QMessageBox.information(self, "Info", "Networks: not implemented yet.")

    def run_isochrones(self):
        QMessageBox.information(self, "Info", "Isochrones: not implemented yet.")

    def run_clustering(self):
        QMessageBox.information(self, "Info", "Clustering: not implemented yet.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SmartAccessDialog()
    dialog.show()
    sys.exit(app.exec_())
