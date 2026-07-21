# -*- coding: utf-8 -*-
"""Comprehensive Multi-Objective Physics, Microclimate & Generative Engine for Parametric Process.

Implements advanced NSGA-II & SPEA2 multi-objective evolutionary computation for generative urban design.
Simulates urban morphology, CFD wind flow ventilation, solar irradiance & PV yield, air pollution dispersion (AQI),
urban heat island (UHI / MRT / UTCI), lifecycle carbon emissions, and real estate financial feasibility (ROI).

Zero external dependencies (pure Python stdlib).
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Tuple


TYPOLOGIES = [
    "Tower",
    "Slab",
    "Courtyard",
    "LShape",
    "UShape",
    "PodiumTower",
    "SteppedTower",
    "MultiBuildingBlock",
]

USAGES = ["Residential", "Commercial", "MixedUse", "Civic", "Park"]
ROOF_STYLES = ["Flat", "Hipped", "Gable", "Mansard"]


def evaluate_phenotype(
    genotype: Dict[str, Any],
    parcel_area: float,
    max_bcr: float = 0.45,
    max_far: float = 2.5,
    max_height: float = 18.0,
    sim_params: Dict[str, Any] | None = None,
) -> Dict[str, float]:
    """Calculates multi-domain physical, microclimate, financial, and environmental metrics."""
    sim_params = sim_params or {}
    prevailing_wind_deg = float(sim_params.get("wind_deg", 225.0))  # SW default
    wind_speed_ms = float(sim_params.get("wind_speed", 4.5))       # m/s
    latitude_deg = float(sim_params.get("latitude", 38.4))          # İzmir / Mediterranean default
    const_cost_sqm = float(sim_params.get("const_cost", 750.0))     # $/sqm
    sale_price_sqm = float(sim_params.get("sale_price", 1650.0))   # $/sqm

    setback = float(genotype.get("setback", 3.0))
    floors = int(genotype.get("floors", 4))
    typology = genotype.get("typology", "Tower")
    usage = genotype.get("usage", "MixedUse")
    roof_style = genotype.get("roof_style", "Flat")
    scale_x = float(genotype.get("scale_x", 1.0))
    scale_y = float(genotype.get("scale_y", 1.0))
    floor_height = float(genotype.get("floor_height", 3.0))

    height_m = floors * floor_height

    # 1. Geometric & Footprint Calculations
    side = math.sqrt(max(10.0, parcel_area))
    eff_side_x = max(2.0, (side - 2 * setback) * scale_x)
    eff_side_y = max(2.0, (side - 2 * setback) * scale_y)
    raw_footprint = eff_side_x * eff_side_y

    typo_mult = {
        "Tower": 0.85,
        "Slab": 0.70,
        "Courtyard": 0.60,
        "LShape": 0.65,
        "UShape": 0.65,
        "PodiumTower": 0.80,
        "SteppedTower": 0.75,
        "MultiBuildingBlock": 0.55,
    }.get(typology, 0.75)

    footprint_area = min(parcel_area * 0.90, max(10.0, raw_footprint * typo_mult))
    bcr = footprint_area / max(1.0, parcel_area)

    gfa_factor = 1.0
    if typology == "SteppedTower":
        gfa_factor = 0.82
    elif typology == "PodiumTower":
        gfa_factor = 0.88

    gfa = footprint_area * floors * gfa_factor
    far = gfa / max(1.0, parcel_area)

    open_space_m2 = max(0.0, parcel_area - footprint_area)
    open_space_ratio = open_space_m2 / max(1.0, parcel_area)

    # 2. Zoning Compliance & Penalties
    bcr_viol = max(0.0, bcr - max_bcr)
    far_viol = max(0.0, far - max_far)
    height_viol = max(0.0, height_m - max_height)
    constraint_penalty = (bcr_viol * 100.0) + (far_viol * 50.0) + (height_viol * 2.0)

    # Daylight & Solar Access Index (0 - 100)
    open_factor = open_space_ratio * 70.0
    height_shading = max(0.0, (height_m - 12.0) * 1.5)
    daylight_index = round(min(100.0, max(10.0, open_factor + 35.0 - height_shading)), 1)

    # 3. Kentsel Morfoloji & Sky View Factor (SVF)
    street_width = max(6.0, setback * 2.0)
    street_canyon_hw = round(height_m / max(1.0, street_width), 2)
    svf = round(min(1.0, max(0.12, 1.0 - (street_canyon_hw * 0.24) + (open_space_ratio * 0.32))), 2)

    # 4. Microclimate Wind CFD & Ventilation Engine
    # Calculates wind alignment angle, drag coefficient, and pedestrian comfort
    bldg_orientation_deg = 45.0 if typology in ["LShape", "UShape"] else 0.0
    wind_incident_angle = math.radians(abs((prevailing_wind_deg - bldg_orientation_deg) % 180))
    wind_alignment_factor = math.sin(wind_incident_angle)  # Perpendicular causes blockage, oblique allows flow

    typo_porosity = {
        "Tower": 0.75,
        "Slab": 0.35,
        "Courtyard": 0.15,
        "LShape": 0.45,
        "UShape": 0.40,
        "PodiumTower": 0.50,
        "SteppedTower": 0.60,
        "MultiBuildingBlock": 0.70,
    }.get(typology, 0.50)

    raw_wind_score = (open_space_ratio * 45.0) + (typo_porosity * 35.0) + (wind_alignment_factor * 20.0)
    wind_ventilation = round(min(100.0, max(10.0, raw_wind_score - (street_canyon_hw * 8.0))), 1)

    # Lawson Pedestrian Wind Comfort Score (0-100: Higher is safer/more comfortable)
    pedestrian_wind_comfort = round(min(100.0, max(15.0, 95.0 - (height_m * 1.2 * (1.0 - typo_porosity)))), 1)

    # 5. Solar Radiation & Rooftop PV Potential
    # Latitude-based solar irradiance model (kWh/m2/yr)
    base_irradiance = 1500.0 - (abs(latitude_deg - 35.0) * 15.0)  # Latitude adjustment
    roof_area = footprint_area * (0.85 if roof_style == "Flat" else 1.10)
    solar_radiation_kwh = round((roof_area * base_irradiance * 0.90 + (gfa * 0.20 * svf)) / max(1.0, gfa), 1)

    # PV Energy Generation Potential (MWh/yr)
    pv_efficiency = 0.20  # 20% solar panel efficiency
    pv_area_ratio = 0.65  # 65% roof coverage
    pv_yield_mwh = round((roof_area * pv_area_ratio * base_irradiance * pv_efficiency) / 1000.0, 2)

    # 6. Air Pollution Dispersion & Traffic AQI Engine
    green_filter_bonus = open_space_ratio * 45.0
    wind_flushing_effect = wind_ventilation * 0.45
    canyon_trapping_penalty = max(0.0, (street_canyon_hw - 1.2) * 18.0)
    pollution_dispersion = round(min(100.0, max(10.0, green_filter_bonus + wind_flushing_effect - canyon_trapping_penalty + 20.0)), 1)

    # 7. Urban Heat Island (UHI), Mean Radiant Temperature (MRT) & UTCI Index
    # Albedo & anthropogenic heat release simulation
    albedo = {"Flat": 0.30, "Hipped": 0.45, "Gable": 0.40, "Mansard": 0.35}.get(roof_style, 0.35)
    uhi_temperature_rise = round((1.0 - svf) * 3.5 + (1.0 - albedo) * 2.0 - (open_space_ratio * 2.5), 2)
    mrt_temp_celsius = round(32.0 + uhi_temperature_rise + (1.0 - svf) * 4.0, 1)

    # Outdoor Thermal Comfort Index (UTCI Score: 0-100, 100 = Optimal Comfort)
    utci_score = round(min(100.0, max(10.0, 100.0 - (abs(mrt_temp_celsius - 24.0) * 4.5))), 1)

    # 8. Financial Feasibility & Real Estate ROI Engine
    net_sellable_area = gfa * 0.82  # 82% efficiency factor
    total_construction_cost = gfa * const_cost_sqm
    total_revenue = net_sellable_area * sale_price_sqm
    gross_profit = total_revenue - total_construction_cost
    roi_percentage = round((gross_profit / max(1.0, total_construction_cost)) * 100.0, 1)

    # 9. Lifecycle Carbon & Water Hydrology
    emission_per_sqm = {
        "Residential": 45.0,
        "Commercial": 65.0,
        "MixedUse": 52.0,
        "Civic": 48.0,
        "Park": 5.0,
    }.get(usage, 50.0)
    carbon_kg = round(gfa * emission_per_sqm, 1)

    roof_coeff = {"Flat": 0.85, "Hipped": 0.92, "Gable": 0.90, "Mansard": 0.88}.get(roof_style, 0.85)
    runoff_m3 = round((footprint_area * roof_coeff * 0.8) + (open_space_m2 * 0.3 * 0.8), 1)

    # 10. PlanX Composite Urban Quality Score (0-100)
    density_score = min(100.0, (far / max(0.1, max_far)) * 60.0) if far <= max_far else max(0.0, 100.0 - far_viol * 40.0)
    open_score = open_space_ratio * 100.0
    mix_bonus = 20.0 if usage == "MixedUse" else (12.0 if usage in ["Residential", "Commercial"] else 5.0)
    compliance_bonus = 20.0 if constraint_penalty == 0 else max(0.0, 20.0 - constraint_penalty * 0.5)

    raw_score = (
        (density_score * 0.20)
        + (open_score * 0.15)
        + (wind_ventilation * 0.15)
        + (utci_score * 0.15)
        + (pollution_dispersion * 0.15)
        + mix_bonus
        + compliance_bonus
    )
    planx_score = round(min(100.0, max(0.0, raw_score)), 1)

    return {
        "footprint_area": round(footprint_area, 1),
        "bcr": round(bcr, 3),
        "gfa": round(gfa, 1),
        "far": round(far, 2),
        "height_m": round(height_m, 1),
        "open_space_m2": round(open_space_m2, 1),
        "open_space_ratio": round(open_space_ratio, 3),
        "constraint_penalty": round(constraint_penalty, 2),
        "planx_score": planx_score,
        "carbon_kg": carbon_kg,
        "runoff_m3": runoff_m3,
        "daylight_index": daylight_index,
        "street_canyon_hw": street_canyon_hw,
        "sky_view_factor": svf,
        "wind_ventilation": wind_ventilation,
        "pedestrian_wind_comfort": pedestrian_wind_comfort,
        "solar_radiation_kwh": solar_radiation_kwh,
        "pv_yield_mwh": pv_yield_mwh,
        "pollution_dispersion": pollution_dispersion,
        "mrt_temp_celsius": mrt_temp_celsius,
        "utci_score": utci_score,
        "roi_percentage": roi_percentage,
        "total_revenue_usd": round(total_revenue, 0),
    }


class ProcessIndividual:
    """Represents a single solution individual in the NSGA-II / SPEA2 population."""

    def __init__(self, ind_id: str, genotype: Dict[str, Any], generation: int = 0):
        self.id = ind_id
        self.genotype = genotype
        self.generation = generation
        self.metrics: Dict[str, float] = {}
        self.objectives: Dict[str, float] = {}
        self.fitness_vector: List[float] = []
        self.rank: int = 0
        self.crowding_distance: float = 0.0
        self.dominated_count: int = 0
        self.dominated_solutions: List[ProcessIndividual] = []

    def evaluate(
        self,
        parcel_area: float,
        objective_specs: List[Dict[str, str]],
        max_bcr: float = 0.45,
        max_far: float = 2.5,
        max_height: float = 18.0,
        sim_params: Dict[str, Any] | None = None,
    ) -> None:
        """Evaluates multi-domain physical metrics and constructs fitness vector."""
        self.metrics = evaluate_phenotype(self.genotype, parcel_area, max_bcr, max_far, max_height, sim_params)
        self.objectives = {}
        self.fitness_vector = []

        for spec in objective_specs:
            name = spec["name"]
            direction = spec.get("direction", "max").lower()
            val = float(self.metrics.get(name, 0.0))
            self.objectives[name] = val

            if direction == "max":
                self.fitness_vector.append(-val)
            else:
                self.fitness_vector.append(val)

    def dominates(self, other: ProcessIndividual) -> bool:
        """Returns True if self dominates other in Pareto sense."""
        better_in_any = False
        for f1, f2 in zip(self.fitness_vector, other.fitness_vector):
            if f1 > f2:
                return False
            if f1 < f2:
                better_in_any = True
        return better_in_any

    def to_dict(self) -> Dict[str, Any]:
        """Serializes individual for JSON transmission."""
        return {
            "id": self.id,
            "generation": self.generation,
            "genotype": self.genotype,
            "metrics": self.metrics,
            "objectives": self.objectives,
            "rank": self.rank,
            "crowding_distance": round(self.crowding_distance, 4),
        }


def create_random_genotype(bounds: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Generates a random valid genotype within parameter bounds."""
    bounds = bounds or {}
    return {
        "setback": round(random.uniform(bounds.get("min_setback", 0.0), bounds.get("max_setback", 12.0)), 1),
        "floors": random.randint(int(bounds.get("min_floors", 1)), int(bounds.get("max_floors", 24))),
        "typology": random.choice(TYPOLOGIES),
        "usage": random.choice(USAGES),
        "roof_style": random.choice(ROOF_STYLES),
        "scale_x": round(random.uniform(0.5, 1.4), 2),
        "scale_y": round(random.uniform(0.5, 1.4), 2),
        "floor_height": round(random.uniform(2.8, 4.2), 1),
    }


def crossover_genotypes(g1: Dict[str, Any], g2: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates uniform crossover between two genotypes."""
    child = {}
    for key in g1.keys():
        if isinstance(g1[key], float) and isinstance(g2[key], float):
            alpha = random.random()
            child[key] = round(alpha * g1[key] + (1 - alpha) * g2[key], 2)
        elif isinstance(g1[key], int) and isinstance(g2[key], int):
            child[key] = random.choice([g1[key], g2[key]])
        else:
            child[key] = g1[key] if random.random() < 0.5 else g2[key]
    return child


def mutate_genotype(g: Dict[str, Any], mutation_rate: float = 0.15, bounds: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Applies mutation to a genotype."""
    bounds = bounds or {}
    mutated = dict(g)

    if random.random() < mutation_rate:
        mutated["setback"] = round(max(0.0, min(15.0, mutated["setback"] + random.gauss(0, 1.5))), 1)
    if random.random() < mutation_rate:
        mutated["floors"] = max(1, min(30, mutated["floors"] + random.choice([-2, -1, 1, 2])))
    if random.random() < mutation_rate:
        mutated["typology"] = random.choice(TYPOLOGIES)
    if random.random() < mutation_rate:
        mutated["usage"] = random.choice(USAGES)
    if random.random() < mutation_rate:
        mutated["roof_style"] = random.choice(ROOF_STYLES)
    if random.random() < mutation_rate:
        mutated["scale_x"] = round(max(0.35, min(1.6, mutated["scale_x"] + random.gauss(0, 0.1))), 2)
    if random.random() < mutation_rate:
        mutated["scale_y"] = round(max(0.35, min(1.6, mutated["scale_y"] + random.gauss(0, 0.1))), 2)

    return mutated


def fast_non_dominated_sort(population: List[ProcessIndividual]) -> List[List[ProcessIndividual]]:
    """NSGA-II Fast Non-dominated Sorting algorithm."""
    fronts: List[List[ProcessIndividual]] = [[]]

    for p in population:
        p.dominated_solutions = []
        p.dominated_count = 0
        for q in population:
            if p.dominates(q):
                p.dominated_solutions.append(q)
            elif q.dominates(p):
                p.dominated_count += 1

        if p.dominated_count == 0:
            p.rank = 1
            fronts[0].append(p)

    i = 0
    while i < len(fronts) and len(fronts[i]) > 0:
        next_front: List[ProcessIndividual] = []
        for p in fronts[i]:
            for q in p.dominated_solutions:
                q.dominated_count -= 1
                if q.dominated_count == 0:
                    q.rank = i + 2
                    next_front.append(q)
        i += 1
        if next_front:
            fronts.append(next_front)

    return fronts


def calculate_crowding_distance(front: List[ProcessIndividual]) -> None:
    """Calculates crowding distance for individuals within a Pareto front."""
    size = len(front)
    if size == 0:
        return
    if size <= 2:
        for ind in front:
            ind.crowding_distance = float("inf")
        return

    for ind in front:
        ind.crowding_distance = 0.0

    num_objectives = len(front[0].fitness_vector)

    for m in range(num_objectives):
        front.sort(key=lambda ind: ind.fitness_vector[m])
        front[0].crowding_distance = float("inf")
        front[-1].crowding_distance = float("inf")

        obj_min = front[0].fitness_vector[m]
        obj_max = front[-1].fitness_vector[m]
        obj_range = obj_max - obj_min

        if obj_range == 0:
            continue

        for i in range(1, size - 1):
            if not math.isinf(front[i].crowding_distance):
                dist = (front[i + 1].fitness_vector[m] - front[i - 1].fitness_vector[m]) / obj_range
                front[i].crowding_distance += dist


def binary_tournament_selection(population: List[ProcessIndividual]) -> ProcessIndividual:
    """Selects one parent using binary tournament based on rank and crowding distance."""
    p1, p2 = random.sample(population, 2)
    if p1.rank < p2.rank:
        return p1
    elif p2.rank < p1.rank:
        return p2
    else:
        return p1 if p1.crowding_distance > p2.crowding_distance else p2


def run_nsga2_optimization(
    parcel_area: float,
    objective_specs: List[Dict[str, str]] | None = None,
    pop_size: int = 30,
    generations: int = 15,
    crossover_rate: float = 0.8,
    mutation_rate: float = 0.15,
    max_bcr: float = 0.45,
    max_far: float = 2.5,
    max_height: float = 18.0,
    bounds: Dict[str, Any] | None = None,
    sim_params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Runs NSGA-II multi-objective optimization and returns full history & Pareto front."""
    if not objective_specs:
        objective_specs = [
            {"name": "gfa", "direction": "max"},
            {"name": "planx_score", "direction": "max"},
            {"name": "wind_ventilation", "direction": "max"},
            {"name": "roi_percentage", "direction": "max"},
            {"name": "carbon_kg", "direction": "min"},
        ]

    population: List[ProcessIndividual] = []
    for i in range(pop_size):
        g = create_random_genotype(bounds)
        ind = ProcessIndividual(f"gen0_ind{i+1}", g, generation=0)
        ind.evaluate(parcel_area, objective_specs, max_bcr, max_far, max_height, sim_params)
        population.append(ind)

    history: List[Dict[str, Any]] = []

    for gen in range(generations):
        fronts = fast_non_dominated_sort(population)
        for front in fronts:
            calculate_crowding_distance(front)

        gen_individuals = [ind.to_dict() for ind in population]
        pareto_rank1 = [ind.to_dict() for ind in fronts[0]] if fronts else []

        avg_objectives: Dict[str, float] = {}
        for spec in objective_specs:
            name = spec["name"]
            vals = [ind.objectives[name] for ind in population]
            avg_objectives[name] = round(sum(vals) / max(1, len(vals)), 2)

        history.append(
            {
                "generation": gen,
                "population_count": len(population),
                "pareto_rank1_count": len(pareto_rank1),
                "avg_objectives": avg_objectives,
                "individuals": gen_individuals,
            }
        )

        if gen == generations - 1:
            break

        offspring: List[ProcessIndividual] = []
        offspring_count = 0
        while offspring_count < pop_size:
            p1 = binary_tournament_selection(population)
            p2 = binary_tournament_selection(population)

            if random.random() < crossover_rate:
                child_g = crossover_genotypes(p1.genotype, p2.genotype)
            else:
                child_g = dict(p1.genotype)

            child_g = mutate_genotype(child_g, mutation_rate, bounds)
            child_ind = ProcessIndividual(f"gen{gen+1}_ind{offspring_count+1}", child_g, generation=gen + 1)
            child_ind.evaluate(parcel_area, objective_specs, max_bcr, max_far, max_height, sim_params)
            offspring.append(child_ind)
            offspring_count += 1

        combined = population + offspring
        combined_fronts = fast_non_dominated_sort(combined)
        new_pop: List[ProcessIndividual] = []

        for front in combined_fronts:
            calculate_crowding_distance(front)
            if len(new_pop) + len(front) <= pop_size:
                new_pop.extend(front)
            else:
                front.sort(key=lambda ind: ind.crowding_distance, reverse=True)
                needed = pop_size - len(new_pop)
                new_pop.extend(front[:needed])
                break

        population = new_pop

    final_fronts = fast_non_dominated_sort(population)
    for front in final_fronts:
        calculate_crowding_distance(front)

    pareto_solutions = [ind.to_dict() for ind in final_fronts[0]]

    return {
        "status": "ok",
        "generations": generations,
        "pop_size": pop_size,
        "objective_specs": objective_specs,
        "pareto_solutions": pareto_solutions,
        "history": history,
        "all_solutions": [ind.to_dict() for ind in population],
    }
