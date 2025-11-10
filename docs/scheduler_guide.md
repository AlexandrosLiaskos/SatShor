# SatShor Scheduler Guide

Comprehensive documentation for the automatic satellite image collection scheduling system.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Configuration Guide](#configuration-guide)
- [Auto-Selection Strategies](#auto-selection-strategies)
- [Deployment Guide](#deployment-guide)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Real-World Examples](#real-world-examples)

## Overview

The SatShor scheduler enables automatic, unattended collection of satellite imagery on recurring schedules. Instead of manually running the collector script, you define collection jobs in a configuration file, and the scheduler executes them automatically according to your specified schedule (yearly, monthly, weekly, or custom intervals).

### Key Benefits

- **Automation**: Set it and forget it - images download automatically
- **Consistency**: Regular monitoring with predictable data collection
- **Efficiency**: Smart product selection minimizes storage and bandwidth
- **Reliability**: Automatic retry on failures, state tracking prevents duplicates
- **Flexibility**: Multiple jobs, different AOIs, custom schedules

### Architecture

```
┌─────────────────────┐
│  config.yaml        │
│  (Job Definitions)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  scheduler_daemon   │
│  (Main Process)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  APScheduler        │
│  (Job Engine)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      ┌─────────────────────┐
│  collection_core    │─────▶│  CDSE API           │
│  (Download Logic)   │      │  (Sentinel-2 Data)  │
└─────────────────────┘      └─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Output Directory   │
│  (Downloaded Images)│
└─────────────────────┘
```

## Configuration Guide

The scheduler uses YAML configuration files to define collection jobs. Each job specifies what to download, when to download it, and how to select products.

### Configuration Structure

```yaml
# Global scheduler settings
max_concurrent_jobs: 1
job_coalesce: true
job_max_instances: 1

# Collection jobs
jobs:
  - name: "job_identifier"
    enabled: true
    aoi_path: "path/to/aoi.geojson"
    schedule:
      type: "weekly|monthly|yearly|custom"
      # ... schedule-specific fields
    date_range:
      type: "relative|absolute"
      # ... date range fields
    filters:
      max_cloud_cover: 20
      min_aoi_coverage: 90
      product_level: "L2A"
    auto_select:
      strategy: "best_n|all_above_threshold|best_per_week"
      # ... strategy-specific fields
    output_dir: "path/to/output"
```

### Global Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_concurrent_jobs` | int | 1 | Maximum number of jobs running simultaneously |
| `job_coalesce` | bool | true | Combine multiple missed runs into one execution |
| `job_max_instances` | int | 1 | Maximum instances of the same job running at once |

### Job Configuration Fields

#### Basic Fields

- **name** (required): Unique identifier for the job. Must contain only letters, numbers, underscores, and hyphens.
- **enabled** (optional, default: true): Whether the job is active. Set to `false` to temporarily disable.
- **aoi_path** (required): Path to GeoJSON file defining the Area of Interest. Supports `~` for home directory.
- **output_dir** (required): Directory where downloaded products will be stored.

#### Schedule Configuration

Defines when the job runs. Four types available:

##### 1. Yearly Schedule

Runs once per year on a specific date.

```yaml
schedule:
  type: "yearly"
  month: 1        # 1-12 (January-December)
  day: 1          # 1-31
  time: "00:00"   # HH:MM (24-hour format)
```

**Example**: Run on January 1st at midnight every year.

##### 2. Monthly Schedule

Runs on a specific day each month.

```yaml
schedule:
  type: "monthly"
  day: 1          # 1-31
  time: "03:00"   # HH:MM (24-hour format)
```

**Example**: Run on the 1st of each month at 3 AM.

##### 3. Weekly Schedule

Runs on a specific day each week.

```yaml
schedule:
  type: "weekly"
  day_of_week: "monday"  # Can be day name or number (0=Monday, 6=Sunday)
  time: "02:00"          # HH:MM (24-hour format)
```

**Valid day_of_week values**: "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", or 0-6.

**Example**: Run every Monday at 2 AM.

##### 4. Custom Schedule

Uses standard cron expressions for maximum flexibility.

```yaml
schedule:
  type: "custom"
  cron: "0 1 */3 * *"  # minute hour day month day_of_week
```

**Cron format**: `minute hour day month day_of_week`

**Common cron examples**:
- `0 2 * * *` - Every day at 2 AM
- `30 4 1,15 * *` - 1st and 15th of month at 4:30 AM
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 1,3,5` - Monday, Wednesday, Friday at midnight
- `0 1 */3 * *` - Every 3 days at 1 AM

#### Date Range Configuration

Defines which time period to search for products.

##### Relative Date Range

Searches for products from the last N days before execution.

```yaml
date_range:
  type: "relative"
  days: 7  # Number of days to look back
```

**Use case**: Always get the most recent imagery (e.g., last week, last month).

##### Absolute Date Range

Always searches the same fixed date range.

```yaml
date_range:
  type: "absolute"
  start_date: "2024-01-01"  # YYYY-MM-DD
  end_date: "2024-12-31"    # YYYY-MM-DD
```

**Use case**: Historical data collection, specific event monitoring.

#### Filter Configuration

Defines product filtering criteria.

```yaml
filters:
  max_cloud_cover: 20      # Maximum cloud cover % (0-100)
  min_aoi_coverage: 90     # Minimum AOI coverage % (0-100)
  product_level: "L2A"     # "L1C" or "L2A"
```

| Field | Range | Recommended | Description |
|-------|-------|-------------|-------------|
| `max_cloud_cover` | 0-100 | 10-25 | Products with more clouds are excluded |
| `min_aoi_coverage` | 0-100 | 80-100 | Products covering less of AOI are excluded |
| `product_level` | L1C/L2A | L2A | Atmospheric correction level |

**Recommendations**:
- Coastal monitoring: `max_cloud_cover: 15-20`, `min_aoi_coverage: 90-100`
- Large area coverage: `max_cloud_cover: 25-30`, `min_aoi_coverage: 70-80`
- High-quality archival: `max_cloud_cover: 5-10`, `min_aoi_coverage: 95-100`

#### Auto-Selection Configuration

Defines how products are automatically selected for download.

```yaml
auto_select:
  strategy: "best_n"           # Selection strategy (see below)
  max_products: 5              # For "best_n" strategy
  quality_threshold: 0.7       # For "all_above_threshold" strategy (0-1)
  
  # Quality score weights (must sum to 1.0)
  aoi_coverage_weight: 0.4     # Weight for AOI coverage
  cloud_cover_weight: 0.4      # Weight for cloud cover
  recency_weight: 0.2          # Weight for date recency
```

See [Auto-Selection Strategies](#auto-selection-strategies) section for details.

## Auto-Selection Strategies

The scheduler uses quality-based algorithms to automatically select which products to download. This eliminates the need for manual selection while ensuring optimal data quality.

### Quality Score Calculation

Each product receives a quality score from 0 to 1 based on three factors:

```
Quality Score = (aoi_weight × AOI_score) + 
                (cloud_weight × Cloud_score) + 
                (recency_weight × Recency_score)
```

Where:
- **AOI_score**: Normalized AOI coverage (0-1, higher is better)
- **Cloud_score**: Inverted cloud cover (0-1, lower cloud cover = higher score)
- **Recency_score**: Normalized date recency (0-1, more recent = higher score)

**Default weights**: AOI 40%, Cloud 40%, Recency 20%

### Strategy 1: best_n

Downloads the top N products ranked by quality score.

```yaml
auto_select:
  strategy: "best_n"
  max_products: 5
  aoi_coverage_weight: 0.4
  cloud_cover_weight: 0.4
  recency_weight: 0.2
```

**Use cases**:
- Regular monitoring with storage constraints
- Need consistent number of images per period
- Want only the highest quality products

**Example**: Weekly coastal monitoring downloading best 3 images.

### Strategy 2: all_above_threshold

Downloads all products meeting a minimum quality threshold.

```yaml
auto_select:
  strategy: "all_above_threshold"
  quality_threshold: 0.7  # 0-1 scale
  aoi_coverage_weight: 0.5
  cloud_cover_weight: 0.4
  recency_weight: 0.1
```

**Use cases**:
- Maximum data coverage
- Variable number of acceptable products
- Don't want to miss any good imagery

**Example**: Monthly archive where any product above 70% quality is valuable.

**Threshold recommendations**:
- 0.8-1.0: Very high quality only
- 0.7-0.8: Good quality
- 0.6-0.7: Acceptable quality
- Below 0.6: May include suboptimal products

### Strategy 3: best_per_week

Groups products by week and downloads the best from each week.

```yaml
auto_select:
  strategy: "best_per_week"
  aoi_coverage_weight: 0.4
  cloud_cover_weight: 0.4
  recency_weight: 0.2
```

**Use cases**:
- Temporal coverage over a long period
- Need representation from each week
- Change detection applications

**Example**: Annual collection ensuring at least one image per week.

### Customizing Quality Weights

Adjust weights based on your priorities:

**Maximize AOI coverage**:
```yaml
aoi_coverage_weight: 0.6
cloud_cover_weight: 0.3
recency_weight: 0.1
```

**Minimize cloud cover**:
```yaml
aoi_coverage_weight: 0.3
cloud_cover_weight: 0.6
recency_weight: 0.1
```

**Prioritize recent imagery**:
```yaml
aoi_coverage_weight: 0.3
cloud_cover_weight: 0.3
recency_weight: 0.4
```

## Deployment Guide

### Prerequisites

1. Python 3.8+ installed
2. Required packages: `pip install -r requirements.txt`
3. CDSE credentials in `.env` file
4. Valid configuration file (`config.yaml`)

### Local Testing

Before deploying as a service, test your configuration:

```bash
# Validate configuration
python scheduler_daemon.py --config config.yaml --validate-only

# Run in foreground with debug logging
python scheduler_daemon.py --config config.yaml --log-level DEBUG
```

Watch the logs to ensure jobs are scheduled correctly:
```bash
tail -f logs/scheduler.log
```

### Linux Deployment (systemd)

#### 1. Create systemd service file

Create `/etc/systemd/system/satshor-scheduler.service`:

```ini
[Unit]
Description=SatShor Satellite Image Collection Scheduler
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your_username
Group=your_group
WorkingDirectory=/path/to/SatShor/src/image_collector
Environment="PATH=/path/to/venv/bin:/usr/bin"
ExecStart=/path/to/venv/bin/python scheduler_daemon.py --config config.yaml
Restart=on-failure
RestartSec=30
StandardOutput=append:/var/log/satshor-scheduler.log
StandardError=append:/var/log/satshor-scheduler-error.log

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and start service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable satshor-scheduler

# Start service
sudo systemctl start satshor-scheduler

# Check status
sudo systemctl status satshor-scheduler

# View logs
sudo journalctl -u satshor-scheduler -f
```

#### 3. Managing the service

```bash
# Stop service
sudo systemctl stop satshor-scheduler

# Restart service
sudo systemctl restart satshor-scheduler

# Disable service
sudo systemctl disable satshor-scheduler
```

### Windows Deployment

#### Option 1: Task Scheduler

1. Open Task Scheduler (`taskschd.msc`)
2. Click "Create Task" (not "Create Basic Task")
3. **General Tab**:
   - Name: "SatShor Scheduler"
   - Description: "Automatic satellite image collection"
   - Select "Run whether user is logged on or not"
   - Check "Run with highest privileges"
4. **Triggers Tab**:
   - New → "At startup"
   - Delay: 1 minute
5. **Actions Tab**:
   - New → "Start a program"
   - Program: `C:\Path\To\Python\python.exe`
   - Arguments: `C:\Path\To\SatShor\src\image_collector\scheduler_daemon.py --config C:\Path\To\config.yaml`
   - Start in: `C:\Path\To\SatShor\src\image_collector`
6. **Conditions Tab**:
   - Uncheck "Start only if on AC power" (for laptops)
7. **Settings Tab**:
   - Check "If the task fails, restart every: 10 minutes"
   - Attempt restart: 3 times

#### Option 2: NSSM (Non-Sucking Service Manager)

1. Download NSSM from https://nssm.cc/
2. Install the service:

```cmd
nssm install SatShorScheduler "C:\Path\To\Python\python.exe" "C:\Path\To\scheduler_daemon.py --config C:\Path\To\config.yaml"
nssm set SatShorScheduler AppDirectory "C:\Path\To\SatShor\src\image_collector"
nssm set SatShorScheduler DisplayName "SatShor Satellite Scheduler"
nssm set SatShorScheduler Description "Automatic Sentinel-2 image collection"
nssm set SatShorScheduler Start SERVICE_AUTO_START
nssm start SatShorScheduler
```

3. Manage the service:
```cmd
# Check status
nssm status SatShorScheduler

# Stop service
nssm stop SatShorScheduler

# Restart service
nssm restart SatShorScheduler

# Remove service
nssm remove SatShorScheduler confirm
```

### Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/image_collector/ .
COPY .env .

# Create necessary directories
RUN mkdir -p logs

# Run scheduler
CMD ["python", "scheduler_daemon.py", "--config", "config.yaml"]
```

Build and run:

```bash
# Build image
docker build -t satshor-scheduler .

# Run container
docker run -d \
  --name satshor-scheduler \
  --restart unless-stopped \
  -v /path/to/data:/app/data \
  -v /path/to/config.yaml:/app/config.yaml \
  satshor-scheduler

# View logs
docker logs -f satshor-scheduler

# Stop container
docker stop satshor-scheduler
```

## Best Practices

### Scheduling Recommendations

| Monitoring Type | Frequency | Date Range | Strategy |
|----------------|-----------|------------|----------|
| Coastal erosion | Weekly | 7 days | best_n (3-5) |
| Seasonal changes | Monthly | 30 days | best_per_week |
| Annual archival | Yearly | 365 days | all_above_threshold |
| Event response | Custom | Variable | best_n (1-2) |

### Storage Management

**Estimate storage requirements**:
- Each Sentinel-2 L2A product: ~600-900 MB compressed, ~1-2 GB extracted
- Monthly collection (4 products): ~8-12 GB/month
- Weekly collection (3 products): ~12-18 GB/month

**Recommendations**:
- Monitor disk space regularly
- Set up automatic cleanup of old products
- Use external storage for long-term archives
- Consider downloading only specific bands if full product not needed

### Credentials Security

- **Never commit `.env` file** to version control
- Use environment variables or secrets management
- Rotate passwords regularly
- Use read-only CDSE accounts if possible
- Set proper file permissions: `chmod 600 .env` (Linux/Mac)

### Monitoring and Maintenance

**Set up log rotation** (Linux):

Create `/etc/logrotate.d/satshor`:
```
/path/to/SatShor/src/image_collector/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 your_user your_group
}
```

**Monitor scheduler health**:
```bash
# Check if running
ps aux | grep scheduler_daemon

# View recent logs
tail -n 100 logs/scheduler.log

# Check for errors
grep ERROR logs/scheduler.log | tail -n 20

# Check disk space
df -h /path/to/output
```

**Email notifications** (Linux):

Add to crontab:
```bash
0 8 * * * grep ERROR /path/to/logs/scheduler.log | tail -n 10 | mail -s "SatShor Errors" your@email.com
```

### Performance Optimization

- **Schedule jobs during off-peak hours** (e.g., 2-6 AM local time)
- **Stagger multiple jobs** to avoid CDSE API rate limits
- **Set reasonable `max_concurrent_jobs`** (default: 1 is safest)
- **Use `job_coalesce: true`** to avoid redundant runs after downtime

## Troubleshooting

### Common Issues

#### 1. Scheduler Not Starting

**Symptoms**: Process exits immediately

**Checks**:
```bash
# Validate configuration
python scheduler_daemon.py --config config.yaml --validate-only

# Check for syntax errors
python -m py_compile scheduler_daemon.py
```

**Common causes**:
- Invalid YAML syntax in config file
- Missing or incorrect AOI file paths
- Missing .env file or credentials
- Python package dependencies not installed

**Solution**:
```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Verify dependencies
pip install -r requirements.txt

# Check .env file exists and has credentials
cat .env | grep CDSE
```

#### 2. Jobs Not Executing

**Symptoms**: Scheduler runs but no downloads occur

**Checks**:
```bash
# View scheduler logs
tail -f logs/scheduler.log

# Check job schedule times
python scheduler_daemon.py --config config.yaml --validate-only
```

**Common causes**:
- Jobs disabled (`enabled: false`)
- Schedule time in the past
- System time/timezone mismatch
- APScheduler not firing triggers

**Solution**:
- Ensure `enabled: true` for jobs
- Check system time: `date`
- Wait for next scheduled run
- Temporarily set schedule to near future for testing

#### 3. Authentication Failures

**Symptoms**: "Error fetching token" or 401 errors in logs

**Checks**:
```bash
# Test credentials manually
python -c "from collector import get_access_token; print(get_access_token())"
```

**Common causes**:
- Incorrect credentials in .env
- Expired password
- CDSE service outage
- Network connectivity issues

**Solution**:
- Verify credentials at https://dataspace.copernicus.eu/
- Update .env with correct credentials
- Test network connectivity: `ping dataspace.copernicus.eu`
- Check CDSE service status

#### 4. No Products Found

**Symptoms**: Scheduler runs successfully but downloads nothing

**Checks**:
```bash
# Review filter criteria in config.yaml
# Check CDSE for available data manually
```

**Common causes**:
- Filters too restrictive (cloud cover, AOI coverage)
- Date range has no available imagery
- AOI too small or in problematic location

**Solution**:
- Relax cloud cover: increase `max_cloud_cover` to 30-40%
- Reduce AOI coverage requirement: decrease `min_aoi_coverage` to 70-80%
- Extend date range: increase `days` value
- Verify AOI coordinates are valid (WGS84)

#### 5. Disk Space Issues

**Symptoms**: Downloads fail, system slow

**Checks**:
```bash
# Check available space
df -h /path/to/output

# Check largest directories
du -h --max-depth=1 /path/to/output | sort -hr
```

**Solution**:
- Delete old products
- Move data to larger storage
- Reduce `max_products` in auto_select
- Use stricter filters to download less

### Debug Mode

Run with debug logging to diagnose issues:

```bash
python scheduler_daemon.py --config config.yaml --log-level DEBUG 2>&1 | tee debug.log
```

This captures all debug output for analysis.

### Getting Help

If issues persist:

1. Check logs: `logs/scheduler.log`
2. Run with `--validate-only` first
3. Test individual components:
   - Credentials: `python -c "from collector import get_access_token; print(get_access_token())"`
   - AOI loading: `python collector.py --aoi path/to/aoi.geojson` (interactive test)
4. Open an issue on GitHub with:
   - Configuration file (redacted credentials)
   - Relevant log excerpts
   - System information (OS, Python version)

## Real-World Examples

### Example 1: Weekly Coastal Erosion Monitoring

**Scenario**: Monitor coastal erosion with weekly updates, prioritizing clear images.

```yaml
jobs:
  - name: "coastal_erosion_weekly"
    enabled: true
    aoi_path: "~/SatShor/aois/coastline.geojson"
    
    schedule:
      type: "weekly"
      day_of_week: "sunday"  # Run Sunday morning
      time: "03:00"
    
    date_range:
      type: "relative"
      days: 7  # Last week
    
    filters:
      max_cloud_cover: 15  # Strict cloud cover
      min_aoi_coverage: 95  # Almost full coverage
      product_level: "L2A"
    
    auto_select:
      strategy: "best_n"
      max_products: 2  # Top 2 images per week
      aoi_coverage_weight: 0.5  # Prioritize coverage
      cloud_cover_weight: 0.4
      recency_weight: 0.1
    
    output_dir: "~/SatShor/data/coastal_monitoring"
```

**Expected behavior**: Downloads 2 best images each week, ~8-10 images/month, ~100 GB/year.

### Example 2: Monthly Seasonal Change Detection

**Scenario**: Track seasonal vegetation changes, need temporal consistency.

```yaml
jobs:
  - name: "seasonal_vegetation"
    enabled: true
    aoi_path: "~/SatShor/aois/forest_area.geojson"
    
    schedule:
      type: "monthly"
      day: 1  # First of month
      time: "04:00"
    
    date_range:
      type: "relative"
      days: 30  # Last month
    
    filters:
      max_cloud_cover: 25  # More lenient
      min_aoi_coverage: 90
      product_level: "L2A"
    
    auto_select:
      strategy: "best_per_week"  # One per week
      aoi_coverage_weight: 0.4
      cloud_cover_weight: 0.3
      recency_weight: 0.3  # Temporal distribution important
    
    output_dir: "~/SatShor/data/seasonal_monitoring"
```

**Expected behavior**: ~4 images per month (one per week), ~50 images/year, ~75 GB/year.

### Example 3: Annual High-Quality Archive

**Scenario**: Build annual archive of highest quality images for research.

```yaml
jobs:
  - name: "annual_archive"
    enabled: true
    aoi_path: "~/SatShor/aois/study_region.geojson"
    
    schedule:
      type: "yearly"
      month: 1  # January
      day: 15
      time: "00:00"
    
    date_range:
      type: "absolute"
      start_date: "2024-01-01"  # Collect previous year
      end_date: "2024-12-31"
    
    filters:
      max_cloud_cover: 5  # Very strict
      min_aoi_coverage: 100  # Full coverage only
      product_level: "L2A"
    
    auto_select:
      strategy: "all_above_threshold"
      quality_threshold: 0.9  # Highest quality only
      aoi_coverage_weight: 0.4
      cloud_cover_weight: 0.5  # Prioritize clear skies
      recency_weight: 0.1
    
    output_dir: "~/SatShor/archives/yearly"
```

**Expected behavior**: Variable count (5-20 images/year depending on cloud conditions), run once per year.

### Example 4: Multi-Site Monitoring

**Scenario**: Monitor multiple locations with different requirements.

```yaml
jobs:
  # Site 1: Critical infrastructure (frequent updates)
  - name: "site1_critical"
    enabled: true
    aoi_path: "~/SatShor/aois/site1.geojson"
    schedule:
      type: "weekly"
      day_of_week: "wednesday"
      time: "02:00"
    date_range:
      type: "relative"
      days: 7
    filters:
      max_cloud_cover: 20
      min_aoi_coverage: 95
      product_level: "L2A"
    auto_select:
      strategy: "best_n"
      max_products: 3
    output_dir: "~/SatShor/data/site1"

  # Site 2: General monitoring (monthly)
  - name: "site2_general"
    enabled: true
    aoi_path: "~/SatShor/aois/site2.geojson"
    schedule:
      type: "monthly"
      day: 10
      time: "03:00"
    date_range:
      type: "relative"
      days: 30
    filters:
      max_cloud_cover: 30
      min_aoi_coverage: 85
      product_level: "L2A"
    auto_select:
      strategy: "best_per_week"
    output_dir: "~/SatShor/data/site2"

  # Site 3: Archive only (yearly)
  - name: "site3_archive"
    enabled: true
    aoi_path: "~/SatShor/aois/site3.geojson"
    schedule:
      type: "yearly"
      month: 12
      day: 31
      time: "23:00"
    date_range:
      type: "relative"
      days: 365
    filters:
      max_cloud_cover: 10
      min_aoi_coverage: 100
      product_level: "L2A"
    auto_select:
      strategy: "all_above_threshold"
      quality_threshold: 0.85
    output_dir: "~/SatShor/archives/site3"
```

**Expected behavior**: Staggered schedules prevent resource conflicts, each site managed independently.

### Example 5: Event-Driven Collection

**Scenario**: Monitor area after natural disaster or event.

```yaml
jobs:
  - name: "event_response_flood"
    enabled: true  # Enable when event occurs
    aoi_path: "~/SatShor/aois/flood_zone.geojson"
    
    schedule:
      type: "custom"
      cron: "0 */12 * * *"  # Every 12 hours
    
    date_range:
      type: "relative"
      days: 2  # Very recent imagery
    
    filters:
      max_cloud_cover: 40  # Lenient due to event conditions
      min_aoi_coverage: 75  # Partial coverage acceptable
      product_level: "L2A"
    
    auto_select:
      strategy: "best_n"
      max_products: 1  # Latest image only
      aoi_coverage_weight: 0.3
      cloud_cover_weight: 0.2
      recency_weight: 0.5  # Prioritize most recent
    
    output_dir: "~/SatShor/events/flood_2024"
```

**Expected behavior**: Frequent checks for new imagery, downloads most recent available, disable after event period ends.

---

## Summary

The SatShor scheduler provides a powerful, flexible system for automated satellite image collection. By understanding the configuration options, auto-selection strategies, and deployment methods, you can build a reliable monitoring system tailored to your specific needs.

**Key Takeaways**:
1. Start with the example configs and customize incrementally
2. Test thoroughly with `--validate-only` before deploying
3. Monitor logs regularly, especially initially
4. Adjust quality weights based on your priorities
5. Plan storage capacity based on collection frequency

For additional help, consult the main README, check logs, or open an issue on GitHub.
