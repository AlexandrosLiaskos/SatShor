# SatShor - Satellite Shoreline Extractor

A toolkit for extracting shorelines from Sentinel-2 satellite imagery. It provides a complete workflow from searching and downloading satellite data to extracting high-precision (~5m) shorelines.

## Overview

SatShor consists of two main components:

1. **Image Collector**: Searches and downloads Sentinel-2 satellite imagery from the Copernicus Data Space Ecosystem (CDSE) based on user-defined criteria (Start-End Date, Cloud %, AoI %).
2. **Shoreline Extractor**: Processes Sentinel-2 Band 8 (NIR) imagery to extract accurate shorelines using cikit-image's minimum thresholding and marching squares subpixel refinement.

## Screenshots

![image](https://github.com/user-attachments/assets/60fa1058-826d-4add-bf87-91bf28f17057)
![image](https://github.com/user-attachments/assets/b1eb402c-0019-43d7-94fd-e5853a1b3a0b)
![image](https://github.com/user-attachments/assets/da0ddf2d-0fbf-4f99-9e89-c9825d05c5b7)
![image](https://github.com/user-attachments/assets/2dd2a27d-85dc-4d86-bc9f-cbc1a5931b20)
![image](https://github.com/user-attachments/assets/fa2bf99c-969e-425c-a124-cb511153f72d)
![image](https://github.com/user-attachments/assets/86229a17-9ff5-4807-ab89-180cbaa6a34b)

## Features

### Image Collector
- Search for Sentinel-2 scenes intersecting a user-defined Area of Interest (AOI)
- Filter scenes by date range and cloud cover percentage
- Calculate AOI coverage for each scene
- Interactive selection of scenes to download
- Automatic download and extraction of selected scenes
- Rich console interface with progress indicators

### Shoreline Extractor
- Extract shorelines from Sentinel-2 L2A Band 8 (NIR) imagery
- Automatic detection of Sentinel-2 coordinate reference systems
- Minimum thresholding method from scikit-image for water/land separation
- Subpixel refinement using marching squares algorithm for smooth, accurate shorelines
- Filtering of small islands and inland water bodies
- Output as GeoJSON files for easy integration with GIS software

## Directory Structure

```
SatShor/
├── src/
│   ├── image_collector/    
|   |   ├── .env                 # CDSE credentials          
│   │   └── logs/               
│   │
│   └── shoreline_extractor/     
│       ├── data/                
│       │   ├── json/            # AOI GeoJSONs
│       │   └── img/             # Sentinel-2 .SAFE Products
│       ├── output/              # Extracted GeoJSON shorelines
│       └── logs/                                              
└── docs/                      
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Additional libraries (See [requirements.txt](requirements.txt))
- Copernicus Data Space Ecosystem account

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/AlexandrosLiaskos/SatShor.git
   cd SatShor
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure CDSE credentials:
   Create a `.env` file in the project root with your Copernicus Data Space Ecosystem credentials:
   ```
   CDSE_USERNAME=your_username
   CDSE_PASSWORD=your_password
   ```

## Usage

### Image Collector

The image collector searches for and downloads Sentinel-2 imagery based on your Area of Interest and date range.

```bash
python src/image_collector/collector.py --aoi path/to/your/aoi.geojson --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```
```bash
usage: collector.py [-h]
                    [--aoi AOI]
                    [--start-date START_DATE]
                    [--end-date END_DATE]
                    [--max-cloud MAX_CLOUD]
                    [--min-aoi MIN_AOI]
                    [--env-file ENV_FILE]
                    [--level {L2A,ALL}]
                    [--output-dir OUTPUT_DIR]

Sentinel-2 Data Collector using
CDSE OData API.

options:
  -h, --help   show this help
               message and exit
  --aoi AOI    Path to the Area of
               Interest GeoJSON
               file. If omitted,
               searches in ~/SatShor/src/sh
               oreline_extractor/da
               ta/json
  --start-date START_DATE
               Start date in YYYY-
               MM-DD format.
               Defaults to 3 months
               ago.
  --end-date END_DATE
               End date in YYYY-MM-
               DD format. Defaults
               to today.
  --max-cloud MAX_CLOUD
               Maximum cloud cover
               percentage (0-100).
               Default: 10.
  --min-aoi MIN_AOI
               Minimum AoI coverage
               percentage (0-100).
               Default: 100.
  --env-file ENV_FILE
               Path to the .env
               file for
               credentials.
               Default: .env
  --level {L2A,ALL}
               Product level to
               fetch (L2A or ALL).
               Default: L2A
  --output-dir OUTPUT_DIR
               Directory to
               download products
               to. Default: src/sho
               reline_extractor/dat
               a/img
```

### Shoreline Extractor

The shoreline extractor processes Sentinel-2 Band 8 imagery to extract shorelines.

```bash
python src/shoreline_extractor/extract.py --b8_input_file path/to/B08_file.jp2 --aoi_path path/to/aoi.geojson
```

```bash
usage: extract.py [-h]
                  [--b8_input_file B8_INPUT_FILE]
                  [--aoi_path AOI_PATH]
                  [--output_geojson OUTPUT_GEOJSON]
                  [--min_sea_area MIN_SEA_AREA_M2]
                  [--min_island_area MIN_ISLAND_AREA_M2]
                  [--loglevel {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

Extracts shorelines (coastline and
island boundaries) from a
Sentinel-2 Band 8 NIR file within a
given AOI.

options:
  -h, --help   show this help
               message and exit
  --b8_input_file B8_INPUT_FILE
               Path to the input
               Sentinel-2 Band 8
               file (e.g.,
               *_B08_10m.jp2 or
               .tif). If not
               provided, will
               prompt to select
               from available
               files. (default:
               None)
  --aoi_path AOI_PATH
               Path to the Area of
               Interest (AOI)
               GeoJSON file. If not
               provided, will
               prompt to select
               from available
               files. (default:
               None)
  --output_geojson OUTPUT_GEOJSON
               Full path for the
               output shoreline
               GeoJSON file. If not
               provided, will
               generate based on
               AOI and product
               names. (default:
               None)
  --min_sea_area MIN_SEA_AREA_M2
               Minimum area in
               square meters for
               the largest water
               body to be
               considered the
               'sea'. (default:
               10000.0)
  --min_island_area MIN_ISLAND_AREA_M2
               Minimum area in
               square meters for an
               island's shoreline
               to be included.
               (default: 50000.0)
  --loglevel {DEBUG,INFO,WARNING,ERROR,CRITICAL}
               Set the logging
               level for console
               output. (default:
               INFO)
```

## Documentation

Additional documentation is available in the `docs` directory:

- [OData API Documentation](docs/OData.md): Details on the Copernicus Data Space Ecosystem API
- [Directory Standards](docs/Directory_Standards.md): Information on the project's directory structure
- [AOI Drawing Guide](docs/AOI_Drawing_Guide.md): Guide for creating compatible Area of Interest files
- [Shoreline Extractor Functions](docs/shoreline_extractor_functions.md): Detailed explanation of the shoreline extraction algorithms

## Future Enhancements

- Remove from Image Search products with zip size less than ~600 MB (Contain a lot of NoData).
- Enhanced water detection using Band 8A (865nm)
- Support for additional satellite platforms (Sentinel-1)
- Time series analysis of shoreline changes
- Super-resolution close-date/low-cloud image composites

## Open-Issues

- Open linestrings of unfinished land/island shoreliens in the AoI edges 
- Edge Artifacts might need handling by rising the `buffer_percentage` from 0.02.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
