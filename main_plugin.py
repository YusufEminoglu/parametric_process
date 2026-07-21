# -*- coding: utf-8 -*-
"""Parametric Process plugin shell — PlanX dock pattern.

Registers the Processing provider and a dockable "Studio" panel
that browses algorithms and launches the 3D WebGL cockpit.
All analytics live in Processing algorithms; all physics in engine/.
"""
from __future__ import annotations

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication

from .processing_provider import ParametricProcessProvider

PLUGIN_DIR = os.path.dirname(__file__)


class ParametricProcessPlugin:
    """Plugin entry: Processing provider + Studio dock."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.dock = None
        self.action = None

    def initGui(self) -> None:
        # Processing Toolbox — 6 algorithms under "Urban Analytics"
        self.provider = ParametricProcessProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        # Single toolbar icon → toggle dock
        icon = QIcon(os.path.join(PLUGIN_DIR, "icons", "icon.png"))
        self.action = QAction(icon, "Parametric Process Studio", self.iface.mainWindow())
        self.action.setToolTip("Open the Parametric Process Studio panel")
        self.action.triggered.connect(self.toggle_dock)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Parametric Process", self.action)

    def unload(self) -> None:
        if self.action is not None:
            self.iface.removePluginMenu("&Parametric Process", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def toggle_dock(self):
        if self.dock is None:
            try:
                from .studio_dock import ParametricProcessStudioDock
                self.dock = ParametricProcessStudioDock(self.iface)
                self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
            except Exception as exc:
                self.iface.messageBar().pushWarning("Parametric Process", f"Studio panel unavailable: {exc}")
                return
        self.dock.setVisible(not self.dock.isVisible())
