"""
Scheduler for automatic periodic satellite image collection.

This module orchestrates automatic downloads using APScheduler based on
configuration files defining collection jobs and schedules.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from config_schema import (
    SchedulerConfig,
    CollectionJobConfig,
    load_config,
    resolve_date_range,
)
from collection_core import run_collection, CollectionResult


class ScheduledCollector:
    """Main scheduler class for orchestrating automatic collection jobs."""
    
    def __init__(self, config_path: str):
        """
        Initialize the scheduler with a configuration file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.config: Optional[SchedulerConfig] = None
        self.scheduler: Optional[BackgroundScheduler] = None
        self._setup_logging()
        
        # Load configuration
        try:
            self.config = load_config(config_path)
            logging.info(f"Loaded configuration with {len(self.config.jobs)} jobs")
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}", exc_info=True)
            raise
    
    def _setup_logging(self):
        """Configure logging for the scheduler."""
        # Create logs directory
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Setup file handler
        log_file = log_dir / "scheduler.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Setup formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to root logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        
        # Also add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def setup_jobs(self):
        """Setup all configured jobs in the scheduler."""
        if self.config is None:
            raise RuntimeError("Configuration not loaded")
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': self.config.job_coalesce,
                'max_instances': self.config.job_max_instances,
            }
        )
        
        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
        
        # Add jobs
        for job_config in self.config.jobs:
            if not job_config.enabled:
                logging.info(f"Skipping disabled job: {job_config.name}")
                continue
            
            try:
                trigger = self._create_trigger(job_config)
                self.scheduler.add_job(
                    func=self.execute_job,
                    trigger=trigger,
                    args=[job_config],
                    id=job_config.name,
                    name=job_config.name,
                    replace_existing=True,
                )
                logging.info(f"Added job: {job_config.name} with schedule: {job_config.schedule.type}")
            except Exception as e:
                logging.error(f"Failed to add job {job_config.name}: {e}", exc_info=True)
    
    def _create_trigger(self, job_config: CollectionJobConfig):
        """
        Create an APScheduler trigger from job configuration.
        
        Args:
            job_config: Collection job configuration
            
        Returns:
            APScheduler trigger object
        """
        schedule = job_config.schedule
        hour, minute = map(int, schedule.time.split(':'))
        
        if schedule.type == "yearly":
            return self._create_yearly_trigger(schedule.month, schedule.day, hour, minute)
        elif schedule.type == "monthly":
            return self._create_monthly_trigger(schedule.day, hour, minute)
        elif schedule.type == "weekly":
            return self._create_weekly_trigger(schedule.day_of_week, hour, minute)
        elif schedule.type == "custom":
            return self._create_custom_trigger(schedule.cron)
        else:
            raise ValueError(f"Unknown schedule type: {schedule.type}")
    
    def _create_yearly_trigger(self, month: int, day: int, hour: int, minute: int) -> CronTrigger:
        """Create a yearly cron trigger."""
        return CronTrigger(
            month=month,
            day=day,
            hour=hour,
            minute=minute
        )
    
    def _create_monthly_trigger(self, day: int, hour: int, minute: int) -> CronTrigger:
        """Create a monthly cron trigger."""
        return CronTrigger(
            day=day,
            hour=hour,
            minute=minute
        )
    
    def _create_weekly_trigger(self, day_of_week: str, hour: int, minute: int) -> CronTrigger:
        """Create a weekly cron trigger."""
        # Convert day name to number if needed
        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        
        if isinstance(day_of_week, str):
            day_of_week_lower = day_of_week.lower()
            if day_of_week_lower in day_map:
                day_num = day_map[day_of_week_lower]
            else:
                try:
                    day_num = int(day_of_week)
                except ValueError:
                    raise ValueError(f"Invalid day_of_week: {day_of_week}")
        else:
            day_num = day_of_week
        
        return CronTrigger(
            day_of_week=day_num,
            hour=hour,
            minute=minute
        )
    
    def _create_custom_trigger(self, cron_expr: str) -> CronTrigger:
        """Create a custom cron trigger from expression."""
        # Parse cron expression: minute hour day month day_of_week
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        
        minute, hour, day, month, day_of_week = parts
        
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        )
    
    def execute_job(self, job_config: CollectionJobConfig):
        """
        Execute a collection job.
        
        Args:
            job_config: Collection job configuration
        """
        job_name = job_config.name
        logging.info(f"Starting job execution: {job_name}")
        
        try:
            # Resolve date range
            start_date, end_date = resolve_date_range(job_config.date_range)
            logging.info(f"Job {job_name}: Date range {start_date} to {end_date}")
            
            # Expand paths
            aoi_path = str(Path(job_config.aoi_path).expanduser())
            output_dir = str(Path(job_config.output_dir).expanduser())
            
            # Run collection
            result: CollectionResult = run_collection(
                aoi_path=aoi_path,
                start_date=start_date,
                end_date=end_date,
                max_cloud=job_config.filters.max_cloud_cover,
                min_aoi=job_config.filters.min_aoi_coverage,
                product_level=job_config.filters.product_level,
                output_dir=output_dir,
                auto_select_strategy=job_config.auto_select.strategy,
                max_products=job_config.auto_select.max_products,
                quality_threshold=job_config.auto_select.quality_threshold,
                aoi_weight=job_config.auto_select.aoi_coverage_weight,
                cloud_weight=job_config.auto_select.cloud_cover_weight,
                recency_weight=job_config.auto_select.recency_weight,
            )
            
            # Log results
            if result.success:
                logging.info(
                    f"Job {job_name} completed successfully: {result.message}. "
                    f"Downloaded: {len(result.downloaded_products)}, "
                    f"Found: {result.total_products_found}, "
                    f"Filtered: {result.total_products_filtered}"
                )
                if result.downloaded_products:
                    logging.info(f"Job {job_name} downloaded products: {', '.join(result.downloaded_products)}")
            else:
                logging.error(f"Job {job_name} failed: {result.message}")
            
            if result.errors:
                for error in result.errors:
                    logging.error(f"Job {job_name} error: {error}")
            
        except Exception as e:
            logging.error(f"Job {job_name} execution failed with exception: {e}", exc_info=True)
            raise
    
    def _job_executed_listener(self, event):
        """Listener for successful job executions."""
        logging.info(f"Job {event.job_id} executed successfully")
    
    def _job_error_listener(self, event):
        """Listener for job execution errors."""
        logging.error(f"Job {event.job_id} raised an error: {event.exception}", exc_info=True)
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler is None:
            raise RuntimeError("Jobs not setup. Call setup_jobs() first.")
        
        self.scheduler.start()
        logging.info("Scheduler started")
        
        # Log next run times
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            next_run = job.next_run_time
            logging.info(f"Job '{job.id}' next run: {next_run}")
    
    def stop(self):
        """Stop the scheduler gracefully."""
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=True)
            logging.info("Scheduler stopped")
    
    def run_forever(self):
        """
        Run the scheduler indefinitely (blocking call).
        
        This method blocks until interrupted (Ctrl+C).
        """
        if self.scheduler is None or not self.scheduler.running:
            raise RuntimeError("Scheduler not started. Call start() first.")
        
        try:
            # Keep the main thread alive
            import time
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logging.info("Received shutdown signal")
            self.stop()
    
    def get_status(self) -> dict:
        """
        Get current scheduler status.
        
        Returns:
            Dictionary with status information
        """
        if self.scheduler is None:
            return {
                "running": False,
                "jobs": []
            }
        
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        
        return {
            "running": self.scheduler.running,
            "jobs": jobs_info,
        }
