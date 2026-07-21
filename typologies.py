# -*- coding: utf-8 -*-
"""Custom Typology Editor & Preset Registry Engine for Parametric Process.

Allows users to define, register, and modify custom procedural building typologies
with customizable footprint ratios, courtyard allocations, and setback profiles.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

BUILTIN_TYPOLOGIES: Dict[str, Dict[str, Any]] = {
    "Tower": {
        "description": "High-rise slender tower massing with maximum daylight and open space retention.",
        "footprint_ratio": 0.35,
        "courtyard_ratio": 0.0,
        "height_modifier": 1.4,
        "setback_profile": "Standard",
        "category": "HighRise"
    },
    "Slab": {
        "description": "Linear slab block aligned for solar orientation and cross-ventilation.",
        "footprint_ratio": 0.45,
        "courtyard_ratio": 0.0,
        "height_modifier": 1.0,
        "setback_profile": "Linear",
        "category": "MidRise"
    },
    "Courtyard": {
        "description": "Perimeter block enclosure with shared private central courtyard garden.",
        "footprint_ratio": 0.55,
        "courtyard_ratio": 0.35,
        "height_modifier": 0.8,
        "setback_profile": "Perimeter",
        "category": "Perimeter"
    },
    "LShape": {
        "description": "L-shaped massing creating a semi-enclosed corner urban plaza.",
        "footprint_ratio": 0.48,
        "courtyard_ratio": 0.15,
        "height_modifier": 1.0,
        "setback_profile": "CornerPlaza",
        "category": "MidRise"
    },
    "UShape": {
        "description": "U-shaped massing framing a central green atrium court.",
        "footprint_ratio": 0.50,
        "courtyard_ratio": 0.25,
        "height_modifier": 0.9,
        "setback_profile": "FramedCourt",
        "category": "Perimeter"
    },
    "PodiumTower": {
        "description": "Multi-story retail podium base with set-back high-rise residential tower.",
        "footprint_ratio": 0.65,
        "courtyard_ratio": 0.10,
        "height_modifier": 1.6,
        "setback_profile": "PodiumTerrace",
        "category": "Hybrid"
    },
    "SteppedTower": {
        "description": "Terraced stepped massing with sky-gardens on step-back roof levels.",
        "footprint_ratio": 0.50,
        "courtyard_ratio": 0.0,
        "height_modifier": 1.3,
        "setback_profile": "TerracedSteps",
        "category": "Stepped"
    },
    "MultiBuildingBlock": {
        "description": "Cluster of multiple smaller pavilions linked by pedestrian plazas.",
        "footprint_ratio": 0.40,
        "courtyard_ratio": 0.20,
        "height_modifier": 0.7,
        "setback_profile": "PavilionCluster",
        "category": "LowRise"
    }
}

_custom_registry: Dict[str, Dict[str, Any]] = {}


def register_custom_typology(
    name: str,
    footprint_ratio: float = 0.45,
    courtyard_ratio: float = 0.0,
    height_modifier: float = 1.0,
    setback_profile: str = "Custom",
    category: str = "Custom",
    description: str = "User-defined custom parametric typology."
) -> Dict[str, Any]:
    """Registers a new custom building typology into the engine."""
    clean_name = name.strip()
    spec = {
        "description": description,
        "footprint_ratio": max(0.10, min(0.90, footprint_ratio)),
        "courtyard_ratio": max(0.0, min(0.60, courtyard_ratio)),
        "height_modifier": max(0.4, min(3.0, height_modifier)),
        "setback_profile": setback_profile,
        "category": category,
        "is_custom": True
    }
    _custom_registry[clean_name] = spec
    return spec


def get_typology_spec(name: str) -> Dict[str, Any]:
    """Retrieves full specification dictionary for a given typology name."""
    if name in _custom_registry:
        return _custom_registry[name]
    return BUILTIN_TYPOLOGIES.get(name, BUILTIN_TYPOLOGIES["Tower"])


def list_available_typologies() -> List[str]:
    """Returns list of all available builtin and custom typology names."""
    return list(BUILTIN_TYPOLOGIES.keys()) + list(_custom_registry.keys())
