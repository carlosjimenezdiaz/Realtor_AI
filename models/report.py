from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class ReportSection:
    title: str
    emoji: str
    content: str           # Final formatted text (HTML for Telegram)

    @property
    def char_count(self) -> int:
        return len(self.content)


@dataclass
class FinalReport:
    header: ReportSection
    executive_summary: ReportSection
    main_stories: list[ReportSection]
    market_data: ReportSection
    latin_investment: ReportSection
    agent_strategies: ReportSection
    on_the_radar: ReportSection
    btc_crypto: ReportSection
    footer: ReportSection
    report_date: date = field(default_factory=date.today)
    state: str = "Florida"

    def all_sections(self) -> list[ReportSection]:
        """Returns all sections in delivery order."""
        return [
            self.header,
            self.executive_summary,
            *self.main_stories,
            self.market_data,
            self.latin_investment,
            self.agent_strategies,
            self.on_the_radar,
            self.btc_crypto,
            self.footer,
        ]
