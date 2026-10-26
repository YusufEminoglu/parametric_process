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
    sun_azimuth_deg: float = 180.0,
    bearing_to_caster_deg: float | None = None,
) -> float:
    """Solar obstruction (%) that a building of height ``h1`` casts on one of height ``h2``.

    With ``bearing_to_caster_deg`` (azimuth from the receiver to the caster,
    clockwise from north) the shadow is projected onto the line joining the
    two: a caster on the side away from the sun casts nothing. Without it the
    caster is assumed to stand on the sun side.
    """
    if distance_m <= 0:
        return 50.0

    shadow_length = h1 / math.tan(math.radians(max(10.0, sun_altitude_deg)))
    if bearing_to_caster_deg is None:
        azimuth_factor = max(0.2, math.cos(math.radians(abs(sun_azimuth_deg - 180.0))))
    else:
        azimuth_factor = math.cos(math.radians(bearing_to_caster_deg - sun_azimuth_deg))
        if azimuth_factor <= 0.0:
            return 0.0
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
            "district_pedestrian_comfort": 80.0,
            "district_runoff_retention_pct": 45.0,
            "district_planx_score": 75.0,
            "district_total_gfa_m2": 0.0
        }

    total_gfa = sum(float(b.get("metrics", {}).get("gfa", b.get("gfa", 400.0))) for b in building_list)
    total_footprint = sum(float(b.get("metrics", {}).get("footprint_area", b.get("footprint_area", 150.0))) for b in building_list)
    n_bldgs = len(building_list)

    # Check if centroid coordinates are available for explicit pairwise modeling
    has_coords = all("centroid_x" in b and "centroid_y" in b for b in building_list)

    if has_coords and n_bldgs >= 2:
        total_shadow_loss = 0.0
        total_wind_speed = 0.0
        total_comfort = 0.0
        pair_count = 0

        for i in range(n_bldgs):
            for j in range(i + 1, n_bldgs):
                b1 = building_list[i]
                b2 = building_list[j]
                h1 = float(b1.get("metrics", {}).get("height_m", b1.get("height_m", 12.0)))
                h2 = float(b2.get("metrics", {}).get("height_m", b2.get("height_m", 12.0)))

                dist = math.hypot(b2["centroid_x"] - b1["centroid_x"], b2["centroid_y"] - b1["centroid_y"])
                if dist <= 0:
                    dist = 10.0

                s_loss = calculate_mutual_solar_obstruction(h1, h2, dist)
                w_wake = calculate_canyon_wind_wake(h1, h2, dist)

                total_shadow_loss += s_loss
                total_wind_speed += w_wake["canyon_wind_speed_ms"]
                total_comfort += w_wake["pedestrian_comfort_score"]
                pair_count += 1

        shadow_loss = round(total_shadow_loss / max(1, pair_count), 1)
        canyon_wind = round(total_wind_speed / max(1, pair_count), 2)
        comfort_score = round(total_comfort / max(1, pair_count), 1)
    else:
        avg_height = sum(float(b.get("metrics", {}).get("height_m", b.get("height_m", 12.0))) for b in building_list) / max(1, n_bldgs)
        avg_gap = max(6.0, math.sqrt(site_area / max(1, n_bldgs)) - 15.0)
        shadow_loss = calculate_mutual_solar_obstruction(avg_height * 1.2, avg_height, avg_gap)
        wind_wake = calculate_canyon_wind_wake(avg_height, avg_height, avg_gap)
        canyon_wind = wind_wake["canyon_wind_speed_ms"]
        comfort_score = wind_wake["pedestrian_comfort_score"]

    district_bcr = total_footprint / max(1.0, site_area)
    runoff_retention = min(90.0, max(20.0, (1.0 - district_bcr) * 85.0))

    scores = [float(b.get("metrics", {}).get("planx_score", b.get("planx_score", 75.0))) for b in building_list]
    avg_planx = sum(scores) / max(1, len(scores))

    return {
        "district_avg_solar_shadow_loss_pct": shadow_loss,
        "district_canyon_wind_speed_ms": canyon_wind,
        "district_pedestrian_comfort": comfort_score,
        "district_runoff_retention_pct": round(runoff_retention, 1),
        "district_planx_score": round(avg_planx, 1),
        "district_total_gfa_m2": round(total_gfa, 1)
    }


def evaluate_building_coupling(
    buildings: List[Dict[str, float]],
    neighbours: Dict[int, List[tuple]] | None = None,
    sun_altitude_deg: float = 45.0,
    sun_azimuth_deg: float = 180.0,
    ambient_wind_speed: float = 3.5,
) -> List[Dict[str, float]]:
    """Per-building coupling: shadow received, canyon wind and comfort.

    ``buildings`` holds ``x``, ``y`` (centroid, metres) and ``height_m``.
    ``neighbours`` maps a building index to ``(other_index, gap_m)`` pairs,
    where the gap is the edge-to-edge distance; without it every pair is
    used with the centroid distance. Shadow from several casters combines as
    independent obstructions, ``1 - prod(1 - s_j)``, capped at 65 %. Canyon
    wind uses the nearest neighbour.
    """
    n = len(buildings)
    if neighbours is None:
        neighbours = {
            i: [(j, math.hypot(buildings[j]["x"] - buildings[i]["x"],
                               buildings[j]["y"] - buildings[i]["y"]))
                for j in range(n) if j != i]
            for i in range(n)
        }

    results = []
    for i in range(n):
        bi = buildings[i]
        hi = float(bi["height_m"])
        unshaded = 1.0
        nearest = None
        for j, gap in neighbours.get(i, []):
            if j == i:
                continue
            bj = buildings[j]
            bearing = math.degrees(math.atan2(bj["x"] - bi["x"], bj["y"] - bi["y"])) % 360.0
            loss = calculate_mutual_solar_obstruction(
                float(bj["height_m"]), hi, max(0.01, gap),
                sun_altitude_deg, sun_azimuth_deg, bearing_to_caster_deg=bearing)
            unshaded *= 1.0 - loss / 100.0
            if nearest is None or gap < nearest[1]:
                nearest = (j, gap)

        if nearest is None:
            wind = {"canyon_wind_speed_ms": round(ambient_wind_speed, 2),
                    "pedestrian_comfort_score": round(max(0.0, min(100.0, 100.0 - (ambient_wind_speed - 3.0) * 15.0)), 1)}
            gap_m = None
        else:
            wind = calculate_canyon_wind_wake(hi, float(buildings[nearest[0]]["height_m"]),
                                              nearest[1], ambient_wind_speed)
            gap_m = round(nearest[1], 2)

        results.append({
            "shadow_loss_pct": round(min(65.0, (1.0 - unshaded) * 100.0), 1),
            "canyon_wind_speed_ms": wind["canyon_wind_speed_ms"],
            "pedestrian_comfort_score": wind["pedestrian_comfort_score"],
            "nearest_gap_m": gap_m,
        })
    return results
