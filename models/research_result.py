from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawArticle:
    title: str
    url: str
    content: str
    score: float = 0.0
    published_date: str = ""
    category: str = ""
    tavily_answer: str = ""  # Tavily's own summary for the query
    source: str = ""         # Domain name


@dataclass
class ResearchBundle:
    articles: list[RawArticle] = field(default_factory=list)
    total_queries_run: int = 0
    state: str = "Florida"
    raw_research_text: str = ""  # Full Claude response text for analysis agent

    def to_prompt_context(self) -> str:
        """Formats articles for use in analysis agent prompt."""
        lines = []
        for i, a in enumerate(self.articles, 1):
            lines.append(
                f"[{i}] CATEGORÍA: {a.category}\n"
                f"    TÍTULO: {a.title}\n"
                f"    URL: {a.url}\n"
                f"    FECHA: {a.published_date or 'No disponible'}\n"
                f"    RESUMEN TAVILY: {a.tavily_answer[:300] if a.tavily_answer else 'N/A'}\n"
                f"    CONTENIDO: {a.content[:500]}...\n"
            )
        return "\n".join(lines)
