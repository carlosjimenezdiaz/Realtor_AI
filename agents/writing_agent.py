from __future__ import annotations
import json
from datetime import date

from agents.base_agent import BaseAgent
from models.analysis_result import AnalysisBundle
from models.report import FinalReport, ReportSection
from prompts.writing_prompts import build_writing_system_prompt, build_writing_user_prompt
from utils.date_utils import format_date_es
from utils.llm_client import make_client, model_id
from utils.section_parser import parse_sections


class WritingAgent(BaseAgent):
    """
    Phase 3: Writes the full Spanish newsletter from the analysis bundle via OpenRouter.
    """

    def __init__(self, config, cost_tracker=None) -> None:
        super().__init__(config, cost_tracker)
        self.client = make_client(config.openrouter_api_key)
        self.model = model_id(config.claude_model)
        self.state_config = config.state_config
        self.max_tokens = config.claude_max_tokens

    def _execute(self, input_data: AnalysisBundle) -> FinalReport:
        analysis_bundle = input_data
        analysis_json = self._bundle_to_json(analysis_bundle)
        formatted_date = format_date_es()

        user_prompt = build_writing_user_prompt(
            analysis_json=analysis_json,
            newsletter_name=self.state_config.newsletter_name,
            newsletter_tagline=self.state_config.newsletter_tagline,
            formatted_date=formatted_date,
            state_name=self.state_config.state_name,
            cities=self.state_config.major_cities,
        )

        self.logger.info(
            f"Writing newsletter with {len(analysis_bundle.selected_articles)} stories"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.7,
            messages=[
                {"role": "system", "content": build_writing_system_prompt(self.state_config.major_cities)},
                {"role": "user", "content": user_prompt},
            ],
        )

        if self.cost_tracker:
            self.cost_tracker.record_claude(
                "writing_agent", self.model,
                response.usage.prompt_tokens, response.usage.completion_tokens,
            )
        raw_text = response.choices[0].message.content
        self.logger.info(f"Writing response: {len(raw_text)} chars")

        return self._build_report(raw_text, analysis_bundle.state)

    def _bundle_to_json(self, bundle: AnalysisBundle) -> str:
        articles = [
            {
                "title": a.title, "url": a.url, "category": a.category,
                "content_summary": a.content_summary,
                "why_important_for_agents": a.why_important_for_agents,
                "key_data_points": a.key_data_points,
            }
            for a in bundle.selected_articles
        ]
        market = {
            "mortgage_rate_30yr": bundle.market_data.mortgage_rate_30yr,
            "mortgage_rate_15yr": bundle.market_data.mortgage_rate_15yr,
            "mortgage_rate_fha": bundle.market_data.mortgage_rate_fha,
            "mortgage_rate_jumbo": bundle.market_data.mortgage_rate_jumbo,
            "inventory_sfh": bundle.market_data.inventory_sfh,
            "inventory_condos": bundle.market_data.inventory_condos,
            "median_price_sfh": bundle.market_data.median_price_sfh,
            "median_days_on_market": bundle.market_data.median_days_on_market,
            "inventory_yoy_change": bundle.market_data.inventory_yoy_change,
            "city_medians": bundle.market_data.city_medians,
        }
        return json.dumps({"articles": articles, "market_data": market}, ensure_ascii=False, indent=2)

    def _build_report(self, raw_text: str, state: str) -> FinalReport:
        sections = dict(parse_sections(raw_text))
        self.logger.info(f"Parsed sections: {list(sections.keys())}")

        story_sections = [
            ReportSection(title=name, emoji="📰", content=content)
            for name, content in sections.items()
            if name.startswith("HISTORIA")
        ]

        def section(name: str, emoji: str = "") -> ReportSection:
            content = sections.get(name, f"[Sección {name} no generada]")
            return ReportSection(title=name, emoji=emoji, content=content)

        return FinalReport(
            header=section("HEADER", "🏡"),
            executive_summary=section("RESUMEN EJECUTIVO", "🎯"),
            main_stories=story_sections,
            market_data=section("MERCADO", "📊"),
            latin_investment=section("INVERSION_LATINA", "🌎"),
            agent_strategies=section("ESTRATEGIAS", "🎯"),
            on_the_radar=section("RADAR", "🔮"),
            btc_crypto=section("BTC_CRIPTO", "₿"),
            footer=section("FOOTER"),
            report_date=date.today(),
            state=state,
        )
