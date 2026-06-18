from __future__ import annotations

from app.services.collectors.base import CollectedPaper


class PaperCollector:
    def collect_from_papers(
        self,
        papers: list[CollectedPaper],
        topic: str,
        venues: list[str] | None = None,
    ) -> list[CollectedPaper]:
        allowed_venues = self._normalize_venues(venues)
        seen_ids: set[str] = set()
        result: list[CollectedPaper] = []

        for paper in papers:
            if allowed_venues and paper.venue not in allowed_venues:
                continue
            if paper.source_id in seen_ids:
                continue
            seen_ids.add(paper.source_id)
            result.append(paper)

        return result

    def _normalize_venues(self, venues: list[str] | None) -> set[str]:
        normalized: set[str] = set()
        for venue in venues or []:
            if not isinstance(venue, str):
                continue
            cleaned = venue.strip()
            if cleaned:
                normalized.add(cleaned)
        return normalized
