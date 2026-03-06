from __future__ import annotations
import anthropic

from agents.base_agent import BaseAgent
from models.scraped_data import ScrapedDataBundle, ScrapedPage

FIRECRAWL_MCP_URL = "https://mcp.firecrawl.dev/v2/mcp"

FIRECRAWL_SYSTEM_PROMPT = """
Eres un extractor de datos de mercado inmobiliario. Tu tarea es usar la herramienta
firecrawl_scrape para obtener el contenido de una lista de URLs y devolver
el contenido en markdown de cada una.

Para cada URL:
1. Llama a firecrawl_scrape con formats=["markdown"] y onlyMainContent=true
2. Devuelve el contenido obtenido con el nombre de la fuente

Sé eficiente: scrapeala todas antes de responder.
"""


class FirecrawlAgent(BaseAgent):
    """
    Phase 0: Scrapes critical real estate data websites via Firecrawl MCP.

    Uses Claude + Firecrawl MCP server so Claude calls firecrawl_scrape as a
    native tool. Falls back to the Python SDK if MCP is unavailable.
    """

    def __init__(self, config) -> None:
        super().__init__(config)
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.firecrawl_api_key = config.firecrawl_api_key
        self.model = config.claude_model
        self.urls: list[dict] = config.state_config.firecrawl_urls

    def _execute(self, input_data=None) -> ScrapedDataBundle:
        urls_text = "\n".join(
            f"- {entry['name']}: {entry['url']}" for entry in self.urls
        )
        user_prompt = (
            f"Scrapeea estas URLs y devuelve su contenido en markdown:\n{urls_text}"
        )

        self.logger.info(f"Firecrawl MCP: scraping {len(self.urls)} URLs")

        try:
            return self._scrape_via_mcp(user_prompt)
        except Exception as exc:
            self.logger.warning(
                f"Firecrawl MCP failed ({exc}). Falling back to SDK."
            )
            return self._scrape_via_sdk()

    # -------------------------------------------------------------------------
    # Primary: Claude + Firecrawl MCP
    # -------------------------------------------------------------------------

    def _scrape_via_mcp(self, user_prompt: str) -> ScrapedDataBundle:
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            mcp_servers=[
                {
                    "type": "url",
                    "url": FIRECRAWL_MCP_URL,
                    "name": "firecrawl",
                    "authorization_token": self.firecrawl_api_key,
                }
            ],
            system=FIRECRAWL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            betas=["mcp-client-2025-04-04"],
        )

        full_text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        self.logger.info(f"Firecrawl MCP response: {len(full_text)} chars")

        # Build pages from the combined MCP response
        pages = self._parse_mcp_response(full_text)
        bundle = ScrapedDataBundle(
            pages=pages,
            successful_count=sum(1 for p in pages if p.success),
            failed_count=sum(1 for p in pages if not p.success),
        )

        self.logger.info(
            f"Firecrawl MCP complete: {bundle.successful_count} ok, "
            f"{bundle.failed_count} failed"
        )
        return bundle

    def _parse_mcp_response(self, full_text: str) -> list[ScrapedPage]:
        """
        Builds ScrapedPage objects from the MCP response.
        When MCP returns a combined response, we create one page per configured URL
        using the full text as shared context (the analysis agent handles it anyway).
        """
        pages: list[ScrapedPage] = []

        # Try to split by source name markers if Claude structured the output
        remaining = full_text
        for entry in self.urls:
            name = entry["name"]
            url = entry["url"]

            # Look for a section header with the source name
            marker_idx = remaining.lower().find(name.lower())
            if marker_idx != -1:
                # Extract content from this marker to the next (up to 8000 chars)
                section = remaining[marker_idx: marker_idx + 8000]
                pages.append(ScrapedPage(
                    url=url,
                    source_name=name,
                    content=section,
                    success=True,
                ))
            else:
                pages.append(ScrapedPage(
                    url=url,
                    source_name=name,
                    content="",
                    success=False,
                    error="Section not found in MCP response",
                ))

        # If we couldn't parse individual sections, return the whole text as one page
        if not any(p.success for p in pages) and full_text:
            pages = [ScrapedPage(
                url="mcp://firecrawl",
                source_name="Firecrawl MCP (combined)",
                content=full_text[:40000],
                success=True,
            )]

        return pages

    # -------------------------------------------------------------------------
    # Fallback: Direct Firecrawl Python SDK
    # -------------------------------------------------------------------------

    def _scrape_via_sdk(self) -> ScrapedDataBundle:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from firecrawl import V1FirecrawlApp

        app = V1FirecrawlApp(api_key=self.firecrawl_api_key)
        bundle = ScrapedDataBundle()
        pages: list[ScrapedPage] = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._sdk_scrape_url, app, entry): entry
                for entry in self.urls
            }
            for future in as_completed(futures):
                entry = futures[future]
                try:
                    page = future.result()
                    pages.append(page)
                    if page.success:
                        bundle.successful_count += 1
                        self.logger.info(
                            f"SDK scraped '{page.source_name}': {len(page.content)} chars"
                        )
                    else:
                        bundle.failed_count += 1
                        self.logger.warning(
                            f"SDK failed '{entry['name']}': {page.error}"
                        )
                except Exception as exc:
                    bundle.failed_count += 1
                    pages.append(ScrapedPage(
                        url=entry["url"],
                        source_name=entry["name"],
                        content="",
                        success=False,
                        error=str(exc),
                    ))

        bundle.pages = pages
        return bundle

    def _sdk_scrape_url(self, app, entry: dict) -> ScrapedPage:
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
            return ScrapedPage(url=url, source_name=name, content="",
                               success=False, error=str(exc))
