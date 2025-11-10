"""
Core collection logic for satellite image downloading.

This module provides programmatic APIs for running satellite image collection
without interactive prompts, suitable for automation and scheduling.
"""

import json
import logging
import os
import pathlib
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Literal
from dataclasses import dataclass

from collector import (
    get_access_token,
    load_aoi_data,
    build_odata_query,
    fetch_products,
    calculate_central_date,
)
from downloader import download_product

try:
    from coverage_optimizer import select_covering_products, CoverageResult
    COVERAGE_OPTIMIZER_AVAILABLE = True
except ImportError:
    COVERAGE_OPTIMIZER_AVAILABLE = False
    logging.warning("Coverage optimizer not available. Coverage strategies will not work.")


@dataclass
class CollectionResult:
    """Result of a collection run."""
    
    success: bool
    downloaded_products: list[str]  # List of product names
    errors: list[str]
    message: str
    total_products_found: int
    total_products_filtered: int


def calculate_quality_score(
    product: dict[str, Any],
    aoi_coverage_pct: float,
    cloud_cover_pct: float,
    date_diff_days: float,
    max_date_diff_days: float,
    aoi_weight: float = 0.4,
    cloud_weight: float = 0.4,
    recency_weight: float = 0.2,
) -> float:
    """
    Calculate a quality score for a product based on multiple factors.
    
    Args:
        product: Product data dictionary
        aoi_coverage_pct: AOI coverage percentage (0-100)
        cloud_cover_pct: Cloud cover percentage (0-100)
        date_diff_days: Days from reference date
        max_date_diff_days: Maximum date difference in the dataset
        aoi_weight: Weight for AOI coverage (default 0.4)
        cloud_weight: Weight for cloud cover (default 0.4)
        recency_weight: Weight for date recency (default 0.2)
        
    Returns:
        Quality score between 0 and 1 (higher is better)
    """
    # Normalize AOI coverage (higher is better)
    aoi_score = aoi_coverage_pct / 100.0
    
    # Normalize cloud cover (lower is better, so invert)
    cloud_score = 1.0 - (cloud_cover_pct / 100.0)
    
    # Normalize date recency (more recent is better, so invert)
    if max_date_diff_days > 0:
        recency_score = 1.0 - (date_diff_days / max_date_diff_days)
    else:
        recency_score = 1.0
    
    # Calculate weighted score
    quality_score = (
        aoi_weight * aoi_score +
        cloud_weight * cloud_score +
        recency_weight * recency_score
    )
    
    return max(0.0, min(1.0, quality_score))  # Clamp to [0, 1]


def auto_select_products(
    processed_products: list[dict[str, Any]],
    strategy: Literal["best_n", "all_above_threshold", "best_per_week", "coverage_greedy", "coverage_optimal"],
    max_products: int = 5,
    quality_threshold: float = 0.7,
    aoi_weight: float = 0.4,
    cloud_weight: float = 0.4,
    recency_weight: float = 0.2,
    aoi_geom: Optional[Any] = None,
    aoi_area_m2: Optional[float] = None,
    target_crs: Optional[Any] = None,
    min_coverage_fraction: float = 0.99,
    grid_spacing_meters: Optional[float] = None,
    solver_timeout: int = 300,
    coverage_cloud_weight: float = 0.3,
    coverage_quality_weight: float = 0.7,
) -> list[dict[str, Any]]:
    """
    Automatically select products based on a strategy.
    
    Args:
        processed_products: List of processed product dictionaries with metadata
        strategy: Selection strategy to use
        max_products: Maximum products for "best_n" strategy
        quality_threshold: Quality threshold for "all_above_threshold" strategy
        aoi_weight: Weight for AOI coverage in quality score
        cloud_weight: Weight for cloud cover in quality score
        recency_weight: Weight for date recency in quality score
        
    Returns:
        List of selected products to download
    """
    if not processed_products:
        return []
    
    # Calculate quality scores for all products
    max_date_diff = max(p.get("date_diff_days", 0) for p in processed_products)
    
    for product in processed_products:
        quality_score = calculate_quality_score(
            product=product,
            aoi_coverage_pct=product.get("aoi_coverage_pct", 0),
            cloud_cover_pct=product.get("cloud_cover_float", 0),
            date_diff_days=product.get("date_diff_days", 0),
            max_date_diff_days=max_date_diff,
            aoi_weight=aoi_weight,
            cloud_weight=cloud_weight,
            recency_weight=recency_weight,
        )
        product["quality_score"] = quality_score
    
    # Sort by quality score (descending)
    sorted_products = sorted(
        processed_products,
        key=lambda p: p.get("quality_score", 0),
        reverse=True
    )
    
    if strategy == "best_n":
        # Select top N products
        return sorted_products[:max_products]
    
    elif strategy == "all_above_threshold":
        # Select all products above quality threshold
        return [p for p in sorted_products if p.get("quality_score", 0) >= quality_threshold]
    
    elif strategy == "best_per_week":
        # Group by week and select best from each week
        from collections import defaultdict
        weekly_products = defaultdict(list)
        
        for product in sorted_products:
            sensing_date_str = product.get("sensing_date")
            if sensing_date_str:
                try:
                    sensing_date = datetime.fromisoformat(sensing_date_str.replace('Z', '+00:00'))
                    # Get ISO week number
                    week_key = f"{sensing_date.year}-W{sensing_date.isocalendar()[1]:02d}"
                    weekly_products[week_key].append(product)
                except (ValueError, AttributeError):
                    continue
        
        # Select best product from each week
        selected = []
        for week, products in weekly_products.items():
            best = max(products, key=lambda p: p.get("quality_score", 0))
            selected.append(best)
        
        # Sort selected by quality score
        selected.sort(key=lambda p: p.get("quality_score", 0), reverse=True)
        return selected
    
    elif strategy in ["coverage_greedy", "coverage_optimal"]:
        # Coverage optimization strategies
        if not COVERAGE_OPTIMIZER_AVAILABLE:
            logging.error("Coverage optimizer not available. Falling back to best_n strategy.")
            return sorted_products[:max_products]
        
        if aoi_geom is None or aoi_area_m2 is None or target_crs is None:
            logging.error("Coverage strategies require AOI geometry, area, and CRS. Falling back to best_n.")
            return sorted_products[:max_products]
        
        # Check that footprint geometries are available
        if not any(p.get("footprint_geom_proj") for p in processed_products):
            logging.error("Coverage strategies require footprint geometries. Falling back to best_n.")
            return sorted_products[:max_products]
        
        try:
            # Run coverage optimization
            coverage_result = select_covering_products(
                processed_products=processed_products,
                aoi_geom=aoi_geom,
                aoi_area_m2=aoi_area_m2,
                target_crs=target_crs,
                strategy=strategy,
                min_coverage_fraction=min_coverage_fraction,
                grid_spacing_meters=grid_spacing_meters,
                solver_timeout=solver_timeout,
                cloud_weight=coverage_cloud_weight,
                quality_weight=coverage_quality_weight,
            )
            
            # Extract selected products by indices
            selected = [processed_products[i] for i in coverage_result.selected_indices]
            
            logging.info(f"Coverage optimization selected {len(selected)} products "
                        f"with {coverage_result.coverage_fraction*100:.2f}% coverage")
            
            return selected
            
        except Exception as e:
            logging.error(f"Coverage optimization failed: {e}", exc_info=True)
            logging.warning("Falling back to best_n strategy")
            return sorted_products[:max_products]
    
    else:
        # Fallback to best_n
        return sorted_products[:max_products]


def check_already_downloaded(product_name: str, output_dir: str) -> bool:
    """
    Check if a product has already been downloaded.
    
    Args:
        product_name: Name of the product
        output_dir: Output directory where products are stored
        
    Returns:
        True if product already exists, False otherwise
    """
    safe_dir_path = pathlib.Path(output_dir) / product_name
    metadata_file_path = safe_dir_path / "metadata.json"
    
    # Check if directory exists and has metadata
    if safe_dir_path.is_dir() and metadata_file_path.exists():
        try:
            with open(metadata_file_path, 'r') as f:
                metadata = json.load(f)
                # Verify it's the same product
                if metadata.get("product_name") == product_name:
                    return True
        except (json.JSONDecodeError, IOError):
            # If metadata is corrupted, assume not downloaded
            pass
    
    return False


def run_collection(
    aoi_path: str,
    start_date: str,
    end_date: str,
    max_cloud: float = 100.0,
    min_aoi: float = 0.0,
    product_level: str = "L2A",
    output_dir: str = ".",
    auto_select_strategy: Literal["best_n", "all_above_threshold", "best_per_week", "coverage_greedy", "coverage_optimal"] = "best_n",
    max_products: int = 5,
    quality_threshold: float = 0.7,
    aoi_weight: float = 0.4,
    cloud_weight: float = 0.4,
    recency_weight: float = 0.2,
    min_coverage_fraction: float = 0.99,
    grid_spacing_meters: Optional[float] = None,
    solver_timeout: int = 300,
    coverage_cloud_weight: float = 0.3,
    coverage_quality_weight: float = 0.7,
) -> CollectionResult:
    """
    Run a satellite image collection programmatically.
    
    This is the main entry point for automated collection, used by both
    the CLI and the scheduler.
    
    Args:
        aoi_path: Path to AOI GeoJSON file
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        max_cloud: Maximum cloud cover percentage (0-100)
        min_aoi: Minimum AOI coverage percentage (0-100)
        product_level: Product level ("L1C" or "L2A")
        output_dir: Output directory for downloads
        auto_select_strategy: Strategy for automatic product selection
        max_products: Maximum products for "best_n" strategy
        quality_threshold: Quality threshold for "all_above_threshold"
        aoi_weight: Weight for AOI coverage in quality score
        cloud_weight: Weight for cloud cover in quality score
        recency_weight: Weight for date recency in quality score
        
    Returns:
        CollectionResult with success status and details
    """
    from collector import process_products
    import geopandas as gpd
    from rich.console import Console
    
    console = Console()
    errors = []
    downloaded_products = []
    
    try:
        # Get access token
        access_token = get_access_token()
        
        # Load AOI
        aoi_wkt, aoi_gdf = load_aoi_data(aoi_path)
        if aoi_wkt is None or aoi_gdf is None:
            return CollectionResult(
                success=False,
                downloaded_products=[],
                errors=["Failed to load AOI data"],
                message=f"Failed to load AOI from {aoi_path}",
                total_products_found=0,
                total_products_filtered=0,
            )
        
        # Build query
        odata_query = build_odata_query(
            aoi_wkt=aoi_wkt,
            start_date=start_date,
            end_date=end_date,
            product_level=product_level,
        )
        
        # Fetch products
        products = fetch_products(odata_query, access_token)
        total_found = len(products)
        
        if not products:
            return CollectionResult(
                success=True,
                downloaded_products=[],
                errors=[],
                message="No products found for the specified criteria",
                total_products_found=0,
                total_products_filtered=0,
            )
        
        # Calculate center date for sorting
        from datetime import datetime
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        center_date = calculate_central_date(start_date_obj, end_date_obj)
        
        # Process products (filtering and metadata extraction)
        # Import process_products with special parameters to get processed list
        from collector import (
            get_utm_crs,
            check_aoi_utm_zones,
        )
        from shapely.geometry import Polygon
        
        # Process products similar to process_products function
        # but without interactive prompts
        logging.info(f"Processing {len(products)} potential products.")
        
        aoi_geom = aoi_gdf.geometry.iloc[0]
        aoi_crs = aoi_gdf.crs
        
        # Reproject to WGS84
        aoi_gdf_wgs84 = aoi_gdf.to_crs("EPSG:4326")
        aoi_geom_wgs84 = aoi_gdf_wgs84.geometry.iloc[0]
        aoi_centroid_wgs84 = aoi_geom_wgs84.centroid
        
        # Get UTM CRS
        spans_multiple_zones, utm_zones, recommended_crs = check_aoi_utm_zones(aoi_geom_wgs84)
        if spans_multiple_zones:
            target_crs = recommended_crs
        else:
            target_crs = get_utm_crs(aoi_centroid_wgs84.x, aoi_centroid_wgs84.y)
        
        # Calculate AOI area
        aoi_gdf_proj = aoi_gdf_wgs84.to_crs(target_crs)
        aoi_geom_proj = aoi_gdf_proj.geometry.iloc[0]
        aoi_area_m2 = aoi_geom_proj.area
        
        # Filter and process products
        processed_results = []
        products.sort(key=lambda p: p.get("ContentDate", {}).get("Start"), reverse=True)
        
        for product in products:
            product_name = product["Name"]
            content_length = product.get("ContentLength")
            attributes = {
                attr["Name"]: attr["Value"] for attr in product.get("Attributes", [])
            }
            cloud_cover = attributes.get("cloudCover", None)
            
            if isinstance(cloud_cover, str):
                try:
                    cloud_cover = float(cloud_cover)
                except ValueError:
                    cloud_cover = None
            
            # Apply cloud cover filter
            if cloud_cover is not None and cloud_cover > max_cloud:
                continue
            
            # Size filter (>= 600MB)
            if content_length is not None and content_length < 600 * 1024 * 1024:
                continue
            
            # Calculate AOI coverage
            footprint_wkt = product.get("GeoFootprint")
            if not footprint_wkt:
                continue
            
            try:
                from shapely.wkt import loads as wkt_loads
                footprint_geom_wgs84 = wkt_loads(footprint_wkt)
                footprint_gdf_wgs84 = gpd.GeoDataFrame(
                    geometry=[footprint_geom_wgs84], crs="EPSG:4326"
                )
                footprint_gdf_proj = footprint_gdf_wgs84.to_crs(target_crs)
                footprint_geom_proj = footprint_gdf_proj.geometry.iloc[0]
                
                intersection = aoi_geom_proj.intersection(footprint_geom_proj)
                intersection_area_m2 = intersection.area if not intersection.is_empty else 0.0
                
                aoi_coverage_pct = (intersection_area_m2 / aoi_area_m2 * 100.0) if aoi_area_m2 > 0 else 0.0
                
                # Apply AOI coverage filter
                if aoi_coverage_pct < min_aoi:
                    continue
                
            except Exception as e:
                logging.warning(f"Error calculating coverage for {product_name}: {e}")
                continue
            
            # Calculate date difference
            sensing_date_str = product.get("ContentDate", {}).get("Start")
            if sensing_date_str:
                try:
                    sensing_date = datetime.fromisoformat(sensing_date_str.replace('Z', '+00:00'))
                    date_diff = abs((sensing_date - center_date).days)
                except (ValueError, AttributeError):
                    date_diff = 999999
            else:
                date_diff = 999999
            
            # Add to processed results
            processed_product = {
                "Name": product_name,
                "Id": product["Id"],
                "cloud_cover_float": cloud_cover if cloud_cover is not None else 0.0,
                "aoi_coverage_pct": aoi_coverage_pct,
                "date_diff_days": date_diff,
                "sensing_date": sensing_date_str,
                "ContentLength": content_length,
                "footprint_geom_proj": footprint_geom_proj,  # Store for coverage optimization
            }
            processed_results.append(processed_product)
        
        total_filtered = len(processed_results)
        
        if not processed_results:
            return CollectionResult(
                success=True,
                downloaded_products=[],
                errors=[],
                message=f"No products met the filtering criteria (cloud < {max_cloud}%, AOI > {min_aoi}%)",
                total_products_found=total_found,
                total_products_filtered=0,
            )
        
        # Auto-select products
        selected_products = auto_select_products(
            processed_products=processed_results,
            strategy=auto_select_strategy,
            max_products=max_products,
            quality_threshold=quality_threshold,
            aoi_weight=aoi_weight,
            cloud_weight=cloud_weight,
            recency_weight=recency_weight,
            aoi_geom=aoi_geom_proj,
            aoi_area_m2=aoi_area_m2,
            target_crs=target_crs,
            min_coverage_fraction=min_coverage_fraction,
            grid_spacing_meters=grid_spacing_meters,
            solver_timeout=solver_timeout,
            coverage_cloud_weight=coverage_cloud_weight,
            coverage_quality_weight=coverage_quality_weight,
        )
        
        if not selected_products:
            return CollectionResult(
                success=True,
                downloaded_products=[],
                errors=[],
                message=f"No products selected by strategy '{auto_select_strategy}'",
                total_products_found=total_found,
                total_products_filtered=total_filtered,
            )
        
        # Download selected products
        for product in selected_products:
            product_name = product["Name"]
            product_id = product["Id"]
            cloud_cover = product.get("cloud_cover_float")
            
            # Check if already downloaded
            if check_already_downloaded(product_name, output_dir):
                console.print(f"[green]Product '{product_name}' already exists. Skipping.[/green]")
                downloaded_products.append(product_name)
                continue
            
            # Download product
            try:
                console.print(f"[cyan]Downloading {product_name}...[/cyan]")
                download_product(
                    product_id,
                    product_name=product_name,
                    access_token=access_token,
                    output_dir=output_dir,
                    node_path=None,
                )
                
                # Save metadata
                safe_dir_path = pathlib.Path(output_dir) / product_name
                metadata_file_path = safe_dir_path / "metadata.json"
                safe_dir_path.mkdir(parents=True, exist_ok=True)
                
                metadata_to_save = {
                    "product_name": product_name,
                    "odata_id": product_id,
                    "cloud_cover_percentage": cloud_cover,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "quality_score": product.get("quality_score", 0.0),
                    "aoi_coverage_percentage": product.get("aoi_coverage_pct", 0.0),
                }
                
                with open(metadata_file_path, "w") as f:
                    json.dump(metadata_to_save, f, indent=4)
                
                downloaded_products.append(product_name)
                console.print(f"[green]Successfully downloaded {product_name}[/green]")
                
            except Exception as e:
                error_msg = f"Failed to download {product_name}: {e}"
                errors.append(error_msg)
                logging.error(error_msg, exc_info=True)
                console.print(f"[red]Error: {error_msg}[/red]")
        
        # Return result
        success = len(downloaded_products) > 0
        message = f"Downloaded {len(downloaded_products)} of {len(selected_products)} selected products"
        
        return CollectionResult(
            success=success,
            downloaded_products=downloaded_products,
            errors=errors,
            message=message,
            total_products_found=total_found,
            total_products_filtered=total_filtered,
        )
        
    except Exception as e:
        error_msg = f"Collection failed: {e}"
        logging.error(error_msg, exc_info=True)
        return CollectionResult(
            success=False,
            downloaded_products=downloaded_products,
            errors=[error_msg],
            message=error_msg,
            total_products_found=0,
            total_products_filtered=0,
        )
