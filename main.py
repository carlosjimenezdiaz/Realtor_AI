"""
main.py — Single-execution entry point for the Florida Realty Intel pipeline.

Usage:
    python main.py              # Full run → sends to Telegram
    python main.py --dry-run    # Full run → prints to console, no Telegram
"""

import argparse
import sys

from config.settings import load_config
from pipeline.orchestrator import Orchestrator
from utils.logger import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Florida Realty Intel — Daily Real Estate Intelligence Report"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full pipeline but print output to console instead of sending to Telegram",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load config first to get log level
    try:
        config = load_config()
    except EnvironmentError as exc:
        # Can't set up proper logging yet — print to stderr
        print(f"[ERROR] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    setup_logging(config.log_level)

    import logging
    logger = logging.getLogger("main")

    if args.dry_run:
        logger.info("Starting pipeline in DRY-RUN mode (no Telegram delivery)")
    else:
        logger.info("Starting pipeline in PRODUCTION mode")

    try:
        orchestrator = Orchestrator(config, dry_run=args.dry_run)
        result = orchestrator.run()

        logger.info(f"Pipeline finished successfully: {result}")
        sys.exit(0)

    except Exception as exc:
        logger.exception(f"Pipeline failed with unhandled exception: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
