# -*- coding: utf-8 -*-
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

class ParametricProcessProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()

    def id(self):
        return 'parametric_process'

    def name(self):
        return 'Parametric Process Studio'

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'icon.png')
        return QIcon(icon_path)

    def loadAlgorithms(self):
        from .processing_algorithm import (
            ParametricOptimizationAlgorithm,
            UrbanPhysicsEvaluatorAlgorithm
        )
        self.addAlgorithm(ParametricOptimizationAlgorithm())
        self.addAlgorithm(UrbanPhysicsEvaluatorAlgorithm())
