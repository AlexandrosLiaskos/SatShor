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
*   **Automatic periodic downloads** (yearly, monthly, weekly, or custom intervals)
*   **Configurable auto-selection strategies** for unattended operation
*   **Scheduler daemon** for long-running automated collection
*   **State tracking** to prevent duplicate downloads

## Prerequisites

*   Python 3.x
*   Required Python packages (see `requirements.txt`)
*   Copernicus Data Space Ecosystem account credentials (Username/Password or Tokens) stored in a `.env` file.

## Usage (Manual Collection)

### Interactive Mode (Default)

```bash
python collector.py --aoi path/to/your/aoi.geojson --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

### Automatic Selection Mode

```bash
# Download top 5 products by quality score
python collector.py --aoi path/to/aoi.geojson --start-date 2024-01-01 --end-date 2024-01-31 --auto-select best_n --max-products 5

# Download all products above quality threshold
python collector.py --aoi path/to/aoi.geojson --start-date 2024-01-01 --end-date 2024-01-31 --auto-select all_above_threshold

# Download best product per week
python collector.py --aoi path/to/aoi.geojson --start-date 2024-01-01 --end-date 2024-01-31 --auto-select best_per_week

# Greedy coverage optimization
python collector.py --aoi path/to/aoi.geojson --start-date 2024-01-01 --end-date 2024-01-31 --auto-select coverage_greedy --min-coverage 0.98 --grid-spacing 100

# Optimal coverage with MILP solver
python collector.py --aoi path/to/aoi.geojson --start-date 2024-01-01 --end-date 2024-01-31 --auto-select coverage_optimal --min-coverage 1.0 --solver-timeout 600
```

### Coverage Optimization Strategies (OCAS)

OCAS (Optimal Coverage Acquisition System) solves the geometric set cover problem for satellite imagery selection. Unlike quality-based strategies that select the best individual images, coverage strategies guarantee complete area coverage with minimal number of images.

#### When to Use Coverage Optimization

**Quality-based strategies** (`best_n`, `all_above_threshold`, `best_per_week`):
- Best when: You want the highest quality individual images
- Characteristics: Fast, simple, good for spot coverage
- Limitation: May leave gaps in area coverage

**Coverage-based strategies** (`coverage_greedy`, `coverage_optimal`):
- Best when: You need complete area coverage without gaps
- Characteristics: Solves geometric set cover problem, minimizes image count
- Use cases: Large area mapping, creating seamless mosaics, cost minimization

#### Strategy Details

**`coverage_greedy`**: Fast Greedy Heuristic
- **Algorithm**: Iteratively selects images with best marginal coverage gain per cost
- **Performance**: Near-optimal solution (typically within 10-20% of optimal)
- **Runtime**: O(n²) where n is number of candidates
- **Suitable for**: Large AOIs (>1000 km²), time-sensitive operations
- **Example**:
  ```bash
  python collector.py --aoi large_area.geojson --start-date 2024-01-01 --end-date 2024-01-31 \
    --auto-select coverage_greedy --min-coverage 0.98 --grid-spacing 100
  ```

**`coverage_optimal`**: MILP-Based Globally Optimal Solver
- **Algorithm**: Mixed-Integer Linear Programming using OR-Tools CBC solver
- **Performance**: Guarantees minimal number of images for complete coverage
- **Runtime**: May be slow for large problems (>100 candidates)
- **Suitable for**: Small-medium AOIs (<500 km²), archival quality requirements
- **Requirements**: **Optional dependency** - `pip install ortools>=9.14.0`
- **Note**: Falls back to greedy algorithm if OR-Tools is not installed
- **Example**:
  ```bash
  python collector.py --aoi study_area.geojson --start-date 2024-01-01 --end-date 2024-01-31 \
    --auto-select coverage_optimal --min-coverage 1.0 --solver-timeout 600
  ```

#### Configuration Parameters

**`--min-coverage`** (0.0-1.0, default: 0.99)
- Target coverage fraction of the AOI
- 1.0 = require complete coverage (no gaps allowed)
- 0.95 = allow 5% of area to remain uncovered
- Trade-off: Lower values allow faster solutions with fewer images

**`--grid-spacing`** (meters, default: auto-calculated)
- Distance between sample points in the coverage grid
- Finer spacing (50-100m) = more accurate coverage measurement but slower
- Coarser spacing (150-200m) = faster processing but less precise
- Auto-calculation uses: `sqrt(AOI area) / 100`, clamped to 50-200m

**`--solver-timeout`** (seconds, default: 300)
- Time limit for MILP solver (coverage_optimal only)
- Increase for large problems that need more time
- Solver returns best found solution if timeout is reached

**`--coverage-cloud-weight`** (0.0-1.0, default: 0.3)
- Weight for cloud cover in coverage cost function
- Higher value = prioritize low cloud cover images

**`--coverage-quality-weight`** (0.0-1.0, default: 0.7)
- Weight for quality score in coverage cost function
- Must sum to 1.0 with coverage-cloud-weight

#### Algorithm Details

1. **Point Sampling**: AOI is discretized into a uniform grid of points
2. **Coverage Matrix**: For each candidate image, determine which points it covers
3. **Set Cover Problem**: Find minimal subset of images that cover all (or target fraction) of points
4. **Cost Function**: `gain / (cloud_weight × cloud_penalty + quality_weight × quality_penalty)`

**Greedy Algorithm**:
- Each iteration selects the candidate with best gain/cost ratio
- Stops when coverage target is reached or no progress possible
- Fast and near-optimal for most cases

**MILP Algorithm**:
- Formulates as binary integer program
- Decision variables: x[j] ∈ {0,1} for each candidate
- Constraints: Each point must be covered by at least one selected candidate
- Objective: Minimize weighted sum of selected candidates
- Solved with branch-and-bound using OR-Tools

#### Performance Considerations

- **Grid spacing** affects both accuracy and runtime:
  - 50m spacing: High accuracy, slower (recommended for <100 km² AOIs)
  - 100m spacing: Good balance (recommended default)
  - 200m spacing: Fast but less precise (for >1000 km² AOIs)

- **Pre-filtering** reduces candidate pool:
  - Use stricter `max_cloud_cover` and `min_aoi_coverage` filters
  - Reduces problem size and improves solver performance

- **Very large AOIs** (>5000 km²):
  - Consider partitioning into sub-regions
  - Use coarser grid spacing (150-200m)
  - Use greedy strategy instead of optimal

- **MILP solver timeout**:
  - Default 300s (5 min) works for most small-medium problems
  - Increase to 600-1800s for larger problems
  - If timeout occurs, solver returns best feasible solution found

## Automatic Scheduling

The collector now supports automatic periodic downloads using a scheduler daemon. This allows for unattended, recurring image collection based on configurable schedules.

### Schedule Types

*   **Yearly**: Run once per year on a specific date (e.g., January 1st)
*   **Monthly**: Run on a specific day each month (e.g., 1st of every month)
*   **Weekly**: Run on a specific day each week (e.g., every Monday)
*   **Custom**: Define a custom schedule using cron expressions

### Auto-Selection Strategies

*   **best_n**: Download the top N products ranked by quality score
*   **all_above_threshold**: Download all products meeting a minimum quality threshold
*   **best_per_week**: Download the best product from each week in the date range
*   **coverage_greedy**: Fast greedy heuristic for near-optimal area coverage (suitable for large AOIs)
*   **coverage_optimal**: MILP-based globally optimal coverage solution (requires OR-Tools, best for small-medium AOIs)

Quality scores (for quality-based strategies) are calculated from weighted combination of:
- AOI coverage percentage (higher is better)
- Cloud cover percentage (lower is better)
- Date recency (more recent is better)

### Configuration

1. Create a configuration file (e.g., `config.yaml`) based on `config.example.yaml`:

```yaml
jobs:
  - name: "weekly_coastal_monitoring"
    aoi_path: "~/SatShor/src/shoreline_extractor/data/json/coastal_area.geojson"
    schedule:
      type: "weekly"
      day_of_week: "monday"
      time: "02:00"
    date_range:
      type: "relative"
      days: 7
    filters:
      max_cloud_cover: 20
      min_aoi_coverage: 90
      product_level: "L2A"
    auto_select:
      strategy: "best_n"  # or "coverage_greedy", "coverage_optimal"
      max_products: 3
      # Coverage optimization parameters (for coverage_greedy/coverage_optimal)
      min_coverage_fraction: 0.98  # Target coverage (0.95-1.0)
      grid_spacing_meters: 100  # Sampling density (50-200m recommended)
      solver_timeout_seconds: 600  # Time limit for MILP solver
      coverage_cloud_weight: 0.3  # Weight for cloud cover in cost
      coverage_quality_weight: 0.7  # Weight for quality score in cost
    output_dir: "~/SatShor/src/shoreline_extractor/data/img"
```

See `config.example.yaml` for comprehensive examples of all configuration options.

### Running the Scheduler

```bash
# Run scheduler in foreground
python scheduler_daemon.py --config config.yaml

# Validate configuration without running
python scheduler_daemon.py --config config.yaml --validate-only

# Run with debug logging
python scheduler_daemon.py --config config.yaml --log-level DEBUG

# Run as daemon (Unix-like systems only)
python scheduler_daemon.py --config config.yaml --daemon --pid-file /var/run/satshor_scheduler.pid
```

### Deployment

#### Linux (systemd service)

Create a systemd service file at `/etc/systemd/system/satshor-scheduler.service`:

```ini
[Unit]
Description=SatShor Satellite Image Collection Scheduler
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/SatShor/src/image_collector
ExecStart=/usr/bin/python3 scheduler_daemon.py --config config.yaml
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable satshor-scheduler
sudo systemctl start satshor-scheduler
sudo systemctl status satshor-scheduler
```

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "When the computer starts"
4. Set action to start program: `python.exe`
5. Add arguments: `C:\Path\To\SatShor\src\image_collector\scheduler_daemon.py --config C:\Path\To\config.yaml`
6. Set "Start in": `C:\Path\To\SatShor\src\image_collector`

#### Using cron (Alternative to daemon)

For simpler setups, you can use cron to run collections directly:

```bash
# Run weekly collection every Monday at 2 AM
0 2 * * 1 cd /path/to/SatShor/src/image_collector && python collector.py --aoi /path/to/aoi.geojson --auto-select best_n --max-products 3
```

### Monitoring and Logs

Scheduler logs are written to `logs/scheduler.log`. Monitor with:

```bash
# View logs
tail -f logs/scheduler.log

# Check for errors
grep ERROR logs/scheduler.log
```

## Configuration

Create a `.env` file in the `SatShor` root directory with your CDSE credentials:

```dotenv
CDSE_USERNAME=your_username
CDSE_PASSWORD=your_password
# Or:
# CDSE_ACCESS_TOKEN=your_access_token
```

## Development Notes

*   Uses the CDSE OData API (`https://catalogue.dataspace.copernicus.eu/odata/v1/`).
*   Handles CDSE authentication via OAuth2.
*   Calculates AoI coverage using geometric intersection (requires `shapely` and `geopandas`).
*   Uses `rich` for presentation.
*   Uses `APScheduler` for job scheduling.
*   Configuration uses YAML format for readability and flexibility.
