from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScrapedPage:
    url: str
    source_name: str        # e.g. "Florida Realtors", "Freddie Mac"
    content: str            # Cleaned markdown content from Firecrawl
    success: bool = True
    error: Optional[str] = None


@dataclass
class ScrapedDataBundle:
    pages: list[ScrapedPage] = field(default_factory=list)
    successful_count: int = 0
    failed_count: int = 0

    def get_combined_context(self) -> str:
        """Returns all successful page contents concatenated for use in prompts."""
        sections = []
        for page in self.pages:
            if page.success and page.content:
                sections.append(
                    f"=== FUENTE: {page.source_name} ({page.url}) ===\n{page.content}\n"
                )
        return "\n".join(sections)
