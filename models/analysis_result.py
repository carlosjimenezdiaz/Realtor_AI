from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScoredArticle:
    title: str
    url: str
    category: str
    score_total: int
    content_summary: str
    why_important_for_agents: str
    key_data_points: list[str] = field(default_factory=list)
    scores: dict = field(default_factory=dict)


@dataclass
class MarketData:
    mortgage_rate_30yr: str = "N/D"
    mortgage_rate_15yr: str = "N/D"
    mortgage_rate_fha: str = "N/D"
    mortgage_rate_jumbo: str = "N/D"
    inventory_sfh: str = "N/D"
    inventory_condos: str = "N/D"
    median_price_sfh: str = "N/D"
    median_days_on_market: str = "N/D"
    inventory_yoy_change: str = "N/D"
    # Per-city data
    miami_median: str = "N/D"
    orlando_median: str = "N/D"
    tampa_median: str = "N/D"
    jacksonville_median: str = "N/D"
    fort_lauderdale_median: str = "N/D"


@dataclass
class AnalysisBundle:
    selected_articles: list[ScoredArticle] = field(default_factory=list)
    market_data: MarketData = field(default_factory=MarketData)
    coverage_gaps: list[str] = field(default_factory=list)
    state: str = "Florida"
