from __future__ import annotations
import logging
from datetime import datetime

from config.settings import Config
from utils.cost_tracker import CostTracker
from agents.firecrawl_agent import FirecrawlAgent
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.writing_agent import WritingAgent
from agents.editorial_agent import EditorialAgent
from agents.delivery_agent import DeliveryAgent


class Orchestrator:
    """
    Wires all 6 pipeline agents together in sequence.

    Each agent's output becomes the next agent's input.
    The orchestrator manages data flow, logs phase transitions,
    and returns a summary dict of the full run.
    """

    def __init__(self, config: Config, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run  # If True, skip Telegram delivery
        self.logger = logging.getLogger("Orchestrator")

        self.cost_tracker = CostTracker()
        self.firecrawl_agent = FirecrawlAgent(config, self.cost_tracker)
        self.research_agent = ResearchAgent(config, self.cost_tracker)
        self.analysis_agent = AnalysisAgent(config, self.cost_tracker)
        self.writing_agent = WritingAgent(config, self.cost_tracker)
        self.editorial_agent = EditorialAgent(config, self.cost_tracker)
        self.delivery_agent = DeliveryAgent(config)

    def run(self) -> dict:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        state = self.config.state_config.state_name

        self.logger.info(f"{'='*50}")
        self.logger.info(f"Pipeline run {run_id} | State: {state}")
        self.logger.info(f"{'='*50}")

        # Phase 0: Firecrawl — scrape critical data websites
        self.logger.info("--- Phase 0: Firecrawl ---")
        scraped_bundle = self.firecrawl_agent.run(None)

        # Phase 1: Research — Perplexity Sonar API
        self.logger.info("--- Phase 1: Research (Perplexity) ---")
        research_bundle = self.research_agent.run(None)

        # Phase 2: Analysis — combine + score + select
        self.logger.info("--- Phase 2: Analysis ---")
        analysis_bundle = self.analysis_agent.run((research_bundle, scraped_bundle))

        # Phase 3: Writing — full Spanish newsletter
        self.logger.info("--- Phase 3: Writing ---")
        draft_report = self.writing_agent.run(analysis_bundle)

        # Phase 4: Editorial — quality review + Telegram formatting
        self.logger.info("--- Phase 4: Editorial ---")
        final_messages = self.editorial_agent.run(draft_report)

        # Phase 5: Delivery — send to Telegram
        if self.dry_run:
            self.logger.info("--- Phase 5: SKIPPED (dry-run mode) ---")
            self._print_dry_run(final_messages)
            delivery_result = {
                "sent_count": 0,
                "failed_count": 0,
                "message_ids": [],
                "dry_run": True,
            }
        else:
            self.logger.info("--- Phase 5: Delivery ---")
            delivery_result = self.delivery_agent.run(final_messages)

        log_file = self.cost_tracker.save(run_id)
        self.logger.info(
            f"Cost tracking saved: {log_file} | "
            f"Total cost: ${self.cost_tracker.total_usd():.4f}"
        )

        summary = {
            "run_id": run_id,
            "state": state,
            "scraped_pages": scraped_bundle.successful_count,
            "articles_found": len(research_bundle.articles),
            "articles_selected": len(analysis_bundle.selected_articles),
            "messages_sent": delivery_result["sent_count"],
            "messages_failed": delivery_result.get("failed_count", 0),
            "dry_run": self.dry_run,
            "total_cost_usd": self.cost_tracker.total_usd(),
        }

        self.logger.info(f"{'='*50}")
        self.logger.info(f"Run complete: {summary}")
        self.logger.info(f"{'='*50}")

        return summary

    def _print_dry_run(self, messages: list[str]) -> None:
        """Prints messages to console instead of sending to Telegram."""
        print("\n" + "=" * 60)
        print("DRY RUN — Messages that would be sent to Telegram:")
        print("=" * 60)
        for i, msg in enumerate(messages, 1):
            print(f"\n--- Message {i}/{len(messages)} ({len(msg)} chars) ---")
            print(msg)
        print("\n" + "=" * 60)
        print(f"Total: {len(messages)} messages")
        print("=" * 60)
