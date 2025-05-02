import argparse
import json
import logging
import math
import os
import pathlib
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import geopandas as gpd
import pyproj
import requests
from dotenv import load_dotenv
from downloader import download_product, list_product_nodes
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.filesize import decimal
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.rule import Rule
from rich.status import Status
from rich.table import Table
from shapely.errors import GEOSException
from shapely.geometry import Polygon
from shapely.wkt import dumps as wkt_dumps
from shapely.wkt import loads as wkt_loads

CDSE_BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/"
PRODUCTS_ENDPOINT = "Products"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT_API = "%Y-%m-%dT%H:%M:%S.%fZ"
MAX_RESULTS_PER_PAGE = 100
SCRIPT_DIR = pathlib.Path(__file__).parent
SRC_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SRC_DIR.parent
DEFAULT_AOI_DIR = PROJECT_ROOT / "src" / "shoreline_extractor" / "data" / "json"
console = Console()


def get_access_token():
    load_dotenv()
    token = os.getenv("CDSE_ACCESS_TOKEN")
    username = os.getenv("CDSE_USERNAME")
    password = os.getenv("CDSE_PASSWORD")
    if token:
        console.print("[green]Using access token from environment variable.[/green]")
        return token
    if username and password:
        token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        data = {
            "client_id": "cdse-public",
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        try:
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("access_token")
            if access_token:
                console.print("[green]Successfully obtained access token.[/green]")
                return access_token
            else:
                console.print(
                    "[red]Error:[/red] 'access_token' not found in response.",
                    response.text,
                )
                sys.exit(1)
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error fetching token:[/red] {e}")
            console.print(
                "Please provide credentials in .env or set CDSE_ACCESS_TOKEN."
            )
            sys.exit(1)
        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Could not decode token response JSON.")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]An unexpected error occurred loading token:[/red] {e}")
            sys.exit(1)
    console.print(
        "[red]Error:[/red] CDSE credentials (username/password) or access token not found."
    )
    console.print(
        "Please set CDSE_USERNAME and CDSE_PASSWORD, or CDSE_ACCESS_TOKEN in your .env file or environment."
    )
    sys.exit(1)


def load_aoi_data(geojson_path: str) -> tuple[str, gpd.GeoDataFrame]:
    console = Console()
    try:
        logging.info(f"Loading AOI from: {geojson_path}")
        aoi_gdf = gpd.read_file(geojson_path)
        if aoi_gdf.empty:
            logging.error("AOI GeoDataFrame is empty after loading.")
            return None, None
        if aoi_gdf.crs is None:
            logging.warning(
                "AOI file has no CRS defined. Assuming EPSG:4326 (WGS84). Verify this is correct!"
            )
            try:
                aoi_gdf.crs = "EPSG:4326"
            except Exception as crs_err:
                logging.error(f"Failed to set assumed CRS EPSG:4326: {crs_err}")
                return None, None
        logging.info(f"Initial AOI CRS: {aoi_gdf.crs}")
        aoi_gdf = aoi_gdf.explode(index_parts=True)
        aoi_gdf = aoi_gdf[aoi_gdf.geometry.geom_type == "Polygon"]
        if aoi_gdf.empty:
            logging.error("No valid Polygon geometries found in the AOI file.")
            return None, None
        if len(aoi_gdf) > 1:
            logging.info(
                f"AOI contains {len(aoi_gdf)} polygons. Performing unary union."
            )
            try:
                unified_geom = aoi_gdf.geometry.unary_union
                if unified_geom.geom_type != "Polygon":
                    logging.warning(
                        f"Unary union resulted in a {unified_geom.geom_type}, not a Polygon. Attempting convex hull."
                    )
                    unified_geom = unified_geom.convex_hull
                    if unified_geom.geom_type != "Polygon":
                        logging.error(
                            "Could not obtain a single Polygon after union/convex hull."
                        )
                        return None, None
                aoi_gdf = gpd.GeoDataFrame(
                    [1], geometry=[unified_geom], crs=aoi_gdf.crs
                )
            except Exception as union_err:
                logging.error(f"Error during unary union of AOI polygons: {union_err}")
                return None, None
        aoi_shapely = aoi_gdf.geometry.iloc[0]
        if not isinstance(aoi_shapely, Polygon):
            logging.error(
                f"Final AOI geometry is not a Polygon (type: {aoi_shapely.geom_type})"
            )
            return None, None
        if not aoi_shapely.is_valid:
            logging.warning("AOI geometry is invalid, attempting buffer(0) fix.")
            aoi_shapely_fixed = aoi_shapely.buffer(0)
            if (
                not aoi_shapely_fixed.is_valid
                or aoi_shapely_fixed.is_empty
                or not isinstance(aoi_shapely_fixed, Polygon)
            ):
                logging.error(
                    "Buffer(0) failed to fix invalid AOI geometry or resulted in non-polygon/empty."
                )
                return None, None
            aoi_gdf = gpd.GeoDataFrame(
                [1], geometry=[aoi_shapely_fixed], crs=aoi_gdf.crs
            )
            logging.info("AOI geometry fixed using buffer(0).")
        logging.info(
            f"Validated AOI geometry: Type={aoi_gdf.geometry.iloc[0].geom_type}, CRS={aoi_gdf.crs}"
        )
        try:
            aoi_gdf_4326 = aoi_gdf.to_crs("EPSG:4326")
            aoi_wkt_4326 = wkt_dumps(aoi_gdf_4326.geometry.iloc[0])
            api_wkt = f"SRID=4326;{aoi_wkt_4326}"
            logging.info(f"Generated API WKT (EPSG:4326) for query: {api_wkt[:100]}...")
        except Exception as wkt_err:
            logging.error(
                f"Failed to reproject AOI to EPSG:4326 for WKT generation: {wkt_err}"
            )
            return (
                None,
                aoi_gdf,
            )
        return api_wkt, aoi_gdf
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] AOI file not found at {geojson_path}")
        return None, None
    except Exception as e:
        console.print(f"[red]An unexpected error occurred loading AOI:[/red] {e}")
        logging.error(f"Unexpected AOI loading error: {e}", exc_info=True)
        return None, None


def calculate_central_date(start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, DATE_FORMAT)
    end_date = datetime.strptime(end_date_str, DATE_FORMAT)
    return start_date + (end_date - start_date) / 2


def build_odata_query(
    aoi_wkt: str,
    start_date_str: str,
    end_date_str: str,
    max_cloud_cover: int = 100,
    product_level: str = "L2A",
    satellite: str = "SENTINEL-2",
) -> str:
    intersects_filter = f"OData.CSC.Intersects(area=geography'{aoi_wkt}')"
    date_filter = f"ContentDate/Start ge {start_date_str}T00:00:00.000Z and ContentDate/Start le {end_date_str}T23:59:59.999Z"
    cloud_filter = f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {max_cloud_cover})"
    base_filter = f"{intersects_filter} and {date_filter} and {cloud_filter}"
    if product_level.upper() == "L2A":
        product_filter = "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A')"
        final_filter = f"{base_filter} and {product_filter}"
    else:
        final_filter = base_filter
    collection_filter = f"Collection/Name eq '{satellite}'"
    final_filter = f"({final_filter}) and {collection_filter}"
    params_unquoted = {
        "$format": "json",
        "$filter": final_filter,
        "$expand": "Attributes",
        "$orderby": "ContentDate/Start desc",
    }
    query_string_parts = []
    odata_filter_safe_chars = "()'=;:/,"
    for key, value in params_unquoted.items():
        if key == "$filter":
            quoted_value = quote(value, safe=odata_filter_safe_chars)
        else:
            quoted_value = quote(str(value))
        query_string_parts.append(f"{key}={quoted_value}")
    full_query_url = (
        f"{CDSE_BASE_URL}{PRODUCTS_ENDPOINT}?{'&'.join(query_string_parts)}"
    )
    logging.info(f"Constructed OData Query URL: {full_query_url[:300]}...")
    return full_query_url


def fetch_products(
    access_token: str,
    initial_query_params: dict[str, Any],
    status: Status | None = None,
    direct_url: str | None = None,
) -> list[dict[str, Any]]:
    all_products = []
    headers = {"Authorization": f"Bearer {access_token}"}
    next_link = direct_url if direct_url else f"{CDSE_BASE_URL}{PRODUCTS_ENDPOINT}"
    current_params = None if direct_url else initial_query_params
    request_count = 0
    session = requests.Session()
    while next_link:
        if status:
            status.update(f"Fetching page {request_count + 1}...")
        try:
            req = requests.Request(
                "GET", next_link, params=current_params, headers=headers
            )
            prepared_req = session.prepare_request(req)
            logging.info(
                f"Prepared Request URL (Page {request_count + 1}): {prepared_req.url}"
            )
            response = session.send(prepared_req, timeout=60)
            response.raise_for_status()
            data = response.json()
            products = data.get("value", [])
            all_products.extend(products)
            next_link = data.get("@odata.nextLink")
            request_count += 1
            current_params = None
            logging.debug(
                f"Page {request_count}: Fetched {len(products)} products. Total: {len(all_products)}. Next page: {'Yes' if next_link else 'No'}"
            )
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            console.print(f"[red]Error:[/red] Failed to fetch data from CDSE API: {e}")
            break
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode API response JSON: {e}")
            console.print("[red]Error:[/red] Invalid JSON received from CDSE API.")
            break
    if status:
        status.update(
            f"Fetched {len(all_products)} total products across {request_count} pages."
        )
    logging.info(f"Completed fetching products. Total found: {len(all_products)}.")
    return all_products


def get_utm_crs(lon, lat):
    """
    Get the UTM CRS for a given longitude and latitude.

    Args:
        lon: Longitude in decimal degrees
        lat: Latitude in decimal degrees

    Returns:
        pyproj.CRS: The UTM CRS for the given coordinates
    """
    utm_band = str(math.floor((lon + 180) / 6) + 1).zfill(2)
    if lat >= 0:
        epsg_code = "326" + utm_band
    else:
        epsg_code = "327" + utm_band
    try:
        return pyproj.CRS(f"EPSG:{epsg_code}")
    except pyproj.exceptions.CRSError:
        logging.warning(
            f"Could not determine UTM CRS for EPSG:{epsg_code}. Falling back to EPSG:3857."
        )
        return pyproj.CRS("EPSG:3857")


def check_aoi_utm_zones(geometry, crs="EPSG:4326"):
    if crs != "EPSG:4326":
        transformer = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

        def transform_coords(x, y):
            return transformer.transform(x, y)

        from shapely.ops import transform
        geometry = transform(transform_coords, geometry)

    minx, miny, maxx, maxy = geometry.bounds

    utm_zones = set()
    for lon in [minx, maxx]:
        utm_band = math.floor((lon + 180) / 6) + 1
        utm_zones.add(utm_band)

    spans_multiple_zones = len(utm_zones) > 1

    if spans_multiple_zones:
        in_europe = (minx >= -10 and maxx <= 40 and miny >= 35 and maxy <= 75)

        if in_europe:
            recommended_crs = pyproj.CRS("EPSG:3035")
        else:

            recommended_crs = pyproj.CRS("EPSG:6933")
    else:
        utm_zone = list(utm_zones)[0]
        is_northern = (miny + maxy) / 2 >= 0

        if is_northern:
            epsg_code = f"EPSG:326{utm_zone:02d}"
        else:
            epsg_code = f"EPSG:327{utm_zone:02d}"

        try:
            recommended_crs = pyproj.CRS(epsg_code)
        except pyproj.exceptions.CRSError:
            logging.warning(f"Could not create CRS for {epsg_code}, falling back to EPSG:3857")
            recommended_crs = pyproj.CRS("EPSG:3857")

    return spans_multiple_zones, list(utm_zones), recommended_crs


def process_products(
    products: list[dict[str, Any]],
    aoi_gdf: gpd.GeoDataFrame,
    center_date: datetime,
    end_date_obj: datetime,
    access_token: str,
    min_aoi_coverage: float = 0,
    output_dir: str = ".",
) -> list[dict[str, Any]]:
    console = Console()
    logging.info(f"Processing {len(products)} potential products.")
    if aoi_gdf is None or aoi_gdf.empty:
        logging.error("Invalid or empty AoI GeoDataFrame provided to process_products.")
        return []
    if aoi_gdf.crs is None:
        logging.error("AOI GeoDataFrame missing CRS in process_products.")
        return []
    try:
        aoi_geom = aoi_gdf.geometry.iloc[0]
        if not isinstance(aoi_geom, Polygon):
            logging.error(
                f"AOI geometry in GeoDataFrame is not a Polygon ({aoi_geom.geom_type}) in process_products."
            )
            return []
    except IndexError:
        logging.error("AOI GeoDataFrame has no geometry in process_products.")
        return []

    aoi_crs = aoi_gdf.crs
    logging.info(f"Processing using AOI with original CRS: {aoi_crs}")

    try:
        aoi_gdf_wgs84 = aoi_gdf.to_crs("EPSG:4326")
        aoi_geom_wgs84 = aoi_gdf_wgs84.geometry.iloc[0]
        aoi_centroid_wgs84 = aoi_geom_wgs84.centroid
        logging.info(f"Successfully reprojected AOI to WGS84 (EPSG:4326)")
    except Exception as e:
        logging.error(f"Failed to reproject AOI to WGS84: {e}", exc_info=True)
        return []

    spans_multiple_zones, utm_zones, recommended_crs = check_aoi_utm_zones(aoi_geom_wgs84)

    if spans_multiple_zones:
        logging.warning(
            f"AOI spans multiple UTM zones: {utm_zones}. "
            f"Using {recommended_crs.name} for area calculations instead of a single UTM zone."
        )
        console.print(
            f"[yellow]Warning:[/yellow] AOI spans multiple UTM zones: {utm_zones}. "
            f"Using {recommended_crs.name} for area calculations."
        )
        target_crs = recommended_crs
    else:
        logging.info(f"AOI is contained within a single UTM zone: {utm_zones[0]}")
        target_crs = get_utm_crs(aoi_centroid_wgs84.x, aoi_centroid_wgs84.y)

    logging.info(f"Using CRS for area calculation: {target_crs.name} ({target_crs.to_epsg() if target_crs.is_projected else 'non-projected'})")

    try:
        aoi_gdf_proj = aoi_gdf_wgs84.to_crs(target_crs)
        aoi_geom_proj = aoi_gdf_proj.geometry.iloc[0]
        aoi_area_m2 = aoi_geom_proj.area
        if aoi_area_m2 <= 0:
            logging.warning(
                f"Projected AOI area is zero or negative ({aoi_area_m2:.2f} m²) in CRS {target_crs.name}. "
                f"Coverage calculation may be inaccurate."
            )
        else:
            logging.info(f"Projected AOI Area: {aoi_area_m2:.2f} m² in CRS {target_crs.name}")
    except Exception as e:
        logging.error(
            f"Error during AOI reprojection to {target_crs.name} or area calculation: {e}. "
            f"Proceeding without accurate coverage.",
            exc_info=True,
        )
        aoi_area_m2 = 0.0

    processed_results = []
    product_map = {}
    display_id_counter = 1
    products.sort(key=lambda p: p.get("ContentDate", {}).get("Start"), reverse=True)
    processed_count = 0

    for product in products:
        product_name = product["Name"]
        product_odata_id = product["Id"]
        attributes = {
            attr["Name"]: attr["Value"] for attr in product.get("Attributes", [])
        }
        cloud_cover = attributes.get("cloudCover", None)
        if isinstance(cloud_cover, str):
            try:
                cloud_cover = float(cloud_cover)
            except ValueError:
                console.print(
                    f"[yellow]Warning:[/yellow] Invalid cloud cover value '{cloud_cover}' for {product_name}"
                )
                cloud_cover = None
        product["cloud_cover_float"] = cloud_cover
        sensing_date_str = product.get("ContentDate", {}).get("Start")
        sensing_date = None
        days_from_end = None
        if sensing_date_str:
            try:
                sensing_date = datetime.fromisoformat(
                    sensing_date_str.replace("Z", "+00:00")
                )
                days_from_end = (end_date_obj - sensing_date.date()).days
            except ValueError:
                console.print(
                    f"[yellow]Warning:[/yellow] Invalid date format '{sensing_date_str}' for {product_name}"
                )

        aoi_coverage_percent = None
        product_geom = None
        footprint_wkt = product.get("Footprint")

        if footprint_wkt:
            cleaned_wkt = None
            try:
                wkt_start_index = footprint_wkt.find("POLYGON")
                if wkt_start_index == -1:
                    wkt_start_index = footprint_wkt.find("MULTIPOLYGON")
                if wkt_start_index != -1:
                    if footprint_wkt.endswith("'"):
                        cleaned_wkt = footprint_wkt[wkt_start_index:-1]
                    else:
                        cleaned_wkt = footprint_wkt[wkt_start_index:]
                else:
                    cleaned_wkt = footprint_wkt

                product_geom = wkt_loads(cleaned_wkt)
                if not product_geom.is_valid:
                    product_geom = product_geom.buffer(0)

                if product_geom.is_valid:
                    product_gdf = gpd.GeoDataFrame(
                        [1], geometry=[product_geom], crs="EPSG:4326"
                    )

                    if aoi_area_m2 > 0:
                        try:
                            product_gdf_proj = product_gdf.to_crs(target_crs)
                            product_geom_proj = product_gdf_proj.geometry.iloc[0]
                            intersection_geom_proj = aoi_geom_proj.intersection(product_geom_proj)
                            intersection_area_m2 = intersection_geom_proj.area
                            aoi_coverage_percent = (intersection_area_m2 / aoi_area_m2) * 100
                            logging.debug(
                                f"Product {product_name}: Projected calculation - AOI Area={aoi_area_m2:.2f} m², "
                                f"Intersection Area={intersection_area_m2:.2f} m², Coverage={aoi_coverage_percent:.2f}%"
                            )

                            if processed_count < 5:
                                crs_name = target_crs.name
                                crs_id = target_crs.to_epsg() if target_crs.is_projected else "non-projected"
                                log_msg = (
                                    f"Prod {product_odata_id[:8]} Areas (CRS: {crs_id} - {crs_name}):\n"
                                    + f"  AOI Projected Area  : {aoi_area_m2:,.2f} m²\n"
                                    + f"  Prod Projected Area : {product_geom_proj.area:,.2f} m²\n"
                                    + f"  Intersection Area   : {intersection_area_m2:,.2f} m²\n"
                                    + f"  Coverage Percentage : {aoi_coverage_percent:.2f}%"
                                )
                                logging.debug(log_msg)
                        except Exception as proj_err:
                            logging.warning(
                                f"Product {product_name}: Projected CRS calculation failed: {proj_err}. "
                                f"Falling back to WGS84 calculation."
                            )
                            try:
                                intersection_geom_wgs84 = aoi_geom_wgs84.intersection(product_geom)
                                import pyproj
                                geod = pyproj.Geod(ellps="WGS84")

                                def geodesic_area(geom):
                                    if geom.is_empty:
                                        return 0.0
                                    if geom.geom_type == 'Polygon':
                                        return abs(geod.geometry_area_perimeter(geom)[0])
                                    elif geom.geom_type == 'MultiPolygon':
                                        return sum(abs(geod.geometry_area_perimeter(part)[0]) for part in geom.geoms)
                                    return 0.0

                                aoi_area_geodesic = geodesic_area(aoi_geom_wgs84)
                                intersection_area_geodesic = geodesic_area(intersection_geom_wgs84)

                                if aoi_area_geodesic > 0:
                                    aoi_coverage_percent = (intersection_area_geodesic / aoi_area_geodesic) * 100

                                    logging.debug(
                                        f"Product {product_name}: WGS84 geodesic calculation - "
                                        f"AOI Area={aoi_area_geodesic:.2f} m², "
                                        f"Intersection Area={intersection_area_geodesic:.2f} m², "
                                        f"Coverage={aoi_coverage_percent:.2f}%"
                                    )
                                else:
                                    aoi_coverage_percent = 0.0
                                    logging.warning(f"Product {product_name}: AOI geodesic area is zero or negative.")
                            except Exception as wgs_err:
                                logging.warning(
                                    f"Product {product_name}: WGS84 geodesic calculation failed: {wgs_err}. "
                                    f"Falling back to simple degree-based calculation."
                                )

                                try:
                                    intersection_geom = aoi_geom_wgs84.intersection(product_geom)
                                    intersection_area_deg2 = intersection_geom.area
                                    aoi_area_deg2 = aoi_geom_wgs84.area

                                    if aoi_area_deg2 > 1e-9:
                                        aoi_coverage_percent = (intersection_area_deg2 / aoi_area_deg2) * 100
                                    else:
                                        aoi_coverage_percent = 0.0

                                    logging.debug(
                                        f"Product {product_name}: Simple degree calculation - "
                                        f"AOI Area={aoi_area_deg2:.6f}°², "
                                        f"Intersection Area={intersection_area_deg2:.6f}°², "
                                        f"Coverage={aoi_coverage_percent:.2f}% (approx)"
                                    )
                                except Exception as deg_err:
                                    logging.error(
                                        f"Product {product_name}: All coverage calculation methods failed. "
                                        f"Last error: {deg_err}"
                                    )
                                    aoi_coverage_percent = None
                    else:
                        logging.warning(
                            f"Product {product_name}: Projected area calculation unavailable. "
                            f"Falling back to WGS84 calculation."
                        )
                        try:
                            intersection_geom_wgs84 = aoi_geom_wgs84.intersection(product_geom)
                            intersection_area_deg2 = intersection_geom_wgs84.area
                            aoi_area_deg2 = aoi_geom_wgs84.area

                            if aoi_area_deg2 > 1e-9:
                                aoi_coverage_percent = (intersection_area_deg2 / aoi_area_deg2) * 100
                            else:
                                aoi_coverage_percent = 0.0

                            logging.debug(
                                f"Product {product_name}: WGS84 degree calculation - "
                                f"AOI Area={aoi_area_deg2:.6f}°², "
                                f"Intersection Area={intersection_area_deg2:.6f}°², "
                                f"Coverage={aoi_coverage_percent:.2f}% (approx)"
                            )
                        except Exception as e:
                            logging.error(
                                f"Product {product_name}: WGS84 fallback calculation failed: {e}"
                            )
                            aoi_coverage_percent = None
                else:
                    logging.warning(
                        f"Product {product_name}: Invalid product geometry after buffer(0) fix."
                    )
                    aoi_coverage_percent = None
            except GEOSException as geos_err:
                logging.warning(
                    f"Product {product_name}: GEOS geometry error: {geos_err}"
                )
                aoi_coverage_percent = None
            except Exception as e:
                logging.error(
                    f"Error calculating coverage for product {product_name}: {e}",
                    exc_info=True,
                )
                aoi_coverage_percent = None
        else:
            logging.warning(
                f"Product {product_name}: Missing footprint WKT in product metadata."
            )
            aoi_coverage_percent = None

        # Store the processed data
        processed_data = {
            "name": product_name,
            "sensing_date": (
                sensing_date.strftime("%Y-%m-%d") if sensing_date else "N/A"
            ),
            "sensing_datetime": sensing_date,
            "cloud_cover": cloud_cover,
            "aoi_coverage": aoi_coverage_percent,
            "days_from_end": days_from_end,
        }
        processed_results.append(processed_data)
        product_map[display_id_counter] = product
        display_id_counter += 1
        processed_count += 1
    logging.info(f"Finished processing {len(processed_results)} products for coverage.")
    filtered_results = [
        p
        for p in processed_results
        if p["aoi_coverage"] is not None and p["aoi_coverage"] >= min_aoi_coverage
    ]
    logging.info(
        f"Filtered down to {len(filtered_results)} products based on min_aoi_coverage >= {min_aoi_coverage}%."
    )
    filtered_product_map = {}
    filtered_id_counter = 1
    name_to_new_id = {}
    for result in filtered_results:
        product_name = result["name"]
        for _, product in product_map.items():
            if product["Name"] == product_name:
                filtered_product_map[filtered_id_counter] = product
                name_to_new_id[product_name] = filtered_id_counter
                filtered_id_counter += 1
                break
    product_map = filtered_product_map
    processed_results = filtered_results
    processed_results.sort(
        key=lambda x: (
            -(x["aoi_coverage"] if x["aoi_coverage"] is not None else -1),
            (x["cloud_cover"] if x["cloud_cover"] is not None else float("inf")),
            (
                -x["sensing_datetime"].toordinal()
                if x.get("sensing_datetime")
                else float("inf")
            ),
        )
    )
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
    )
    table.add_column("ID", style="dim", width=4, justify="right")
    table.add_column("Sensing Date", style="dim", justify="center")
    table.add_column("Clouds %", justify="center")
    table.add_column("AoI %", justify="center")

    def get_cloud_style(cloud_cover):
        if cloud_cover is None:
            return "dim"
        elif cloud_cover <= 20:
            return "bright_green"
        elif cloud_cover <= 50:
            return "yellow"
        else:
            return "red"

    def get_date_recency_style(days_from_end):
        if days_from_end is None or days_from_end < 0:
            return "dim"
        if days_from_end <= 7:
            return "bright_cyan"
        elif days_from_end <= 30:
            return "bright_green"
        elif days_from_end <= 90:
            return "yellow"
        else:
            return "red"

    def get_aoi_coverage_style(aoi_coverage):
        if aoi_coverage is None:
            return "dim"
        elif aoi_coverage >= 90:
            return "bright_green"
        elif aoi_coverage >= 50:
            return "green"
        elif aoi_coverage > 0:
            return "yellow"
        else:
            return "red"

    display_id_counter = 1
    for result in processed_results:
        result.get("name", "N/A")
        sensing_date_str = result.get("sensing_date", "N/A")
        cloud_cover = result.get("cloud_cover")
        aoi_coverage_percent = result.get("aoi_coverage")
        days_diff = result.get("days_from_end", None)
        cloud_style = get_cloud_style(cloud_cover)
        aoi_style = get_aoi_coverage_style(aoi_coverage_percent)
        date_recency_style = get_date_recency_style(days_diff)
        cloud_str = (
            f"[{cloud_style}]{cloud_cover:.1f}[/]"
            if cloud_cover is not None
            else "[dim]N/A[/]"
        )
        aoi_str = (
            f"[{aoi_style}]{aoi_coverage_percent:.1f}[/]"
            if aoi_coverage_percent is not None
            else "[dim]N/A[/]"
        )
        table.add_row(
            str(display_id_counter),
            f"[{date_recency_style}]{sensing_date_str}[/]",
            cloud_str,
            aoi_str,
        )
        display_id_counter += 1
    cloud_legend_text = (
        f"  [{get_cloud_style(10)}]<= 20%[/] (Low)\n"
        f"  [{get_cloud_style(35)}]<= 50%[/] (Medium)\n"
        f"  [{get_cloud_style(70)}]> 50%[/] (High)"
    )
    cloud_panel = Panel(
        cloud_legend_text,
        title="[sky_blue1]Cloud Legend[/]",
        border_style="dim",
        expand=False,
        padding=(1, 2),
    )
    aoi_legend_text = (
        f"  [{get_aoi_coverage_style(95)}]>= 90%[/] (Excellent)\n"
        f"  [{get_aoi_coverage_style(70)}]>= 50%[/] (Good)\n"
        f"  [{get_aoi_coverage_style(25)}]> 0%[/] (Partial)"
    )
    aoi_panel = Panel(
        aoi_legend_text,
        title="[chartreuse1]AoI Legend[/]",
        border_style="dim",
        expand=False,
        padding=(1, 2),
    )
    date_legend_text = (
        f"  [{get_date_recency_style(5)}]<= 7 days[/] (Very Recent)\n"
        f"  [{get_date_recency_style(15)}]<= 30 days[/] (Recent)\n"
        f"  [{get_date_recency_style(45)}]<= 90 days[/] (Less Recent)"
    )
    date_panel = Panel(
        date_legend_text,
        title="[medium_purple1]Date Recency Legend[/]",
        border_style="dim",
        expand=False,
        padding=(1, 2),
    )
    legend_columns = Columns([cloud_panel, aoi_panel, date_panel], equal=True)
    console.print()
    console.print(table)
    console.print(legend_columns)
    console.print(Rule(style="blue"))
    if product_map:
        console.print(Rule("[bold cyan]Select Product for Download[/]"))
        while True:
            try:
                choices = [str(k) for k in product_map.keys()] + ["q"]
                selected_id_str = Prompt.ask(
                    "Enter the [bold yellow]ID[/] of the product to download (or 'q' to quit)",
                    choices=choices,
                )
                if selected_id_str.lower() == "q":
                    console.print("Exiting download selection.")
                    break
                selected_id = int(selected_id_str)
                if selected_id in product_map:
                    selected_product = product_map[selected_id]
                    selected_product_name = selected_product["Name"]
                    selected_product_odata_id = selected_product["Id"]
                    selected_cloud_cover = selected_product.get("cloud_cover_float")
                    safe_dir_path = pathlib.Path(output_dir) / selected_product_name
                    metadata_file_path = safe_dir_path / "metadata.json"
                    if safe_dir_path.is_dir():
                        console.print(
                            f"[green]Product '{selected_product_name}' already exists locally. Skipping download.[/green]"
                        )
                    else:
                        try:
                            console.print(
                                f"[cyan]Initiating download for {selected_product_name}...[/cyan]"
                            )
                            download_product(
                                product_odata_id,
                                product_name=selected_product_name,
                                access_token=access_token,
                                output_dir=output_dir,
                                node_path=None,
                            )
                            console.print(
                                f"[green]Download call for {selected_product_name} completed.[/green]"
                            )
                        except Exception as e:
                            console.print(
                                f"[red]Error during download initiation for {selected_product_name}:[/red] {e}"
                            )
                            logging.error(
                                f"Exception during download call for {selected_product_name}: {e}",
                                exc_info=True,
                            )
                            continue
                    try:
                        safe_dir_path.mkdir(parents=True, exist_ok=True)
                        metadata_to_save = {
                            "product_name": selected_product_name,
                            "odata_id": selected_product_odata_id,
                            "cloud_cover_percentage": selected_cloud_cover,
                            "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        }
                        with open(metadata_file_path, "w") as f:
                            json.dump(metadata_to_save, f, indent=4)
                        console.print(
                            f"[blue]Saved metadata to {metadata_file_path}[/blue]"
                        )
                    except Exception as e:
                        console.print(
                            f"[red]Error saving metadata file for {selected_product_name}:[/red] {e}"
                        )
                        logging.error(
                            f"Failed to save metadata for {selected_product_name}: {e}",
                            exc_info=True,
                        )
            except KeyboardInterrupt:
                console.print("\nDownload selection cancelled by user.")
                break
    else:
        console.print(
            "[yellow]No products met the criteria for display/download.[/yellow]"
        )
    return product_map


def browse_and_download_nodes(
    product_id: str, product_name: str, access_token: str, output_dir: str
):
    console.print(f"  [cyan]Browsing nodes for:[/cyan] {product_name}")
    current_path = ""
    history = []
    while True:
        console.print(
            f"  [cyan]Current Path:[/cyan] {product_name}.SAFE/{current_path if current_path else '.'}"
        )
        nodes = list_product_nodes(product_id, access_token, current_path)
        if nodes is None:
            console.print(
                "[bold red]  -> Error listing nodes. Check logs. Aborting browse.[/bold red]"
            )
            break
        if not nodes:
            is_file_node = current_path and not list_product_nodes(
                product_id, access_token, os.path.dirname(current_path)
            )
            if is_file_node:
                console.print("[yellow]  -> Cannot list nodes for a file.[/yellow]")
            else:
                console.print(
                    "[yellow]  -> Directory appears empty or is not listable.[/yellow]"
                )
            if history:
                current_path = history.pop()
                console.print("  -> Automatically going up...")
                continue
            else:
                console.print("  -> No more history to go back. Exiting browse.")
                break
        table = Table(title="Nodes", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Type", width=8)
        table.add_column("Size", style="magenta", justify="right")
        folders = []
        files = []
        for node in nodes:
            is_folder = (
                node.get("ContentLength", -1) == 0 or node.get("ChildrenNumber", 0) > 0
            )
            if is_folder:
                folders.append(node)
            else:
                files.append(node)
        node_map = {}
        display_index = 1
        for folder in folders:
            folder_name = folder.get("Name", "Unknown Folder")
            node_map[display_index] = {
                "Name": folder_name,
                "IsFolder": True,
                "Path": os.path.join(current_path, folder_name),
            }
            table.add_row(
                str(display_index),
                f"[bold green]{folder_name}/[/bold green]",
                "Folder",
                "",
            )
            display_index += 1
        for file_node in files:
            file_name = file_node.get("Name", "Unknown File")
            size_bytes = file_node.get("ContentLength", 0)
            node_map[display_index] = {
                "Name": file_name,
                "IsFolder": False,
                "Path": os.path.join(current_path, file_name),
            }
            table.add_row(
                str(display_index),
                file_name,
                "File",
                str(decimal(size_bytes)) if size_bytes is not None else "N/A",
            )
            display_index += 1
        console.print(table)
        action = Prompt.ask(
            "  [bold]Action?[/bold] (Enter # to download file / open folder, 'u'p, 'q'uit)",
            default="q",
        ).lower()
        if action == "q":
            break
        elif action == "u":
            if history:
                current_path = history.pop()
            else:
                console.print("[yellow]  -> Already at the root.[/yellow]")
        else:
            try:
                selected_index = int(action)
                if selected_index in node_map:
                    selected_node = node_map[selected_index]
                    if selected_node["IsFolder"]:
                        history.append(current_path)
                        current_path = selected_node["Path"]
                    else:
                        node_full_path = selected_node["Path"]
                        console.print(
                            f"  -> Scheduling download for file: [cyan]{selected_node['Name']}[/cyan]"
                        )
                        try:
                            download_product(
                                product_id=product_id,
                                product_name=product_name,
                                access_token=access_token,
                                output_dir=output_dir,
                                node_path=node_full_path,
                            )
                        except Exception as e:
                            console.print(
                                f"[bold red]  -> Error occurred trying to download node {selected_node['Name']}: {e}[/bold red]"
                            )
                            logging.error(
                                f"Exception during node download scheduling/call for {product_id}, node {node_full_path}: {e}",
                                exc_info=True,
                            )
                else:
                    console.print("[bold red]  -> Invalid selection number.[/bold red]")
            except ValueError:
                console.print(
                    "[bold red]  -> Invalid input. Enter a number, 'u', or 'q'.[/bold red]"
                )
    console.print(f"  [cyan]Finished browsing nodes for:[/cyan] {product_name}")
    console.print(
        f"[italic yellow]  Node browsing for '{product_name}' not yet implemented. Skipping specific file download.[/italic yellow]"
    )


def find_geojson_files(directory: pathlib.Path) -> list[pathlib.Path]:
    if not directory.is_dir():
        console.print(f"[red]Error:[/red] AOI directory not found: {directory}")
        return []
    return sorted(list(directory.glob("*.geojson")))


def select_aoi_file(aoi_dir: pathlib.Path) -> pathlib.Path | None:
    geojson_files = find_geojson_files(aoi_dir)
    if not geojson_files:
        console.print(f"[red]Error:[/red] No GeoJSON files found in {aoi_dir}.")
        console.print(
            "Please place a GeoJSON file in this directory or specify one using the --aoi argument."
        )
        return None
    if len(geojson_files) == 1:
        selected_file = geojson_files[0]
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
    for idx, file_path in enumerate(geojson_files):
        table.add_row(str(idx + 1), file_path.name)
    console.print(table)
    while True:
        choice = IntPrompt.ask(
            "Enter the number of the AOI file to use", console=console
        )
        if 1 <= choice <= len(geojson_files):
            selected_file = geojson_files[choice - 1]
            console.print(f"[green]Selected:[/green] {selected_file.name}")
            return selected_file
        else:
            console.print(
                f"[red]Invalid choice.[/red] Please enter a number between 1 and {len(geojson_files)}."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sentinel-2 Data Collector using CDSE OData API."
    )
    parser.add_argument(
        "--aoi",
        required=False,
        default=None,
        help=f"Path to the Area of Interest GeoJSON file. If omitted, searches in {DEFAULT_AOI_DIR}",
    )
    parser.add_argument(
        "--start-date",
        required=False,
        default=None,
        help="Start date in YYYY-MM-DD format. Defaults to 3 months ago.",
    )
    parser.add_argument(
        "--end-date",
        required=False,
        default=None,
        help="End date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--max-cloud",
        type=int,
        default=10,
        help="Maximum cloud cover percentage (0-100). Default: 10.",
    )
    parser.add_argument(
        "--min-aoi",
        type=float,
        default=100.0,
        help="Minimum AoI coverage percentage (0-100). Default: 100.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the .env file for credentials. Default: .env",
    )
    parser.add_argument(
        "--level",
        choices=["L2A", "ALL"],
        default="L2A",
        help="Product level to fetch (L2A or ALL). Default: L2A",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.expanduser("~/SatShor/src/shoreline_extractor/data/img"),
        help="Directory to download products to. Default: ~/SatShor/src/shoreline_extractor/data/img",
    )
    args = parser.parse_args()
    output_path = pathlib.Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    console.print(
        f"[dim]Using output directory:[/dim] [cyan]{output_path.resolve()}[/]"
    )
    if os.path.exists(args.env_file):
        load_dotenv(dotenv_path=args.env_file)
    else:
        if args.env_file != ".env" and os.path.exists(".env"):
            load_dotenv()
            console.print(
                "[yellow]Warning:[/yellow] Specified --env-file not found, loaded default .env"
            )
        elif args.env_file == ".env":
            console.print(
                "[yellow]Warning:[/yellow] Default .env file not found. Relying on system environment variables."
            )
        else:
            console.print(
                f"[yellow]Warning:[/yellow] Specified --env-file '{args.env_file}' not found. Relying on system environment variables."
            )
    end_date_obj = None
    start_date_obj = None
    if args.end_date:
        try:
            end_date_obj = datetime.strptime(args.end_date, DATE_FORMAT).date()
        except ValueError:
            console.print(
                f"[red]Invalid end date format:[/red] {args.end_date}. Use YYYY-MM-DD."
            )
            sys.exit(1)
    else:
        end_date_obj = date.today()
        console.print(
            f"[dim]No --end-date specified, defaulting to today:[/dim] [cyan]{end_date_obj.strftime(DATE_FORMAT)}[/]"
        )
    if args.start_date:
        try:
            start_date_obj = datetime.strptime(args.start_date, DATE_FORMAT).date()
        except ValueError:
            console.print(
                f"[red]Invalid start date format:[/red] {args.start_date}. Use YYYY-MM-DD."
            )
            sys.exit(1)
    else:
        start_date_obj = end_date_obj - timedelta(days=90)
        console.print(
            f"[dim]No --start-date specified, defaulting to 90 days prior:[/dim] [cyan]{start_date_obj.strftime(DATE_FORMAT)}[/]"
        )
    if start_date_obj > end_date_obj:
        console.print(
            f"[red]Error:[/red] Start date ({start_date_obj.strftime(DATE_FORMAT)}) cannot be after end date ({end_date_obj.strftime(DATE_FORMAT)})."
        )
        sys.exit(1)
    if not 0 <= args.max_cloud <= 100:
        console.print("[red]Error:[/red] --max-cloud must be between 0 and 100.")
        sys.exit(1)
    if not 0 <= args.min_aoi <= 100:
        console.print("[red]Error:[/red] --min-aoi must be between 0 and 100.")
        sys.exit(1)
    console.print(Rule("[bold magenta]SatShor[/]"))
    selected_aoi_path = None
    if args.aoi:
        selected_aoi_path = pathlib.Path(args.aoi)
        if not selected_aoi_path.is_file():
            console.print(
                f"[red]Error:[/red] Specified AOI file not found: {selected_aoi_path}"
            )
            sys.exit(1)
    else:
        console.print(
            f"[dim]No --aoi specified, searching in default directory:[/dim] [cyan]{DEFAULT_AOI_DIR}[/]"
        )
        selected_aoi_path = select_aoi_file(DEFAULT_AOI_DIR)
        if selected_aoi_path is None:
            sys.exit(1)
    parameter_text = (
        f"[bold]AOI File:[/bold] [cyan]{selected_aoi_path.name}[/]\n"
        f" ([dim]Path: {selected_aoi_path}[/dim])\n"
        f"[bold]Date Range:[/bold] [cyan]{start_date_obj.strftime(DATE_FORMAT)}[/] to [cyan]{end_date_obj.strftime(DATE_FORMAT)}[/]\n"
        f"[bold]Max Cloud Cover:[/bold] [cyan]{args.max_cloud}%[/]\n"
        f"[bold]Min AoI Coverage:[/bold] [cyan]{args.min_aoi}%[/]\n"
        f"[bold]Product Level:[/bold] [cyan]{args.level}[/]"
    )
    console.print(
        Panel(parameter_text, title="Parameters", border_style="blue", expand=False)
    )
    console.print(Rule(style="blue"))
    all_products = []
    product_map = {}
    with console.status("[bold green]Initializing...") as status:
        status.update("Authenticating...")
        access_token = get_access_token()
        status.update("Loading AOI...")
        aoi_wkt, aoi_gdf = load_aoi_data(str(selected_aoi_path))
        central_date = calculate_central_date(
            start_date_obj.strftime(DATE_FORMAT), end_date_obj.strftime(DATE_FORMAT)
        )
        query_details = {
            "aoi_wkt": aoi_wkt,
            "start_date_str": start_date_obj.strftime(DATE_FORMAT),
            "end_date_str": end_date_obj.strftime(DATE_FORMAT),
            "max_cloud_cover": args.max_cloud,
            "product_level": args.level,
        }
        query_url = build_odata_query(**query_details)
        status.update("Fetching products...")
        parsed_params = {}
        if "?" in query_url:
            base_url, query_string = query_url.split("?", 1)
            all_products = fetch_products(
                access_token, None, status=status, direct_url=query_url
            )
        else:
            console.print("[red]Error:[/red] Invalid query URL format.")
            all_products = []
        status.stop()
    if not all_products:
        console.print("[yellow]No products found for the specified criteria.[/yellow]")
    else:
        console.print("[green]Product search complete. Processing results...[/]")
        product_map = process_products(
            all_products,
            aoi_gdf,
            central_date,
            end_date_obj,
            access_token,
            min_aoi_coverage=args.min_aoi,
            output_dir=args.output_dir,
        )
    console.print(Rule("[bold magenta]Collection Complete[/]"))
