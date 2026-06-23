from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from app.services.collectors.base import CollectedPaper
from app.services.collectors.http_utils import read_json_url


class CrossrefProceedingsSource:
    API_URL = "https://api.crossref.org/works"
    REQUEST_HEADERS = {
        "User-Agent": "ResearchMind/0.1 (mailto:researchmind@example.com)",
    }
    TIMEOUT_SECONDS = 8

    def fetch_icme(self, *, year: int, limit: int | None = None) -> list[CollectedPaper]:
        rows = max(limit or 100, 100)
        query = urlencode(
            {
                "filter": f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31,type:proceedings-article",
                "query.container-title": "IEEE International Conference on Multimedia and Expo",
                "rows": rows,
            }
        )
        payload = read_json_url(
            f"{self.API_URL}?{query}",
            headers=self.REQUEST_HEADERS,
            timeout=self.TIMEOUT_SECONDS,
        )
        items = payload.get("message", {}).get("items", [])
        papers: list[CollectedPaper] = []
        seen: set[str] = set()
        for item in items:
            paper = self._build_icme_paper(item, year=year)
            if paper is None or paper.url in seen:
                continue
            seen.add(paper.url)
            papers.append(paper)
            if limit is not None and len(papers) >= limit:
                break
        return papers

    def fetch_coling(self, *, year: int, limit: int | None = None) -> list[CollectedPaper]:
        rows = max(limit or 100, 100)
        query = urlencode(
            {
                "filter": f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31,type:proceedings-article",
                "query.container-title": "International Conference on Computational Linguistics",
                "rows": rows,
            }
        )
        payload = read_json_url(
            f"{self.API_URL}?{query}",
            headers=self.REQUEST_HEADERS,
            timeout=self.TIMEOUT_SECONDS,
        )
        items = payload.get("message", {}).get("items", [])
        papers: list[CollectedPaper] = []
        seen: set[str] = set()
        for item in items:
            paper = self._build_coling_paper(item, year=year)
            if paper is None or paper.url in seen:
                continue
            seen.add(paper.url)
            papers.append(paper)
            if limit is not None and len(papers) >= limit:
                break
        return papers

    def _build_icme_paper(self, item: dict[str, object], *, year: int) -> CollectedPaper | None:
        container_titles = [str(value).strip() for value in item.get("container-title", []) if str(value).strip()]
        container_blob = " ".join(container_titles).lower()
        if "multimedia and expo" not in container_blob or "ieee" not in container_blob:
            return None
        titles = item.get("title", [])
        title = str(titles[0]).strip() if isinstance(titles, list) and titles else ""
        doi = str(item.get("DOI", "")).strip()
        if not title or not doi:
            return None
        published = item.get("published-print") or item.get("published-online") or {}
        published_parts = published.get("date-parts", []) if isinstance(published, dict) else []
        if published_parts and published_parts[0]:
            item_year = int(published_parts[0][0])
            if item_year != year:
                return None
        authors: list[str] = []
        for author in item.get("author", []):
            if not isinstance(author, dict):
                continue
            given = str(author.get("given", "")).strip()
            family = str(author.get("family", "")).strip()
            name = " ".join(part for part in (given, family) if part).strip()
            if name:
                authors.append(name)
        return CollectedPaper(
            source_id=doi,
            title=title.rstrip(".").strip(),
            authors=authors,
            abstract="",
            year=year,
            venue=f"ICME {year}",
            url=f"https://doi.org/{doi}",
            source="icme",
            published_at=date(year, 1, 1),
        )

    def _build_coling_paper(self, item: dict[str, object], *, year: int) -> CollectedPaper | None:
        container_titles = [str(value).strip() for value in item.get("container-title", []) if str(value).strip()]
        container_blob = " ".join(container_titles).lower()
        if "computational linguistics" not in container_blob:
            return None
        titles = item.get("title", [])
        title = str(titles[0]).strip() if isinstance(titles, list) and titles else ""
        doi = str(item.get("DOI", "")).strip()
        if not title or not doi:
            return None
        published = item.get("published-print") or item.get("published-online") or {}
        published_parts = published.get("date-parts", []) if isinstance(published, dict) else []
        if published_parts and published_parts[0]:
            item_year = int(published_parts[0][0])
            if item_year != year:
                return None
        authors: list[str] = []
        for author in item.get("author", []):
            if not isinstance(author, dict):
                continue
            given = str(author.get("given", "")).strip()
            family = str(author.get("family", "")).strip()
            name = " ".join(part for part in (given, family) if part).strip()
            if name:
                authors.append(name)
        return CollectedPaper(
            source_id=doi,
            title=title.rstrip(".").strip(),
            authors=authors,
            abstract="",
            year=year,
            venue=f"COLING {year}",
            url=f"https://doi.org/{doi}",
            source="coling",
            published_at=date(year, 1, 1),
        )
