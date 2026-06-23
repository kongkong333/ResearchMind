from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser

from app.services.collectors.base import CollectedPaper
from app.services.collectors.http_utils import read_text_url


class _AnthologyLinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        self._href = dict(attrs).get("href")
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        text = " ".join(part.strip() for part in self._parts if part.strip()).strip()
        self.links.append((self._href, text))
        self._href = None
        self._parts = []


class AclAnthologyProceedingsSource:
    BASE_URL = "https://aclanthology.org"
    REQUEST_HEADERS = {
        "User-Agent": "ResearchMind/0.1 (+https://aclanthology.org)",
    }

    def fetch_coling(self, *, year: int, limit: int | None = None) -> list[CollectedPaper]:
        html = self._fetch_text(self._event_url(year))
        return self._parse_coling_event_html(html, year=year, limit=limit)

    def _event_url(self, year: int) -> str:
        if year == 2024:
            return f"{self.BASE_URL}/events/lrec-coling-{year}/"
        return f"{self.BASE_URL}/events/coling-{year}/"

    def _parse_coling_event_html(self, html: str, *, year: int, limit: int | None) -> list[CollectedPaper]:
        collector = _AnthologyLinkCollector()
        collector.feed(html)
        pattern = re.compile(rf"/{year}\.coling-main\.\d+/?$", re.IGNORECASE)
        seen: set[str] = set()
        papers: list[CollectedPaper] = []
        for href, text in collector.links:
            if not pattern.search(href):
                continue
            if href in seen or not text:
                continue
            seen.add(href)
            papers.append(
                CollectedPaper(
                    source_id=href.strip("/"),
                    title=text,
                    authors=[],
                    abstract="",
                    year=year,
                    venue=f"COLING {year}",
                    url=f"{self.BASE_URL}{href}" if href.startswith("/") else href,
                    source="coling",
                    published_at=date(year, 1, 1),
                )
            )
            if limit is not None and len(papers) >= limit:
                break
        return papers

    def _fetch_text(self, url: str) -> str:
        return read_text_url(url, headers=self.REQUEST_HEADERS)
