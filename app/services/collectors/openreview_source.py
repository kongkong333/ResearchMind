from __future__ import annotations

import json
import re
from datetime import date
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.services.collectors.base import CollectedPaper


class OpenReviewPaperSource:
    SOURCE_NAME = "openreview"
    _API2_BASE_URL = "https://api2.openreview.net"
    _API1_BASE_URL = "https://api.openreview.net"
    _PAGE_SIZE = 100
    _VENUE_PATTERNS = {
        "iclr": "ICLR.cc/{year}/Conference",
        "neurips": "NeurIPS.cc/{year}/Conference",
        "nips": "NeurIPS.cc/{year}/Conference",
        "icml": "ICML.cc/{year}/Conference",
        "colm": "COLMweb.org/{year}/Conference",
        "aaai": "AAAI.org/{year}/Conference",
    }

    def fetch(
        self,
        conference: str,
        *,
        year: int,
        limit: int | None = None,
    ) -> list[CollectedPaper]:
        venue_id = self._resolve_venue_id(conference, year)
        try:
            api_version = self._detect_api_version(venue_id)
        except HTTPError as exc:
            raise self._wrap_lookup_error(exc, conference=conference, year=year, venue_id=venue_id) from exc
        if api_version == 2:
            try:
                papers = self._fetch_api2_accepted(venue_id=venue_id, year=year, limit=limit)
                if not papers:
                    papers = self._fetch_api1_accepted(venue_id=venue_id, year=year)
            except HTTPError as exc:
                raise self._wrap_lookup_error(exc, conference=conference, year=year, venue_id=venue_id) from exc
        else:
            try:
                papers = self._fetch_api1_accepted(venue_id=venue_id, year=year)
            except HTTPError as exc:
                raise self._wrap_lookup_error(exc, conference=conference, year=year, venue_id=venue_id) from exc
        return papers[:limit] if limit is not None else papers

    def _detect_api_version(self, venue_id: str) -> int:
        payload = self._get_json("groups", {"id": venue_id}, api_version=2)
        groups = payload.get("groups", [])
        if groups and groups[0].get("domain"):
            return 2
        return 1

    def _fetch_api2_accepted(self, *, venue_id: str, year: int, limit: int | None) -> list[CollectedPaper]:
        notes: list[dict[str, Any]] = []
        offset = 0
        while True:
            payload = self._get_json(
                "notes",
                {
                    "content.venueid": venue_id,
                    "limit": self._PAGE_SIZE,
                    "offset": offset,
                },
                api_version=2,
            )
            page = payload.get("notes", [])
            if not page:
                break
            notes.extend(page)
            if limit is not None and len(notes) >= limit:
                notes = notes[:limit]
                break
            if len(page) < self._PAGE_SIZE:
                break
            offset += len(page)
        venue_label = self._format_venue_label(venue_id, year)
        papers = [self._build_api2_paper(note, venue_label=venue_label, year=year) for note in notes]
        return [paper for paper in papers if paper is not None]

    def _fetch_api1_accepted(self, *, venue_id: str, year: int) -> list[CollectedPaper]:
        blind_notes = self._get_api1_submission_notes(venue_id, invitation_suffix="Blind_Submission", include_original=True)
        if blind_notes:
            accepted_notes: list[dict[str, Any]] = []
            for note in blind_notes:
                replies = note.get("details", {}).get("directReplies", [])
                decision_note = self._find_decision_reply(replies)
                if decision_note is None or not self._decision_is_accept(decision_note):
                    continue
                original = note.get("details", {}).get("original")
                if isinstance(original, dict):
                    accepted_notes.append(original)
            if accepted_notes:
                venue_label = self._format_venue_label(venue_id, year)
                papers = [self._build_api1_paper(note, venue_label=venue_label, year=year) for note in accepted_notes]
                return [paper for paper in papers if paper is not None]

        submission_notes = self._get_api1_submission_notes(venue_id, invitation_suffix="Submission", include_original=False)
        venue_label = self._format_venue_label(venue_id, year)
        accepted: list[CollectedPaper] = []
        for note in submission_notes:
            replies = note.get("details", {}).get("directReplies", [])
            decision_note = self._find_decision_reply(replies)
            if decision_note is None or not self._decision_is_accept(decision_note):
                continue
            paper = self._build_api1_paper(note, venue_label=venue_label, year=year)
            if paper is not None:
                accepted.append(paper)
        return accepted

    def _get_api1_submission_notes(
        self,
        venue_id: str,
        *,
        invitation_suffix: str,
        include_original: bool,
    ) -> list[dict[str, Any]]:
        details = "directReplies,original" if include_original else "directReplies"
        payload = self._get_json(
            "notes",
            {
                "invitation": f"{venue_id}/-/{invitation_suffix}",
                "details": details,
            },
            api_version=1,
        )
        return payload.get("notes", [])

    def _build_api2_paper(self, note: dict[str, Any], *, venue_label: str, year: int) -> CollectedPaper | None:
        note_id = str(note.get("id", "")).strip()
        title = self._content_value(note.get("content", {}), "title")
        if not note_id or not title:
            return None
        abstract = self._content_value(note.get("content", {}), "abstract")
        authors = self._content_list(note.get("content", {}), "authors")
        return CollectedPaper(
            source_id=note_id,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            venue=venue_label,
            url=f"https://openreview.net/forum?id={note_id}",
            keywords=[],
            source=self.SOURCE_NAME,
            published_at=date(year, 1, 1),
        )

    def _build_api1_paper(self, note: dict[str, Any], *, venue_label: str, year: int) -> CollectedPaper | None:
        note_id = str(note.get("id", "")).strip()
        content = note.get("content", {})
        title = self._coerce_text(content.get("title"))
        if not note_id or not title:
            return None
        abstract = self._coerce_text(content.get("abstract"))
        authors = [self._coerce_text(item) for item in content.get("authors", []) if self._coerce_text(item)]
        score = self._extract_score(note.get("details", {}).get("directReplies", []))
        keywords = [f"score:{score:.2f}"] if score is not None else []
        return CollectedPaper(
            source_id=note_id,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            venue=venue_label,
            url=f"https://openreview.net/forum?id={note_id}",
            keywords=keywords,
            source=self.SOURCE_NAME,
            published_at=date(year, 1, 1),
        )

    def _find_decision_reply(self, replies: list[dict[str, Any]]) -> dict[str, Any] | None:
        for reply in replies:
            invitations = reply.get("invitations") or []
            invitation = reply.get("invitation")
            values = [*invitations, invitation]
            if any(isinstance(value, str) and value.endswith("Decision") for value in values if value):
                return reply
        return None

    def _decision_is_accept(self, decision_note: dict[str, Any]) -> bool:
        decision = self._coerce_text(decision_note.get("content", {}).get("decision"))
        return "accept" in decision.lower()

    def _extract_score(self, replies: list[dict[str, Any]]) -> float | None:
        scores: list[float] = []
        for reply in replies:
            invitations = reply.get("invitations") or []
            invitation = reply.get("invitation")
            values = [*invitations, invitation]
            if not any(isinstance(value, str) and value.endswith("Official_Review") for value in values if value):
                continue
            rating = self._extract_rating_value(reply.get("content", {}))
            parsed = self._parse_numeric_prefix(rating)
            if parsed is not None:
                scores.append(parsed)
        if not scores:
            return None
        return sum(scores) / len(scores)

    def _extract_rating_value(self, content: dict[str, Any]) -> str:
        for key in ("rating", "recommendation", "overall_rating", "overall"):
            if key in content:
                return self._coerce_text(content.get(key))
        return ""

    def _parse_numeric_prefix(self, raw: str) -> float | None:
        match = re.match(r"\s*(-?\d+(?:\.\d+)?)", raw)
        if match is None:
            return None
        return float(match.group(1))

    def _score_from_keywords(self, keywords: list[str]) -> float:
        for keyword in keywords:
            if keyword.startswith("score:"):
                try:
                    return float(keyword.split(":", 1)[1])
                except ValueError:
                    return -1.0
        return -1.0

    def _content_value(self, content: dict[str, Any], key: str) -> str:
        return self._coerce_text(content.get(key))

    def _content_list(self, content: dict[str, Any], key: str) -> list[str]:
        raw = content.get(key)
        if isinstance(raw, dict):
            raw = raw.get("value")
        if not isinstance(raw, list):
            return []
        return [self._coerce_text(item) for item in raw if self._coerce_text(item)]

    def _coerce_text(self, raw: Any) -> str:
        if isinstance(raw, dict):
            raw = raw.get("value")
        if isinstance(raw, list):
            return ""
        return " ".join(str(raw or "").split()).strip()

    def _format_venue_label(self, venue_id: str, year: int) -> str:
        prefix = venue_id.split("/", 1)[0]
        short = prefix.split(".", 1)[0].upper()
        return f"{short} {year}"

    def _resolve_venue_id(self, conference: str, year: int) -> str:
        normalized = conference.strip()
        if "/" in normalized:
            return normalized
        alias = normalized.lower()
        if alias not in self._VENUE_PATTERNS:
            supported = ", ".join(sorted(set(self._VENUE_PATTERNS)))
            raise ValueError(f"Unsupported OpenReview conference '{conference}'. Supported values: {supported}.")
        return self._VENUE_PATTERNS[alias].format(year=year)

    def _wrap_lookup_error(self, error: HTTPError, *, conference: str, year: int, venue_id: str) -> ValueError:
        alias = conference.strip().upper() or venue_id
        if error.code == 404:
            return ValueError(
                f"{alias} {year} venue was not found on OpenReview (venue id: {venue_id}, HTTP 404). "
                "Check whether that year is available or whether the conference still uses OpenReview."
            )
        return ValueError(
            f"Failed to fetch {alias} {year} from OpenReview (venue id: {venue_id}, HTTP {error.code})."
        )

    def _get_json(self, path: str, params: dict[str, object], *, api_version: int = 2) -> dict[str, Any]:
        base_url = self._API2_BASE_URL if api_version == 2 else self._API1_BASE_URL
        query = urlencode({key: value for key, value in params.items() if value is not None}, doseq=True)
        url = f"{base_url}/{path}"
        if query:
            url = f"{url}?{query}"
        with urlopen(url, timeout=30) as response:  # noqa: S310
            payload = response.read().decode("utf-8")
        return json.loads(payload)
