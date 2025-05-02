# SatShor Directory Standards

## Project Structure

```
SatShor/
├── src/
│   ├── image_collector/                      
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

## Directory Specifications

The `image_collector` outputs the Sentinel-2 unziped .SAFE products in `src/shoreline_extractor/data/img`.

The `shoreline_extractor` searches for AoIs in `src/shoreline_extractor/data/json` and B08 images in `src/shoreline_extractor/data/img`.

The extracted GeoJSON shorelines are saved in `src/shoreline_extractor/output`.