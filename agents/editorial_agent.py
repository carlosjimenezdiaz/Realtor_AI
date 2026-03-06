from __future__ import annotations
import anthropic

from agents.base_agent import BaseAgent
from models.report import FinalReport, ReportSection
from prompts.editorial_prompts import EDITORIAL_SYSTEM_PROMPT, EDITORIAL_USER_PROMPT_TEMPLATE
from utils.text_splitter import split_for_telegram, MAX_CHARS

SECTION_MARKER = "---SECCIÓN:"
SECTION_END = "---"


class EditorialAgent(BaseAgent):
    """
    Phase 4: Quality review and Telegram formatting.

    Claude verifies Spanish grammar, correct HTML tags, and section lengths.
    Any section exceeding MAX_CHARS is automatically split.
    Returns a list of ready-to-send Telegram message strings.
    """

    def __init__(self, config, cost_tracker=None) -> None:
        super().__init__(config, cost_tracker)
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.model = config.claude_model

    def _execute(self, input_data: FinalReport) -> list[str]:
        report = input_data

        # Serialize the full report into a single text for review
        full_text = self._report_to_text(report)

        user_prompt = EDITORIAL_USER_PROMPT_TEMPLATE.format(report_text=full_text)

        self.logger.info(
            f"Editorial review: {len(full_text)} chars, "
            f"{len(report.main_stories)} stories"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.config.claude_max_tokens,
            temperature=0.1,
            system=EDITORIAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        if self.cost_tracker:
            self.cost_tracker.record_claude(
                "editorial_agent", self.model,
                response.usage.input_tokens, response.usage.output_tokens,
            )
        reviewed_text = response.content[0].text
        self.logger.info(f"Editorial response: {len(reviewed_text)} chars")

        # Parse sections from reviewed text and split long ones
        messages = self._sections_to_messages(reviewed_text)
        self.logger.info(f"Editorial complete: {len(messages)} Telegram messages")

        return messages

    def _report_to_text(self, report: FinalReport) -> str:
        """Serializes FinalReport back to marked-section text for editorial review."""
        parts = []
        for section in report.all_sections():
            parts.append(f"---SECCIÓN: {section.title}---")
            parts.append(section.content)
        return "\n\n".join(parts)

    def _sections_to_messages(self, reviewed_text: str) -> list[str]:
        """
        Parses section markers and builds the final list of Telegram messages.
        Each section becomes at least one message; long sections are split.
        """
        messages: list[str] = []
        current_name = None
        current_lines: list[str] = []

        for line in reviewed_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith(SECTION_MARKER):
                if current_name and current_lines:
                    content = "\n".join(current_lines).strip()
                    if content:
                        chunks = split_for_telegram(content)
                        messages.extend(chunks)
                current_name = (
                    stripped
                    .replace(SECTION_MARKER, "")
                    .rstrip(SECTION_END)
                    .strip()
                )
                current_lines = []
            else:
                if current_name:
                    current_lines.append(line)

        # Last section
        if current_name and current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                chunks = split_for_telegram(content)
                messages.extend(chunks)

        # Filter out empty messages
        return [m for m in messages if m.strip()]
