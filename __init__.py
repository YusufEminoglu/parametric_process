# -*- coding: utf-8 -*-
"""Parametric Process QGIS Plugin Entry Point.
"""

def classFactory(iface):
    """Load ParametricProcessPlugin class from main_plugin.py."""
    from .main_plugin import ParametricProcessPlugin
    return ParametricProcessPlugin(iface)
