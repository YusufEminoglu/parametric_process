# -*- coding: utf-8 -*-
"""Generative Plan Note Codifier & Decoding Engine for Parametric Process.

Inspired by Mert Akay's METU M.Sc. Thesis: 'Algorithmic Design Control for Plot-Based Urbanism' (2019).
Translates Pareto-optimal 3D urban block morphologies into explicit, legal-compliant
generative plan notes for Turkish 1/1000 Implementation Plans (Uygulama İmar Plan Notları).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


def decode_solution_to_plan_notes(
    solution: Dict[str, Any],
    parcel_area: float = 1000.0,
    max_bcr: float = 0.45,
    max_far: float = 2.5,
    max_height: float = 18.0
) -> List[str]:
    """Decodes a Pareto-optimal phenotype into formal Turkish planning legal codes / plan notes."""
    g = solution.get("genotype", {})
    m = solution.get("metrics", {})

    floors = int(g.get("floors", 4))
    floor_h = float(g.get("floor_height", 3.0))
    setback = float(g.get("setback", 3.0))
    typology = g.get("typology", "Tower")
    usage = g.get("usage", "MixedUse")

    height_m = float(m.get("height_m", floors * floor_h))
    bcr = float(m.get("bcr", 0.40))
    far = float(m.get("far", 1.6))
    gfa = float(m.get("gfa", parcel_area * far))
    enclosure = float(m.get("enclosure_index", 60.0))
    canyon_hw = float(m.get("canyon_hw", 1.2))

    bvr = round((gfa * floor_h) / max(1.0, parcel_area * max_height), 3)

    notes = [
        f"1. Yapı yüksekliği en fazla Hmax = {height_m:.1f} m ({floors} kat) olarak uygulanacaktır.",
        f"2. Kat yüksekliği konut kullanımlarında h = {floor_h:.1f} m, zemin kat ticari alanlarda en az 3.50 m olacaktır.",
        f"3. Parsel üzerinde Emsal (KAKS) = {far:.2f}, Taban Alanı Katsayısı (TAKS) en fazla = {bcr:.2f} uygulanacaktır.",
        f"4. Ön ve yan bahçe mesafeleri en az {setback:.1f} m olarak bırakılacak, sokak cephesinde %{int(min(40, setback*10))} oranında ritmik girinti/çıkıntı (recession/protrusion) serbesttir.",
        f"5. İnşa Edilebilir Hacim Oranı (BVR - Buildable Volume Ratio) BVR = {bvr:.3f} değerini aşamaz.",
        f"6. Bina tipolojisi '{typology}' esaslarına uygun olarak inşa edilecek, zemin katta en az %{int(100*(1.0-bcr))}' oranında emsal harici sert/yeşil açık alan düzenlenecektir.",
    ]

    if typology == "Courtyard":
        notes.append("7. Yapı kütlesinin merkezinde en az 150 m² alanında kamuya veya bina sakinlerine açık avlu bahçesi bırakılacaktır.")
    elif typology == "SteppedTower":
        notes.append("7. Yapı yüksekliği boyunca her 4 katta bir en az 3.0 m teraslanma (stepback) yapılacaktır.")
    elif typology == "PodiumTower":
        notes.append("7. Zemin ve 1. normal kat podyum kütlesi olarak düzenlenecek, üst katlar kule kütlesi şeklinde çekmeli yapılacaktır.")

    if usage == "MixedUse":
        notes.append("8. Zemin kat tamamen ticari/sosyal donatı alanı olarak kullanılacak, üst katlarda konut fonksiyonuna yer verilecektir.")

    if canyon_hw > 1.5:
        notes.append(f"9. Sokak kanyonu H/W = {canyon_hw:.2f} oranına sahip olduğundan rüzgar koridoru ve doğal havalandırma boşlukları bırakılması zorunludur.")

    return notes


# ==========================================
# FORM-BASED CODE (FBC) EXPORT ENGINE
# ==========================================


def export_form_based_code(
    configured_plots: List[Dict[str, Any]],
    block_typology: str = "PerimeterBlock",
    block_area: float = 5000.0,
    max_bcr: float = 0.45,
    max_far: float = 2.0,
    max_height: float = 18.0,
) -> Dict[str, Any]:
    """Exports a structured JSON form-based zoning code from configured PPUD plots.

    Produces a machine-readable FBC document containing:
    - Regulating plan parameters (build-to line, max envelope, BVR)
    - Per-plot building envelope specifications
    - Street frontage requirements
    - Open space / courtyard mandates
    - Block-level typology rules

    The output format is compatible with the Form-Based Code Institute (FBCI)
    standard structure and can be used to generate regulating plan diagrams.
    """
    from .block_typologies import get_block_typology

    bt = get_block_typology(block_typology)

    # Per-plot envelope specs
    plot_specs = []
    for plot in configured_plots:
        genotype = plot.get("genotype", {})
        metrics = plot.get("metrics", {})

        bvr = 0.0
        if metrics.get("gfa", 0) > 0 and metrics.get("height_m", 0) > 0:
            bvr = round(
                (metrics["gfa"] * float(genotype.get("floor_height", 3.0)))
                / max(1.0, plot.get("area_m2", 1000.0) * max_height),
                3,
            )

        plot_spec = {
            "plot_id": plot.get("plot_id", "?"),
            "area_m2": plot.get("area_m2", 0),
            "frontage_width_m": plot.get("frontage_width_m", 0),
            "building_envelope": {
                "max_footprint_m2": round(
                    plot.get("area_m2", 1000.0) * float(genotype.get("bcr_allocated", max_bcr)), 1
                ),
                "max_height_m": metrics.get("height_m", 12.0),
                "max_floors": int(genotype.get("floors", 4)),
                "setback_front_m": float(genotype.get("setback", 3.0)),
                "setback_side_m": float(genotype.get("setback", 3.0)) * 0.75,
                "setback_rear_m": float(genotype.get("setback", 3.0)) * 0.5,
                "buildable_volume_ratio": bvr,
                "build_to_line": bt.get("street_frontage_continuous", True),
            },
            "building_type": {
                "typology": genotype.get("typology", "Tower"),
                "usage": genotype.get("usage", "MixedUse"),
                "roof_style": genotype.get("roof_style", "Flat"),
            },
            "performance_metrics": {
                "gfa_m2": metrics.get("gfa", 0),
                "far": metrics.get("far", 0),
                "bcr": metrics.get("bcr", 0),
                "open_space_m2": metrics.get("open_space_m2", 0),
                "carbon_kg": metrics.get("carbon_kg", 0),
                "planx_score": metrics.get("planx_score", 0),
            },
        }
        plot_specs.append(plot_spec)

    # Block-level regulating plan
    regulating_plan = {
        "block_typology": block_typology,
        "block_area_m2": round(block_area, 1),
        "plot_count": len(configured_plots),
        "courtyard_ratio": bt.get("courtyard_ratio", 0.0),
        "street_frontage_continuous": bt.get("street_frontage_continuous", True),
        "max_envelope": {
            "max_bcr": max_bcr,
            "max_far": max_far,
            "max_height_m": max_height,
        },
        "open_space_requirements": {
            "min_open_space_ratio": round(1.0 - max_bcr, 2),
            "courtyard_min_area_m2": round(block_area * bt.get("courtyard_ratio", 0.0), 1),
            "permeable_surface_ratio": 0.30,
        },
    }

    # Site-wide performance summary
    total_gfa = sum(ps["performance_metrics"]["gfa_m2"] for ps in plot_specs)
    total_carbon = sum(ps["performance_metrics"]["carbon_kg"] for ps in plot_specs)
    avg_planx = (
        sum(ps["performance_metrics"]["planx_score"] for ps in plot_specs) / max(1, len(plot_specs))
    )

    return {
        "fbc_version": "1.0",
        "fbc_standard": "Form-Based Code Institute (FBCI) compatible",
        "project_name": "PPUD Generated Zoning Code",
        "generated_by": "Parametric Process PPUD Pipeline",
        "regulating_plan": regulating_plan,
        "plot_specifications": plot_specs,
        "site_performance_summary": {
            "total_gfa_m2": round(total_gfa, 1),
            "total_carbon_kg": round(total_carbon, 1),
            "avg_planx_score": round(avg_planx, 1),
            "site_far": round(total_gfa / max(1.0, block_area), 2),
        },
        "development_phasing": {
            "phase_count": max(1, len(configured_plots) // 3),
            "plots_per_phase": 3,
            "climate_adaptive": True,
        },
    }


def export_fbc_json(
    form_based_code: Dict[str, Any],
    filepath: str,
) -> bool:
    """Writes a form-based code dict to a JSON file on disk.

    Returns True on success, False on any I/O error.
    """
    import json
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(form_based_code, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def generate_regulating_diagram_geojson(
    configured_plots: List[Dict[str, Any]],
    block_typology: str = "PerimeterBlock",
    max_bcr: float = 0.45,
    max_far: float = 2.0,
    max_height: float = 18.0,
) -> Dict[str, Any]:
    """Generates a GeoJSON FeatureCollection representing the regulating plan diagram.

    Each plot becomes a GeoJSON Polygon feature with form-based code properties.
    Compatible with QgsJsonExporter for direct QGIS layer creation.
    """
    fbc = export_form_based_code(
        configured_plots, block_typology,
        sum(p.get("area_m2", 0) for p in configured_plots),
        max_bcr, max_far, max_height,
    )

    features = []
    for spec in fbc["plot_specifications"]:
        plot = next((p for p in configured_plots if p.get("plot_id") == spec["plot_id"]), None)
        if not plot or "ring" not in plot:
            continue

        ring = plot["ring"]
        coords = [[[pt["x"], pt["y"]] for pt in ring]]
        # Close the ring
        if coords[0][0] != coords[0][-1]:
            coords[0].append(coords[0][0])

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": coords,
            },
            "properties": {
                "plot_id": spec["plot_id"],
                "area_m2": spec["area_m2"],
                "frontage_m": spec["frontage_width_m"],
                "typology": spec["building_type"]["typology"],
                "usage": spec["building_type"]["usage"],
                "max_floors": spec["building_envelope"]["max_floors"],
                "max_height_m": spec["building_envelope"]["max_height_m"],
                "setback_m": spec["building_envelope"]["setback_front_m"],
                "gfa_m2": spec["performance_metrics"]["gfa_m2"],
                "far": spec["performance_metrics"]["far"],
                "bcr": spec["performance_metrics"]["bcr"],
                "planx_score": spec["performance_metrics"]["planx_score"],
                "build_to_line": spec["building_envelope"]["build_to_line"],
                "block_typology": block_typology,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "description": f"PPUD Regulating Plan Diagram — {block_typology}",
            "fbc_version": "1.0",
            "max_bcr": max_bcr,
            "max_far": max_far,
            "max_height_m": max_height,
        },
    }
