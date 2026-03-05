from qgis.core import QgsApplication
from qgis.analysis import QgsNativeAlgorithms
import sys
import processing

def init_qgis():
    QgsApplication.setPrefixPath("C:/Program Files/QGIS 3.34.15/apps/qgis", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    sys.path.append("C:/Program Files/QGIS 3.34.15/apps/qgis/python/plugins")

    from processing.core.Processing import Processing
    Processing.initialize()
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
    return qgs

