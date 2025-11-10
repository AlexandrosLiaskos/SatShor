"""
Configuration schema for scheduled satellite image collection jobs.

This module defines the data models and validation logic for the scheduler configuration,
including schedule definitions, collection job parameters, and configuration loading.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import re


@dataclass
class ScheduleConfig:
    """Defines the periodicity of a collection job."""
    
    type: Literal["yearly", "monthly", "weekly", "custom"]
    
    # For yearly schedules
    month: Optional[int] = None  # 1-12
    day: Optional[int] = None  # 1-31
    
    # For monthly schedules
    # day: int (1-31)
    
    # For weekly schedules
    day_of_week: Optional[str] = None  # "monday", "tuesday", etc. or 0-6
    
    # For all scheduled types
    time: str = "00:00"  # HH:MM format
    
    # For custom schedules
    cron: Optional[str] = None  # Standard cron expression
    
    def __post_init__(self):
        """Validate schedule configuration."""
        if self.type == "yearly":
            if self.month is None or self.day is None:
                raise ValueError("Yearly schedule requires 'month' and 'day'")
            if not (1 <= self.month <= 12):
                raise ValueError(f"Month must be 1-12, got {self.month}")
            if not (1 <= self.day <= 31):
                raise ValueError(f"Day must be 1-31, got {self.day}")
        
        elif self.type == "monthly":
            if self.day is None:
                raise ValueError("Monthly schedule requires 'day'")
            if not (1 <= self.day <= 31):
                raise ValueError(f"Day must be 1-31, got {self.day}")
        
        elif self.type == "weekly":
            if self.day_of_week is None:
                raise ValueError("Weekly schedule requires 'day_of_week'")
            # Validate day_of_week
            valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            if isinstance(self.day_of_week, str):
                if self.day_of_week.lower() not in valid_days:
                    try:
                        day_num = int(self.day_of_week)
                        if not (0 <= day_num <= 6):
                            raise ValueError(f"day_of_week must be 0-6 or day name, got {self.day_of_week}")
                    except ValueError:
                        raise ValueError(f"Invalid day_of_week: {self.day_of_week}")
        
        elif self.type == "custom":
            if self.cron is None:
                raise ValueError("Custom schedule requires 'cron' expression")
            self._validate_cron(self.cron)
        
        # Validate time format
        self._validate_time_format(self.time)
    
    @staticmethod
    def _validate_time_format(time_str: str):
        """Validate HH:MM time format."""
        pattern = r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$'
        if not re.match(pattern, time_str):
            raise ValueError(f"Invalid time format '{time_str}', expected HH:MM (24-hour)")
    
    @staticmethod
    def _validate_cron(cron_expr: str):
        """Validate cron expression format."""
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Cron expression must have 5 parts, got {len(parts)}: {cron_expr}")
        # Basic validation - APScheduler will do full validation


@dataclass
class DateRangeConfig:
    """Defines how to calculate date ranges for product queries."""
    
    type: Literal["relative", "absolute"]
    
    # For relative date ranges
    days: Optional[int] = None  # Number of days before execution
    
    # For absolute date ranges
    start_date: Optional[str] = None  # YYYY-MM-DD format
    end_date: Optional[str] = None  # YYYY-MM-DD format
    
    def __post_init__(self):
        """Validate date range configuration."""
        if self.type == "relative":
            if self.days is None:
                raise ValueError("Relative date range requires 'days'")
            if self.days <= 0:
                raise ValueError(f"days must be positive, got {self.days}")
        
        elif self.type == "absolute":
            if self.start_date is None or self.end_date is None:
                raise ValueError("Absolute date range requires 'start_date' and 'end_date'")
            # Validate date formats
            try:
                start = datetime.strptime(self.start_date, "%Y-%m-%d")
                end = datetime.strptime(self.end_date, "%Y-%m-%d")
                if start >= end:
                    raise ValueError(f"start_date must be before end_date")
            except ValueError as e:
                raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {e}")
    
    def resolve_dates(self) -> tuple[str, str]:
        """
        Resolve the date range to actual start and end dates.
        
        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format
        """
        if self.type == "absolute":
            return (self.start_date, self.end_date)
        
        # Relative date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days)
        return (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))


@dataclass
class FilterConfig:
    """Defines product filtering criteria."""
    
    max_cloud_cover: float = 100.0  # 0-100
    min_aoi_coverage: float = 0.0  # 0-100
    product_level: str = "L2A"  # "L1C" or "L2A"
    
    def __post_init__(self):
        """Validate filter configuration."""
        if not (0 <= self.max_cloud_cover <= 100):
            raise ValueError(f"max_cloud_cover must be 0-100, got {self.max_cloud_cover}")
        if not (0 <= self.min_aoi_coverage <= 100):
            raise ValueError(f"min_aoi_coverage must be 0-100, got {self.min_aoi_coverage}")
        if self.product_level not in ["L1C", "L2A"]:
            raise ValueError(f"product_level must be 'L1C' or 'L2A', got {self.product_level}")


@dataclass
class AutoSelectConfig:
    """
    Defines automatic product selection strategy.
    
    Available strategies:
    - best_n: Select top N products by quality score
    - all_above_threshold: Select all products above quality threshold
    - best_per_week: Select best product per week
    - coverage_greedy: Fast greedy heuristic for near-optimal coverage (suitable for large AOIs)
    - coverage_optimal: MILP-based globally optimal solution (may be slow for large problems, requires OR-Tools)
    """
    
    strategy: Literal["best_n", "all_above_threshold", "best_per_week", "coverage_greedy", "coverage_optimal"]
    max_products: int = 5  # For "best_n" strategy
    quality_threshold: float = 0.7  # For "all_above_threshold" strategy (0-1)
    
    # Quality score weights (must sum to 1.0)
    aoi_coverage_weight: float = 0.4
    cloud_cover_weight: float = 0.4
    recency_weight: float = 0.2
    
    # Coverage optimization parameters
    min_coverage_fraction: float = 0.99  # Target coverage fraction (0-1), allows tolerance for uncovered areas
    grid_spacing_meters: Optional[float] = None  # Grid spacing for point sampling (None = auto-calculate based on AOI size)
    solver_timeout_seconds: int = 300  # Time limit for MILP solver (only used for coverage_optimal)
    coverage_cloud_weight: float = 0.3  # Weight for cloud cover in coverage cost function
    coverage_quality_weight: float = 0.7  # Weight for quality score in coverage cost function
    
    def __post_init__(self):
        """Validate auto-select configuration."""
        if self.max_products <= 0:
            raise ValueError(f"max_products must be positive, got {self.max_products}")
        if not (0 <= self.quality_threshold <= 1):
            raise ValueError(f"quality_threshold must be 0-1, got {self.quality_threshold}")
        
        # Validate weights
        total_weight = self.aoi_coverage_weight + self.cloud_cover_weight + self.recency_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Quality score weights must sum to 1.0, got {total_weight}")
        
        if any(w < 0 for w in [self.aoi_coverage_weight, self.cloud_cover_weight, self.recency_weight]):
            raise ValueError("All quality score weights must be non-negative")
        
        # Validate coverage optimization parameters
        if not (0.5 <= self.min_coverage_fraction <= 1.0):
            raise ValueError(f"min_coverage_fraction must be 0.5-1.0, got {self.min_coverage_fraction}")
        
        if self.grid_spacing_meters is not None and self.grid_spacing_meters <= 0:
            raise ValueError(f"grid_spacing_meters must be positive, got {self.grid_spacing_meters}")
        
        if self.solver_timeout_seconds <= 0:
            raise ValueError(f"solver_timeout_seconds must be positive, got {self.solver_timeout_seconds}")
        
        # Validate coverage weights
        coverage_weight_sum = self.coverage_cloud_weight + self.coverage_quality_weight
        if abs(coverage_weight_sum - 1.0) > 0.01:
            raise ValueError(f"Coverage weights must sum to 1.0, got {coverage_weight_sum}")
        
        if self.coverage_cloud_weight < 0 or self.coverage_quality_weight < 0:
            raise ValueError("Coverage weights must be non-negative")
        
        # Check OR-Tools availability for coverage_optimal strategy
        if self.strategy == "coverage_optimal":
            try:
                import ortools
            except ImportError:
                raise ValueError("coverage_optimal strategy requires OR-Tools. Install with: pip install ortools>=9.14.0")


@dataclass
class CollectionJobConfig:
    """Defines a single scheduled collection job."""
    
    name: str
    aoi_path: str
    schedule: ScheduleConfig
    date_range: DateRangeConfig
    filters: FilterConfig
    auto_select: AutoSelectConfig
    output_dir: str
    enabled: bool = True
    
    def __post_init__(self):
        """Validate collection job configuration."""
        # Validate AOI file exists
        aoi_path = Path(self.aoi_path).expanduser()
        if not aoi_path.exists():
            raise ValueError(f"AOI file not found: {self.aoi_path}")
        if not aoi_path.suffix.lower() == ".geojson":
            raise ValueError(f"AOI file must be .geojson, got {aoi_path.suffix}")
        
        # Validate output directory is writable
        output_path = Path(self.output_dir).expanduser()
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create output directory {self.output_dir}: {e}")
        
        # Validate name is a valid identifier
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.name):
            raise ValueError(f"Job name must contain only letters, numbers, underscores, and hyphens: {self.name}")


@dataclass
class SchedulerConfig:
    """Root configuration for the scheduler."""
    
    jobs: List[CollectionJobConfig]
    
    # Global settings
    max_concurrent_jobs: int = 1
    job_coalesce: bool = True  # Combine multiple missed runs into one
    job_max_instances: int = 1  # Max instances of same job running simultaneously
    
    def __post_init__(self):
        """Validate scheduler configuration."""
        if not self.jobs:
            raise ValueError("At least one job must be configured")
        
        # Check for duplicate job names
        names = [job.name for job in self.jobs]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate job names found: {duplicates}")
        
        if self.max_concurrent_jobs <= 0:
            raise ValueError(f"max_concurrent_jobs must be positive, got {self.max_concurrent_jobs}")
        if self.job_max_instances <= 0:
            raise ValueError(f"job_max_instances must be positive, got {self.job_max_instances}")


def load_config(config_path: str) -> SchedulerConfig:
    """
    Load and validate scheduler configuration from YAML file.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Validated SchedulerConfig object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
        yaml.YAMLError: If YAML parsing fails
    """
    config_file = Path(config_path).expanduser()
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)
    
    if not isinstance(raw_config, dict):
        raise ValueError("Configuration must be a YAML dictionary")
    
    # Parse jobs
    jobs = []
    for job_data in raw_config.get('jobs', []):
        try:
            # Parse nested configurations
            schedule = ScheduleConfig(**job_data['schedule'])
            date_range = DateRangeConfig(**job_data['date_range'])
            filters = FilterConfig(**job_data.get('filters', {}))
            auto_select = AutoSelectConfig(**job_data['auto_select'])
            
            job = CollectionJobConfig(
                name=job_data['name'],
                aoi_path=job_data['aoi_path'],
                schedule=schedule,
                date_range=date_range,
                filters=filters,
                auto_select=auto_select,
                output_dir=job_data['output_dir'],
                enabled=job_data.get('enabled', True)
            )
            jobs.append(job)
        except KeyError as e:
            raise ValueError(f"Missing required field in job '{job_data.get('name', 'unknown')}': {e}")
        except Exception as e:
            raise ValueError(f"Error parsing job '{job_data.get('name', 'unknown')}': {e}")
    
    # Parse global settings
    config = SchedulerConfig(
        jobs=jobs,
        max_concurrent_jobs=raw_config.get('max_concurrent_jobs', 1),
        job_coalesce=raw_config.get('job_coalesce', True),
        job_max_instances=raw_config.get('job_max_instances', 1)
    )
    
    return config


def resolve_date_range(date_range_config: DateRangeConfig) -> tuple[str, str]:
    """
    Convenience function to resolve a DateRangeConfig to actual dates.
    
    Args:
        date_range_config: DateRangeConfig object
        
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    return date_range_config.resolve_dates()
