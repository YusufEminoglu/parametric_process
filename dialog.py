# -*- coding: utf-8 -*-
"""Multi-tab QDialog with layer picker, server options, and release-ready styling for Parametric Process.
"""
from __future__ import annotations

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox


class PluginDialog(QDialog):
    runRequested = pyqtSignal(dict)

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Parametric Process")
        self.resize(540, 430)
        self._apply_theme()
        self._build_ui()

    def _apply_theme(self) -> None:
        qss = """
        QDialog {
            background-color: #f8fafc;
            color: #0f172a;
        }
        QTabWidget::pane {
            border: 1px solid #cbd5e1;
            background: #ffffff;
            border-radius: 8px;
            padding: 10px;
        }
        QTabBar::tab {
            background: #e2e8f0;
            color: #475569;
            padding: 10px 16px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 3px;
            font-weight: 500;
        }
        QTabBar::tab:selected {
            background: #0f766e;
            color: #ffffff;
            border-bottom: 2px solid #0d9488;
            font-weight: bold;
        }
        QTabBar::tab:hover:!selected {
            background: #cbd5e1;
            color: #0f172a;
        }
        QLabel {
            color: #0f172a;
            font-family: "Inter", "Segoe UI", Helvetica, sans-serif;
            font-size: 12px;
        }
        QLineEdit, QSpinBox, QComboBox {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 6px 10px;
            min-height: 20px;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border: 1px solid #0d9488;
            background-color: #f8fafc;
        }
        QCheckBox {
            color: #334155;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            background-color: #ffffff;
            border: 1px solid #94a3b8;
            border-radius: 4px;
        }
        QCheckBox::indicator:checked {
            background-color: #0d9488;
            border-color: #14b8a6;
        }
        QPushButton {
            background-color: #0f766e;
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: bold;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #0d9488;
        }
        QPushButton:pressed {
            background-color: #115e59;
        }
        """
        self.setStyleSheet(qss)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        # Tab 1: Layer & Cockpit Setup
        tab_setup = QWidget()
        setup_layout = QFormLayout(tab_setup)
        setup_layout.setContentsMargins(10, 10, 10, 10)

        self.layer_combo = QgsMapLayerComboBox(self)
        try:
            from qgis.core import QgsWgcGeometryType
            self.layer_combo.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        except (ImportError, AttributeError):
            self.layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8090)

        self.chk_browser = QCheckBox("Open browser automatically", self)
        self.chk_browser.setChecked(True)

        setup_layout.addRow(QLabel("Target Parcel/Block Layer:"), self.layer_combo)
        setup_layout.addRow(QLabel("Local Cockpit Port:"), self.port_spin)
        setup_layout.addRow(self.chk_browser)

        self.tabs.addTab(tab_setup, "3D Cockpit Setup")

        # Tab 2: Info / About
        tab_about = QWidget()
        about_layout = QVBoxLayout(tab_about)
        info_label = QLabel(
            "<b>Parametric Process v0.1.0</b><br><br>"
            "Generative parametric urban design and multi-objective evolutionary optimization lab for QGIS.<br><br>"
            "• NSGA-II Evolutionary Solver (GFA, PlanX Score, Carbon, Runoff, Daylight)<br>"
            "• Interactive Parallel Coordinates (PCP) & Pareto Front Scatter Plots<br>"
            "• 3D Phenotype preview & 2-way QGIS Vector Layer Sync<br><br>"
            "Developed by Yusuf Eminoğlu."
        )
        info_label.setWordWrap(True)
        about_layout.addWidget(info_label)

        self.tabs.addTab(tab_about, "About & Engine Info")

        layout.addWidget(self.tabs)

        self.status_label = QLabel("Ready to launch Parametric Process cockpit.")
        self.status_label.setStyleSheet("color: #475569; font-style: italic; margin-top: 4px;")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(self)
        buttons.addButton("Launch Cockpit", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        buttons.accepted.connect(self._on_launch)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_launch(self) -> None:
        params = {
            "layer": self.layer_combo.currentLayer(),
            "port": self.port_spin.value(),
            "launch_browser": self.chk_browser.isChecked(),
        }
        self.runRequested.emit(params)
        self.accept()

    def set_status(self, msg: str, error: bool = False) -> None:
        color = "#ef4444" if error else "#0f766e"
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
