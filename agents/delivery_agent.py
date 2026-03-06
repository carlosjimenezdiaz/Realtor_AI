from __future__ import annotations
import time
import requests

from agents.base_agent import BaseAgent

TELEGRAM_MIN_DELAY = 1.2  # minimum seconds between messages (Telegram rate limit)
MAX_SEND_RETRIES = 3
REQUEST_TIMEOUT = 30      # seconds per HTTP request


class DeliveryAgent(BaseAgent):
    """
    Phase 5: Sends the formatted report to Telegram.

    Strategy:
    - Sends each message section sequentially with rate-limiting
    - Handles 429 (Too Many Requests) using the retry_after value from Telegram
    - Pins the first message (header) in the channel
    - Logs each message ID for auditability
    """

    def __init__(self, config) -> None:
        super().__init__(config)
        self.bot_token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.message_delay = max(TELEGRAM_MIN_DELAY, config.message_delay_seconds)

    def _execute(self, input_data: list[str]) -> dict:
        messages = input_data
        sent_ids: list[int] = []
        failed_count = 0

        self.logger.info(f"Sending {len(messages)} messages to Telegram")

        for idx, text in enumerate(messages, 1):
            self.logger.info(
                f"Message {idx}/{len(messages)} ({len(text)} chars)"
            )
            try:
                message_id = self._send_message(text)
                sent_ids.append(message_id)
            except Exception as exc:
                failed_count += 1
                self.logger.error(f"Failed to send message {idx}: {exc}")

            # Pacing between messages (configurable via MESSAGE_DELAY_SECONDS)
            if idx < len(messages):
                time.sleep(self.message_delay)

        # Pin the header (first message) for quick reference
        if sent_ids:
            try:
                self._pin_message(sent_ids[0])
                self.logger.info(f"Pinned message {sent_ids[0]}")
            except Exception as exc:
                self.logger.warning(f"Could not pin message: {exc}")

        self.logger.info(
            f"Delivery complete: {len(sent_ids)} sent, {failed_count} failed"
        )

        return {
            "sent_count": len(sent_ids),
            "failed_count": failed_count,
            "message_ids": sent_ids,
        }

    def _send_message(self, text: str) -> int:
        """Sends one Telegram message and returns its message_id."""
        for attempt in range(1, MAX_SEND_RETRIES + 1):
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 200:
                return response.json()["result"]["message_id"]

            elif response.status_code == 429:
                retry_after = (
                    response.json()
                    .get("parameters", {})
                    .get("retry_after", 30)
                )
                self.logger.warning(
                    f"Rate limited by Telegram. Sleeping {retry_after}s"
                )
                time.sleep(retry_after)

            else:
                error_desc = response.json().get("description", "Unknown error")
                self.logger.warning(
                    f"Telegram error {response.status_code}: {error_desc} "
                    f"(attempt {attempt}/{MAX_SEND_RETRIES})"
                )
                if attempt < MAX_SEND_RETRIES:
                    time.sleep(2 * attempt)

        raise RuntimeError(
            f"Failed to send message after {MAX_SEND_RETRIES} attempts. "
            f"Last status: {response.status_code}"
        )

    def _pin_message(self, message_id: int) -> None:
        """Pins a message in the chat."""
        requests.post(
            f"{self.base_url}/pinChatMessage",
            json={
                "chat_id": self.chat_id,
                "message_id": message_id,
                "disable_notification": True,
            },
            timeout=REQUEST_TIMEOUT,
        )
