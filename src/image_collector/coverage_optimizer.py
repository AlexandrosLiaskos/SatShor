"""
OCAS - Optimal Coverage Acquisition System

This module implements geometric set cover algorithms for satellite image coverage optimization.
It solves the SIMSP (Satellite Image Mosaic Selection Problem) to select a minimal set of
satellite images that completely cover a geographic area of interest.

Two approaches are provided:
1. Greedy heuristic: Fast, near-optimal solution suitable for large areas
2. MILP-based optimal: Globally optimal solution using OR-Tools (may be slow for large problems)
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Set, Optional, Dict, Any, Tuple

from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.prepared import prep
from shapely.ops import unary_union
import numpy as np

# Optional OR-Tools import
try:
    from ortools.linear_solver import pywraplp
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logging.warning("OR-Tools not available. Install with: pip install ortools>=9.14.0")

logger = logging.getLogger(__name__)


@dataclass
class CoverageCandidate:
    """Represents a satellite image product candidate for coverage optimization."""
    index: int  # Index in original product list
    footprint: Polygon  # Footprint geometry in target CRS
    cloud_cover: float  # Cloud cover percentage (0-100)
    date: str  # Acquisition date
    quality_score: float  # Overall quality score (0-1)
    covered_points: Set[int]  # Set of sample point indices covered by this candidate


@dataclass
class CoverageResult:
    """Result of coverage optimization algorithm."""
    selected_indices: List[int]  # Indices of selected products
    coverage_fraction: float  # Fraction of AOI covered (0-1)
    uncovered_area_m2: float  # Area of uncovered region in square meters
    num_candidates: int  # Total number of candidate products
    num_selected: int  # Number of selected products
    solver_type: str  # "greedy" or "milp"
    solver_time_seconds: Optional[float] = None  # Solver runtime
    optimal: Optional[bool] = None  # Whether solution is provably optimal


def sample_points_in_polygon(
    aoi_polygon: Polygon,
    grid_spacing_meters: float,
    crs: Any
) -> List[Point]:
    """
    Generate a uniform grid of sample points within the AOI polygon.
    
    Args:
        aoi_polygon: Area of interest polygon in projected CRS
        grid_spacing_meters: Distance between grid points in meters
        crs: Projected CRS (for validation)
    
    Returns:
        List of Point geometries representing the sample grid
    """
    logger.info(f"Sampling AOI with grid spacing: {grid_spacing_meters:.1f} meters")
    
    # Get bounding box
    minx, miny, maxx, maxy = aoi_polygon.bounds
    
    # Generate grid points
    x_coords = np.arange(minx, maxx, grid_spacing_meters)
    y_coords = np.arange(miny, maxy, grid_spacing_meters)
    
    # Create points and filter to those within polygon
    prepared_polygon = prep(aoi_polygon)
    sample_points = []
    
    for x in x_coords:
        for y in y_coords:
            point = Point(x, y)
            if prepared_polygon.covers(point):
                sample_points.append(point)
    
    logger.info(f"Generated {len(sample_points)} sample points within AOI")
    return sample_points


def build_coverage_matrix(
    sample_points: List[Point],
    candidate_footprints: List[Polygon | MultiPolygon],
    crs: Any
) -> List[Set[int]]:
    """
    Build coverage matrix showing which sample points are covered by each candidate.
    
    Args:
        sample_points: List of sample points within AOI
        candidate_footprints: List of candidate footprint polygons or multipolygons
        crs: Projected CRS (for validation)
    
    Returns:
        List of sets where coverage_sets[j] = set of point indices covered by candidate j
    """
    logger.info(f"Building coverage matrix for {len(candidate_footprints)} candidates and {len(sample_points)} points")
    
    coverage_sets = []
    
    for j, footprint in enumerate(candidate_footprints):
        # Use prepared geometry for fast point-in-polygon tests
        prepared_footprint = prep(footprint)
        covered_points = set()
        
        # Pre-filter points using bounding box for performance
        minx, miny, maxx, maxy = footprint.bounds
        
        for i, point in enumerate(sample_points):
            # Quick bbox check before expensive geometric test
            if minx <= point.x <= maxx and miny <= point.y <= maxy:
                if prepared_footprint.covers(point):
                    covered_points.add(i)
        
        coverage_sets.append(covered_points)
        
        if (j + 1) % 10 == 0 or j == len(candidate_footprints) - 1:
            logger.debug(f"Processed {j + 1}/{len(candidate_footprints)} candidates")
    
    logger.info(f"Coverage matrix built successfully")
    return coverage_sets


def greedy_set_cover(
    candidates: List[CoverageCandidate],
    coverage_sets: List[Set[int]],
    sample_points: List[Point],
    aoi_area_m2: float,
    min_coverage_fraction: float,
    cloud_weight: float,
    quality_weight: float
) -> CoverageResult:
    """
    Greedy heuristic algorithm for weighted set cover.
    
    Iteratively selects the candidate with the best marginal gain per cost ratio
    until the minimum coverage fraction is achieved.
    
    Args:
        candidates: List of coverage candidates
        coverage_sets: Precomputed coverage sets for each candidate
        sample_points: Sample points within AOI
        aoi_area_m2: Total AOI area in square meters
        min_coverage_fraction: Minimum fraction of points to cover (0-1)
        cloud_weight: Weight for cloud cover in cost function
        quality_weight: Weight for quality score in cost function
    
    Returns:
        CoverageResult with selected indices and statistics
    """
    import time
    start_time = time.time()
    
    logger.info(f"Starting greedy set cover (target coverage: {min_coverage_fraction*100:.1f}%)")
    
    uncovered_points = set(range(len(sample_points)))
    selected_indices = []
    total_points = len(sample_points)
    target_points = int(total_points * min_coverage_fraction)
    
    iteration = 0
    while len(uncovered_points) > (total_points - target_points):
        best_candidate_idx = None
        best_gain_per_cost = 0
        best_gain = 0
        
        # Find candidate with best marginal gain per cost
        for j, candidate in enumerate(candidates):
            if j in selected_indices:
                continue
            
            # Calculate marginal gain (new points covered)
            marginal_gain = len(coverage_sets[j] & uncovered_points)
            
            if marginal_gain == 0:
                continue
            
            # Calculate cost (weighted by cloud cover and quality)
            cloud_penalty = candidate.cloud_cover / 100.0
            quality_penalty = 1.0 - candidate.quality_score
            cost = cloud_weight * cloud_penalty + quality_weight * quality_penalty
            cost = max(cost, 0.01)  # Avoid division by zero
            
            # Calculate gain per cost ratio
            gain_per_cost = marginal_gain / cost
            
            if gain_per_cost > best_gain_per_cost:
                best_gain_per_cost = gain_per_cost
                best_candidate_idx = j
                best_gain = marginal_gain
        
        # Check if no progress can be made
        if best_candidate_idx is None:
            logger.warning(f"No more candidates can improve coverage. Stopping at {(1 - len(uncovered_points)/total_points)*100:.1f}% coverage")
            break
        
        # Add best candidate to selection
        selected_indices.append(best_candidate_idx)
        uncovered_points -= coverage_sets[best_candidate_idx]
        
        iteration += 1
        current_coverage = 1 - len(uncovered_points) / total_points
        logger.debug(f"Iteration {iteration}: Selected candidate {best_candidate_idx} "
                    f"(gain: {best_gain} points, coverage: {current_coverage*100:.1f}%)")
    
    # Calculate final statistics
    coverage_fraction = 1 - len(uncovered_points) / total_points
    uncovered_area_m2 = (len(uncovered_points) / total_points) * aoi_area_m2
    solver_time = time.time() - start_time
    
    logger.info(f"Greedy algorithm completed in {solver_time:.2f}s: "
               f"Selected {len(selected_indices)} products, "
               f"Coverage: {coverage_fraction*100:.2f}%")
    
    return CoverageResult(
        selected_indices=[candidates[i].index for i in selected_indices],
        coverage_fraction=coverage_fraction,
        uncovered_area_m2=uncovered_area_m2,
        num_candidates=len(candidates),
        num_selected=len(selected_indices),
        solver_type="greedy",
        solver_time_seconds=solver_time,
        optimal=False
    )


def optimal_set_cover_milp(
    candidates: List[CoverageCandidate],
    coverage_sets: List[Set[int]],
    sample_points: List[Point],
    aoi_area_m2: float,
    min_coverage_fraction: float,
    cloud_weight: float,
    quality_weight: float,
    time_limit_seconds: int
) -> Optional[CoverageResult]:
    """
    MILP-based optimal solution for weighted set cover using OR-Tools.
    
    Formulates the problem as a binary integer program and solves with branch-and-bound.
    
    Args:
        candidates: List of coverage candidates
        coverage_sets: Precomputed coverage sets for each candidate
        sample_points: Sample points within AOI
        aoi_area_m2: Total AOI area in square meters
        min_coverage_fraction: Minimum fraction of points to cover (0-1)
        cloud_weight: Weight for cloud cover in cost function
        quality_weight: Weight for quality score in cost function
        time_limit_seconds: Maximum solver time in seconds
    
    Returns:
        CoverageResult with optimal selection, or None if infeasible/timeout
    """
    if not ORTOOLS_AVAILABLE:
        logger.error("OR-Tools not available. Cannot run optimal solver.")
        return None
    
    import time
    start_time = time.time()
    
    logger.info(f"Starting MILP optimal solver (time limit: {time_limit_seconds}s)")
    
    # Create solver using CBC (more widely available in pip wheels than SCIP)
    solver = pywraplp.Solver.CreateSolver('CBC')
    if not solver:
        logger.error("Failed to create CBC solver")
        return None
    
    solver.SetTimeLimit(time_limit_seconds * 1000)  # Convert to milliseconds
    
    # Decision variables: x[j] = 1 if candidate j is selected
    x = {}
    for j in range(len(candidates)):
        x[j] = solver.BoolVar(f'x_{j}')
    
    # Coverage constraints: each point must be covered by at least one selected candidate
    total_points = len(sample_points)
    target_points = int(total_points * min_coverage_fraction)
    
    # Only require coverage for target_points (allows some uncovered points)
    # We use a soft constraint approach: maximize covered points while minimizing cost
    
    # Create indicator variables for each point
    point_covered = {}
    for i in range(total_points):
        point_covered[i] = solver.BoolVar(f'p_{i}')
    
    # Constraint: point i is covered if at least one candidate covering it is selected
    for i in range(total_points):
        # Find candidates covering point i
        covering_candidates = [j for j, cov_set in enumerate(coverage_sets) if i in cov_set]
        
        if covering_candidates:
            # point_covered[i] <= sum(x[j] for j in covering_candidates)
            # If any covering candidate is selected, point can be covered
            solver.Add(point_covered[i] <= sum(x[j] for j in covering_candidates))
        else:
            # Point cannot be covered
            solver.Add(point_covered[i] == 0)
    
    # Constraint: minimum coverage requirement
    solver.Add(sum(point_covered[i] for i in range(total_points)) >= target_points)
    
    # Objective: minimize weighted cost of selected candidates
    # Add small epsilon to prefer fewer images when costs tie
    objective_terms = []
    epsilon = 1e-6
    for j, candidate in enumerate(candidates):
        cloud_penalty = candidate.cloud_cover / 100.0
        quality_penalty = 1.0 - candidate.quality_score
        cost = cloud_weight * cloud_penalty + quality_weight * quality_penalty
        cost = max(cost, 0.01)
        objective_terms.append(cost * x[j])
    
    # Add tie-breaker: prefer fewer images
    cardinality_penalty = epsilon * sum(x[j] for j in range(len(candidates)))
    solver.Minimize(sum(objective_terms) + cardinality_penalty)
    
    # Solve
    logger.info("Solving MILP problem...")
    status = solver.Solve()
    
    solver_time = time.time() - start_time
    
    if status == pywraplp.Solver.OPTIMAL:
        logger.info(f"Optimal solution found in {solver_time:.2f}s")
        optimal = True
    elif status == pywraplp.Solver.FEASIBLE:
        logger.warning(f"Feasible solution found in {solver_time:.2f}s (not proven optimal, time limit reached)")
        optimal = False
    else:
        logger.error(f"Solver failed with status: {status}")
        return None
    
    # Extract solution
    selected_indices = []
    covered_points_set = set()
    
    for j in range(len(candidates)):
        if x[j].solution_value() > 0.5:  # Binary variable
            selected_indices.append(candidates[j].index)
            covered_points_set |= coverage_sets[j]
    
    # Calculate statistics
    coverage_fraction = len(covered_points_set) / total_points
    uncovered_area_m2 = (1 - coverage_fraction) * aoi_area_m2
    
    logger.info(f"MILP solution: Selected {len(selected_indices)} products, "
               f"Coverage: {coverage_fraction*100:.2f}%")
    
    return CoverageResult(
        selected_indices=selected_indices,
        coverage_fraction=coverage_fraction,
        uncovered_area_m2=uncovered_area_m2,
        num_candidates=len(candidates),
        num_selected=len(selected_indices),
        solver_type="milp",
        solver_time_seconds=solver_time,
        optimal=optimal
    )


def select_covering_products(
    processed_products: List[Dict[str, Any]],
    aoi_geom: Polygon,
    aoi_area_m2: float,
    target_crs: Any,
    strategy: str,
    min_coverage_fraction: float = 0.99,
    grid_spacing_meters: Optional[float] = None,
    solver_timeout: int = 300,
    cloud_weight: float = 0.3,
    quality_weight: float = 0.7
) -> CoverageResult:
    """
    Main entry point for coverage optimization.
    
    Orchestrates the full workflow: extract footprints, sample AOI, build coverage matrix,
    run selected algorithm (greedy or MILP).
    
    Args:
        processed_products: List of product dictionaries with footprint geometries
        aoi_geom: Area of interest polygon in target CRS
        aoi_area_m2: Total AOI area in square meters
        target_crs: Projected CRS for geometric operations
        strategy: "coverage_greedy" or "coverage_optimal"
        min_coverage_fraction: Minimum coverage fraction (0-1)
        grid_spacing_meters: Grid spacing for point sampling (None = auto-calculate)
        solver_timeout: Time limit for MILP solver in seconds
        cloud_weight: Weight for cloud cover in cost function (0-1)
        quality_weight: Weight for quality score in cost function (0-1)
    
    Returns:
        CoverageResult with selected product indices and statistics
    """
    logger.info(f"Starting coverage optimization with strategy: {strategy}")
    logger.info(f"AOI area: {aoi_area_m2/1e6:.2f} km², Min coverage: {min_coverage_fraction*100:.1f}%")
    
    # Validate inputs
    if not processed_products:
        raise ValueError("No products provided for coverage optimization")
    
    if not isinstance(aoi_geom, (Polygon, MultiPolygon)):
        raise ValueError("AOI geometry must be a Polygon or MultiPolygon")
    
    # Handle MultiPolygon by using unary union
    if isinstance(aoi_geom, MultiPolygon):
        aoi_geom = unary_union(aoi_geom)
    
    # Auto-calculate grid spacing if not provided
    if grid_spacing_meters is None:
        # Use sqrt(area) / 100 as default, clamped to reasonable range
        grid_spacing_meters = max(50, min(200, math.sqrt(aoi_area_m2) / 100))
        logger.info(f"Auto-calculated grid spacing: {grid_spacing_meters:.1f} meters")
    
    # Extract footprints and create candidates
    candidates = []
    candidate_footprints = []
    
    for i, product in enumerate(processed_products):
        footprint = product.get("footprint_geom_proj")
        
        if footprint is None:
            logger.warning(f"Product {i} missing footprint geometry, skipping")
            continue
        
        if not isinstance(footprint, (Polygon, MultiPolygon)):
            logger.warning(f"Product {i} has invalid footprint type: {type(footprint)}, skipping")
            continue
        
        # Read cloud cover, preferring float field with fallback, clamped to [0,100]
        cloud_cover = product.get("cloud_cover_float")
        if cloud_cover is None:
            cloud_cover = product.get("cloud_cover", 0.0)
        cloud_cover = max(0.0, min(100.0, float(cloud_cover)))
        
        candidate = CoverageCandidate(
            index=i,
            footprint=footprint,
            cloud_cover=cloud_cover,
            date=product.get("date", "unknown"),
            quality_score=product.get("quality_score", 0.0),
            covered_points=set()  # Will be populated later
        )
        
        candidates.append(candidate)
        candidate_footprints.append(footprint)
    
    if not candidates:
        raise ValueError("No valid candidates with footprint geometries")
    
    logger.info(f"Extracted {len(candidates)} valid candidates from {len(processed_products)} products")
    
    # Sample AOI into grid points
    sample_points = sample_points_in_polygon(aoi_geom, grid_spacing_meters, target_crs)
    
    if not sample_points:
        raise ValueError("Failed to sample points in AOI")
    
    # Build coverage matrix
    coverage_sets = build_coverage_matrix(sample_points, candidate_footprints, target_crs)
    
    # Update candidates with coverage information
    for i, candidate in enumerate(candidates):
        candidate.covered_points = coverage_sets[i]
    
    # Check if complete coverage is possible
    all_covered_points = set()
    for cov_set in coverage_sets:
        all_covered_points |= cov_set
    
    max_possible_coverage = len(all_covered_points) / len(sample_points)
    logger.info(f"Maximum possible coverage: {max_possible_coverage*100:.2f}%")
    
    if max_possible_coverage < min_coverage_fraction:
        logger.warning(f"Target coverage {min_coverage_fraction*100:.1f}% not achievable. "
                      f"Maximum possible: {max_possible_coverage*100:.2f}%")
    
    # Run selected algorithm
    if strategy == "coverage_greedy":
        result = greedy_set_cover(
            candidates=candidates,
            coverage_sets=coverage_sets,
            sample_points=sample_points,
            aoi_area_m2=aoi_area_m2,
            min_coverage_fraction=min_coverage_fraction,
            cloud_weight=cloud_weight,
            quality_weight=quality_weight
        )
    elif strategy == "coverage_optimal":
        result = optimal_set_cover_milp(
            candidates=candidates,
            coverage_sets=coverage_sets,
            sample_points=sample_points,
            aoi_area_m2=aoi_area_m2,
            min_coverage_fraction=min_coverage_fraction,
            cloud_weight=cloud_weight,
            quality_weight=quality_weight,
            time_limit_seconds=solver_timeout
        )
        
        if result is None:
            logger.warning("MILP solver failed, falling back to greedy algorithm")
            result = greedy_set_cover(
                candidates=candidates,
                coverage_sets=coverage_sets,
                sample_points=sample_points,
                aoi_area_m2=aoi_area_m2,
                min_coverage_fraction=min_coverage_fraction,
                cloud_weight=cloud_weight,
                quality_weight=quality_weight
            )
    else:
        raise ValueError(f"Unknown coverage strategy: {strategy}")
    
    logger.info(f"Coverage optimization complete: {result.num_selected} products selected, "
               f"{result.coverage_fraction*100:.2f}% coverage")
    
    return result
