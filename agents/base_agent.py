from __future__ import annotations
import logging
import time
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds; multiplied by attempt number (linear backoff)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Abstract base for all pipeline agents.

    Subclasses implement _execute(). The public run() method adds:
    - Retry logic with linear backoff
    - Timing and structured logging
    - Consistent error propagation
    """

    def __init__(self, config) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def _execute(self, input_data: InputT) -> OutputT:
        """Core agent logic. Must be implemented by each subclass."""

    def run(self, input_data: InputT) -> OutputT:
        """Public entry point with retry logic."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self.logger.info(f"Starting (attempt {attempt}/{MAX_RETRIES})")
                start = time.monotonic()
                result = self._execute(input_data)
                elapsed = time.monotonic() - start
                self.logger.info(f"Completed in {elapsed:.2f}s")
                return result
            except Exception as exc:
                self.logger.warning(f"Attempt {attempt} failed: {exc}")
                if attempt == MAX_RETRIES:
                    self.logger.error(f"All {MAX_RETRIES} attempts failed. Raising.")
                    raise
                sleep_time = RETRY_BASE_DELAY * attempt
                self.logger.info(f"Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
