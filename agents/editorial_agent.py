from __future__ import annotations

from agents.base_agent import BaseAgent
from models.report import FinalReport
from prompts.editorial_prompts import EDITORIAL_SYSTEM_PROMPT, EDITORIAL_USER_PROMPT_TEMPLATE
from utils.llm_client import make_client, model_id
from utils.section_parser import parse_sections
from utils.text_splitter import split_for_telegram


class EditorialAgent(BaseAgent):
    """
    Phase 4: Quality review and Telegram formatting via OpenRouter.
    """

    def __init__(self, config, cost_tracker=None) -> None:
        super().__init__(config, cost_tracker)
        self.client = make_client(config.openrouter_api_key)
        self.model = model_id(config.claude_model)
        self.max_tokens = config.claude_max_tokens

    def _execute(self, input_data: FinalReport) -> list[str]:
        report = input_data
        full_text = self._report_to_text(report)

        self.logger.info(
            f"Editorial review: {len(full_text)} chars, {len(report.main_stories)} stories"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.1,
            messages=[
                {"role": "system", "content": EDITORIAL_SYSTEM_PROMPT},
                {"role": "user", "content": EDITORIAL_USER_PROMPT_TEMPLATE.format(report_text=full_text)},
            ],
        )

        if self.cost_tracker:
            self.cost_tracker.record_claude(
                "editorial_agent", self.model,
                response.usage.prompt_tokens, response.usage.completion_tokens,
            )
        reviewed_text = response.choices[0].message.content
        self.logger.info(f"Editorial response: {len(reviewed_text)} chars")

        messages = self._build_messages(reviewed_text)
        self.logger.info(f"Editorial complete: {len(messages)} Telegram messages")
        return messages

    def _report_to_text(self, report: FinalReport) -> str:
        parts = []
        for section in report.all_sections():
            parts.append(f"---SECCIÓN: {section.title}---")
            parts.append(section.content)
        return "\n\n".join(parts)

    def _build_messages(self, reviewed_text: str) -> list[str]:
        messages: list[str] = []
        for _name, content in parse_sections(reviewed_text):
            if content:
                messages.extend(split_for_telegram(content))
        return [m for m in messages if m.strip()]
