# Area of Interest (AOI) Drawing Guide for Shoreline Extraction

This guide provides step-by-step instructions for creating Area of Interest (AOI) files that are compatible with the SatShor shoreline extraction system. Properly formatted AOIs are essential for successful satellite image processing and accurate shoreline extraction.

## Table of Contents
1. [Requirements](#requirements)
2. [Tools for Drawing AOIs](#tools-for-drawing-aois)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Best Practices](#best-practices)
5. [Common Issues and Solutions](#common-issues-and-solutions)
6. [Advanced Tips](#advanced-tips)

## Requirements

- **Area**: Near the coastline, containg water, islands of interest and land with a positive buffer in mind of ~100 meters for safety and the whole AoI area contained on a Sentinel-2 scene.
- **File Format**: GeoJSON (.geojson)
- **Coordinate System**: WGS84 (EPSG:4326)
- **Geometry Type**: Polygon or MultiPolygon
- **Validity**: Must be a valid geometry without self-intersections

## Tools for Drawing AOIs

### 1. GeoJSON.io (Recommended for Beginners)
- **Website**: [geojson.io](https://geojson.io/)

### 2. Copernicus Browser
- **Website**: [Copernicus Browser](https://browser.dataspace.copernicus.eu/)

### 3. QGIS (Advanced Users)
- **Website**: [qgis.org](https://qgis.org/)
