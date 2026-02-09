from PyQt5.QtWidgets import QAction
from .smart_access_dialog import SmartAccessDialog

class SmartAcessPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction("SmartAcess", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&SmartAcess", self.action)

    def unload(self):
        self.iface.removePluginMenu("&SmartAcess", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = SmartAccessDialog()
        self.dialog.show()
