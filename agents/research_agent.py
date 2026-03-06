from __future__ import annotations
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.base_agent import BaseAgent
from models.research_result import RawArticle, ResearchBundle
from utils.date_utils import format_date_es
from utils.deduplicator import ArticleDeduplicator

MAX_CONCURRENT_QUERIES = 5
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar-pro"
REQUEST_TIMEOUT = 30


class ResearchAgent(BaseAgent):
    """
    Phase 1: News research using Perplexity Sonar API.

    Runs parallel queries per research category. Each Perplexity response includes
    `search_results` (verified source URLs) that become RawArticle objects for downstream
    analysis. Deduplication is cross-day persistent via ArticleDeduplicator.
    """

    def __init__(self, config, cost_tracker=None) -> None:
        super().__init__(config, cost_tracker)
        self.perplexity_api_key = config.perplexity_api_key
        self.deduplicator = ArticleDeduplicator(
            history_file=config.dedup_history_file,
            lookback_days=config.dedup_lookback_days,
        )
        self.state_config = config.state_config
        self.cities = config.state_config.major_cities

    def _execute(self, input_data=None) -> ResearchBundle:
        state_name = self.state_config.state_name
        categories = self.state_config.research_categories
        return self._research_via_perplexity(state_name, categories)

    # -------------------------------------------------------------------------
    # Perplexity Sonar API (parallel queries with verified citations)
    # -------------------------------------------------------------------------

    def _research_via_perplexity(
        self, state_name: str, categories: list[str]
    ) -> ResearchBundle:
        """Runs parallel Perplexity searches, one per research category."""
        today = format_date_es()
        self.logger.info(
            f"Perplexity research: {state_name} ({len(categories)} categories)"
        )

        all_articles: list[RawArticle] = []
        queries = self._build_queries_from_categories(categories, state_name)

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_QUERIES) as executor:
            future_to_query = {
                executor.submit(self._run_single_query, q, cat, today): (q, cat)
                for q, cat in queries
            }
            for future in as_completed(future_to_query):
                q, cat = future_to_query[future]
                try:
                    results = future.result()
                    all_articles.extend(results)
                    self.logger.info(
                        f"Query '{q[:60]}': {len(results)} articles"
                    )
                except Exception as exc:
                    self.logger.warning(f"Query failed '{q[:60]}': {exc}")

        unique_articles = self.deduplicator.deduplicate(all_articles)

        self.logger.info(
            f"Perplexity: {len(all_articles)} raw → {len(unique_articles)} unique articles"
        )

        research_text = self._articles_to_text(unique_articles)

        return ResearchBundle(
            articles=unique_articles,
            total_queries_run=len(queries),
            state=state_name,
            raw_research_text=research_text,
        )

    def _run_single_query(
        self, query: str, category: str, today: str
    ) -> list[RawArticle]:
        """Calls Perplexity API for one query and converts search_results to RawArticles."""
        response = requests.post(
            PERPLEXITY_API_URL,
            headers={"Authorization": f"Bearer {self.perplexity_api_key}"},
            json={
                "model": PERPLEXITY_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{query} (today: {today})",
                    }
                ],
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        answer_text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        if self.cost_tracker and usage:
            self.cost_tracker.record_perplexity(
                PERPLEXITY_MODEL,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            )
        # Perplexity returns search_results with title, url, date, snippet
        search_results: list[dict] = data.get("search_results", [])

        articles: list[RawArticle] = []
        for result in search_results:
            url = result.get("url", "")
            if not url:
                continue
            articles.append(
                RawArticle(
                    title=result.get("title", self._extract_title_from_url(url)),
                    url=url,
                    content=result.get("snippet", answer_text[:600]),
                    published_date=result.get("date", ""),
                    category=category,
                    tavily_answer=answer_text[:300],
                    source="perplexity",
                )
            )

        return articles

    # -------------------------------------------------------------------------
    # Query builder — all references use state_name (no hardcoded state names)
    # -------------------------------------------------------------------------

    def _build_queries_from_categories(
        self, categories: list[str], state_name: str
    ) -> list[tuple[str, str]]:
        """
        Builds English search queries from the Spanish category descriptions.
        Returns list of (query, category) tuples — 2 queries per category.

        City names are checked FIRST (highest priority) to prevent false matches
        against generic keys like "inventario" that appear in city category names.
        """
        # City queries — checked before general keys to avoid false matches
        city_query_map: dict[str, list[str]] = {
            city: [
                f"{city} {state_name} real estate market 2026 prices inventory trends",
                f"{city} housing market median price days on market 2026",
            ]
            for city in self.cities
        }

        # General thematic query map — only checked if no city matched
        general_query_map: dict[str, list[str]] = {
            "Tasas hipotecarias": [
                f"{state_name} mortgage rates today 2026 30-year fixed",
                f"Fed interest rate decision housing market {state_name} 2026",
            ],
            "Legislación": [
                f"{state_name} real estate legislation new laws 2026",
                f"{state_name} HOA insurance property tax changes 2026",
            ],
            "latinoamericana": [
                f"Latin American buyers {state_name} real estate 2026",
                f"international investors {state_name} real estate Colombia Venezuela Brazil 2026",
            ],
            "lujo": [
                f"{state_name} luxury real estate $5M+ market 2026",
                f"{state_name} ultra-luxury properties sales records 2026",
            ],
            "construcción": [
                f"{state_name} new construction housing starts 2026",
                f"{state_name} new development pre-construction 2026",
            ],
            "inventario": [
                f"{state_name} housing inventory levels prices 2026",
                f"{state_name} median home prices days on market statistics 2026",
            ],
            "económicas": [
                f"{state_name} economy housing market outlook 2026",
                f"{state_name} real estate investment trends 2026",
            ],
            "Bitcoin": [
                f"Bitcoin crypto buyers real estate {state_name} 2026",
                f"cryptocurrency payment real estate property {state_name} BTC 2026",
            ],
            "criptomonedas": [
                f"crypto investors buying real estate {state_name} 2026",
                f"Bitcoin real estate tokenization investment {state_name} 2026",
            ],
        }

        queries: list[tuple[str, str]] = []
        for category in categories:
            # 1. City check first — avoids "inventario" false-matching city categories
            city_matched = False
            for city, city_queries in city_query_map.items():
                if city.lower() in category.lower():
                    for q in city_queries:
                        queries.append((q, category))
                    city_matched = True
                    break
            if city_matched:
                continue

            # 2. General thematic keys
            matched = False
            for key, cat_queries in general_query_map.items():
                if key.lower() in category.lower():
                    for q in cat_queries:
                        queries.append((q, category))
                    matched = True
                    break

            if not matched:
                queries.append((
                    f"{state_name} real estate {category[:50]} 2026",
                    category,
                ))

        return queries

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _extract_title_from_url(self, url: str) -> str:
        """Derives a readable title from a URL path (best effort)."""
        try:
            path = url.split("://", 1)[1] if "://" in url else url
            parts = path.split("/", 1)
            slug = parts[1] if len(parts) > 1 else parts[0]
            slug = slug.split("?")[0].split("#")[0].rstrip("/")
            segment = slug.rsplit("/", 1)[-1] if "/" in slug else slug
            title = re.sub(r"[-_]", " ", segment).strip()
            return title[:120] if title else url[:120]
        except Exception:
            return url[:120]

    def _articles_to_text(self, articles: list[RawArticle]) -> str:
        """Converts a list of RawArticles to a text summary for the analysis prompt."""
        lines = []
        for i, a in enumerate(articles, 1):
            lines.append(
                f"[{i}] CATEGORÍA: {a.category}\n"
                f"    TÍTULO: {a.title}\n"
                f"    URL: {a.url}\n"
                f"    FECHA: {a.published_date or 'N/D'}\n"
                f"    PERPLEXITY SUMMARY: {a.tavily_answer[:200] if a.tavily_answer else 'N/D'}\n"
                f"    CONTENIDO: {a.content[:400]}...\n"
            )
        return "\n".join(lines)
