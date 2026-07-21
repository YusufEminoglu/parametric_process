# -*- coding: utf-8 -*-
"""Multi-tab QDialog with layer picker, server options, and release-ready styling for Parametric Process.
"""
from __future__ import annotations

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
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

        # Tab 1: Layer & Preset Setup
        tab_setup = QWidget()
        setup_layout = QFormLayout(tab_setup)
        setup_layout.setContentsMargins(12, 12, 12, 12)

        self.layer_combo = QgsMapLayerComboBox(self)
        try:
            from qgis.core import QgsWgcGeometryType
            self.layer_combo.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        except (ImportError, AttributeError):
            self.layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        self.combo_preset = QComboBox(self)
        self.combo_preset.addItems([
            "🏆 Balanced Master Plan (Recommended)",
            "🏙️ High Density Urban (Max FAR/GFA)",
            "🌿 Microclimate Eco-District (Max Wind/Solar/Open)",
            "💰 Financial Maximum ROI (Max Profit Yield)",
            "📐 Procedural Courtyard & Shape Grammar",
        ])

        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8090)

        self.chk_browser = QCheckBox("Open browser 3D cockpit automatically", self)
        self.chk_browser.setChecked(True)

        setup_layout.addRow(QLabel("Target Parcel/Block Layer:"), self.layer_combo)
        setup_layout.addRow(QLabel("Design Strategy Preset:"), self.combo_preset)
        setup_layout.addRow(QLabel("Local Cockpit Port:"), self.port_spin)
        setup_layout.addRow(self.chk_browser)

        self.tabs.addTab(tab_setup, "🎯 Setup & Presets")

        # Tab 2: Evolutionary Engine & AI Surrogate
        tab_evo = QWidget()
        evo_layout = QFormLayout(tab_evo)
        evo_layout.setContentsMargins(12, 12, 12, 12)

        self.combo_algo = QComboBox(self)
        self.combo_algo.addItems([
            "NSGA-III (Das & Dennis Reference Points)",
            "MOEA/D (Tchebycheff Decomposition)",
            "NSGA-II (Elitist Non-dominated Sorting)",
            "SPEA-2 (Strength Pareto Evolutionary)",
        ])

        self.spin_pop = QSpinBox(self)
        self.spin_pop.setRange(10, 500)
        self.spin_pop.setValue(40)

        self.spin_gen = QSpinBox(self)
        self.spin_gen.setRange(5, 200)
        self.spin_gen.setValue(20)

        self.chk_surrogate = QCheckBox("🤖 Enable Pure-Python AI Surrogate Model (<0.1ms Physics)", self)
        self.chk_surrogate.setChecked(True)

        evo_layout.addRow(QLabel("Optimization Algorithm:"), self.combo_algo)
        evo_layout.addRow(QLabel("Population Size:"), self.spin_pop)
        evo_layout.addRow(QLabel("Generations:"), self.spin_gen)
        evo_layout.addRow(self.chk_surrogate)

        self.tabs.addTab(tab_evo, "🧬 Evolutionary Solvers")

        # Tab 3: Environmental & Physics Parameters
        tab_env = QWidget()
        env_layout = QFormLayout(tab_env)
        env_layout.setContentsMargins(12, 12, 12, 12)

        self.spin_wind_deg = QSpinBox(self)
        self.spin_wind_deg.setRange(0, 360)
        self.spin_wind_deg.setValue(225)
        self.spin_wind_deg.setSuffix("° (SW)")

        self.spin_wind_speed = QSpinBox(self)
        self.spin_wind_speed.setRange(1, 30)
        self.spin_wind_speed.setValue(5)
        self.spin_wind_speed.setSuffix(" m/s")

        self.spin_latitude = QSpinBox(self)
        self.spin_latitude.setRange(-90, 90)
        self.spin_latitude.setValue(38)
        self.spin_latitude.setSuffix("° N")

        self.spin_const_cost = QSpinBox(self)
        self.spin_const_cost.setRange(100, 10000)
        self.spin_const_cost.setValue(750)
        self.spin_const_cost.setPrefix("$ ")

        self.spin_sale_price = QSpinBox(self)
        self.spin_sale_price.setRange(100, 20000)
        self.spin_sale_price.setValue(1650)
        self.spin_sale_price.setPrefix("$ ")

        env_layout.addRow(QLabel("Prevailing Wind Direction:"), self.spin_wind_deg)
        env_layout.addRow(QLabel("Prevailing Wind Speed:"), self.spin_wind_speed)
        env_layout.addRow(QLabel("Solar Latitude:"), self.spin_latitude)
        env_layout.addRow(QLabel("Construction Cost / m²:"), self.spin_const_cost)
        env_layout.addRow(QLabel("Estimated Sale Price / m²:"), self.spin_sale_price)

        self.tabs.addTab(tab_env, "🌤️ Physics Params")

        # Tab 4: Info / About
        tab_about = QWidget()
        about_layout = QVBoxLayout(tab_about)
        info_label = QLabel(
            "<b>Parametric Process Studio v0.8.1</b><br><br>"
            "Standalone generative parametric urban design, procedural shape grammar, and multi-objective evolutionary optimization lab for QGIS.<br><br>"
            "• <b>Solvers:</b> NSGA-II, NSGA-III (Ref Points), MOEA/D (Decomposition), SPEA-2<br>"
            "• <b>AI Acceleration:</b> Pure-Python Surrogate Model (&lt;0.1ms/eval)<br>"
            "• <b>Morphology Suite:</b> Canyon H/W, Enclosure Index, SA/V Compactness, Shannon Entropy<br>"
            "• <b>Physics Engine:</b> Sol-Air Temp, Solar PV, CFD Wind Arrow Particles, UTCI Thermal Comfort<br>"
            "• <b>Exporters:</b> 3D CityJSON 1.1, Wavefront OBJ Mesh, 3D GeoPackage, Executive HTML Reports<br><br>"
            "Developed by <b>Yusuf Eminoğlu</b>."
        )
        info_label.setWordWrap(True)
        about_layout.addWidget(info_label)

        self.tabs.addTab(tab_about, "ℹ️ About Suite")

        layout.addWidget(self.tabs)

        self.status_label = QLabel("Ready to launch Parametric Process studio.")
        self.status_label.setStyleSheet("color: #0f766e; font-style: italic; margin-top: 4px;")
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
            "preset": self.combo_preset.currentText(),
            "port": self.port_spin.value(),
            "launch_browser": self.chk_browser.isChecked(),
            "algorithm": self.combo_algo.currentText(),
            "pop_size": self.spin_pop.value(),
            "generations": self.spin_gen.value(),
            "use_surrogate": self.chk_surrogate.isChecked(),
            "sim_params": {
                "wind_deg": self.spin_wind_deg.value(),
                "wind_speed": self.spin_wind_speed.value(),
                "latitude": self.spin_latitude.value(),
                "const_cost": self.spin_const_cost.value(),
                "sale_price": self.spin_sale_price.value(),
            }
        }
        self.runRequested.emit(params)
        self.accept()

    def set_status(self, msg: str, error: bool = False) -> None:
        color = "#ef4444" if error else "#0f766e"
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

