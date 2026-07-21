# -*- coding: utf-8 -*-
"""Procedural Shape Grammar & Sub-Parcel Lot Splitting Engine for Parametric Process.

Implements CGA-like shape rules for block-to-lot subdivision, setback terracing,
courtyard allocation, and perimeter block morphology generation.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


def calculate_ring_centroid(ring: List[Dict[str, float]]) -> Tuple[float, float]:
    """Calculates geometric centroid of 2D polygon ring."""
    if not ring:
        return 0.0, 0.0
    cx = sum(pt["x"] for pt in ring) / len(ring)
    cy = sum(pt["y"] for pt in ring) / len(ring)
    return cx, cy


def calculate_polygon_area(ring: List[Dict[str, float]]) -> float:
    """Calculates area of 2D polygon using Shoelace formula."""
    n = len(ring)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += ring[i]["x"] * ring[j]["y"]
        area -= ring[j]["x"] * ring[i]["y"]
    return abs(area) / 2.0


def offset_ring_inward(ring: List[Dict[str, float]], distance: float) -> List[Dict[str, float]]:
    """Offsets a 2D polygon ring inward towards its centroid by distance."""
    n = len(ring)
    if n < 3 or distance <= 0:
        return [dict(pt) for pt in ring]

    cx, cy = calculate_ring_centroid(ring)
    inset_ring = []

    for pt in ring:
        dx = cx - pt["x"]
        dy = cy - pt["y"]
        length = math.hypot(dx, dy)
        if length <= distance:
            inset_ring.append({"x": cx, "y": cy})
        else:
            scale = (length - distance) / length
            inset_ring.append({"x": pt["x"] + dx * (1.0 - scale), "y": pt["y"] + dy * (1.0 - scale)})

    return inset_ring


def subdivide_parcel_block(
    ring: List[Dict[str, float]],
    target_frontage: float = 18.0,
    min_lot_area: float = 250.0
) -> List[List[Dict[str, float]]]:
    """Subdivides a large urban block ring into procedural sub-lots based on frontage width."""
    total_area = calculate_polygon_area(ring)
    if total_area < min_lot_area * 2.2 or len(ring) < 3:
        return [ring]

    max_len = -1.0
    best_edge_idx = 0
    n = len(ring)

    for i in range(n):
        p1 = ring[i]
        p2 = ring[(i + 1) % n]
        length = math.hypot(p2["x"] - p1["x"], p2["y"] - p1["y"])
        if length > max_len:
            max_len = length
            best_edge_idx = i

    num_splits = max(1, min(6, int(max_len / target_frontage)))
    if num_splits <= 1:
        return [ring]

    p1 = ring[best_edge_idx]
    p2 = ring[(best_edge_idx + 1) % n]
    cx, cy = calculate_ring_centroid(ring)

    sublots = []
    dx = (p2["x"] - p1["x"]) / num_splits
    dy = (p2["y"] - p1["y"]) / num_splits

    for i in range(num_splits):
        sp1 = {"x": p1["x"] + i * dx, "y": p1["y"] + i * dy}
        sp2 = {"x": p1["x"] + (i + 1) * dx, "y": p1["y"] + (i + 1) * dy}

        mid_x = (sp1["x"] + sp2["x"]) / 2.0
        mid_y = (sp1["y"] + sp2["y"]) / 2.0

        cp1 = {"x": sp2["x"] + (cx - mid_x) * 0.8, "y": sp2["y"] + (cy - mid_y) * 0.8}
        cp2 = {"x": sp1["x"] + (cx - mid_x) * 0.8, "y": sp1["y"] + (cy - mid_y) * 0.8}

        lot_ring = [sp1, sp2, cp1, cp2]
        if calculate_polygon_area(lot_ring) >= min_lot_area * 0.5:
            sublots.append(lot_ring)

    return sublots if sublots else [ring]


def generate_procedural_massing_spec(
    genotype: Dict[str, Any],
    parcel_area: float
) -> Dict[str, Any]:
    """Generates procedural shape grammar specs for 3D building massings."""
    typology = genotype.get("typology", "Tower")
    floors = int(genotype.get("floors", 4))
    floor_h = float(genotype.get("floor_height", 3.0))
    setback = float(genotype.get("setback", 3.0))

    height_m = floors * floor_h
    side = math.sqrt(max(10.0, parcel_area))
    eff_side = max(2.0, side - 2 * setback)

    if typology == "Courtyard":
        courtyard_ratio = 0.40
        footprint_m2 = (eff_side ** 2) * (1.0 - courtyard_ratio)
        courtyard_area_m2 = (eff_side ** 2) * courtyard_ratio
    elif typology == "SteppedTower":
        footprint_m2 = (eff_side ** 2) * 0.75
        courtyard_area_m2 = 0.0
    elif typology == "PodiumTower":
        podium_h = min(height_m, 2 * floor_h)
        footprint_m2 = (eff_side ** 2) * 0.85
        courtyard_area_m2 = 0.0
    else:
        footprint_m2 = (eff_side ** 2) * 0.70
        courtyard_area_m2 = 0.0

    return {
        "typology": typology,
        "height_m": round(height_m, 1),
        "footprint_m2": round(footprint_m2, 1),
        "courtyard_area_m2": round(courtyard_area_m2, 1),
        "stepback_levels": max(1, floors // 4) if typology == "SteppedTower" else 0,
        "is_courtyard": typology == "Courtyard",
    }
