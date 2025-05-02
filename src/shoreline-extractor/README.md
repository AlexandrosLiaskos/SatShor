# Shoreline Extractor (`extract.py`) Analysis

## Overview

Shoreline extraction from Sentinel-2 L2A B08 using "minimum" thresholding method from scikit-image and the marching squares algorithm for subpixel refinement.

### Core Functions

#### 1. `detect_sentinel2_crs` (Lines 34-59)
**Purpose**: Extracts the Coordinate Reference System from Sentinel-2 file paths.
- Uses regex to identify UTM zone from filename (e.g., T32TMK)
- Determines hemisphere (North/South) from zone letter based on specific letter codes
- Creates appropriate EPSG code (e.g., EPSG:326xx for northern, EPSG:327xx for southern)
- Returns a proper CRS object or falls back to dictionary format if needed
- Critical for handling Sentinel-2 L2A products that may lack embedded CRS information

#### 2. `load_aoi` (Lines 61-106)
**Purpose**: Loads and validates Area of Interest geometries.
- Reads GeoJSON using GeoPandas
- Handles multiple features by combining them
- Validates geometry and attempts to fix invalid geometries
- Sets default CRS (EPSG:4326) if not specified
- Returns both CRS and geometry for further processing

#### 3. `apply_threshold` (Lines 108-123)
**Purpose**: Creates a binary water/land mask from raster data.
- Filters out NaN and negative values
- Applies "minimum" thresholding from scikit-image
- Returns binary mask where values ≤ threshold are True (water)
- Includes error handling for threshold calculation failures

#### 4. `vectorize_mask` (Lines 125-231)
**Purpose**: Converts binary mask to vector shoreline features.
- Uses rasterio.features.shapes to vectorize the mask
- Identifies largest polygon as main water body
- Extracts exterior ring as main coastline
- Filters interior rings (islands) based on minimum area
- Returns LineString features representing shorelines

#### 5. `apply_subpixel_refinement` (Lines 234-319)
**Purpose**: Refines shoreline vectors for smoother, more accurate results.
- Uses marching squares algorithm via scikit-image's find_contours for subpixel precision
- Creates inner buffer (2% of AOI dimensions) to avoid edge effects
- Implements fallback to manual rectangle creation if buffer operation fails
- Matches original shorelines to contours using Hausdorff distance and length ratio metrics
- Filters contour points to those inside the inner polygon
- Preserves original shorelines when no suitable contour match is found
- Returns refined LineString features with improved positional accuracy

#### 6. `extract_shoreline` (Lines 321-550)
**Purpose**: Main processing pipeline that orchestrates the entire workflow.
- Loads AOI and Band 8 raster data
- Handles CRS detection and reprojection between different coordinate systems
- Creates fallback geometries when reprojection fails (e.g., WGS84 to UTM)
- Clips raster to AOI boundaries with proper handling of nodata values
- Applies thresholding to identify water bodies
- Vectorizes mask to extract raw shorelines with area-based filtering
- Clips shorelines to AOI and handles geometry validity issues
- Applies subpixel refinement for smoother, more accurate shorelines
- Saves final results as GeoJSON with proper metadata
- Includes comprehensive error handling at each step

### User Interface Functions

#### 7. `find_aoi_files` & `select_aoi_file` (Lines 553-592)
**Purpose**: Locate and select AOI files.
- Finds all GeoJSON files in the AOI directory
- Presents options in a formatted table using Rich library
- Handles automatic selection when only one file exists
- Validates user input for selection

#### 8. `find_band8_files` & `select_band8_file` (Lines 594-640)
**Purpose**: Locate and select Sentinel-2 Band 8 files.
- Recursively searches for .jp2 and .tif files with "B08" and "10m" in the name
- Presents options in a formatted table
- Handles automatic selection when only one file exists
- Validates user input for selection

#### 9. `generate_output_path` (Lines 642-664)
**Purpose**: Creates standardized output file paths.
- Extracts AOI name from input file
- Extracts product name or tile ID from Band 8 file
- Generates filename in format "shoreline_{aoi_name}_{product_name}.geojson"
- Returns full path in the output directory
