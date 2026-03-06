"""
scheduler.py — APScheduler daemon for daily pipeline execution.

Runs the pipeline at the configured time (default: 8:00 AM ET, Mon-Fri).
Handles graceful shutdown on SIGTERM/SIGINT.

Usage:
    python scheduler.py          # Start the scheduler daemon
"""

import logging
import signal
import sys

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import load_config
from pipeline.orchestrator import Orchestrator
from utils.logger import setup_logging


def run_pipeline() -> None:
    """Called by APScheduler at the scheduled time."""
    logger = logging.getLogger("scheduler.job")
    try:
        logger.info("Scheduled pipeline starting...")
        config = load_config()
        orchestrator = Orchestrator(config, dry_run=False)
        result = orchestrator.run()
        logger.info(f"Scheduled pipeline completed: {result}")
    except Exception as exc:
        logger.exception(f"Scheduled pipeline failed: {exc}")
        # Intentionally do not re-raise — APScheduler will continue running
        # and the next scheduled execution will attempt again


def main() -> None:
    # Load config to validate env and get schedule settings
    try:
        config = load_config()
    except EnvironmentError as exc:
        print(f"[ERROR] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    setup_logging(config.log_level)
    logger = logging.getLogger("scheduler")

    tz = pytz.timezone(config.timezone)

    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(
            day_of_week="mon-fri",         # Monday to Friday only
            hour=config.report_hour,
            minute=config.report_minute,
            timezone=tz,
        ),
        id="daily_realty_report",
        name=f"{config.state_config.newsletter_name} Daily Report",
        misfire_grace_time=300,            # 5-minute tolerance for missed fires
        coalesce=True,                     # If multiple missed fires, run only once
    )

    def shutdown(signum, frame):
        logger.info(f"Signal {signum} received. Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info(
        f"Scheduler started for {config.state_config.newsletter_name}\n"
        f"  Schedule: Mon-Fri at {config.report_hour:02d}:{config.report_minute:02d} "
        f"{config.timezone}\n"
        f"  Waiting for next scheduled run..."
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
