import argparse
import logging
import os
import sys
import re
from pathlib import Path
import glob
import rasterio
from rasterio.mask import mask
from rasterio.features import shapes
import geopandas as gpd
import numpy as np
from shapely.geometry import shape, LineString, MultiPolygon, Point
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union
from skimage.filters import threshold_minimum
from skimage.measure import find_contours
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Prompt, IntPrompt
from rich.status import Status

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
AOI_DIR = DATA_DIR / "json"
IMG_DIR = DATA_DIR / "img"
OUTPUT_DIR = SCRIPT_DIR / "output"
console = Console()


def detect_sentinel2_crs(file_path):
    utm_zone_match = re.search(r'T(\d{2})([A-Z]{3})', file_path)
    if utm_zone_match:
        zone_number = utm_zone_match.group(1)
        zone_letter = utm_zone_match.group(2)[0]  
        is_northern = zone_letter in ['N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X']

        if is_northern:
            epsg_code = f"EPSG:326{zone_number}"
            logging.info(f"Extracted UTM zone {zone_number}N from path")
        else:
            epsg_code = f"EPSG:327{zone_number}"
            logging.info(f"Extracted UTM zone {zone_number}S from path")

        try:
            import rasterio.crs
            crs = rasterio.crs.CRS.from_string(epsg_code)
            logging.info(f"Set CRS to {epsg_code} for Sentinel-2 L2A product")
            return crs
        except Exception as e:
            logging.error(f"Failed to create CRS from EPSG code {epsg_code}: {e}")
            logging.warning(f"Using fallback dictionary CRS format for {epsg_code}")
            return {'init': epsg_code.lower()}

    logging.warning("Could not extract UTM zone from Sentinel-2 file path")
    return None

def load_aoi(aoi_path):
    logging.info(f"Loading AOI: {aoi_path}")
    try:
        aoi_gdf = gpd.read_file(aoi_path)
    except Exception as e:
        logging.error(f"Failed to load AOI file {aoi_path}: {e}")
        return None, None
    if aoi_gdf.empty:
        logging.error("AOI GeoDataFrame is empty.")
        return None, None
    if aoi_gdf.crs is None:
        logging.warning("AOI CRS not set, assuming EPSG:4326.")
        aoi_gdf.crs = "EPSG:4326"
    aoi_geom = None
    if len(aoi_gdf) > 1:
        logging.info("AOI contains multiple features, combining them.")
        try:
            aoi_geom = aoi_gdf.geometry.union_all()
        except AttributeError:
            logging.warning(
                "'.unary_union' alternative."
            )
            try:
                aoi_geom = aoi_gdf.geometry.unary_union
            except Exception as e:
                logging.error(f"Failed to combine AOI geometries: {e}")
                return None, None
    else:
        aoi_geom = aoi_gdf.geometry.iloc[0]
    if (
        not aoi_geom
        or aoi_geom.is_empty
        or not (aoi_geom.geom_type == "Polygon" or aoi_geom.geom_type == "MultiPolygon")
    ):
        logging.error(
            f"AOI geometry is not a valid Polygon or MultiPolygon after loading/combining: type={aoi_geom.geom_type}"
        )
        return None, None
    if not aoi_geom.is_valid:
        logging.warning("AOI geometry is invalid, attempting buffer(0) fix.")
        aoi_geom = aoi_geom.buffer(0)
        if not aoi_geom.is_valid:
            logging.error("Buffer(0) failed to fix invalid AOI geometry.")
            return None, None
    logging.info(f"AOI loaded successfully with CRS: {aoi_gdf.crs}")
    return aoi_gdf.crs, aoi_geom

def apply_threshold(data, method="minimum"):
    valid_data = data[~np.isnan(data) & (data > 0)]
    if valid_data.size == 0:
        logging.error("No valid data found after masking for thresholding.")
        return None, None
    threshold_value = None
    try:
        threshold_value = threshold_minimum(valid_data)
    except RuntimeError as e:
        logging.error(f"Minimum threshold failed: {e}")
        return None, None
    logging.info(
        f"Applied 'minimum' threshold. Determined threshold: {threshold_value}"
    )
    binary_mask = data <= threshold_value
    return binary_mask, threshold_value

def vectorize_mask(
    binary_mask, transform, crs, min_sea_area_m2=10000.0, min_island_area_m2=50000.0
):
    logging.info("Vectorizing all water polygons from mask...")
    binary_mask = binary_mask.astype(bool)
    try:
        results = list(
            shapes(
                binary_mask.astype(np.uint8),
                mask=binary_mask,
                transform=transform,
                connectivity=4,
            )
        )
    except Exception as e:
        logging.error(f"Error during rasterio.features.shapes: {e}")
        return None
    water_polygons_initial = [shape(s) for s, v in results if v == 1]
    if not water_polygons_initial:
        logging.warning("Polygon vectorization resulted in no valid water features.")
        return None
    logging.info(f"Generated {len(water_polygons_initial)} initial water polygons.")
    gdf_polygons = gpd.GeoDataFrame({"geometry": water_polygons_initial}, crs=crs)
    if not gdf_polygons.crs.is_projected:
        logging.warning(
            f"CRS '{gdf_polygons.crs}' is not projected. Area calculation might be inaccurate."
        )
    gdf_polygons["area"] = gdf_polygons.geometry.area
    if gdf_polygons.empty:
        logging.info("No water polygons found after initial vectorization.")
        return None
    max_area = gdf_polygons["area"].max()
    if max_area < min_sea_area_m2:
        logging.warning(
            f"Largest water body area ({max_area:.2f} m^2) is below threshold ({min_sea_area_m2} m^2). No significant sea polygon found."
        )
        return None
    largest_polygons = gdf_polygons[gdf_polygons["area"] == max_area]
    logging.info(
        f"Found {len(largest_polygons)} polygon(s) with max area {max_area:.2f} m^2 (threshold: {min_sea_area_m2} m^2). Assuming this is the main sea body."
    )
    shoreline_lines = []
    total_interiors_found = 0
    kept_interiors = 0
    logging.info(f"Filtering islands with area < {min_island_area_m2} m^2...")
    for geom in largest_polygons.geometry:
        if not geom.is_valid:
            logging.warning(
                f"Largest polygon geometry is invalid, attempting buffer(0) fix."
            )
            geom = geom.buffer(0)
            if not geom.is_valid:
                logging.error(
                    "Buffer(0) failed to fix invalid geometry. Skipping this polygon."
                )
                continue
        if geom.geom_type == "Polygon":
            shoreline_lines.append(geom.exterior)
            total_interiors_found += len(geom.interiors)
            for interior in geom.interiors:
                try:
                    island_poly = ShapelyPolygon(interior)
                    if island_poly.is_valid and island_poly.area >= min_island_area_m2:
                        shoreline_lines.append(interior)
                        kept_interiors += 1
                except Exception as e:
                    logging.warning(f"Could not process an interior ring (island): {e}")
        elif geom.geom_type == "MultiPolygon":
            for poly in geom.geoms:
                if not poly.is_valid:
                    logging.warning(
                        f"Part of largest multipolygon geometry is invalid, attempting buffer(0) fix."
                    )
                    poly = poly.buffer(0)
                    if not poly.is_valid:
                        logging.error(
                            "Buffer(0) failed to fix invalid part. Skipping this part."
                        )
                        continue
                shoreline_lines.append(poly.exterior)
                total_interiors_found += len(poly.interiors)
                for interior in poly.interiors:
                    try:
                        island_poly = ShapelyPolygon(interior)
                        if (
                            island_poly.is_valid
                            and island_poly.area >= min_island_area_m2
                        ):
                            shoreline_lines.append(interior)
                            kept_interiors += 1
                    except Exception as e:
                        logging.warning(
                            f"Could not process an interior ring (island): {e}"
                        )
    if not shoreline_lines:
        logging.warning(
            "Could not extract any shoreline features (exterior/interiors) from the largest water polygon(s) or no islands met the area threshold."
        )
        return None
    logging.info(
        f"Found {total_interiors_found} total island candidates. Kept {kept_interiors} islands with area >= {min_island_area_m2} m^2."
    )
    raw_shorelines_gdf = gpd.GeoDataFrame({"geometry": shoreline_lines}, crs=crs)
    logging.info(
        f"Extracted {len(raw_shorelines_gdf)} raw shoreline features (coastline + filtered islands) from largest water body."
    )
    return raw_shorelines_gdf


def apply_subpixel_refinement(binary_mask, transform, shorelines_gdf, aoi_polygon):
    logging.info("Applying subpixel refinement using marching squares method...")
    contours = find_contours(binary_mask.astype(float), 0.5)
    if not contours:
        logging.warning("No contours found during subpixel refinement.")
        return shorelines_gdf
    minx, miny, maxx, maxy = aoi_polygon.bounds
    width_deg = maxx - minx
    height_deg = maxy - miny
    buffer_percentage = 0.02
    buffer_distance = -min(width_deg, height_deg) * buffer_percentage
    try:
        inner_polygon = aoi_polygon.buffer(buffer_distance)
        if inner_polygon.is_empty or not inner_polygon.is_valid:
            raise ValueError("Buffer resulted in an empty or invalid polygon")
        logging.info(
            f"Created negative buffer with {buffer_percentage*100}% of AOI dimensions ({buffer_distance} degrees)."
        )
    except Exception as e:
        logging.warning(
            f"Negative buffer failed: {str(e)}. Creating manual inner rectangle."
        )
        shrink_factor = buffer_percentage
        inner_minx = minx + (width_deg * shrink_factor)
        inner_miny = miny + (height_deg * shrink_factor)
        inner_maxx = maxx - (width_deg * shrink_factor)
        inner_maxy = maxy - (height_deg * shrink_factor)
        inner_coords = [
            (inner_minx, inner_miny),
            (inner_minx, inner_maxy),
            (inner_maxx, inner_maxy),
            (inner_maxx, inner_miny),
            (inner_minx, inner_miny),
        ]
        inner_polygon = ShapelyPolygon(inner_coords)
        logging.info(
            f"Created manual inner rectangle with {shrink_factor*100}% shrinkage from each edge."
        )
    final_lines = []
    for orig_line in shorelines_gdf.geometry:
        orig_buffer = orig_line.buffer(50.0)
        best_contour = None
        best_score = float("inf")
        for contour in contours:
            world_coords = []
            for point in contour:
                y, x = point[0], point[1]
                world_x, world_y = transform * (x, y)
                world_coords.append((world_x, world_y))
            if len(world_coords) < 2:
                continue
            temp_line = LineString(world_coords)
            if not temp_line.intersects(orig_buffer):
                continue
            dist_score = orig_line.hausdorff_distance(temp_line)
            length_ratio = abs(temp_line.length - orig_line.length) / max(
                orig_line.length, 1.0
            )
            combined_score = dist_score + (length_ratio * 100)
            if combined_score < best_score:
                best_score = combined_score
                best_contour = world_coords
        if best_contour and len(best_contour) >= 2:
            filtered_coords = []
            for point in best_contour:
                point_geom = Point(point)
                if inner_polygon.contains(point_geom):
                    filtered_coords.append(point)
            if len(filtered_coords) >= 2:
                refined_line = LineString(filtered_coords)
                final_lines.append(refined_line)
                logging.debug(
                    f"Added refined line with {len(filtered_coords)} points (from {len(best_contour)} original points)"
                )
            else:
                logging.debug(
                    f"Skipped line - not enough points after filtering ({len(filtered_coords)} points)"
                )
        else:
            final_lines.append(orig_line)
            logging.debug("Using original line (no good contour match)")
    final_gdf = gpd.GeoDataFrame({"geometry": final_lines}, crs=shorelines_gdf.crs)
    logging.info(
        f"Subpixel refinement complete. Refined {len(final_lines)} shoreline features."
    )
    return final_gdf

def extract_shoreline(
    b8_file_path,
    aoi_path,
    output_path,
    min_sea_area_m2=10000.0,
    min_island_area_m2=50000.0,
):
    logging.info(
        f"Starting shoreline extraction for file {b8_file_path} using AOI {aoi_path}"
    )
    logging.info(f"Using threshold method: minimum")
    logging.info(
        f"Filtering strategy: Shorelines from largest water body (min area: {min_sea_area_m2} m^2), islands filtered (min area: {min_island_area_m2} m^2), clipped to AOI."
    )
    if not Path(b8_file_path).is_file():
        logging.error(f"Input Band 8 file not found: {b8_file_path}")
        return
    aoi_crs, aoi_geom = load_aoi(aoi_path)
    if aoi_geom is None:
        return
    try:
        with rasterio.open(b8_file_path) as src:
            logging.info(f"Opened raster: {b8_file_path}")
            raster_crs = src.crs
            nodata_val = src.nodata

            if raster_crs is None:
                logging.warning("Raster CRS is None. This is a Sentinel-2 L2A product, setting appropriate UTM CRS.")
                raster_crs = detect_sentinel2_crs(b8_file_path)

                if raster_crs is None:
                    logging.error("Failed to detect CRS from Sentinel-2 file path. Cannot proceed.")
                    return

                logging.info(f"Using detected CRS {raster_crs} for processing without modifying read-only raster")

            aoi_geom_proj = None
            if aoi_crs != raster_crs:
                logging.info(f"Reprojecting AOI from {aoi_crs} to {raster_crs}")
                try:
                    # Create a GeoDataFrame with the AOI geometry
                    aoi_gdf = gpd.GeoDataFrame([1], geometry=[aoi_geom], crs=aoi_crs)

                    # Handle both CRS object and dictionary format
                    if isinstance(raster_crs, dict) and 'init' in raster_crs:
                        # For dictionary format CRS
                        epsg_code = raster_crs['init'].upper()
                        if epsg_code.startswith('EPSG:'):
                            epsg_num = int(epsg_code.split(':')[1])
                            logging.info(f"Using EPSG code {epsg_num} for reprojection")
                            aoi_gdf_proj = aoi_gdf.to_crs(epsg=epsg_num)
                        else:
                            logging.warning(f"Unsupported CRS format: {raster_crs}")
                            raise ValueError(f"Unsupported CRS format: {raster_crs}")
                    else:
                        aoi_gdf_proj = aoi_gdf.to_crs(raster_crs)

                    try:
                        aoi_geom_proj = aoi_gdf_proj.geometry.union_all()
                    except AttributeError:
                        logging.warning(
                            "'.union_all()' method not found, trying older '.unary_union' attribute for reprojection."
                        )
                        try:
                            aoi_geom_proj = aoi_gdf_proj.geometry.unary_union
                        except Exception as e:
                            logging.error(
                                f"Failed to combine reprojected AOI geometries: {e}"
                            )
                            return
                except Exception as e:
                    logging.warning(f"AOI reprojection failed: {e}")
                    logging.warning("AOI geometry is invalid or became empty after projection. Creating a fallback polygon.")
                    bounds = src.bounds
                    center_x = (bounds.left + bounds.right) / 2
                    center_y = (bounds.bottom + bounds.top) / 2
                    width = (bounds.right - bounds.left) * 0.8 
                    height = (bounds.top - bounds.bottom) * 0.8 
                    minx = center_x - width/2
                    miny = center_y - height/2
                    maxx = center_x + width/2
                    maxy = center_y + height/2
                    utm_coords = [
                        (minx, miny),
                        (minx, maxy),
                        (maxx, maxy),
                        (maxx, miny),
                        (minx, miny)
                    ]

                    aoi_geom_proj = ShapelyPolygon(utm_coords)
                    logging.info(f"Created fallback polygon in UTM zone with bounds: {aoi_geom_proj.bounds}")
            else:
                aoi_geom_proj = aoi_geom

            if aoi_geom_proj is None or aoi_geom_proj.is_empty:
                logging.error(
                    "AOI geometry is invalid or became empty after projection."
                )
                return

            if not aoi_geom_proj.is_valid:
                logging.warning(
                    "Projected AOI geometry is invalid, attempting buffer(0) fix."
                )
                aoi_geom_proj = aoi_geom_proj.buffer(0)
                if not aoi_geom_proj.is_valid:
                    logging.error(
                        "Buffer(0) failed to fix invalid projected AOI geometry."
                    )
                    return

            logging.info("Clipping Band 8 raster to AOI...")
            try:
                out_image, out_transform = mask(
                    src,
                    [aoi_geom_proj],
                    crop=True,
                    all_touched=True,
                    nodata=nodata_val if nodata_val is not None else 0,
                )
                out_meta = src.meta.copy()
            except ValueError as e:
                logging.error(
                    f"Error during raster masking. Check AOI overlap with raster bounds ({src.bounds}): {e}"
                )
                return
            except Exception as e:
                logging.error(f"An unexpected error occurred during masking: {e}")
                return

            out_meta.update(
                {
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "crs": raster_crs,
                    "nodata": nodata_val if nodata_val is not None else 0,
                }
            )

            clipped_b8_data = out_image[0].astype(float)
            current_nodata = out_meta["nodata"]
            if current_nodata is not None:
                clipped_b8_data[clipped_b8_data == current_nodata] = np.nan
            else:
                clipped_b8_data[clipped_b8_data == 0] = np.nan

            binary_mask, _ = apply_threshold(clipped_b8_data)
            if binary_mask is None:
                logging.error("Thresholding failed, cannot proceed.")
                return

            logging.info(
                f"Vectorizing mask to find largest sea body (min area {min_sea_area_m2} m^2) and filter islands (min area {min_island_area_m2} m^2)..."
            )
            raw_shorelines_gdf = vectorize_mask(
                binary_mask,
                out_transform,
                out_meta["crs"],
                min_sea_area_m2=min_sea_area_m2,
                min_island_area_m2=min_island_area_m2,
            )

            if raw_shorelines_gdf is None:
                logging.error(
                    "Vectorization failed or yielded no significant sea body / shorelines after island filtering."
                )
                return

            logging.info(
                f"Clipping {len(raw_shorelines_gdf)} raw shorelines (coast/filtered islands) to AOI polygon interior..."
            )
            clipped_lines = []
            aoi_polygon_for_clipping = aoi_geom_proj

            for line in raw_shorelines_gdf.geometry:
                if not line.is_valid:
                    logging.warning(
                        "Raw shoreline segment is invalid, attempting buffer(0)."
                    )
                    line = line.buffer(0)
                    if not line.geom_type.startswith("LineString"):
                        logging.warning(
                            f"Skipping geometry after buffer(0) resulted in non-LineString type: {line.geom_type}"
                        )
                        continue
                clipped = line.intersection(aoi_polygon_for_clipping)
                if not clipped.is_empty:
                    if clipped.geom_type == "LineString":
                        clipped_lines.append(clipped)
                    elif clipped.geom_type == "MultiLineString":
                        clipped_lines.extend(list(clipped.geoms))

            clipped_shorelines_gdf = gpd.GeoDataFrame(
                {"geometry": clipped_lines}, crs=raw_shorelines_gdf.crs
            )

            if clipped_shorelines_gdf.empty:
                logging.warning(
                    "No shoreline features remained after clipping to AOI interior."
                )
                return

            logging.info(
                f"{len(clipped_shorelines_gdf)} shoreline features remain after clipping to AOI."
            )

            final_shorelines_gdf = apply_subpixel_refinement(
                binary_mask, out_transform, clipped_shorelines_gdf, aoi_geom_proj
            )

            logging.info(
                f"Saving final refined shoreline LineString features to {output_path}..."
            )
            final_shorelines_gdf.to_file(output_path, driver="GeoJSON")
            logging.info(
                f"Saved {len(final_shorelines_gdf)} final shoreline LineString features to {output_path}"
            )
            logging.info("Shoreline extraction complete.")

    except rasterio.RasterioIOError as e:
        logging.error(f"Error opening or reading raster file {b8_file_path}: {e}")
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
    except Exception as e:
        logging.error(
            f"An unexpected error occurred in extract_shoreline: {e}", exc_info=True
        )


def find_aoi_files():
    if not AOI_DIR.is_dir():
        console.print(f"[red]Error:[/red] AOI directory not found: {AOI_DIR}")
        return []
    return sorted(list(AOI_DIR.glob("*.geojson")))

def select_aoi_file():
    aoi_files = find_aoi_files()
    if not aoi_files:
        console.print(f"[red]Error:[/red] No GeoJSON files found in {AOI_DIR}.")
        console.print("Please place a GeoJSON file in this directory.")
        return None
    if len(aoi_files) == 1:
        selected_file = aoi_files[0]
        console.print(f"[green]Using AOI file:[/green] {selected_file.name}")
        return selected_file
    table = Table(
        title="Select AOI GeoJSON File",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Filename", style="cyan", no_wrap=True)
    for idx, file_path in enumerate(aoi_files):
        table.add_row(str(idx + 1), file_path.name)
    console.print(table)
    while True:
        choice = IntPrompt.ask(
            "Enter the number of the AOI file to use", console=console
        )
        if 1 <= choice <= len(aoi_files):
            selected_file = aoi_files[choice - 1]
            console.print(f"[green]Selected:[/green] {selected_file.name}")
            return selected_file
        else:
            console.print(
                f"[red]Invalid choice.[/red] Please enter a number between 1 and {len(aoi_files)}."
            )

def find_band8_files():
    if not IMG_DIR.is_dir():
        console.print(f"[red]Error:[/red] Image directory not found: {IMG_DIR}")
        return []
    b8_files = []
    jp2_files = glob.glob(str(IMG_DIR) + "/**/*B08*10m.jp2", recursive=True)
    b8_files.extend(jp2_files)
    tif_files = glob.glob(str(IMG_DIR) + "/**/*B08*10m.tif", recursive=True)
    b8_files.extend(tif_files)
    return sorted(b8_files)

def select_band8_file():
    b8_files = find_band8_files()
    if not b8_files:
        console.print(
            f"[red]Error:[/red] No Band 8 files found in {IMG_DIR} (recursive search)."
        )
        console.print("Please place Sentinel-2 data in this directory.")
        return None
    if len(b8_files) == 1:
        selected_file = b8_files[0]
        console.print(
            f"[green]Using Band 8 file:[/green] {os.path.basename(selected_file)}"
        )
        return selected_file
    table = Table(
        title="Select Band 8 File",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Filename", style="cyan", no_wrap=True)
    for idx, file_path in enumerate(b8_files):
        table.add_row(str(idx + 1), os.path.basename(file_path))
    console.print(table)
    while True:
        choice = IntPrompt.ask(
            "Enter the number of the Band 8 file to use", console=console
        )
        if 1 <= choice <= len(b8_files):
            selected_file = b8_files[choice - 1]
            console.print(f"[green]Selected:[/green] {os.path.basename(selected_file)}")
            return selected_file
        else:
            console.print(
                f"[red]Invalid choice.[/red] Please enter a number between 1 and {len(b8_files)}."
            )

def generate_output_path(b8_file_path, aoi_path):
    aoi_name = Path(aoi_path).stem
    b8_file = Path(b8_file_path)
    parts = b8_file.parts
    product_name = None
    for part in parts:
        if part.startswith("S2") and ".SAFE" in part:
            product_name = part.split(".SAFE")[0]
            break
    if not product_name:
        filename = b8_file.name
        tile_id = None
        for part in filename.split("_"):
            if part.startswith("T") and len(part) == 6:
                tile_id = part
                break
        if tile_id:
            product_name = tile_id
        else:
            product_name = "sentinel2"
    output_filename = f"shoreline_{aoi_name}_{product_name}.geojson"
    output_path = OUTPUT_DIR / output_filename
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extracts shorelines (coastline and island boundaries) from a Sentinel-2 Band 8 NIR file within a given AOI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--b8_input_file",
        type=str,
        help="Path to the input Sentinel-2 Band 8 file (e.g., *_B08_10m.jp2 or .tif). If not provided, will prompt to select from available files.",
    )
    parser.add_argument(
        "--aoi_path",
        type=str,
        help="Path to the Area of Interest (AOI) GeoJSON file. If not provided, will prompt to select from available files.",
    )
    parser.add_argument(
        "--output_geojson",
        type=str,
        help="Full path for the output shoreline GeoJSON file. If not provided, will generate based on AOI and product names.",
    )
    parser.add_argument(
        "--min_sea_area",
        type=float,
        default=10000.0,
        dest="min_sea_area_m2",
        help="Minimum area in square meters for the largest water body to be considered the 'sea'.",
    )
    parser.add_argument(
        "--min_island_area",
        type=float,
        default=50000.0,
        dest="min_island_area_m2",
        help="Minimum area in square meters for an island's shoreline to be included.",
    )
    parser.add_argument(
        "--loglevel",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level for console output.",
    )
    args = parser.parse_args()
    log_level = getattr(logging, args.loglevel.upper(), logging.INFO)
    log_dir = SCRIPT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "shoreline_extractor.log"
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=str(log_file),
        filemode="a",
        force=True,
    )
    logging.info(f"Logging level set to {args.loglevel.upper()}")
    console.print(Rule("[bold magenta]Shoreline Extractor[/]"))
    aoi_path = args.aoi_path
    if not aoi_path:
        console.print(Rule("[bold cyan]Select Area of Interest[/]"))
        aoi_file = select_aoi_file()
        if not aoi_file:
            console.print("[red]Error:[/red] No AOI file selected. Exiting.")
            sys.exit(1)
        aoi_path = str(aoi_file)
    else:
        console.print(
            f"[green]Using provided AOI file:[/green] {os.path.basename(aoi_path)}"
        )
    b8_file_path = args.b8_input_file
    if not b8_file_path:
        console.print(Rule("[bold cyan]Select Band 8 File[/]"))
        b8_file = select_band8_file()
        if not b8_file:
            console.print("[red]Error:[/red] No Band 8 file selected. Exiting.")
            sys.exit(1)
        b8_file_path = b8_file
    else:
        console.print(
            f"[green]Using provided Band 8 file:[/green] {os.path.basename(b8_file_path)}"
        )
    output_path = args.output_geojson
    if not output_path:
        output_path = str(generate_output_path(b8_file_path, aoi_path))
        console.print(f"[blue]Generated output path:[/blue] {output_path}")
    else:
        console.print(f"[blue]Using provided output path:[/blue] {output_path}")
    output_path_obj = Path(output_path)
    output_dir = output_path_obj.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]Ensured output directory exists:[/green] {output_dir}")
    except OSError as e:
        console.print(
            f"[red]Error:[/red] Could not create output directory {output_dir}: {e}"
        )
        sys.exit(1)
    console.print(Rule("[bold cyan]Processing[/]"))
    with Status(
        "[yellow]Extracting shoreline...[/yellow] This may take a few moments.",
        spinner="dots",
    ) as status:
        extract_shoreline(
            b8_file_path,
            aoi_path,
            output_path,
            args.min_sea_area_m2,
            args.min_island_area_m2,
        )
    console.print(Rule("[bold green]Extraction Complete[/]"))
    console.print(f"[green]Shoreline extracted successfully to:[/green] {output_path}")
