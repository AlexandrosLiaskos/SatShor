"""
Daemon script for running the satellite image collection scheduler.

This script provides a command-line interface for running the scheduler
as a long-running service, with support for daemon mode and process management.
"""

import argparse
import logging
import sys
import signal
import os
from pathlib import Path

from scheduler import ScheduledCollector
from config_schema import load_config


def setup_signal_handlers(collector: ScheduledCollector):
    """
    Setup signal handlers for graceful shutdown.
    
    Args:
        collector: ScheduledCollector instance
    """
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        collector.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def validate_startup(config_path: str) -> bool:
    """
    Validate startup conditions before running scheduler.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        True if validation passes, False otherwise
    """
    from dotenv import load_dotenv
    from rich.console import Console
    
    console = Console()
    
    # Check .env file exists
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        console.print(f"[red]Error: .env file not found at {env_path}[/red]")
        console.print("Please create a .env file with CDSE credentials")
        return False
    
    # Load and check credentials
    load_dotenv()
    has_token = os.getenv("CDSE_ACCESS_TOKEN") is not None
    has_credentials = (
        os.getenv("CDSE_USERNAME") is not None and 
        os.getenv("CDSE_PASSWORD") is not None
    )
    
    if not (has_token or has_credentials):
        console.print("[red]Error: CDSE credentials not found in .env file[/red]")
        console.print("Please set either:")
        console.print("  - CDSE_ACCESS_TOKEN, or")
        console.print("  - CDSE_USERNAME and CDSE_PASSWORD")
        return False
    
    # Validate configuration
    try:
        config = load_config(config_path)
        console.print(f"[green]Configuration validated: {len(config.jobs)} jobs configured[/green]")
        
        # Display job summary
        console.print("\n[bold cyan]Configured Jobs:[/bold cyan]")
        for job in config.jobs:
            status = "[green]enabled[/green]" if job.enabled else "[dim]disabled[/dim]"
            console.print(f"  • {job.name} ({job.schedule.type}) - {status}")
        
        # Check AOI files
        console.print("\n[bold cyan]Validating AOI files:[/bold cyan]")
        all_aois_exist = True
        for job in config.jobs:
            aoi_path = Path(job.aoi_path).expanduser()
            if aoi_path.exists():
                console.print(f"  ✓ {job.name}: {job.aoi_path}")
            else:
                console.print(f"  [red]✗ {job.name}: {job.aoi_path} (NOT FOUND)[/red]")
                all_aois_exist = False
        
        if not all_aois_exist:
            console.print("[red]Some AOI files are missing. Please check the configuration.[/red]")
            return False
        
        # Test API connectivity
        console.print("\n[bold cyan]Testing CDSE API connectivity:[/bold cyan]")
        try:
            from collector import get_access_token
            token = get_access_token()
            console.print("  ✓ Successfully obtained access token")
        except Exception as e:
            console.print(f"  [red]✗ Failed to obtain access token: {e}[/red]")
            return False
        
        console.print("\n[green]All startup validations passed![/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]Configuration validation failed: {e}[/red]")
        logging.error(f"Configuration validation error: {e}", exc_info=True)
        return False


def display_schedule_info(collector: ScheduledCollector):
    """
    Display information about scheduled jobs.
    
    Args:
        collector: ScheduledCollector instance
    """
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    status = collector.get_status()
    
    if not status["jobs"]:
        console.print("[yellow]No jobs scheduled[/yellow]")
        return
    
    table = Table(title="Scheduled Jobs", show_header=True)
    table.add_column("Job Name", style="cyan")
    table.add_column("Next Run", style="green")
    
    for job_info in status["jobs"]:
        next_run = job_info["next_run_time"]
        if next_run:
            # Parse and format datetime
            from datetime import datetime
            next_run_dt = datetime.fromisoformat(next_run)
            next_run_str = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            next_run_str = "Not scheduled"
        
        table.add_row(job_info["name"], next_run_str)
    
    console.print(table)


def write_pid_file(pid_file: str):
    """
    Write process ID to file.
    
    Args:
        pid_file: Path to PID file
    """
    pid = os.getpid()
    with open(pid_file, 'w') as f:
        f.write(str(pid))
    logging.info(f"PID {pid} written to {pid_file}")


def remove_pid_file(pid_file: str):
    """
    Remove PID file.
    
    Args:
        pid_file: Path to PID file
    """
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
            logging.info(f"Removed PID file {pid_file}")
    except Exception as e:
        logging.warning(f"Failed to remove PID file {pid_file}: {e}")


def main():
    """Main entry point for the scheduler daemon."""
    parser = argparse.ArgumentParser(
        description="Satellite Image Collection Scheduler Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run scheduler in foreground
  python scheduler_daemon.py --config config.yaml
  
  # Run with debug logging
  python scheduler_daemon.py --config config.yaml --log-level DEBUG
  
  # Run as daemon with PID file (Unix-like systems)
  python scheduler_daemon.py --config config.yaml --daemon --pid-file /var/run/satshor.pid
        """
    )
    
    parser.add_argument(
        "--config",
        required=True,
        help="Path to scheduler configuration YAML file"
    )
    
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon (detach from terminal, Unix-like systems only)"
    )
    
    parser.add_argument(
        "--pid-file",
        help="Path to PID file for daemon management"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging level
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Validate startup conditions
    if not validate_startup(args.config):
        sys.exit(1)
    
    if args.validate_only:
        print("Configuration validation successful. Exiting.")
        sys.exit(0)
    
    # Daemon mode (Unix-like systems only)
    if args.daemon:
        if sys.platform == "win32":
            print("Error: Daemon mode is not supported on Windows.")
            print("Please use Windows services or Task Scheduler instead.")
            sys.exit(1)
        
        try:
            import daemon
            import daemon.pidfile
            
            # Setup daemon context
            pid_file = args.pid_file if args.pid_file else "/tmp/satshor_scheduler.pid"
            
            with daemon.DaemonContext(
                working_directory=str(Path(__file__).parent),
                pidfile=daemon.pidfile.PIDLockFile(pid_file),
            ):
                run_scheduler(args.config, args.pid_file)
        except ImportError:
            print("Error: python-daemon library not installed.")
            print("Install with: pip install python-daemon")
            sys.exit(1)
    else:
        # Run in foreground
        run_scheduler(args.config, args.pid_file)


def run_scheduler(config_path: str, pid_file: str = None):
    """
    Run the scheduler.
    
    Args:
        config_path: Path to configuration file
        pid_file: Optional path to PID file
    """
    from rich.console import Console
    
    console = Console()
    
    try:
        # Write PID file if specified
        if pid_file:
            write_pid_file(pid_file)
        
        # Create and setup scheduler
        console.print("[cyan]Initializing scheduler...[/cyan]")
        collector = ScheduledCollector(config_path)
        collector.setup_jobs()
        
        # Setup signal handlers
        setup_signal_handlers(collector)
        
        # Start scheduler
        console.print("[green]Starting scheduler...[/green]")
        collector.start()
        
        # Display schedule info
        console.print()
        display_schedule_info(collector)
        console.print()
        console.print("[bold green]Scheduler is running. Press Ctrl+C to stop.[/bold green]")
        
        # Run forever (blocking)
        collector.run_forever()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Received interrupt signal, shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[red]Scheduler failed: {e}[/red]")
        logging.error(f"Scheduler error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up PID file
        if pid_file:
            remove_pid_file(pid_file)


if __name__ == "__main__":
    main()
