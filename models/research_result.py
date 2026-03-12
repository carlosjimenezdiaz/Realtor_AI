from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class RawArticle:
    title: str
    url: str
    content: str
    published_date: str = ""
    category: str = ""
    perplexity_answer: str = ""  # Perplexity's synthesized answer for the query
    source: str = ""             # Domain name


@dataclass
class ResearchBundle:
    articles: list[RawArticle] = field(default_factory=list)
    total_queries_run: int = 0
    state: str = "Florida"

    def to_prompt_context(self) -> str:
        """Formats articles for use in downstream agent prompts."""
        lines = []
        for i, a in enumerate(self.articles, 1):
            lines.append(
                f"[{i}] CATEGORÍA: {a.category}\n"
                f"    TÍTULO: {a.title}\n"
                f"    URL: {a.url}\n"
                f"    FECHA: {a.published_date or 'N/D'}\n"
                f"    PERPLEXITY SUMMARY: {a.perplexity_answer[:300] if a.perplexity_answer else 'N/D'}\n"
                f"    CONTENIDO: {a.content[:500]}...\n"
            )
        return "\n".join(lines)
