from __future__ import annotations
import hashlib
import json
import os
from datetime import date, timedelta
from difflib import SequenceMatcher
from models.research_result import RawArticle


TITLE_SIMILARITY_THRESHOLD = 0.70


class ArticleDeduplicator:
    """
    Removes duplicate articles using two passes:
    1. URL hash deduplication (exact duplicates)
    2. Title similarity deduplication (near-duplicates from different sources)

    Optionally persists seen URL hashes to a JSON file for cross-day deduplication.
    Articles seen within `lookback_days` are filtered out on subsequent runs.
    """

    def __init__(
        self,
        history_file: str | None = None,
        lookback_days: int = 7,
    ) -> None:
        self.history_file = history_file
        self.lookback_days = lookback_days
        self._persistent_hashes: dict[str, str] = {}  # hash → date string

        if history_file:
            self._load_history()

    def _load_history(self) -> None:
        """Loads the seen-article history from disk, ignoring entries older than lookback_days."""
        if not os.path.exists(self.history_file):  # type: ignore[arg-type]
            return

        with open(self.history_file) as f:
            raw: dict[str, str] = json.load(f)

        cutoff = date.today() - timedelta(days=self.lookback_days)
        self._persistent_hashes = {
            h: d for h, d in raw.items()
            if date.fromisoformat(d) >= cutoff
        }

    def _save_history(self, new_hashes: set[str]) -> None:
        """Appends newly accepted article hashes and saves the pruned history to disk."""
        today = date.today().isoformat()
        for h in new_hashes:
            self._persistent_hashes[h] = today

        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)  # type: ignore[arg-type]
        with open(self.history_file, "w") as f:  # type: ignore[arg-type]
            json.dump(self._persistent_hashes, f)

    def deduplicate(self, articles: list[RawArticle]) -> list[RawArticle]:
        # Pre-populate with hashes seen in previous runs
        seen_url_hashes: set[str] = set(self._persistent_hashes.keys())
        new_hashes: set[str] = set()
        unique: list[RawArticle] = []

        for article in articles:
            url_hash = hashlib.sha256(article.url.encode()).hexdigest()
            if url_hash in seen_url_hashes:
                continue

            if self._is_similar_to_existing(article, unique):
                continue

            seen_url_hashes.add(url_hash)
            new_hashes.add(url_hash)
            unique.append(article)

        if self.history_file and new_hashes:
            self._save_history(new_hashes)

        return unique

    def _is_similar_to_existing(
        self, candidate: RawArticle, accepted: list[RawArticle]
    ) -> bool:
        candidate_title = candidate.title.lower().strip()
        for existing in accepted:
            ratio = SequenceMatcher(
                None,
                candidate_title,
                existing.title.lower().strip(),
            ).ratio()
            if ratio >= TITLE_SIMILARITY_THRESHOLD:
                return True
        return False
