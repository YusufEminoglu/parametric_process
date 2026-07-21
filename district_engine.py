# -*- coding: utf-8 -*-
"""Multi-Parcel District Environmental Coupling Engine for Parametric Process.

Simulates mutual solar shadowing, inter-building wind canyon wake acceleration,
and district-wide green infrastructure stormwater balancing across linked parcels.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


def calculate_mutual_solar_obstruction(
    h1: float,
    h2: float,
    distance_m: float,
    sun_altitude_deg: float = 45.0,
    sun_azimuth_deg: float = 180.0
) -> float:
    """Calculates directional 3D solar obstruction percentage cast by neighboring massing h1 onto h2."""
    if distance_m <= 0:
        return 50.0

    shadow_length = h1 / math.tan(math.radians(max(10.0, sun_altitude_deg)))
    # Directional azimuth projection factor (higher obstruction when sun aligns with inter-building axis)
    azimuth_factor = max(0.2, math.cos(math.radians(abs(sun_azimuth_deg - 180.0))))
    effective_shadow = shadow_length * azimuth_factor

    if effective_shadow <= distance_m:
        return 0.0

    overlap_m = effective_shadow - distance_m
    loss_pct = min(65.0, (overlap_m / max(1.0, h2)) * 38.0)
    return round(loss_pct, 1)


def calculate_canyon_wind_wake(
    h1: float,
    h2: float,
    gap_width_m: float,
    ambient_wind_speed: float = 3.5
) -> Dict[str, float]:
    """Simulates wind canyon wake acceleration and stagnation in narrow inter-building passages."""
    avg_h = (h1 + h2) / 2.0
    gap = max(2.0, gap_width_m)
    hw_ratio = avg_h / gap
    if hw_ratio > 1.5:
        accel_factor = min(2.2, 1.0 + (hw_ratio * 0.35))
    else:
        accel_factor = max(0.6, 1.0 - (0.2 / max(0.5, hw_ratio)))

    canyon_speed = round(ambient_wind_speed * accel_factor, 2)
    comfort_score = max(0.0, min(100.0, 100.0 - (canyon_speed - 3.0) * 15.0))

    return {
        "canyon_wind_speed_ms": canyon_speed,
        "accel_factor": round(accel_factor, 2),
        "pedestrian_comfort_score": round(comfort_score, 1)
    }


def evaluate_district_coupling(
    building_list: List[Dict[str, Any]],
    site_area: float = 5000.0
) -> Dict[str, float]:
    """Evaluates unified district-wide performance metrics for linked urban block massings."""
    if not building_list:
        return {
            "district_avg_solar_shadow_loss_pct": 0.0,
            "district_canyon_wind_speed_ms": 3.5,
            "district_runoff_retention_pct": 45.0,
            "district_planx_score": 75.0
        }

    total_gfa = sum(float(b.get("metrics", {}).get("gfa", 400.0)) for b in building_list)
    total_footprint = sum(float(b.get("metrics", {}).get("footprint_area", 150.0)) for b in building_list)
    avg_height = sum(float(b.get("metrics", {}).get("height_m", 12.0)) for b in building_list) / len(building_list)

    avg_gap = max(6.0, math.sqrt(site_area / max(1, len(building_list))) - 15.0)

    shadow_loss = calculate_mutual_solar_obstruction(avg_height * 1.2, avg_height, avg_gap)
    wind_wake = calculate_canyon_wind_wake(avg_height, avg_height, avg_gap)

    district_bcr = total_footprint / max(1.0, site_area)
    runoff_retention = min(90.0, max(20.0, (1.0 - district_bcr) * 85.0))

    scores = [float(b.get("metrics", {}).get("planx_score", 75.0)) for b in building_list]
    avg_planx = sum(scores) / len(scores)

    return {
        "district_avg_solar_shadow_loss_pct": shadow_loss,
        "district_canyon_wind_speed_ms": wind_wake["canyon_wind_speed_ms"],
        "district_pedestrian_comfort": wind_wake["pedestrian_comfort_score"],
        "district_runoff_retention_pct": round(runoff_retention, 1),
        "district_planx_score": round(avg_planx, 1),
        "district_total_gfa_m2": round(total_gfa, 1)
    }
