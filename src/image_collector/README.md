 # SatShor Collector

This module is part of the SatShor (Satellite Shoreline Extractor) package. Its purpose is to search the Copernicus Data Space Ecosystem (CDSE) for Sentinel-2 satellite scenes based on user-defined criteria and download them.

## Features

*   Find Sentinel-2 scenes intersecting a user-provided Area of Interest (AoI) defined in a GeoJSON file (WGS84).
> Drawn in [GeoJSON.io](https://geojson.io/) or [Copernicus Browser](https://browser.dataspace.copernicus.eu/)
*   Filter scenes by a specific date range.
*   Retrieve metadata for each scene, including:
    *   Scene Name/ID
    *   Sensing Date
    *   Cloud Cover Percentage
*   Calculate and display:
    *   AoI Coverage Percentage (how much of the user's AoI is covered by the scene).
    *   Days from Central Date (difference between scene date and the middle date of the user's requested range).
*   Presents results in a clear, interactive table using the Rich library.

## Prerequisites

*   Python 3.x
*   Required Python packages (see `requirements.txt`)
*   Copernicus Data Space Ecosystem account credentials (Username/Password or Tokens) stored in a `.env` file.

## Usage (Planned)

```bash
python collector.py --aoi path/to/your/aoi.geojson --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

## Configuration

Create a `.env` file in the `SatShor_Collector` directory with your CDSE credentials:

```dotenv
CDSE_USERNAME=your_username
CDSE_PASSWORD=your_password
# Or potentially:
# CDSE_ACCESS_TOKEN=your_access_token
# CDSE_REFRESH_TOKEN=your_refresh_token
```

## Development Notes

*   Uses the CDSE OData API (`https://catalogue.dataspace.copernicus.eu/odata/v1/`).
*   Requires handling of CDSE authentication (likely OAuth2).
*   Calculates AoI coverage using geometric intersection (requires libraries like `shapely`).
*   Uses `rich` for presentation.
