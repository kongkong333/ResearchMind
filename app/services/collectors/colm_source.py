from __future__ import annotations

import html
import re
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from app.services.collectors.base import CollectedPaper


class ColmAcceptedPapersSource:
    BASE_URL = "https://colmweb.org"
    REQUEST_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def fetch(self, *, year: int, limit: int | None = None) -> list[CollectedPaper]:
        page_url = f"{self.BASE_URL}/{year}/AcceptedPapers.html"
        html_text = self._fetch_text(page_url)
        papers = self._parse_papers(html_text, year=year)
        return papers[:limit] if limit is not None else papers

    def _parse_papers(self, html_text: str, *, year: int) -> list[CollectedPaper]:
        link_pattern = re.compile(
            r'<a[^>]+href="(?P<href>https?://openreview\.net/[^"]+)"[^>]*>(?P<title>.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        papers: list[CollectedPaper] = []
        seen_urls: set[str] = set()
        for match in link_pattern.finditer(html_text):
            url = urljoin(self.BASE_URL, match.group("href").strip())
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = self._normalize_html_text(match.group("title"))
            if not title:
                continue
            papers.append(
                CollectedPaper(
                    source_id=url,
                    title=title,
                    authors=[],
                    abstract="",
                    year=year,
                    venue=f"COLM {year}",
                    url=url,
                    source="colm",
                    published_at=date(year, 1, 1),
                )
            )
        return papers

    def _normalize_html_text(self, value: str) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", value)
        return " ".join(html.unescape(cleaned).split()).strip()

    def _fetch_text(self, url: str) -> str:
        request = Request(url, headers=self.REQUEST_HEADERS)
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except HTTPError as exc:
            if exc.code == 404:
                raise RuntimeError(f"COLM {self._extract_year(url)} accepted papers page was not found.") from exc
            raise RuntimeError(f"COLM accepted papers request failed with HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError("Unable to reach COLM accepted papers page.") from exc

    def _extract_year(self, url: str) -> str:
        match = re.search(r"/(\d{4})/AcceptedPapers\.html$", url)
        return match.group(1) if match else "unknown"
