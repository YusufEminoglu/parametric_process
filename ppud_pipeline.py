# -*- coding: utf-8 -*-
"""PPUD (Parametric Plot-based Urban Design) Sequential Pipeline Engine.

Implements the three-stage PPUD framework from Mert Akay's METU MSc thesis
"Algorithmic Design Control for Plot-Based Urbanism" (2019) and the 2025
Urban Design International follow-up:

  Stage 1 — Plot Layout Generation (multi-strategy block subdivision)
  Stage 2 — Building Configuration (per-plot genotype assignment + evaluation)
  Stage 3 — Incremental Block Fabric Formation (piecemeal development with
            climate feedback loops)

All three stages are connected in a sequential, feedback-driven pipeline
that can be invoked headless (QGIS Processing) or interactively (web cockpit).
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

from .nsga2_engine import _LCG
from .block_typologies import (
    build_zoning_envelope,
    get_block_typology,
    get_strategy_defaults,
    suggest_building_typologies,
)
from .district_engine import (
    calculate_canyon_wind_wake,
    calculate_mutual_solar_obstruction,
)
from .morphology_engine import calculate_urban_morphology_suite
from .nsga2_engine import (
    create_random_genotype,
    evaluate_phenotype,
    mutate_genotype,
)
from .procedural_grammar import (
    calculate_polygon_area,
    calculate_ring_centroid,
    generate_procedural_massing_spec,
    subdivide_parcel_block_strategy,
)


# ==========================================
# PIPELINE DATA STRUCTURES
# ==========================================


def _make_plot(
    plot_id: int,
    ring: List[Dict[str, float]],
    parent_block_id: str = "",
) -> Dict[str, Any]:
    """Create a Plot data dict from a subdivision result ring."""
    area = calculate_polygon_area(ring)
    cx, cy = calculate_ring_centroid(ring)
    return {
        "plot_id": plot_id,
        "parent_block": parent_block_id,
        "ring": ring,
        "area_m2": round(area, 1),
        "centroid_x": round(cx, 1),
        "centroid_y": round(cy, 1),
        "frontage_width_m": _estimate_frontage(ring),
    }


def _estimate_frontage(ring: List[Dict[str, float]]) -> float:
    """Estimate the frontage width as the minimum edge length (closest to street)."""
    if len(ring) < 3:
        return 12.0
    n = len(ring)
    edge_lengths = []
    for i in range(n):
        p1 = ring[i]
        p2 = ring[(i + 1) % n]
        edge_lengths.append(math.hypot(p2["x"] - p1["x"], p2["y"] - p1["y"]))
    edge_lengths.sort()
    # Return the second-smallest edge (smallest might be an artifact)
    return round(edge_lengths[1] if len(edge_lengths) > 1 else edge_lengths[0], 1)


def _make_configured_plot(
    plot: Dict[str, Any],
    genotype: Dict[str, Any],
    metrics: Dict[str, float],
    massing_spec: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a ConfiguredPlot dict with assigned building genotype and evaluated metrics."""
    return {
        **plot,
        "genotype": genotype,
        "metrics": metrics,
        "massing_spec": massing_spec,
    }


def _make_fabric_step(
    step: int,
    developed_plot_ids: List[int],
    all_plots: List[Dict[str, Any]],
    climate_metrics: Dict[str, float],
) -> Dict[str, Any]:
    """Create a fabric history step dict."""
    from collections import Counter

    typologies = [p.get("genotype", {}).get("typology", "Tower") for p in all_plots if p.get("genotype")]
    counts = Counter(typologies)
    total = len(typologies) or 1
    shannon = 0.0
    for count in counts.values():
        p_val = count / total
        if p_val > 0:
            shannon -= p_val * math.log(p_val)

    avg_canyon_hw = 0.0
    canyon_count = 0
    for p in all_plots:
        m = p.get("metrics", {})
        if "street_canyon_hw" in m:
            avg_canyon_hw += m["street_canyon_hw"]
            canyon_count += 1
    if canyon_count > 0:
        avg_canyon_hw /= canyon_count

    total_carbon = sum(p.get("metrics", {}).get("carbon_kg", 0) for p in all_plots if p.get("metrics"))
    total_gfa = sum(p.get("metrics", {}).get("gfa", 0) for p in all_plots if p.get("metrics"))

    return {
        "step": step,
        "developed_plot_count": len(developed_plot_ids),
        "developed_plot_ids": list(developed_plot_ids),
        "typology_diversity_shannon": round(shannon, 4),
        "avg_canyon_hw": round(avg_canyon_hw, 2),
        "cumulative_carbon_kg": round(total_carbon, 1),
        "cumulative_gfa_m2": round(total_gfa, 1),
        "climate_metrics": climate_metrics,
    }


# ==========================================
# PPUD PIPELINE ORCHESTRATOR
# ==========================================


class PpudPipeline:
    """Three-stage Parametric Plot-based Urban Design pipeline orchestrator.

    Usage:
        pipeline = PpudPipeline()
        result = pipeline.run_full_pipeline(block_ring, {
            "strategy": "perimeter",
            "block_typology": "PerimeterBlock",
            "max_bcr": 0.45,
            "max_far": 2.0,
            "max_height": 18.0,
            "incremental_steps": 5,
            "climate_feedback": True,
            "sim_params": {"wind_deg": 225, "wind_speed": 4.5, "latitude": 38.4},
        })
    """

    def __init__(self, seed: int | None = None):
        self._rng = _LCG(seed) if seed is not None else _LCG()

    # ----- Stage 1: Plot Layout Generation -----

    def stage1_plot_layout(
        self,
        block_ring: List[Dict[str, float]],
        strategy: str = "frontage",
        block_typology_name: str = "PerimeterBlock",
        strategy_params: Dict[str, Any] | None = None,
        parent_block_id: str = "block_1",
    ) -> List[Dict[str, Any]]:
        """Stage 1: Subdivide a block into plots using the chosen strategy.

        Args:
            block_ring: Polygon ring of the parent block.
            strategy: Subdivision strategy name.
            block_typology_name: Block typology (used for plot count constraints).
            strategy_params: Override default strategy parameters.
            parent_block_id: Identifier for the parent block.

        Returns:
            List of Plot dicts with ring, area, centroid, and frontage_width.
        """
        block_area = calculate_polygon_area(block_ring)
        if block_area < 100.0:
            return [_make_plot(1, block_ring, parent_block_id)]

        # Merge default strategy params with overrides
        defaults = get_strategy_defaults(strategy)
        if strategy_params:
            defaults.update(strategy_params)

        # Subdivide
        sub_rings = subdivide_parcel_block_strategy(block_ring, strategy, **defaults)

        # Enforce plot count constraints from block typology
        bt = get_block_typology(block_typology_name)
        min_plots = bt.get("min_plot_count", 3)
        max_plots = bt.get("max_plot_count", 12)

        if len(sub_rings) < min_plots and strategy != "frontage":
            # Fallback: use frontage strategy to hit min plot count
            fb_defaults = get_strategy_defaults("frontage")
            fb_defaults["target_frontage"] = max(8.0, math.sqrt(block_area) / min_plots)
            sub_rings = subdivide_parcel_block_strategy(block_ring, "frontage", **fb_defaults)

        # Trim to max if needed
        if len(sub_rings) > max_plots:
            # Keep largest plots by area
            sized = [(calculate_polygon_area(r), r) for r in sub_rings]
            sized.sort(key=lambda x: x[0], reverse=True)
            sub_rings = [r for _, r in sized[:max_plots]]

        plots = []
        for idx, ring in enumerate(sub_rings, start=1):
            plot = _make_plot(idx, ring, parent_block_id)
            if plot["area_m2"] >= 50.0:  # Minimum viable plot area
                plots.append(plot)

        return plots if plots else [_make_plot(1, block_ring, parent_block_id)]

    # ----- Stage 2: Building Configuration -----

    def stage2_building_config(
        self,
        plots: List[Dict[str, Any]],
        block_typology_name: str = "PerimeterBlock",
        zoning_overrides: Dict[str, Any] | None = None,
        sim_params: Dict[str, Any] | None = None,
        optimization_rounds: int = 3,
    ) -> List[Dict[str, Any]]:
        """Stage 2: Assign building genotypes to each plot and evaluate performance.

        For each plot:
        1. Select compatible building typologies from block typology
        2. Generate candidate genotypes
        3. Evaluate phenotypes against zoning + physics
        4. Select the best genotype (highest planx_score within constraints)

        Args:
            plots: List of Plot dicts from stage 1.
            block_typology_name: Block typology for building type suggestions.
            zoning_overrides: Override zoning envelope (max_bcr, max_far, max_height).
            sim_params: Physics simulation parameters (wind, latitude, costs).
            optimization_rounds: Number of candidate genotypes to try per plot.

        Returns:
            List of ConfiguredPlot dicts with genotype, metrics, and massing_spec.
        """
        zoning = build_zoning_envelope(block_typology_name, zoning_overrides)
        compatible_types = suggest_building_typologies(block_typology_name)

        configured = []
        for plot in plots:
            best_genotype = None
            best_metrics = None
            best_score = -1.0

            for _ in range(optimization_rounds):
                # Generate a candidate genotype biased toward compatible types
                genotype = create_random_genotype()
                genotype["typology"] = self._rng.choice(compatible_types)

                # Evaluate
                metrics = evaluate_phenotype(
                    genotype,
                    parcel_area=plot["area_m2"],
                    max_bcr=zoning["max_bcr"],
                    max_far=zoning["max_far"],
                    max_height=zoning["max_height"],
                    sim_params=sim_params,
                )

                # Score: prefer feasible (no penalty) and high planx_score
                penalty = metrics.get("constraint_penalty", 0)
                if penalty == 0 and metrics.get("planx_score", 0) > best_score:
                    best_score = metrics["planx_score"]
                    best_genotype = dict(genotype)
                    best_metrics = dict(metrics)

            # If all candidates are infeasible, pick the one with lowest penalty
            if best_genotype is None:
                best_genotype = create_random_genotype()
                best_genotype["typology"] = compatible_types[0]
                best_metrics = evaluate_phenotype(
                    best_genotype,
                    parcel_area=plot["area_m2"],
                    max_bcr=zoning["max_bcr"],
                    max_far=zoning["max_far"],
                    max_height=zoning["max_height"],
                    sim_params=sim_params,
                )

            massing = generate_procedural_massing_spec(best_genotype, plot["area_m2"])
            cp = _make_configured_plot(plot, best_genotype, best_metrics, massing)
            configured.append(cp)

        return configured

    # ----- Stage 3: Incremental Block Fabric Formation -----

    def stage3_incremental_fabric(
        self,
        configured_plots: List[Dict[str, Any]],
        steps: int = 5,
        climate_feedback: bool = True,
        sim_params: Dict[str, Any] | None = None,
        max_bcr: float = 0.45,
        max_far: float = 2.5,
        max_height: float = 18.0,
    ) -> Dict[str, Any]:
        """Stage 3: Simulate piecemeal urban development with environmental feedback.

        Plots are developed one at a time in randomized order. After each step,
        mutual solar shadowing and wind canyon effects are recalculated across
        already-developed neighboring plots.

        If climate_feedback is enabled, plots developed later may have their
        genotypes adjusted in response to cumulative shadow/wind impacts from
        earlier development.

        Args:
            configured_plots: List of ConfiguredPlot dicts from stage 2.
            steps: Number of incremental development steps (plots per step).
            climate_feedback: If True, re-optimize later plots based on neighbor impacts.
            sim_params: Physics simulation parameters.
            max_bcr, max_far, max_height: Zoning constraints.

        Returns:
            Dict with fabric_history (list of per-step snapshots) and final plots.
        """
        n_plots = len(configured_plots)
        if n_plots == 0:
            return {"fabric_history": [], "final_plots": []}

        # Randomize development order
        dev_order = list(range(n_plots))
        # Fisher-Yates shuffle using LCG
        for i in range(len(dev_order) - 1, 0, -1):
            j = int(self._rng.random() * (i + 1))
            dev_order[i], dev_order[j] = dev_order[j], dev_order[i]

        developed_ids: List[int] = []
        fabric_history: List[Dict[str, Any]] = []

        # Apply phenotypes to all plots (initially undeveloped = vacant lot)
        for p in configured_plots:
            if "genotype" not in p or not p.get("genotype"):
                p["genotype"] = {"setback": 3.0, "floors": 0, "typology": "Vacant",
                                 "usage": "Park", "roof_style": "Flat",
                                 "scale_x": 1.0, "scale_y": 1.0, "floor_height": 3.0}
            if "metrics" not in p or not p.get("metrics"):
                p["metrics"] = {"height_m": 0, "gfa": 0, "footprint_area": 0,
                                "planx_score": 50.0, "carbon_kg": 0}

        # Develop plots incrementally
        for step in range(steps):
            plots_this_step = min(max(1, n_plots // steps), n_plots - len(developed_ids))
            if plots_this_step <= 0:
                break

            new_developments = []
            for _ in range(plots_this_step):
                for idx in dev_order:
                    if idx not in developed_ids:
                        developed_ids.append(idx)
                        new_developments.append(idx)
                        break

            # Climate feedback: re-evaluate mutual impacts among developed plots
            climate_metrics: Dict[str, float] = {"avg_shadow_loss_pct": 0.0, "avg_canyon_wind_ms": 3.5}
            if climate_feedback and len(developed_ids) >= 2:
                climate_metrics = self._compute_mutual_impacts(
                    [configured_plots[i] for i in developed_ids],
                    sim_params,
                )

                # Re-optimize newly developed plots under cumulative shadow/wind
                for idx in new_developments:
                    if climate_metrics["avg_shadow_loss_pct"] > 15.0:
                        self._adapt_to_shadow(configured_plots[idx], climate_metrics,
                                              max_bcr, max_far, max_height, sim_params)
                    if climate_metrics.get("avg_canyon_wind_ms", 3.5) > 6.0:
                        self._adapt_to_wind(configured_plots[idx], climate_metrics,
                                            max_bcr, max_far, max_height, sim_params)

            # Record fabric state
            step_data = _make_fabric_step(
                step + 1, developed_ids, configured_plots, climate_metrics
            )
            fabric_history.append(step_data)

        return {
            "fabric_history": fabric_history,
            "final_plots": configured_plots,
            "development_order": dev_order,
        }

    def _compute_mutual_impacts(
        self,
        developed: List[Dict[str, Any]],
        sim_params: Dict[str, Any] | None = None,
    ) -> Dict[str, float]:
        """Compute mutual solar shadowing and wind wake among developed plots."""
        sim_params = sim_params or {}
        total_shadow_loss = 0.0
        total_wind_speed = 0.0
        pair_count = 0

        for i in range(len(developed)):
            for j in range(i + 1, len(developed)):
                p1 = developed[i]
                p2 = developed[j]

                h1 = float(p1.get("metrics", {}).get("height_m", 12.0))
                h2 = float(p2.get("metrics", {}).get("height_m", 12.0))

                # Estimate distance between plot centroids
                cx1 = p1.get("centroid_x", 0)
                cy1 = p1.get("centroid_y", 0)
                cx2 = p2.get("centroid_x", 0)
                cy2 = p2.get("centroid_y", 0)
                distance = math.hypot(cx2 - cx1, cy2 - cy1)
                if distance <= 0:
                    distance = 10.0

                sun_alt = float(sim_params.get("sun_altitude", 45.0))
                sun_az = float(sim_params.get("sun_azimuth", 180.0))

                shadow_loss = calculate_mutual_solar_obstruction(h1, h2, distance, sun_alt, sun_az)
                total_shadow_loss += shadow_loss

                wind = calculate_canyon_wind_wake(h1, h2, distance,
                                                  float(sim_params.get("wind_speed", 4.5)))
                total_wind_speed += wind.get("canyon_wind_speed_ms", 3.5)

                pair_count += 1

        if pair_count == 0:
            return {"avg_shadow_loss_pct": 0.0, "avg_canyon_wind_ms": 3.5}

        return {
            "avg_shadow_loss_pct": round(total_shadow_loss / pair_count, 1),
            "avg_canyon_wind_ms": round(total_wind_speed / pair_count, 2),
        }

    def _adapt_to_shadow(
        self,
        plot: Dict[str, Any],
        climate: Dict[str, float],
        max_bcr: float,
        max_far: float,
        max_height: float,
        sim_params: Dict[str, Any] | None = None,
    ) -> None:
        """Adjust plot genotype to compensate for high shadow loss from neighbors."""
        genotype = plot.get("genotype", {})
        shadow_loss = climate.get("avg_shadow_loss_pct", 0)

        if shadow_loss > 30.0:
            # Severe shadowing: reduce height, increase setback
            genotype["floors"] = max(1, int(genotype.get("floors", 4)) - 2)
            genotype["setback"] = min(12.0, float(genotype.get("setback", 3.0)) + 3.0)
        elif shadow_loss > 15.0:
            # Moderate shadowing: slight adjustment
            genotype["floors"] = max(1, int(genotype.get("floors", 4)) - 1)
            genotype["setback"] = min(10.0, float(genotype.get("setback", 3.0)) + 1.5)

        # Re-evaluate
        metrics = evaluate_phenotype(
            genotype,
            parcel_area=plot.get("area_m2", 1000.0),
            max_bcr=max_bcr,
            max_far=max_far,
            max_height=max_height,
            sim_params=sim_params,
        )
        plot["genotype"] = genotype
        plot["metrics"] = metrics

    def _adapt_to_wind(
        self,
        plot: Dict[str, Any],
        climate: Dict[str, float],
        max_bcr: float,
        max_far: float,
        max_height: float,
        sim_params: Dict[str, Any] | None = None,
    ) -> None:
        """Adjust plot genotype to mitigate high wind canyon speeds."""
        genotype = plot.get("genotype", {})
        wind_speed = climate.get("avg_canyon_wind_ms", 3.5)

        if wind_speed > 8.0:
            # Strong canyon wind: increase porosity, switch to stepped/tower
            current = genotype.get("typology", "Tower")
            if current in ["Slab", "Courtyard"]:
                genotype["typology"] = "SteppedTower"
            genotype["setback"] = min(14.0, float(genotype.get("setback", 3.0)) + 2.0)
            genotype["scale_x"] = max(0.5, float(genotype.get("scale_x", 1.0)) - 0.2)
        elif wind_speed > 6.0:
            genotype["setback"] = min(12.0, float(genotype.get("setback", 3.0)) + 1.0)

        metrics = evaluate_phenotype(
            genotype,
            parcel_area=plot.get("area_m2", 1000.0),
            max_bcr=max_bcr,
            max_far=max_far,
            max_height=max_height,
            sim_params=sim_params,
        )
        plot["genotype"] = genotype
        plot["metrics"] = metrics

    # ----- Full Pipeline -----

    def run_full_pipeline(
        self,
        block_ring: List[Dict[str, float]],
        config: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Run the complete three-stage PPUD pipeline.

        Args:
            block_ring: Polygon ring of the parent urban block.
            config: Pipeline configuration dict with keys:
                - strategy (str): Subdivision strategy name.
                - block_typology (str): Block typology name.
                - max_bcr, max_far, max_height (float): Zoning envelope.
                - incremental_steps (int): Number of fabric development steps.
                - climate_feedback (bool): Enable climate feedback in stage 3.
                - optimization_rounds (int): Genotype candidates per plot in stage 2.
                - sim_params (dict): Physics simulation parameters.
                - parent_block_id (str): Identifier for the parent block.

        Returns:
            PpudResult dict with keys:
                - stage1_plots: List of Plot dicts.
                - stage2_configured: List of ConfiguredPlot dicts.
                - stage3_fabric: Dict with fabric_history and final_plots.
                - summary: Dict with key metrics across all stages.
                - elapsed_seconds: Total pipeline runtime.
        """
        config = config or {}
        start_time = time.time()

        strategy = config.get("strategy", "frontage")
        block_typology_name = config.get("block_typology", "PerimeterBlock")
        max_bcr = float(config.get("max_bcr", 0.45))
        max_far = float(config.get("max_far", 2.0))
        max_height = float(config.get("max_height", 18.0))
        incremental_steps = int(config.get("incremental_steps", 5))
        climate_feedback = bool(config.get("climate_feedback", True))
        optimization_rounds = int(config.get("optimization_rounds", 3))
        sim_params = config.get("sim_params", {})
        parent_block_id = str(config.get("parent_block_id", "block_1"))
        strategy_params = config.get("strategy_params", None)

        # Stage 1: Plot Layout
        stage1_plots = self.stage1_plot_layout(
            block_ring,
            strategy=strategy,
            block_typology_name=block_typology_name,
            strategy_params=strategy_params,
            parent_block_id=parent_block_id,
        )

        # Stage 2: Building Configuration
        stage2_configured = self.stage2_building_config(
            stage1_plots,
            block_typology_name=block_typology_name,
            zoning_overrides={"max_bcr": max_bcr, "max_far": max_far, "max_height": max_height},
            sim_params=sim_params,
            optimization_rounds=optimization_rounds,
        )

        # Stage 3: Incremental Fabric Formation
        stage3_result = self.stage3_incremental_fabric(
            stage2_configured,
            steps=incremental_steps,
            climate_feedback=climate_feedback,
            sim_params=sim_params,
            max_bcr=max_bcr,
            max_far=max_far,
            max_height=max_height,
        )

        elapsed = round(time.time() - start_time, 2)

        # Build summary
        plot_count = len(stage1_plots)
        total_gfa = sum(p.get("metrics", {}).get("gfa", 0) for p in stage2_configured)
        total_area = sum(p.get("area_m2", 0) for p in stage1_plots)
        site_far = round(total_gfa / max(1.0, total_area), 2)
        site_bcr = round(
            sum(p.get("metrics", {}).get("footprint_area", 0) for p in stage2_configured)
            / max(1.0, total_area), 3
        )
        avg_planx = (
            sum(p.get("metrics", {}).get("planx_score", 0) for p in stage2_configured) / max(1, plot_count)
        )

        final_fabric = stage3_result.get("fabric_history", [])
        final_diversity = final_fabric[-1]["typology_diversity_shannon"] if final_fabric else 0.0
        final_carbon = final_fabric[-1]["cumulative_carbon_kg"] if final_fabric else 0.0

        return {
            "stage1_plots": stage1_plots,
            "stage2_configured": stage2_configured,
            "stage3_fabric": stage3_result,
            "summary": {
                "plot_count": plot_count,
                "total_area_m2": round(total_area, 1),
                "total_gfa_m2": round(total_gfa, 1),
                "site_far": site_far,
                "site_bcr": site_bcr,
                "avg_planx_score": round(avg_planx, 1),
                "final_typology_diversity": final_diversity,
                "final_cumulative_carbon_kg": round(final_carbon, 1),
                "strategy_used": strategy,
                "block_typology": block_typology_name,
                "development_steps": len(final_fabric),
            },
            "elapsed_seconds": elapsed,
        }


# ==========================================
# CONVENIENCE FUNCTION
# ==========================================


def run_ppud_pipeline(
    block_ring: List[Dict[str, float]],
    strategy: str = "perimeter",
    block_typology: str = "PerimeterBlock",
    max_bcr: float = 0.45,
    max_far: float = 2.0,
    max_height: float = 18.0,
    incremental_steps: int = 5,
    climate_feedback: bool = True,
    sim_params: Dict[str, Any] | None = None,
    seed: int | None = None,
) -> Dict[str, Any]:
    """Convenience function to run the full PPUD pipeline with keyword arguments.

    This is the primary public API — call this from Processing algorithms,
    API endpoints, or test scripts.
    """
    pipeline = PpudPipeline(seed=seed)
    return pipeline.run_full_pipeline(block_ring, {
        "strategy": strategy,
        "block_typology": block_typology,
        "max_bcr": max_bcr,
        "max_far": max_far,
        "max_height": max_height,
        "incremental_steps": incremental_steps,
        "climate_feedback": climate_feedback,
        "sim_params": sim_params or {},
    })
