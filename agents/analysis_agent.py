from __future__ import annotations
import json
import re

from agents.base_agent import BaseAgent
from models.analysis_result import AnalysisBundle, MarketData, ScoredArticle
from models.research_result import ResearchBundle
from models.scraped_data import ScrapedDataBundle
from prompts.analysis_prompts import build_analysis_system_prompt, build_analysis_user_prompt
from utils.llm_client import make_client, model_id

MAX_ARTICLES_FOR_ANALYSIS = 40
ANALYSIS_MAX_TOKENS = 8192


class AnalysisAgent(BaseAgent):
    """
    Phase 2: Combines Firecrawl data + Perplexity articles and selects the best content.
    Uses OpenRouter (OpenAI-compatible API) to call Claude.
    """

    def __init__(self, config, cost_tracker=None) -> None:
        super().__init__(config, cost_tracker)
        self.client = make_client(config.openrouter_api_key)
        self.model = model_id(config.claude_model)
        self.state_config = config.state_config

    def _execute(
        self,
        input_data: tuple[ResearchBundle, ScrapedDataBundle],
    ) -> AnalysisBundle:
        research_bundle, scraped_bundle = input_data
        state_name = self.state_config.state_name
        cities = self.state_config.major_cities

        top_articles = research_bundle.articles[:MAX_ARTICLES_FOR_ANALYSIS]
        research_text = research_bundle.to_prompt_context()
        scraped_context = scraped_bundle.get_combined_context()

        user_prompt = build_analysis_user_prompt(
            research_text=research_text,
            scraped_context=scraped_context,
            state_name=state_name,
            cities=cities,
        )

        self.logger.info(
            f"Analyzing {len(top_articles)} articles "
            f"+ {scraped_bundle.successful_count} scraped pages"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=ANALYSIS_MAX_TOKENS,
            temperature=0.2,
            messages=[
                {"role": "system", "content": build_analysis_system_prompt(state_name)},
                {"role": "user", "content": user_prompt},
            ],
        )

        if self.cost_tracker:
            self.cost_tracker.record_claude(
                "analysis_agent", self.model,
                response.usage.prompt_tokens, response.usage.completion_tokens,
            )
        raw_text = response.choices[0].message.content.strip()
        return self._parse_response(raw_text, state_name)

    def _parse_response(self, raw_text: str, state_name: str) -> AnalysisBundle:
        clean = re.sub(r"^```(?:json)?\n?", "", raw_text.strip())
        clean = re.sub(r"\n?```$", "", clean.strip())

        try:
            data = json.loads(clean)
            return self._build_bundle(data, state_name)
        except json.JSONDecodeError:
            pass

        self.logger.warning("JSON truncated — attempting repair extraction")
        return self._repair_and_parse(clean, state_name)

    def _repair_and_parse(self, raw: str, state_name: str) -> AnalysisBundle:
        articles: list[ScoredArticle] = []

        article_pattern = re.compile(
            r'\{\s*"title":\s*"([^"]+)".*?"url":\s*"([^"]+)".*?"category":\s*"([^"]+)"'
            r'.*?"score_total":\s*(\d+).*?"content_summary":\s*"([^"]*)"'
            r'.*?"why_important_for_agents":\s*"([^"]*)"',
            re.DOTALL,
        )
        for m in article_pattern.finditer(raw):
            articles.append(ScoredArticle(
                title=m.group(1), url=m.group(2), category=m.group(3),
                score_total=int(m.group(4)), content_summary=m.group(5),
                why_important_for_agents=m.group(6),
            ))

        def extract_field(field: str) -> str:
            m = re.search(rf'"{field}":\s*"([^"]+)"', raw)
            return m.group(1) if m else "N/D"

        city_medians: dict[str, str] = {}
        cm_match = re.search(r'"city_medians"\s*:\s*\{([^}]+)\}', raw, re.DOTALL)
        if cm_match:
            for pair in re.finditer(r'"([^"]+)":\s*"([^"]+)"', cm_match.group(1)):
                city_medians[pair.group(1)] = pair.group(2)

        market_data = MarketData(
            mortgage_rate_30yr=extract_field("mortgage_rate_30yr"),
            mortgage_rate_15yr=extract_field("mortgage_rate_15yr"),
            mortgage_rate_fha=extract_field("mortgage_rate_fha"),
            mortgage_rate_jumbo=extract_field("mortgage_rate_jumbo"),
            inventory_sfh=extract_field("inventory_sfh"),
            inventory_condos=extract_field("inventory_condos"),
            median_price_sfh=extract_field("median_price_sfh"),
            median_days_on_market=extract_field("median_days_on_market"),
            inventory_yoy_change=extract_field("inventory_yoy_change"),
            city_medians=city_medians,
        )

        if not articles:
            raise ValueError("Analysis agent returned JSON that could not be repaired.")

        self.logger.info(f"Repair extracted {len(articles)} articles")
        return AnalysisBundle(selected_articles=articles, market_data=market_data, state=state_name)

    def _build_bundle(self, data: dict, state_name: str) -> AnalysisBundle:
        articles = [
            ScoredArticle(
                title=a.get("title", ""), url=a.get("url", ""),
                category=a.get("category", "General"),
                score_total=a.get("score_total", 0),
                content_summary=a.get("content_summary", ""),
                why_important_for_agents=a.get("why_important_for_agents", ""),
                key_data_points=a.get("key_data_points", []),
                scores=a.get("scores", {}),
            )
            for a in data.get("selected_articles", [])
        ]
        md_raw = data.get("market_data", {})
        market_data = MarketData(
            mortgage_rate_30yr=md_raw.get("mortgage_rate_30yr", "N/D"),
            mortgage_rate_15yr=md_raw.get("mortgage_rate_15yr", "N/D"),
            mortgage_rate_fha=md_raw.get("mortgage_rate_fha", "N/D"),
            mortgage_rate_jumbo=md_raw.get("mortgage_rate_jumbo", "N/D"),
            inventory_sfh=md_raw.get("inventory_sfh", "N/D"),
            inventory_condos=md_raw.get("inventory_condos", "N/D"),
            median_price_sfh=md_raw.get("median_price_sfh", "N/D"),
            median_days_on_market=md_raw.get("median_days_on_market", "N/D"),
            inventory_yoy_change=md_raw.get("inventory_yoy_change", "N/D"),
            city_medians=md_raw.get("city_medians", {}),
        )
        self.logger.info(
            f"Analysis complete: {len(articles)} articles, "
            f"30yr rate: {market_data.mortgage_rate_30yr}"
        )
        return AnalysisBundle(
            selected_articles=articles, market_data=market_data,
            coverage_gaps=data.get("coverage_gaps", []), state=state_name,
        )
