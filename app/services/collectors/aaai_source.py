from __future__ import annotations

import gzip
import html
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from http.client import RemoteDisconnected
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from app.services.collectors.base import CollectedPaper


@dataclass(slots=True)
class AAAITrack:
    track_id: str
    title: str
    url: str
    theme: str = ""
    series: str = ""


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._text_parts: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        self._href = dict(attrs).get("href")
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        text = " ".join(part.strip() for part in self._text_parts if part.strip()).strip()
        self.anchors.append((self._href, text))
        self._href = None
        self._text_parts = []


class AAAIProceedingsSource:
    ARCHIVE_URL = "https://ojs.aaai.org/index.php/AAAI/issue/archive"
    BASE_URL = "https://ojs.aaai.org"
    REQUEST_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    }
    MAX_FETCH_ATTEMPTS = 3

    def list_tracks(self, year: int) -> list[AAAITrack]:
        tracks: list[AAAITrack] = []
        next_page_url: str | None = self.ARCHIVE_URL
        visited_pages: set[str] = set()
        seen_track_urls: set[str] = set()

        while next_page_url and next_page_url not in visited_pages:
            visited_pages.add(next_page_url)
            html_text = self._fetch_text(next_page_url)
            for track in self._parse_tracks_from_archive_html(html_text, year=year):
                if track.url in seen_track_urls:
                    continue
                seen_track_urls.add(track.url)
                tracks.append(track)
            next_page_url = self._extract_next_archive_page_url(html_text)

        return tracks

    def _parse_tracks_from_archive_html(self, html: str, *, year: int) -> list[AAAITrack]:
        target = f"AAAI-{str(year)[-2:]}"
        title_pattern = re.compile(
            rf"\b{re.escape(target)}\s+Technical\s+Tracks\s+\d+\b",
            re.IGNORECASE,
        )
        seen: set[str] = set()
        tracks: list[AAAITrack] = []
        for item in self._iter_archive_issue_summaries(html):
            href = item["href"]
            text = item["title"]
            if "/issue/view/" not in href:
                continue
            normalized = " ".join(text.split())
            if not title_pattern.search(normalized):
                continue
            track_url = urljoin(self.BASE_URL, href)
            if track_url in seen:
                continue
            seen.add(track_url)
            tracks.append(
                AAAITrack(
                    track_id=track_url,
                    title=normalized,
                    url=track_url,
                    theme=item["theme"],
                    series=item["series"],
                )
            )
        return tracks

    def _iter_archive_issue_summaries(self, html_text: str) -> list[dict[str, str]]:
        summary_pattern = re.compile(
            r'<div class="obj_issue_summary">(?P<body>.*?)</div><!-- \.obj_issue_summary -->',
            re.IGNORECASE | re.DOTALL,
        )
        summaries: list[dict[str, str]] = []
        for match in summary_pattern.finditer(html_text):
            body = match.group("body")
            title_match = re.search(
                r'<a[^>]*class="title"[^>]*href="(?P<href>[^"]+/issue/view/[^"]+)"[^>]*>(?P<title>.*?)</a>',
                body,
                re.IGNORECASE | re.DOTALL,
            )
            if not title_match:
                continue
            series_match = re.search(
                r'<div class="series">\s*(?P<series>.*?)\s*</div>',
                body,
                re.IGNORECASE | re.DOTALL,
            )
            description_match = re.search(
                r'<div class="description">\s*(?P<description>.*?)\s*</div>',
                body,
                re.IGNORECASE | re.DOTALL,
            )
            summaries.append(
                {
                    "href": title_match.group("href"),
                    "title": self._normalize_html_text(title_match.group("title")),
                    "series": self._normalize_html_text(series_match.group("series")) if series_match else "",
                    "theme": self._extract_track_theme(description_match.group("description")) if description_match else "",
                }
            )
        if summaries:
            return summaries

        fallback: list[dict[str, str]] = []
        for href, title in self._iter_archive_issue_links(html_text):
            fallback.append({"href": href, "title": title, "series": "", "theme": ""})
        return fallback

    def _iter_archive_issue_links(self, html_text: str) -> list[tuple[str, str]]:
        issue_link_pattern = re.compile(
            r"<a\b[^>]*href=[\"'](?P<href>[^\"']*/issue/view/[^\"']+)[\"'][^>]*>(?P<label>.*?)</a>",
            re.IGNORECASE | re.DOTALL,
        )
        matches: list[tuple[str, str]] = []
        for match in issue_link_pattern.finditer(html_text):
            matches.append((match.group("href"), self._normalize_html_text(match.group("label"))))
        if matches:
            return matches

        collector = _AnchorCollector()
        collector.feed(html_text)
        return collector.anchors

    def _extract_track_theme(self, description_html: str) -> str:
        paragraphs = re.findall(r"<p>(?P<text>.*?)</p>", description_html, re.IGNORECASE | re.DOTALL)
        normalized = [self._normalize_html_text(paragraph) for paragraph in paragraphs]
        for paragraph in reversed(normalized):
            if "Technical Track" in paragraph:
                return self._format_track_theme(paragraph)
        return ""

    def _format_track_theme(self, paragraph: str) -> str:
        parts = re.findall(r"AAAI Technical Track on .*?(?=AAAI Technical Track on |$)", paragraph)
        cleaned = [" ".join(part.split()) for part in parts if part.strip()]
        if cleaned:
            return " / ".join(cleaned)
        return paragraph

    def _normalize_html_text(self, value: str) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", value)
        return " ".join(html.unescape(cleaned).split()).strip()

    def _extract_next_archive_page_url(self, html_text: str) -> str | None:
        match = re.search(
            r'<a[^>]*class="next"[^>]*href="(?P<href>[^"]+)"[^>]*>\s*Next\s*</a>',
            html_text,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None
        return urljoin(self.BASE_URL, match.group("href"))

    def fetch(self, *, year: int, track_ids: list[str], limit: int | None = None) -> list[CollectedPaper]:
        papers: list[CollectedPaper] = []
        target_urls = [track_id for track_id in track_ids if track_id.strip()]
        for track_url in target_urls:
            for href, title in self._extract_article_links(self._fetch_text(track_url)):
                papers.append(
                    CollectedPaper(
                        source_id=href,
                        title=title,
                        authors=[],
                        abstract="",
                        year=year,
                        venue=self._track_title_to_venue(track_url, year),
                        url=href,
                        source="aaai",
                    )
                )
                if limit is not None and len(papers) >= limit:
                    return papers[:limit]
        return papers[:limit] if limit is not None else papers

    def _extract_article_links(self, html: str) -> list[tuple[str, str]]:
        collector = _AnchorCollector()
        collector.feed(html)
        seen: set[str] = set()
        articles: list[tuple[str, str]] = []
        for href, text in collector.anchors:
            if "/article/view/" not in href or not text:
                continue
            article_url = urljoin(self.BASE_URL, href)
            if article_url in seen:
                continue
            seen.add(article_url)
            articles.append((article_url, text))
        return articles

    def _track_title_to_venue(self, track_url: str, year: int) -> str:
        match = re.search(r"/issue/view/(\d+)", track_url)
        suffix = match.group(1) if match else "track"
        return f"AAAI {year} Track {suffix}"

    def _fetch_text(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.MAX_FETCH_ATTEMPTS + 1):
            request = Request(url, headers=self.REQUEST_HEADERS)
            try:
                with urlopen(request, timeout=30) as response:  # noqa: S310
                    charset = response.headers.get_content_charset() or "utf-8"
                    raw = response.read()
                    content_encoding = (response.headers.get("Content-Encoding") or "").lower()
                    if content_encoding == "gzip" or raw[:2] == b"\x1f\x8b":
                        raw = gzip.decompress(raw)
                    return raw.decode(charset, errors="replace")
            except HTTPError as exc:
                raise RuntimeError(f"AAAI proceedings request failed with HTTP {exc.code}.") from exc
            except (RemoteDisconnected, URLError) as exc:
                last_error = exc
                if attempt >= self.MAX_FETCH_ATTEMPTS:
                    break
                time.sleep(0.2 * attempt)
        raise RuntimeError("Unable to reach AAAI proceedings site.") from last_error
