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


# ==========================================
# MULTI-STRATEGY SUBDIVISION ENGINE (PPUD)
# ==========================================


def subdivide_grid(
    ring: List[Dict[str, float]],
    target_width: float = 20.0,
    target_depth: float = 30.0,
    min_lot_area: float = 300.0,
) -> List[List[Dict[str, float]]]:
    """Subdivides a block into a regular grid of rectangular plots.

    Finds the dominant axis of the ring and creates rows × columns of roughly
    equal-sized rectangular sub-lots.
    """
    total_area = calculate_polygon_area(ring)
    if total_area < min_lot_area * 2.0 or len(ring) < 3:
        return [ring]

    cx, cy = calculate_ring_centroid(ring)

    # Compute bounding-box extents along dominant axes
    xs = [pt["x"] for pt in ring]
    ys = [pt["y"] for pt in ring]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)

    cols = max(1, int(width / target_width))
    rows = max(1, int(height / target_depth))

    if cols * rows <= 1:
        return [ring]

    col_w = width / cols
    row_h = height / rows

    x0 = min(xs)
    y0 = min(ys)

    sublots = []
    for r in range(rows):
        for c in range(cols):
            x1 = x0 + c * col_w
            y1 = y0 + r * row_h
            x2 = x1 + col_w
            y2 = y1 + row_h

            lot_ring = [
                {"x": x1, "y": y1},
                {"x": x2, "y": y1},
                {"x": x2, "y": y2},
                {"x": x1, "y": y2},
            ]
            if calculate_polygon_area(lot_ring) >= min_lot_area * 0.5:
                sublots.append(lot_ring)

    return sublots if sublots else [ring]


def subdivide_perimeter(
    ring: List[Dict[str, float]],
    depth_ratio: float = 0.30,
    min_lot_area: float = 200.0,
) -> List[List[Dict[str, float]]]:
    """Subdivides a block into perimeter plots wrapping a central courtyard.

    Each edge of the ring produces depth_ratio-depth plots facing outward,
    while the interior is left as a shared courtyard (not returned as a plot).
    """
    total_area = calculate_polygon_area(ring)
    if total_area < min_lot_area * 3.0 or len(ring) < 4:
        return [ring]

    # Calculate appropriate inset depth based on block size
    side_est = math.sqrt(total_area)
    inset_distance = depth_ratio * side_est * 0.45

    inset = offset_ring_inward(ring, inset_distance)
    inset_area = calculate_polygon_area(inset)
    if inset_area < min_lot_area * 0.5:
        # Fallback: use frontage strategy if inset would consume too much
        return subdivide_parcel_block(ring, target_frontage=18.0, min_lot_area=min_lot_area)

    n = len(ring)
    sublots = []

    for i in range(n):
        p1 = ring[i]
        p2 = ring[(i + 1) % n]
        q1 = inset[i]
        q2 = inset[(i + 1) % n]

        edge_len = math.hypot(p2["x"] - p1["x"], p2["y"] - p1["y"])
        num_splits = max(1, int(edge_len / 18.0))

        for s in range(num_splits):
            t0 = s / num_splits
            t1 = (s + 1) / num_splits

            # Outer edge points: p1 → p2
            rp1 = {"x": p1["x"] + t0 * (p2["x"] - p1["x"]), "y": p1["y"] + t0 * (p2["y"] - p1["y"])}
            rp2 = {"x": p1["x"] + t1 * (p2["x"] - p1["x"]), "y": p1["y"] + t1 * (p2["y"] - p1["y"])}

            # Inner edge points: q1 → q2 (same direction), ordered for CCW lot ring
            ip_near_p2 = {"x": q1["x"] + t1 * (q2["x"] - q1["x"]), "y": q1["y"] + t1 * (q2["y"] - q1["y"])}
            ip_near_p1 = {"x": q1["x"] + t0 * (q2["x"] - q1["x"]), "y": q1["y"] + t0 * (q2["y"] - q1["y"])}

            # CCW ring: outer_p1 → outer_p2 → inner_p2 → inner_p1
            lot_ring = [rp1, rp2, ip_near_p2, ip_near_p1]
            if calculate_polygon_area(lot_ring) >= min_lot_area * 0.3:
                sublots.append(lot_ring)

    return sublots if sublots else [ring]


def subdivide_organic(
    ring: List[Dict[str, float]],
    min_area: float = 180.0,
    randomness: float = 0.40,
    target_plot_count: int = 8,
) -> List[List[Dict[str, float]]]:
    """Subdivides a block into irregular organic plots using recursive splits
    with randomized split positions and varying frontage widths.

    Produces a medieval-style fabric with varied plot sizes and non-uniform boundaries.
    Uses a simplified recursive bisection that splits along varying axes.
    """
    total_area = calculate_polygon_area(ring)
    if total_area < min_area * 2.0 or len(ring) < 3:
        return [ring]

    # Deterministic LCG seeded from ring geometry (B311 compliant)
    cx, cy = calculate_ring_centroid(ring)
    _state = int(cx * 1000 + cy * 100 + total_area) & 0x7FFFFFFF
    def _lcg_random():
        nonlocal _state
        _state = (_state * 1103515245 + 12345) & 0x7FFFFFFF
        return _state / 0x7FFFFFFF

    def _recursive_split(poly_ring: List[Dict[str, float]], depth: int = 0) -> List[List[Dict[str, float]]]:
        area = calculate_polygon_area(poly_ring)
        if area < min_area * 1.6 or depth > 5:
            return [poly_ring]

        n = len(poly_ring)
        if n < 4:
            return [poly_ring]

        # Find the longest edge
        best_i, best_len = 0, -1.0
        for i in range(n):
            p1 = poly_ring[i]
            p2 = poly_ring[(i + 1) % n]
            d = math.hypot(p2["x"] - p1["x"], p2["y"] - p1["y"])
            if d > best_len:
                best_len = d
                best_i = i

        if best_len < 6.0:
            return [poly_ring]

        # Split position along the longest edge (with randomness)
        split_t = 0.3 + _lcg_random() * randomness  # 0.3–0.7 range
        p_a = poly_ring[best_i]
        p_b = poly_ring[(best_i + 1) % n]
        split_pt = {
            "x": p_a["x"] + split_t * (p_b["x"] - p_a["x"]),
            "y": p_a["y"] + split_t * (p_b["y"] - p_a["y"]),
        }

        # Find the opposite edge (the one closest to the split point's opposite)
        opposite_i = (best_i + n // 2) % n
        p_c = poly_ring[opposite_i]
        p_d = poly_ring[(opposite_i + 1) % n]

        # Target point on opposite edge (with independent randomness)
        opp_t = 0.3 + _lcg_random() * randomness
        opp_pt = {
            "x": p_c["x"] + opp_t * (p_d["x"] - p_c["x"]),
            "y": p_c["y"] + opp_t * (p_d["y"] - p_c["y"]),
        }

        # Build two child polygons split by the line (split_pt → opp_pt)
        left_ring = []
        right_ring = []
        crossed = False
        split_start_i = best_i
        split_end_i = opposite_i

        for i in range(n):
            pt = poly_ring[i]
            if i == split_start_i:
                left_ring.append(pt)
                left_ring.append(split_pt)
                right_ring.append(split_pt)
                crossed = True
            elif i == split_end_i:
                left_ring.append(opp_pt)
                right_ring.append(opp_pt)
                right_ring.append(pt)
                left_ring.append(pt)
                crossed = False
            else:
                if crossed:
                    right_ring.append(pt)
                else:
                    left_ring.append(pt)

        if len(left_ring) < 3 or len(right_ring) < 3:
            return [poly_ring]

        results = []
        results.extend(_recursive_split(left_ring, depth + 1))
        results.extend(_recursive_split(right_ring, depth + 1))
        return results

    sublots = _recursive_split(ring)
    valid = [s for s in sublots if calculate_polygon_area(s) >= min_area * 0.35]
    return valid if valid else [ring]


def subdivide_radial(
    ring: List[Dict[str, float]],
    num_sectors: int = 8,
    inner_radius_ratio: float = 0.15,
    min_lot_area: float = 200.0,
) -> List[List[Dict[str, float]]]:
    """Subdivides a block into radial (pie-slice) plots emanating from the centroid.

    Creates a small central plaza/courtyard (inner radius) with radiating plots.
    The outer radius is computed as the minimum distance from centroid to ring edges
    so that all plots stay within the block.
    """
    total_area = calculate_polygon_area(ring)
    if total_area < min_lot_area * 3.0 or len(ring) < 3:
        return [ring]

    cx, cy = calculate_ring_centroid(ring)

    # Compute outer radius as the minimum distance from centroid to any edge
    # so radial plots stay fully inside the block
    n = len(ring)
    outer_r = float("inf")
    for i in range(n):
        p1 = ring[i]
        p2 = ring[(i + 1) % n]
        # Distance from centroid to edge p1→p2
        edge_dx = p2["x"] - p1["x"]
        edge_dy = p2["y"] - p1["y"]
        edge_len_sq = edge_dx * edge_dx + edge_dy * edge_dy
        if edge_len_sq < 1e-9:
            dist = math.hypot(cx - p1["x"], cy - p1["y"])
        else:
            t = max(0.0, min(1.0, ((cx - p1["x"]) * edge_dx + (cy - p1["y"]) * edge_dy) / edge_len_sq))
            proj_x = p1["x"] + t * edge_dx
            proj_y = p1["y"] + t * edge_dy
            dist = math.hypot(cx - proj_x, cy - proj_y)
        outer_r = min(outer_r, dist)

    if outer_r <= 0 or outer_r == float("inf"):
        return [ring]

    inner_r = max(2.0, outer_r * inner_radius_ratio)

    angle_step = 2.0 * math.pi / num_sectors
    sublots = []
    for i in range(num_sectors):
        a0 = i * angle_step
        a1 = (i + 1) * angle_step

        p1 = {"x": cx + inner_r * math.cos(a0), "y": cy + inner_r * math.sin(a0)}
        p2 = {"x": cx + inner_r * math.cos(a1), "y": cy + inner_r * math.sin(a1)}
        p3 = {"x": cx + outer_r * math.cos(a1), "y": cy + outer_r * math.sin(a1)}
        p4 = {"x": cx + outer_r * math.cos(a0), "y": cy + outer_r * math.sin(a0)}

        lot_ring = [p1, p2, p3, p4]
        if calculate_polygon_area(lot_ring) >= min_lot_area * 0.4:
            sublots.append(lot_ring)

    return sublots if sublots else [ring]


def subdivide_hybrid(
    ring: List[Dict[str, float]],
    perimeter_depth_ratio: float = 0.25,
    interior_strategy: str = "grid",
    interior_grid_width: float = 22.0,
    min_lot_area: float = 200.0,
) -> List[List[Dict[str, float]]]:
    """Subdivides a block using a hybrid approach: perimeter plots along edges
    plus interior plots using a secondary strategy (grid or organic).

    Creates a rich, varied fabric — perimeter for street-facing continuity,
    interior for density or courtyard clusters.
    """
    total_area = calculate_polygon_area(ring)
    if total_area < min_lot_area * 4.0 or len(ring) < 4:
        return [ring]

    # Step 1: Extract perimeter plots
    side_est = math.sqrt(total_area)
    inset = offset_ring_inward(ring, perimeter_depth_ratio * side_est * 0.45)
    inset_area = calculate_polygon_area(inset)

    perimeter_plots = subdivide_perimeter(ring, perimeter_depth_ratio, min_lot_area)

    # Step 2: Subdivide interior using secondary strategy
    if inset_area >= min_lot_area * 1.5 and len(inset) >= 3:
        if interior_strategy == "grid":
            interior_plots = subdivide_grid(inset, interior_grid_width, interior_grid_width, min_lot_area)
        elif interior_strategy == "organic":
            interior_plots = subdivide_organic(inset, min_lot_area, randomness=0.30)
        else:
            interior_plots = [inset]
    else:
        interior_plots = []

    all_plots = perimeter_plots + interior_plots
    return all_plots if all_plots else [ring]


# ==========================================
# UNIFIED SUBDIVISION DISPATCHER
# ==========================================

SUBDIVISION_STRATEGIES = {
    "frontage": subdivide_parcel_block,
    "grid": subdivide_grid,
    "perimeter": subdivide_perimeter,
    "organic": subdivide_organic,
    "radial": subdivide_radial,
    "hybrid": subdivide_hybrid,
}


def subdivide_parcel_block_strategy(
    ring: List[Dict[str, float]],
    strategy: str = "frontage",
    **params: Any,
) -> List[List[Dict[str, float]]]:
    """Unified entry point for all subdivision strategies.

    Args:
        ring: Polygon ring as list of {"x": float, "y": float} dicts.
        strategy: One of "frontage", "grid", "perimeter", "organic", "radial", "hybrid".
        **params: Strategy-specific parameters (see STRATEGY_PARAM_DEFAULTS in block_typologies.py).

    Returns:
        List of sub-lot polygon rings.
    """
    strategy_fn = SUBDIVISION_STRATEGIES.get(strategy, subdivide_parcel_block)

    # Filter params to only those accepted by the strategy function
    import inspect
    try:
        sig = inspect.signature(strategy_fn)
        valid_params = {k: v for k, v in params.items() if k in sig.parameters}
    except (ValueError, TypeError):
        valid_params = params

    return strategy_fn(ring, **valid_params)
