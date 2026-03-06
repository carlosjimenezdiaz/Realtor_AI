from __future__ import annotations
import json
import re
import anthropic

from agents.base_agent import BaseAgent
from models.analysis_result import AnalysisBundle, MarketData, ScoredArticle
from models.research_result import ResearchBundle
from models.scraped_data import ScrapedDataBundle
from prompts.analysis_prompts import ANALYSIS_SYSTEM_PROMPT, build_analysis_user_prompt

MAX_ARTICLES_FOR_ANALYSIS = 40  # Cap to stay within token budget
ANALYSIS_MAX_TOKENS = 8192


class AnalysisAgent(BaseAgent):
    """
    Phase 2: Combines Firecrawl data + Tavily articles and selects the best content.

    Claude scores each article on 5 criteria and extracts key market data numbers
    from both scraped pages (structured data) and news articles (narrative data).
    Output is a clean AnalysisBundle ready for the writing agent.
    """

    def __init__(self, config, cost_tracker=None) -> None:
        super().__init__(config, cost_tracker)
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.model = config.claude_model
        self.state_config = config.state_config

    def _execute(
        self,
        input_data: tuple[ResearchBundle, ScrapedDataBundle],
    ) -> AnalysisBundle:
        research_bundle, scraped_bundle = input_data
        state_name = self.state_config.state_name

        # Cap articles to avoid exceeding token budget
        top_articles = sorted(
            research_bundle.articles, key=lambda a: a.score, reverse=True
        )[:MAX_ARTICLES_FOR_ANALYSIS]

        # Build a trimmed text context from top articles
        research_text = self._articles_to_prompt_text(top_articles)
        # Also include the raw research text if articles are few
        if len(top_articles) < 20 and research_bundle.raw_research_text:
            research_text = research_bundle.raw_research_text[:15000]

        scraped_context = scraped_bundle.get_combined_context()

        user_prompt = build_analysis_user_prompt(
            research_text=research_text,
            scraped_context=scraped_context,
            state_name=state_name,
            cities=self.state_config.major_cities,
        )

        self.logger.info(
            f"Analyzing {len(top_articles)} articles (of {len(research_bundle.articles)}) "
            f"+ {scraped_bundle.successful_count} scraped pages"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=ANALYSIS_MAX_TOKENS,
            temperature=0.2,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        if self.cost_tracker:
            self.cost_tracker.record_claude(
                "analysis_agent", self.model,
                response.usage.input_tokens, response.usage.output_tokens,
            )
        raw_text = response.content[0].text.strip()
        return self._parse_response(raw_text, state_name)

    def _articles_to_prompt_text(self, articles) -> str:
        """Converts top articles to a compact text for the analysis prompt."""
        lines = []
        for i, a in enumerate(articles, 1):
            lines.append(
                f"[{i}] {a.category} | {a.title}\n"
                f"    URL: {a.url}\n"
                f"    FECHA: {a.published_date or 'N/D'}\n"
                f"    CONTENIDO: {a.content[:300]}...\n"
            )
        return "\n".join(lines)

    def _parse_response(self, raw_text: str, state_name: str) -> AnalysisBundle:
        """Parses Claude's JSON response into an AnalysisBundle with repair fallback."""
        # Strip markdown code fences
        clean = re.sub(r"^```(?:json)?\n?", "", raw_text.strip())
        clean = re.sub(r"\n?```$", "", clean.strip())

        # Try direct parse
        try:
            data = json.loads(clean)
            return self._build_bundle(data, state_name)
        except json.JSONDecodeError:
            pass

        # Repair: try to extract what was successfully parsed before truncation
        self.logger.warning("JSON truncated — attempting repair extraction")
        return self._repair_and_parse(clean, state_name)

    def _repair_and_parse(self, raw: str, state_name: str) -> AnalysisBundle:
        """
        Extracts partial JSON data when the response was truncated.
        Salvages whatever articles were fully parsed before the cutoff.
        """
        articles: list[ScoredArticle] = []

        # Extract individual article objects using regex
        article_pattern = re.compile(
            r'\{\s*"title":\s*"([^"]+)".*?"url":\s*"([^"]+)".*?"category":\s*"([^"]+)"'
            r'.*?"score_total":\s*(\d+).*?"content_summary":\s*"([^"]*)"'
            r'.*?"why_important_for_agents":\s*"([^"]*)"',
            re.DOTALL,
        )

        for m in article_pattern.finditer(raw):
            articles.append(
                ScoredArticle(
                    title=m.group(1),
                    url=m.group(2),
                    category=m.group(3),
                    score_total=int(m.group(4)),
                    content_summary=m.group(5),
                    why_important_for_agents=m.group(6),
                )
            )

        # Extract market data
        def extract_field(field: str) -> str:
            m = re.search(rf'"{field}":\s*"([^"]+)"', raw)
            return m.group(1) if m else "N/D"

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
            miami_median=extract_field("miami_median"),
            orlando_median=extract_field("orlando_median"),
            tampa_median=extract_field("tampa_median"),
            jacksonville_median=extract_field("jacksonville_median"),
            fort_lauderdale_median=extract_field("fort_lauderdale_median"),
        )

        if not articles:
            raise ValueError(
                "Analysis agent returned JSON that could not be repaired. "
                "No articles extracted."
            )

        self.logger.info(
            f"Repair extracted {len(articles)} articles, "
            f"30yr rate: {market_data.mortgage_rate_30yr}"
        )

        return AnalysisBundle(
            selected_articles=articles,
            market_data=market_data,
            coverage_gaps=[],
            state=state_name,
        )

    def _build_bundle(self, data: dict, state_name: str) -> AnalysisBundle:
        """Builds AnalysisBundle from successfully parsed JSON dict."""
        articles = [
            ScoredArticle(
                title=a.get("title", ""),
                url=a.get("url", ""),
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
            miami_median=md_raw.get("miami_median", "N/D"),
            orlando_median=md_raw.get("orlando_median", "N/D"),
            tampa_median=md_raw.get("tampa_median", "N/D"),
            jacksonville_median=md_raw.get("jacksonville_median", "N/D"),
            fort_lauderdale_median=md_raw.get("fort_lauderdale_median", "N/D"),
        )

        self.logger.info(
            f"Analysis complete: {len(articles)} articles selected, "
            f"30yr rate: {market_data.mortgage_rate_30yr}"
        )

        return AnalysisBundle(
            selected_articles=articles,
            market_data=market_data,
            coverage_gaps=data.get("coverage_gaps", []),
            state=state_name,
        )
