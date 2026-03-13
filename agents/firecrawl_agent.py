from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.base_agent import BaseAgent
from models.scraped_data import ScrapedDataBundle, ScrapedPage


class FirecrawlAgent(BaseAgent):
    """
    Phase 0: Scrapes critical real estate data websites via Firecrawl SDK.

    Uses the Firecrawl Python SDK directly (parallel scraping, 3 workers).
    Falls back gracefully to an empty page if a URL fails.
    """

    def __init__(self, config, cost_tracker=None) -> None:
        super().__init__(config, cost_tracker)
        self.firecrawl_api_key = config.firecrawl_api_key
        self.urls: list[dict] = config.state_config.firecrawl_urls

    def _execute(self, input_data=None) -> ScrapedDataBundle:
        from firecrawl import V1FirecrawlApp

        app = V1FirecrawlApp(api_key=self.firecrawl_api_key)
        self.logger.info(f"Firecrawl SDK: scraping {len(self.urls)} URLs")

        pages: list[ScrapedPage] = []
        successful = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._scrape_url, app, entry): entry
                for entry in self.urls
            }
            for future in as_completed(futures):
                entry = futures[future]
                try:
                    page = future.result()
                    pages.append(page)
                    if page.success:
                        successful += 1
                        self.logger.info(
                            f"Scraped '{page.source_name}': {len(page.content)} chars"
                        )
                    else:
                        failed += 1
                        self.logger.warning(f"Failed '{entry['name']}': {page.error}")
                except Exception as exc:
                    failed += 1
                    pages.append(ScrapedPage(
                        url=entry["url"], source_name=entry["name"],
                        content="", success=False, error=str(exc),
                    ))

        if self.cost_tracker:
            self.cost_tracker.record_firecrawl_pages(len(self.urls))

        self.logger.info(f"Firecrawl complete: {successful} ok, {failed} failed")
        return ScrapedDataBundle(pages=pages, successful_count=successful, failed_count=failed)

    def _scrape_url(self, app, entry: dict) -> ScrapedPage:
        url, name = entry["url"], entry["name"]
        try:
            result = app.scrape_url(
                url,
                formats=["markdown"],
                only_main_content=True,
                timeout=30000,
            )
            content = ""
            if result and hasattr(result, "markdown"):
                content = result.markdown or ""
            elif isinstance(result, dict):
                content = result.get("markdown", "") or result.get("content", "")
            content = content[:8000] if content else ""
            return ScrapedPage(
                url=url, source_name=name, content=content,
                success=bool(content),
                error=None if content else "Empty response",
            )
        except Exception as exc:
            return ScrapedPage(url=url, source_name=name, content="", success=False, error=str(exc))
