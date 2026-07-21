# -*- coding: utf-8 -*-
"""Parametric Process main plugin class.
"""
from __future__ import annotations

import os
import threading
import webbrowser
from qgis.PyQt.QtCore import QObject, QCoreApplication, QThread, pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMessageBox

try:
    from qgis.PyQt.QtWidgets import QAction
except ImportError:
    from qgis.PyQt.QtGui import QAction

from qgis.core import (
    QgsVectorLayer,
    QgsJsonExporter,
    QgsGeometry,
    QgsPointXY,
)

from .dialog import PluginDialog
from .server import ParametricProcessServer


def _make_field(name: str, kind: str):
    """Create a QgsField across QGIS 3/4."""
    from qgis.core import QgsField
    try:
        from qgis.PyQt.QtCore import QMetaType
        meta = {
            "double": QMetaType.Type.Double,
            "integer": QMetaType.Type.Int,
            "string": QMetaType.Type.QString,
        }
        return QgsField(name, meta[kind])
    except Exception:
        from qgis.PyQt.QtCore import QVariant
        legacy = {
            "double": QVariant.Double,
            "integer": QVariant.Int,
            "string": QVariant.String,
        }
        return QgsField(name, legacy[kind])


class _SyncBridge(QObject):
    """Marshal HTTP sync requests from the server thread to QGIS' main thread."""

    request = pyqtSignal(object, object)

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.request.connect(self._handle_request)

    @pyqtSlot(object, object)
    def _handle_request(self, data, token):
        try:
            token["result"] = self.plugin._sync_to_qgis(data)
        except Exception as exc:
            token["result"] = (False, f"Sync failed: {exc}")
        finally:
            token["event"].set()


class ParametricProcessPlugin:
    MENU_NAME = "&Parametric Process"

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.icon_path = os.path.join(self.plugin_dir, "icons", "icon.png")
        self.action: QAction | None = None
        self.dialog = None
        self.server = None
        self.active_layer = None
        self.crs_transformed = False
        self.export_crs = None
        self.sync_bridge = _SyncBridge(self)

    def initGui(self) -> None:
        self.action = QAction(QIcon(self.icon_path), "Parametric Process", self.iface.mainWindow())
        self.action.setStatusTip("Parametric Generative Design & Evolutionary Optimization Studio")
        self.action.triggered.connect(self.show_dialog)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.MENU_NAME, self.action)

    def unload(self) -> None:
        if self.action:
            self.iface.removePluginMenu(self.MENU_NAME, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.dialog:
            self.dialog.close()
            self.dialog = None
        if self.server:
            self.server.stop()
            self.server = None

    def show_dialog(self) -> None:
        if self.dialog is None:
            self.dialog = PluginDialog(self.iface, self.iface.mainWindow())
            self.dialog.runRequested.connect(self.run_action)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def run_action(self, params: dict) -> None:
        layer = params["layer"]
        port = params["port"]
        launch = params["launch_browser"]

        if not isinstance(layer, QgsVectorLayer):
            self._error("Error", "Active layer must be a valid vector layer.")
            return

        self.active_layer = layer

        crs = layer.crs()
        crs_is_geographic = crs.isGeographic()

        from qgis.core import QgsCoordinateReferenceSystem
        if crs_is_geographic:
            self.export_crs = QgsCoordinateReferenceSystem("EPSG:3857")
            self.crs_transformed = True
            self.iface.messageBar().pushWarning(
                "Parametric Process",
                "Active layer uses geographic coordinates. Geometries are projected to Web Mercator for 3D rendering."
            )
        else:
            self.export_crs = crs
            self.crs_transformed = False

        web_dir = os.path.join(self.plugin_dir, "web")
        if not os.path.exists(web_dir):
            os.makedirs(web_dir, exist_ok=True)

        try:
            if self.server:
                self.server.stop()
            self.server = ParametricProcessServer(port, web_dir, self.sync_callback)
            self.server.start()
        except Exception as e:
            self._error("Server Error", f"Could not start local server on port {port}:\n{e}")
            return

        if self.server.port != port:
            self.iface.messageBar().pushInfo(
                "Parametric Process",
                f"Port {port} was busy; cockpit is served on port {self.server.port}."
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

            try:
                import json
                geojson_dict = json.loads(geojson_str)
                geojson_dict["crs_is_geographic"] = crs_is_geographic
                geojson_str = json.dumps(geojson_dict)
            except Exception as json_err:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"Failed to inject CRS info: {json_err}", "ParametricProcess", Qgis.Warning)

            self.server.update_geojson(geojson_str)
        except Exception as e:
            self._error("Data Export Error", f"Could not convert layer features to GeoJSON:\n{e}")
            return

        msg = f"Parametric Process server started on port {port}. Layer loaded successfully."
        self.iface.messageBar().pushSuccess("Parametric Process", msg)
        if self.dialog:
            self.dialog.set_status(msg)

        if launch:
            webbrowser.open(f"http://127.0.0.1:{port}/index.html")

    def sync_callback(self, data: dict) -> tuple[bool, str]:
        """Server-thread callback for POST /sync."""
        app = QCoreApplication.instance()
        if app is None or QThread.currentThread() == app.thread():
            return self._sync_to_qgis(data)

        token = {"event": threading.Event(), "result": None}
        self.sync_bridge.request.emit(data, token)
        if not token["event"].wait(30):
            return False, "Sync timed out while waiting for QGIS main thread"
        return token["result"] or (False, "Sync failed without a result")

    def _sync_to_qgis(self, data: dict) -> tuple[bool, str]:
        """Apply browser design updates & Pareto solution attributes to the active QGIS layer."""
        if not self.active_layer:
            return False, "QGIS active layer is not set"

        was_editing = self.active_layer.isEditable()

        try:
            updates = data.get("updates", [])
            if not updates:
                return True, "No updates provided"

            fields_to_add = {
                "far": "double",
                "bcr": "double",
                "gfa": "double",
                "setback": "double",
                "scale_x": "double",
                "scale_y": "double",
                "floors": "integer",
                "usage": "string",
                "floor_h": "double",
                "typology": "string",
                "max_bcr": "double",
                "max_far": "double",
                "max_height": "double",
                "roof_style": "string",
                "stepback_i": "integer",
                "stepback_d": "double",
                "plan_score": "double",
                "const_load": "double",
                "height_m": "double",
                "z_base": "double",
                "z_top": "double",
                "pop_est": "integer",
                "carbon": "double",
                "runoff": "double",
                "open_space": "double",
                "wind_score": "double",
                "solar_kwh": "double",
                "poll_disp": "double",
                "svf_ratio": "double",
                "canyon_hw": "double",
                "pareto_rank": "integer",
                "wallacei_id": "string",
            }

            existing_fields = [f.name() for f in self.active_layer.fields()]

            fields_to_create = [
                _make_field(name, ftype)
                for name, ftype in fields_to_add.items()
                if name not in existing_fields
            ]

            if fields_to_create and was_editing:
                for field in fields_to_create:
                    if not self.active_layer.addAttribute(field):
                        return False, f"Could not add field '{field.name()}' to editable layer"
                self.active_layer.updateFields()
            elif fields_to_create:
                if not self.active_layer.dataProvider().addAttributes(fields_to_create):
                    return False, "Could not add required fields to layer"
                self.active_layer.updateFields()

            if not self.active_layer.isEditable() and not self.active_layer.startEditing():
                return False, "Could not start an edit session for active layer"

            self.active_layer.beginEditCommand("Parametric Process sync")

            field_indices = {
                name: self.active_layer.fields().indexOf(name)
                for name in fields_to_add
            }

            for item in updates:
                try:
                    fid = int(item.get("id"))
                except (TypeError, ValueError):
                    raise RuntimeError(f"Invalid feature id in sync payload: {item.get('id')!r}")

                values = {
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
                    "pareto_rank": int(item.get("pareto_rank", 1)),
                    "wallacei_id": str(item.get("wallacei_id", "sol_1")),
                }
                for name, value in values.items():
                    if not self.active_layer.changeAttributeValue(fid, field_indices[name], value):
                        raise RuntimeError(f"Could not update '{name}' for feature {fid}")

            self.active_layer.endEditCommand()
            if not was_editing:
                self.active_layer.commitChanges()

            return True, f"Successfully updated {len(updates)} feature(s) in QGIS."
        except Exception as e:
            if self.active_layer and self.active_layer.isEditable():
                self.active_layer.destroyEditCommand()
            return False, f"Sync error: {e}"

    def _error(self, title: str, message: str) -> None:
        QMessageBox.critical(self.iface.mainWindow(), title, message)
