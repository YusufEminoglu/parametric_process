# -*- coding: utf-8 -*-
"""Block Typology System for Parametric Process PPUD Pipeline.

Defines urban block-level typologies distinct from building typologies.
Each block typology prescribes: subdivision strategy, compatible building types,
typical zoning envelopes, and morphological character.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

BLOCK_TYPOLOGIES: Dict[str, Dict[str, Any]] = {
    "PerimeterBlock": {
        "description": "Closed perimeter block with central shared courtyard garden.",
        "subdivision_strategy": "perimeter",
        "typical_bcr": 0.45,
        "typical_far": 2.0,
        "typical_max_height": 18.0,
        "suggested_building_types": ["Courtyard", "Slab", "UShape"],
        "min_plot_count": 4,
        "max_plot_count": 12,
        "courtyard_ratio": 0.35,
        "street_frontage_continuous": True,
        "category": "Traditional",
    },
    "LinearBlock": {
        "description": "Linear row block aligned along a primary street axis with rhythmic plot subdivision.",
        "subdivision_strategy": "frontage",
        "typical_bcr": 0.40,
        "typical_far": 1.8,
        "typical_max_height": 15.0,
        "suggested_building_types": ["Slab", "LShape", "MultiBuildingBlock"],
        "min_plot_count": 3,
        "max_plot_count": 10,
        "courtyard_ratio": 0.10,
        "street_frontage_continuous": True,
        "category": "Linear",
    },
    "PavilionBlock": {
        "description": "Freestanding point towers distributed in open landscape with generous spacing.",
        "subdivision_strategy": "grid",
        "typical_bcr": 0.25,
        "typical_far": 2.5,
        "typical_max_height": 45.0,
        "suggested_building_types": ["Tower", "SteppedTower", "PodiumTower"],
        "min_plot_count": 2,
        "max_plot_count": 8,
        "courtyard_ratio": 0.0,
        "street_frontage_continuous": False,
        "category": "Modernist",
    },
    "OrganicBlock": {
        "description": "Irregular medieval-style organic fabric with varied plot sizes and non-orthogonal geometry.",
        "subdivision_strategy": "organic",
        "typical_bcr": 0.50,
        "typical_far": 1.5,
        "typical_max_height": 12.0,
        "suggested_building_types": ["MultiBuildingBlock", "LShape", "Slab"],
        "min_plot_count": 5,
        "max_plot_count": 20,
        "courtyard_ratio": 0.15,
        "street_frontage_continuous": False,
        "category": "Organic",
    },
    "HybridBlock": {
        "description": "Mixed composition: perimeter base with freestanding tower accents at corners or centre.",
        "subdivision_strategy": "hybrid",
        "typical_bcr": 0.40,
        "typical_far": 2.8,
        "typical_max_height": 36.0,
        "suggested_building_types": ["Courtyard", "Tower", "PodiumTower", "Slab"],
        "min_plot_count": 5,
        "max_plot_count": 15,
        "courtyard_ratio": 0.20,
        "street_frontage_continuous": True,
        "category": "Hybrid",
    },
}

STRATEGY_PARAM_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "frontage": {"target_frontage": 18.0, "min_lot_area": 250.0},
    "grid": {"target_width": 20.0, "target_depth": 30.0, "min_lot_area": 300.0},
    "perimeter": {"depth_ratio": 0.30, "min_lot_area": 200.0},
    "organic": {"min_area": 180.0, "randomness": 0.40, "target_plot_count": 8},
    "radial": {"num_sectors": 8, "inner_radius_ratio": 0.15, "min_lot_area": 200.0},
    "hybrid": {"perimeter_depth_ratio": 0.25, "interior_strategy": "grid", "interior_grid_width": 22.0},
}


def get_block_typology(name: str) -> Dict[str, Any]:
    """Retrieve full block typology spec by name. Falls back to PerimeterBlock."""
    return BLOCK_TYPOLOGIES.get(name, BLOCK_TYPOLOGIES["PerimeterBlock"])


def list_block_typologies() -> List[str]:
    """Return list of all available block typology names."""
    return list(BLOCK_TYPOLOGIES.keys())


def suggest_subdivision_strategy(block_typology_name: str) -> str:
    """Return the recommended subdivision strategy for a given block typology."""
    bt = get_block_typology(block_typology_name)
    return bt.get("subdivision_strategy", "frontage")


def suggest_building_typologies(block_typology_name: str) -> List[str]:
    """Return compatible building typologies for a given block typology."""
    bt = get_block_typology(block_typology_name)
    return bt.get("suggested_building_types", ["Tower", "Slab"])


def get_strategy_defaults(strategy: str) -> Dict[str, Any]:
    """Return default parameters for a subdivision strategy."""
    return STRATEGY_PARAM_DEFAULTS.get(strategy, STRATEGY_PARAM_DEFAULTS["frontage"])


def get_plot_count_range(block_typology_name: str) -> tuple:
    """Return (min, max) plot count for a block typology."""
    bt = get_block_typology(block_typology_name)
    return bt.get("min_plot_count", 3), bt.get("max_plot_count", 12)


def build_zoning_envelope(block_typology_name: str, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build a zoning envelope dict (max_bcr, max_far, max_height) from block typology defaults,
    overridden by any user-supplied values."""
    bt = get_block_typology(block_typology_name)
    envelope = {
        "max_bcr": bt.get("typical_bcr", 0.45),
        "max_far": bt.get("typical_far", 2.0),
        "max_height": bt.get("typical_max_height", 18.0),
    }
    if overrides:
        envelope.update(overrides)
    return envelope
