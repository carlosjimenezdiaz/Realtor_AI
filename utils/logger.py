from __future__ import annotations
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Outputs logs as JSON lines for structured monitoring."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger with console (readable) and file (JSON) handlers."""
    Path("logs").mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    root.handlers.clear()

    # Console — human readable
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(console)

    # File — JSON for structured log analysis
    today = datetime.now().strftime("%Y%m%d")
    file_handler = logging.FileHandler(f"logs/pipeline_{today}.log", encoding="utf-8")
    file_handler.setFormatter(JSONFormatter())
    root.addHandler(file_handler)
