from __future__ import annotations

from datetime import date
from html.parser import HTMLParser

from app.services.collectors.base import CollectedPaper
from app.services.collectors.http_utils import read_text_url


class _DblpIcmeHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._entry_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._current_url = ""
        self.entries: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "") or ""
        if tag == "li" and "entry" in classes.split():
            self._entry_depth += 1
            if self._entry_depth == 1:
                self._current_url = ""
                self._title_parts = []
                self._in_title = False
            return
        if self._entry_depth == 0:
            return
        if tag == "nav" and "publ" in classes.split():
            return
        if tag == "a":
            href = attributes.get("href") or ""
            if "/rec/conf/icme/" in href:
                self._current_url = href
            return
        if tag == "span" and "title" in classes.split():
            self._in_title = True
            self._title_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_title and self._entry_depth > 0:
            self._title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._in_title:
            self._in_title = False
            return
        if tag == "li" and self._entry_depth > 0:
            self._entry_depth -= 1
            if self._entry_depth == 0:
                title = " ".join(part.strip() for part in self._title_parts if part.strip()).strip()
                if self._current_url and title:
                    self.entries.append((self._current_url, title))
                self._current_url = ""
                self._title_parts = []
                self._in_title = False


class DblpIcmeProceedingsSource:
    BASE_URL = "https://dblp.org"
    REQUEST_HEADERS = {
        "User-Agent": "ResearchMind/0.1 (+https://dblp.org)",
    }
    TIMEOUT_SECONDS = 8

    def fetch(self, *, year: int, limit: int | None = None) -> list[CollectedPaper]:
        html = read_text_url(self._proceedings_url(year), headers=self.REQUEST_HEADERS, timeout=self.TIMEOUT_SECONDS)
        return self._parse_proceedings_html(html, year=year, limit=limit)

    def _proceedings_url(self, year: int) -> str:
        return f"{self.BASE_URL}/db/conf/icme/icme{year}.html"

    def _parse_proceedings_html(self, html: str, *, year: int, limit: int | None) -> list[CollectedPaper]:
        parser = _DblpIcmeHtmlParser()
        parser.feed(html)
        papers: list[CollectedPaper] = []
        seen: set[str] = set()
        for href, title in parser.entries:
            paper_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
            if paper_url in seen:
                continue
            seen.add(paper_url)
            papers.append(
                CollectedPaper(
                    source_id=paper_url.removeprefix(f"{self.BASE_URL}/").strip("/"),
                    title=title.rstrip(".").strip(),
                    authors=[],
                    abstract="",
                    year=year,
                    venue=f"ICME {year}",
                    url=paper_url,
                    source="icme",
                    published_at=date(year, 1, 1),
                )
            )
            if limit is not None and len(papers) >= limit:
                break
        return papers
