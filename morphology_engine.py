# -*- coding: utf-8 -*-
"""Advanced Urban Morphology & Topological Connectivity Engine for Parametric Process.

Simulates street canyon ratios (H/W), Sky View Factor (SVF), Street Enclosure Index,
Building Surface-to-Volume Compactness (SA/V), and Shannon Entropy Typological Diversity.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List


def calculate_canyon_hw(height_m: float, street_width: float = 12.0) -> float:
    """Calculates street canyon height-to-width ratio (H/W)."""
    return round(height_m / max(1.0, street_width), 2)


def calculate_enclosure_index(height_m: float, setback: float = 3.0) -> float:
    """Calculates street enclosure index (0-100: higher means more enclosed urban canyon)."""
    effective_street_width = max(4.0, setback * 2.0 + 6.0)
    hw = height_m / effective_street_width
    enclosure = min(100.0, max(0.0, hw * 45.0))
    return round(enclosure, 1)


def calculate_compactness_sav(footprint_area: float, height_m: float, floors: int = 4) -> float:
    """Calculates building Surface Area to Volume ratio (SA/V). Lower is more energy compact."""
    if footprint_area <= 0 or height_m <= 0:
        return 0.0
    side = math.sqrt(footprint_area)
    perimeter = 4.0 * side
    facade_area = perimeter * height_m
    roof_area = footprint_area
    total_surface = facade_area + (2.0 * roof_area)
    volume = footprint_area * height_m
    sav_ratio = total_surface / max(1.0, volume)
    return round(sav_ratio, 3)


def calculate_shannon_entropy(typologies: List[str]) -> float:
    """Calculates Shannon Entropy diversity index across building typologies in a district."""
    if not typologies:
        return 0.0
    counts = Counter(typologies)
    total = len(typologies)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log(p)
    return round(entropy, 3)


def calculate_urban_morphology_suite(
    genotype: Dict[str, Any],
    parcel_area: float,
    max_bcr: float = 0.45,
    max_far: float = 2.5,
    max_height: float = 18.0
) -> Dict[str, float]:
    """Calculates comprehensive morphological suite for a single building / lot."""
    floors = int(genotype.get("floors", 4))
    floor_h = float(genotype.get("floor_height", 3.0))
    setback = float(genotype.get("setback", 3.0))
    typology = genotype.get("typology", "Tower")

    height_m = floors * floor_h
    side = math.sqrt(max(10.0, parcel_area))
    eff_side = max(2.0, side - 2 * setback)
    footprint_area = min(parcel_area * 0.90, eff_side ** 2 * 0.75)
    gfa = footprint_area * floors

    far = gfa / max(1.0, parcel_area)
    bcr = footprint_area / max(1.0, parcel_area)
    open_space = max(0.0, parcel_area - footprint_area)
    osr = open_space / max(1.0, parcel_area)

    hw = calculate_canyon_hw(height_m)
    enclosure = calculate_enclosure_index(height_m, setback)
    sav = calculate_compactness_sav(footprint_area, height_m, floors)
    svf = round(min(1.0, max(0.12, 1.0 - (hw * 0.24) + (osr * 0.32))), 2)

    return {
        "canyon_hw": hw,
        "enclosure_index": enclosure,
        "compactness_sav": sav,
        "sky_view_factor": svf,
        "far": round(far, 2),
        "bcr": round(bcr, 3),
        "open_space_ratio": round(osr, 3),
        "height_m": round(height_m, 1),
    }
