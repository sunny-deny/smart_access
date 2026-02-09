def classFactory(iface):
    from .smart_acess_plugin import SmartAcessPlugin
    return SmartAcessPlugin(iface)
