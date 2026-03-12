from __future__ import annotations

import json
from datetime import date
from pathlib import Path

# ── Pricing tables (USD) ───────────────────────────────────────────────────────
_CLAUDE_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":         {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "claude-opus-4-6":           {"input": 15.0 / 1_000_000, "output": 75.0 / 1_000_000},
    "claude-haiku-4-5-20251001": {"input": 0.8 / 1_000_000, "output": 4.0 / 1_000_000},
}
_CLAUDE_DEFAULT = {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000}

_PERPLEXITY_PRICING: dict[str, dict[str, float]] = {
    "sonar-pro": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000, "per_request": 5.0 / 1_000},
    "sonar":     {"input": 1.0 / 1_000_000, "output": 5.0 / 1_000_000,  "per_request": 5.0 / 1_000},
}
_PERPLEXITY_DEFAULT = {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000, "per_request": 5.0 / 1_000}

_FIRECRAWL_COST_PER_PAGE = 0.001


class CostTracker:
    """
    Cost accumulator for a single pipeline run.
    Sequential execution — no locking needed.
    """

    def __init__(self) -> None:
        self._claude: dict[str, dict] = {}
        self._perplexity = {
            "model": "",
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        }
        self._firecrawl = {"pages": 0, "cost_usd": 0.0}

    def record_claude(
        self, agent: str, model: str, input_tokens: int, output_tokens: int
    ) -> None:
        pricing = _CLAUDE_PRICING.get(model, _CLAUDE_DEFAULT)
        cost = input_tokens * pricing["input"] + output_tokens * pricing["output"]
        if agent not in self._claude:
            self._claude[agent] = {
                "model": model, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
            }
        entry = self._claude[agent]
        entry["input_tokens"] += input_tokens
        entry["output_tokens"] += output_tokens
        entry["cost_usd"] = round(entry["cost_usd"] + cost, 6)

    def record_perplexity(
        self, model: str, input_tokens: int, output_tokens: int, requests: int = 1
    ) -> None:
        pricing = _PERPLEXITY_PRICING.get(model, _PERPLEXITY_DEFAULT)
        cost = (
            input_tokens * pricing["input"]
            + output_tokens * pricing["output"]
            + requests * pricing["per_request"]
        )
        p = self._perplexity
        p["model"] = model
        p["requests"] += requests
        p["input_tokens"] += input_tokens
        p["output_tokens"] += output_tokens
        p["cost_usd"] = round(p["cost_usd"] + cost, 6)

    def record_firecrawl_pages(self, pages: int) -> None:
        self._firecrawl["pages"] += pages
        self._firecrawl["cost_usd"] = round(
            self._firecrawl["cost_usd"] + pages * _FIRECRAWL_COST_PER_PAGE, 6
        )

    def total_usd(self) -> float:
        claude_total = sum(v["cost_usd"] for v in self._claude.values())
        return round(claude_total + self._perplexity["cost_usd"] + self._firecrawl["cost_usd"], 6)

    def to_dict(self, run_id: str) -> dict:
        claude_total = sum(v["cost_usd"] for v in self._claude.values())
        return {
            "date": date.today().isoformat(),
            "run_id": run_id,
            "claude": {
                "by_agent": {
                    agent: {
                        "model": data["model"],
                        "input_tokens": data["input_tokens"],
                        "output_tokens": data["output_tokens"],
                        "cost_usd": data["cost_usd"],
                    }
                    for agent, data in self._claude.items()
                },
                "total_cost_usd": round(claude_total, 6),
            },
            "perplexity": {
                "model": self._perplexity["model"],
                "total_requests": self._perplexity["requests"],
                "total_input_tokens": self._perplexity["input_tokens"],
                "total_output_tokens": self._perplexity["output_tokens"],
                "cost_usd": self._perplexity["cost_usd"],
            },
            "firecrawl": {
                "pages_scraped": self._firecrawl["pages"],
                "cost_usd": self._firecrawl["cost_usd"],
            },
            "total_cost_usd": self.total_usd(),
        }

    def save(self, run_id: str, costs_dir: str = "costs") -> Path:
        """Appends this run's cost record to costs/costs_log.json."""
        path = Path(costs_dir)
        path.mkdir(exist_ok=True)
        log_file = path / "costs_log.json"

        existing: list[dict] = []
        if log_file.exists():
            try:
                existing = json.loads(log_file.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        existing.append(self.to_dict(run_id))
        log_file.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return log_file
