# -*- coding: utf-8 -*-
"""Parametric Process Studio dock — PlanX-style Processing browser + cockpit launcher."""
from __future__ import annotations

import os
import webbrowser
import threading

from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsJsonExporter,
    QgsMapLayerProxyModel,
    QgsMessageLog,
    QgsVectorLayer,
    Qgis,
)
from qgis.gui import QgsMapLayerComboBox

PLUGIN_DIR = os.path.dirname(__file__)

_DOCK_QSS = """
QDockWidget { font-size: 12px; }
QLabel#ppHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0f766e, stop:1 #14b8a6);
    color: white; font-weight: bold; font-size: 13px;
    padding: 10px 12px; border-radius: 6px;
}
QTreeWidget { border: none; font-size: 12px; }
QPushButton#btnLaunch {
    background: #0f766e; color: white; border: none;
    border-radius: 6px; padding: 8px 16px; font-weight: bold; min-height: 28px;
}
QPushButton#btnLaunch:hover { background: #0d9488; }
QPushButton#btnLaunch:disabled { background: #94a3b8; }
"""


class _SyncBridge(QObject):
    """Marshal HTTP sync requests from server thread to QGIS main thread."""
    request = pyqtSignal(object, object)

    def __init__(self, plugin_ref):
        super().__init__()
        self.plugin_ref = plugin_ref
        self.request.connect(self._handle)

    @pyqtSlot(object, object)
    def _handle(self, data, token):
        try:
            token["result"] = self.plugin_ref._sync_to_qgis(data)
        except Exception as exc:
            token["result"] = (False, f"Sync failed: {exc}")
        finally:
            token["event"].set()


class ParametricProcessStudioDock(QDockWidget):
    """Docked panel: 3D cockpit launcher + Processing algorithm browser."""

    def __init__(self, iface):
        super().__init__("Parametric Process Studio")
        self.iface = iface
        self.setObjectName("ParametricProcessStudioDock")
        self.server = None
        self.active_layer = None
        self.export_crs = None
        self.crs_transformed = False
        self.sync_bridge = _SyncBridge(self)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(8, 8, 8, 8)

        # ---- Header ----
        header = QLabel("Parametric Process Studio")
        header.setObjectName("ppHeader")
        layout.addWidget(header)

        # ---- Cockpit Launcher ----
        cockpit_group = QWidget()
        cform = QFormLayout(cockpit_group)
        cform.setContentsMargins(4, 8, 4, 4)

        self.layer_combo = QgsMapLayerComboBox()
        try:
            from qgis.core import QgsWgcGeometryType
            self.layer_combo.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        except (ImportError, AttributeError):
            self.layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8090)

        self.chk_browser = QCheckBox("Open browser automatically")
        self.chk_browser.setChecked(True)

        cform.addRow(QLabel("Parcel / Block Layer:"), self.layer_combo)
        cform.addRow(QLabel("Local Port:"), self.port_spin)
        cform.addRow(self.chk_browser)

        layout.addWidget(cockpit_group)

        btn_row = QHBoxLayout()
        self.btn_launch = QPushButton("🚀 Launch 3D Cockpit")
        self.btn_launch.setObjectName("btnLaunch")
        self.btn_launch.clicked.connect(self._launch_cockpit)
        btn_row.addWidget(self.btn_launch)

        self.btn_stop = QPushButton("⏹ Stop Server")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_server)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #0f766e; font-style: italic; padding: 2px 4px;")
        layout.addWidget(self.status_label)

        # ---- Algorithm Browser (PlanX-style tree) ----
        algo_label = QLabel("<b>Processing Tools</b> — double-click to run")
        algo_label.setStyleSheet("padding-top: 8px; color: #475569;")
        layout.addWidget(algo_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._launch_algorithm)
        layout.addWidget(self.tree)

        body.setStyleSheet(_DOCK_QSS)
        self.setWidget(body)
        self._populate_tree()

    # ------------------------------------------------------------------ #
    # Algorithm tree
    # ------------------------------------------------------------------ #
    def _populate_tree(self):
        self.tree.clear()
        provider = QgsApplication.processingRegistry().providerById("parametric_process")
        if provider is None:
            self.tree.addTopLevelItem(QTreeWidgetItem(["Provider not loaded yet"]))
            return
        fallback = QIcon(os.path.join(PLUGIN_DIR, "icons", "icon.png"))
        groups: dict[str, list] = {}
        for alg in provider.algorithms():
            groups.setdefault(alg.group(), []).append(alg)
        for group in sorted(groups):
            parent = QTreeWidgetItem([group])
            self.tree.addTopLevelItem(parent)
            for alg in sorted(groups[group], key=lambda a: a.displayName()):
                item = QTreeWidgetItem([alg.displayName()])
                try:
                    icon = alg.icon()
                except Exception:
                    icon = fallback
                item.setIcon(0, icon if not icon.isNull() else fallback)
                item.setToolTip(0, alg.shortHelpString())
                item.setData(0, Qt.ItemDataRole.UserRole, alg.id())
                parent.addChild(item)
            parent.setExpanded(True)

    def _launch_algorithm(self, item, _column):
        alg_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not alg_id:
            return
        try:
            import processing
            processing.execAlgorithmDialog(alg_id, {})
        except Exception as exc:
            self.iface.messageBar().pushWarning("Parametric Process", f"Could not open tool: {exc}")

    # ------------------------------------------------------------------ #
    # Cockpit server
    # ------------------------------------------------------------------ #
    def _launch_cockpit(self):
        layer = self.layer_combo.currentLayer()
        if not isinstance(layer, QgsVectorLayer):
            self.iface.messageBar().pushWarning("Parametric Process", "Select a valid polygon layer.")
            return

        self.active_layer = layer
        crs = layer.crs()
        crs_is_geographic = crs.isGeographic()

        if crs_is_geographic:
            self.export_crs = QgsCoordinateReferenceSystem("EPSG:3857")
            self.crs_transformed = True
            self.iface.messageBar().pushWarning(
                "Parametric Process",
                "Geographic CRS detected — projecting to Web Mercator for 3D rendering."
            )
        else:
            self.export_crs = crs
            self.crs_transformed = False

        web_dir = os.path.join(PLUGIN_DIR, "web")
        os.makedirs(web_dir, exist_ok=True)

        port = self.port_spin.value()
        try:
            if self.server:
                self.server.stop()
            from .server import ParametricProcessServer
            self.server = ParametricProcessServer(port, web_dir, self._sync_callback)
            self.server.start()
        except Exception as e:
            self.iface.messageBar().pushCritical("Parametric Process", f"Server error: {e}")
            return

        if self.server.port != port:
            self.iface.messageBar().pushInfo(
                "Parametric Process", f"Port {port} busy — using {self.server.port}"
            )
        port = self.server.port

        try:
            exporter = QgsJsonExporter(layer)
            exporter.setPrecision(6)
            exporter.setIncludeAttributes(True)
            exporter.setDestinationCrs(self.export_crs)

            if layer.selectedFeatureCount() > 0:
                features = list(layer.selectedFeatures())
            else:
                features = list(layer.getFeatures())

            geojson_str = exporter.exportFeatures(features)
            import json
            geojson_dict = json.loads(geojson_str)
            geojson_dict["crs_is_geographic"] = crs_is_geographic
            geojson_str = json.dumps(geojson_dict)

            self.server.update_geojson(geojson_str)
        except Exception as e:
            self.iface.messageBar().pushCritical("Parametric Process", f"Data export error: {e}")
            return

        self.status_label.setText(f"Server running on port {port}")
        self.status_label.setStyleSheet("color: #0f766e; font-weight: bold;")
        self.btn_launch.setEnabled(False)
        self.btn_stop.setEnabled(True)

        if self.chk_browser.isChecked():
            webbrowser.open(f"http://127.0.0.1:{port}/index.html")

        self.iface.messageBar().pushSuccess("Parametric Process", f"Cockpit live on port {port}")

    def _stop_server(self):
        if self.server:
            self.server.stop()
            self.server = None
        self.status_label.setText("Server stopped.")
        self.status_label.setStyleSheet("color: #64748b; font-style: italic;")
        self.btn_launch.setEnabled(True)
        self.btn_stop.setEnabled(False)

    # ------------------------------------------------------------------ #
    # Sync bridge (server thread → QGIS main thread)
    # ------------------------------------------------------------------ #
    def _sync_callback(self, data: dict) -> tuple[bool, str]:
        app = QgsApplication.instance()
        if app is None or QThread.currentThread() == app.thread():
            return self._sync_to_qgis(data)

        token = {"event": threading.Event(), "result": None}
        self.sync_bridge.request.emit(data, token)
        if not token["event"].wait(30):
            return False, "Sync timed out"
        return token["result"] or (False, "Sync failed")

    def _sync_to_qgis(self, data: dict) -> tuple[bool, str]:
        if not self.active_layer:
            return False, "No active layer"

        was_editing = self.active_layer.isEditable()
        try:
            updates = data.get("updates", [])
            if not updates:
                return True, "No updates"

            fields_to_add = {
                "far": "double", "bcr": "double", "gfa": "double",
                "setback": "double", "scale_x": "double", "scale_y": "double",
                "floors": "integer", "usage": "string", "floor_h": "double",
                "typology": "string", "max_bcr": "double", "max_far": "double",
                "max_height": "double", "roof_style": "string",
                "stepback_i": "integer", "stepback_d": "double",
                "plan_score": "double", "const_load": "double",
                "height_m": "double", "z_base": "double", "z_top": "double",
                "pop_est": "integer", "carbon": "double", "runoff": "double",
                "open_space": "double", "wind_score": "double",
                "solar_kwh": "double", "poll_disp": "double",
                "svf_ratio": "double", "canyon_hw": "double",
                "roi_yield": "double", "mrt_temp": "double",
                "utci_score": "double", "pv_kwh": "double",
                "pareto_rank": "integer", "wallacei_id": "string",
            }

            existing = [f.name() for f in self.active_layer.fields()]
            to_create = [
                self._make_field(n, t) for n, t in fields_to_add.items() if n not in existing
            ]
            if to_create:
                if was_editing:
                    for field in to_create:
                        self.active_layer.addAttribute(field)
                    self.active_layer.updateFields()
                else:
                    self.active_layer.dataProvider().addAttributes(to_create)
                    self.active_layer.updateFields()

            if not self.active_layer.isEditable() and not self.active_layer.startEditing():
                return False, "Could not start editing"

            self.active_layer.beginEditCommand("Parametric Process sync")
            field_idx = {n: self.active_layer.fields().indexOf(n) for n in fields_to_add}

            for item in updates:
                fid = int(item.get("id"))
                vals = {
                    "far": float(item.get("far", 0)),
                    "bcr": float(item.get("bcr", 0)),
                    "gfa": float(item.get("gfa", 0)),
                    "setback": float(item.get("setback", 0)),
                    "scale_x": float(item.get("scale_x", 1)),
                    "scale_y": float(item.get("scale_y", 1)),
                    "floors": int(item.get("floors", 1)),
                    "usage": str(item.get("usage", "MixedUse")),
                    "floor_h": float(item.get("floor_h", 3.0)),
                    "typology": str(item.get("typology", "Tower")),
                    "max_bcr": float(item.get("max_bcr", 0.45)),
                    "max_far": float(item.get("max_far", 2.5)),
                    "max_height": float(item.get("max_height", 18.0)),
                    "roof_style": str(item.get("roof_style", "Flat")),
                    "stepback_i": int(item.get("stepback_i", 4)),
                    "stepback_d": float(item.get("stepback_d", 1.5)),
                    "plan_score": float(item.get("plan_score", 0)),
                    "const_load": float(item.get("const_load", 0)),
                    "height_m": float(item.get("height_m", 0)),
                    "z_base": float(item.get("z_base", 0)),
                    "z_top": float(item.get("z_top", 0)),
                    "pop_est": int(item.get("pop_est", 0)),
                    "carbon": float(item.get("carbon", 0)),
                    "runoff": float(item.get("runoff", 0)),
                    "open_space": float(item.get("open_space", 0)),
                    "wind_score": float(item.get("wind_score", 0)),
                    "solar_kwh": float(item.get("solar_kwh", 0)),
                    "poll_disp": float(item.get("poll_disp", 0)),
                    "svf_ratio": float(item.get("svf_ratio", 0)),
                    "canyon_hw": float(item.get("canyon_hw", 0)),
                    "roi_yield": float(item.get("roi_yield", 0)),
                    "mrt_temp": float(item.get("mrt_temp", 0)),
                    "utci_score": float(item.get("utci_score", 0)),
                    "pv_kwh": float(item.get("pv_kwh", 0)),
                    "pareto_rank": int(item.get("pareto_rank", 1)),
                    "wallacei_id": str(item.get("wallacei_id", "sol_1")),
                }
                for name, value in vals.items():
                    self.active_layer.changeAttributeValue(fid, field_idx[name], value)

            self.active_layer.endEditCommand()
            if not was_editing:
                self.active_layer.commitChanges()
            return True, f"Synced {len(updates)} feature(s)"
        except Exception as e:
            if self.active_layer and self.active_layer.isEditable():
                self.active_layer.destroyEditCommand()
            return False, f"Sync error: {e}"

    @staticmethod
    def _make_field(name: str, kind: str):
        from qgis.core import QgsField
        try:
            from qgis.PyQt.QtCore import QMetaType
            meta = {"double": QMetaType.Type.Double, "integer": QMetaType.Type.Int, "string": QMetaType.Type.QString}
            return QgsField(name, meta[kind])
        except Exception:
            from qgis.PyQt.QtCore import QVariant
            legacy = {"double": QVariant.Double, "integer": QVariant.Int, "string": QVariant.String}
            return QgsField(name, legacy[kind])

    # ------------------------------------------------------------------ #
    def closeEvent(self, event):
        self._stop_server()
        super().closeEvent(event)
