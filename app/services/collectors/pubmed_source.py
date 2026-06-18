from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from app.services.collectors.base import CollectedPaper


class PubMedPaperSource:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, base_url: str | None = None, limit: int = 5) -> None:
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._limit = limit

    def fetch(
        self,
        topic: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
    ) -> list[CollectedPaper]:
        normalized_topic = topic.strip()
        if not normalized_topic:
            return []

        effective_limit = limit or self._limit
        candidate_limit = max(effective_limit * 3, effective_limit)
        query = self._build_topic_query(normalized_topic)
        merged_ids = self._search_ids(
            query,
            sort="relevance",
            limit=candidate_limit,
            start_date=start_date,
            end_date=end_date,
        )[:candidate_limit]
        if not merged_ids:
            return []

        summaries = self._fetch_summaries(merged_ids)
        details = self._fetch_article_details(merged_ids)
        papers: list[CollectedPaper] = []

        for pmid in merged_ids:
            detail = details.get(pmid, {})
            paper = self._build_paper(
                pmid=pmid,
                summary=summaries.get(pmid, {}),
                abstract=str(detail.get("abstract", "")),
                keywords=list(detail.get("keywords", []) or []),
                published_at=detail.get("published_at"),
            )
            if paper is not None:
                papers.append(paper)
            if len(papers) >= effective_limit:
                break

        return papers

    def _build_topic_query(self, topic: str) -> str:
        terms = [token.strip() for token in re.findall(r"[A-Za-z0-9-]+", topic) if token.strip()]
        if not terms:
            return topic.strip()
        if len(terms) == 1:
            return f"{terms[0]}[Title/Abstract]"
        return "(" + " AND ".join(f"{term}[Title/Abstract]" for term in terms) + ")"

    def _search_ids(
        self,
        topic: str,
        sort: str,
        limit: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[str]:
        params: dict[str, object] = {
            "db": "pubmed",
            "term": topic,
            "retmode": "json",
            "retmax": limit,
            "sort": sort,
            "tool": "researchmind",
        }
        if start_date is not None:
            params["mindate"] = start_date.strftime("%Y/%m/%d")
        if end_date is not None:
            params["maxdate"] = end_date.strftime("%Y/%m/%d")
        if start_date is not None or end_date is not None:
            params["datetype"] = "pdat"

        payload = self._get_json(
            "esearch.fcgi",
            params,
        )
        id_list = payload.get("esearchresult", {}).get("idlist", [])
        return [str(item) for item in id_list if str(item).strip()]

    def _fetch_summaries(self, pmids: list[str]) -> dict[str, dict[str, Any]]:
        if not pmids:
            return {}

        payload = self._get_json(
            "esummary.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
                "tool": "researchmind",
            },
        )
        result = payload.get("result", {})
        summaries: dict[str, dict[str, Any]] = {}
        for pmid in pmids:
            item = result.get(str(pmid), {})
            if isinstance(item, dict):
                summaries[str(pmid)] = item
        return summaries

    def _fetch_article_details(
        self,
        pmids: list[str],
        xml_text: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        if not pmids:
            return {}

        if xml_text is None:
            xml_text = self._get_text(
                "efetch.fcgi",
                {
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "retmode": "xml",
                    "rettype": "abstract",
                    "tool": "researchmind",
                },
            )
        root = ET.fromstring(xml_text)
        details: dict[str, dict[str, Any]] = {}
        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//MedlineCitation/PMID", default="").strip()
            if not pmid:
                continue
            segments: list[str] = []
            for node in article.findall(".//Abstract/AbstractText"):
                text = "".join(node.itertext()).strip()
                if text:
                    label = (node.attrib.get("Label") or "").strip()
                    segments.append(f"{label}: {text}" if label else text)
            details[pmid] = {
                "abstract": "\n".join(segments).strip(),
                "keywords": self._extract_keywords(article),
                "published_at": self._extract_journal_publication_date(article),
            }
        return details

    def _fetch_abstracts(self, pmids: list[str]) -> dict[str, str]:
        return {
            pmid: str(payload.get("abstract", "")).strip()
            for pmid, payload in self._fetch_article_details(pmids).items()
        }

    def _build_paper(
        self,
        *,
        pmid: str,
        summary: dict[str, Any],
        abstract: str,
        keywords: list[str] | None = None,
        published_at: date | None = None,
    ) -> CollectedPaper | None:
        title = str(summary.get("title", "")).strip()
        normalized_abstract = abstract.strip()
        if not title or not normalized_abstract:
            return None

        journal = str(summary.get("source", "")).strip() or "PubMed"
        authors = self._extract_authors(summary.get("authors", []))
        summary_pubdate = self._extract_publication_date(str(summary.get("pubdate", "")).strip())
        publication_date = published_at or summary_pubdate
        if summary_pubdate is not None:
            publication_date = summary_pubdate
        year = publication_date.year if publication_date is not None else self._extract_year(str(summary.get("pubdate", "")).strip())
        return CollectedPaper(
            source_id=pmid,
            title=title,
            authors=authors,
            abstract=normalized_abstract,
            year=year,
            venue=journal,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            pdf_url="",
            keywords=keywords or self._infer_keywords(title, normalized_abstract),
            source="pubmed",
            published_at=publication_date,
        )

    def _extract_authors(self, raw_authors: Any) -> list[str]:
        authors: list[str] = []
        if not isinstance(raw_authors, list):
            return authors
        for item in raw_authors:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if name:
                authors.append(name)
        return authors

    def _extract_year(self, pubdate: str) -> int:
        match = re.search(r"(19|20)\d{2}", pubdate)
        if match:
            return int(match.group(0))
        return 0

    def _extract_publication_date(self, pubdate: str) -> date | None:
        match = re.search(r"(?P<year>(19|20)\d{2})\s+(?P<month>[A-Za-z]{3,})\s+(?P<day>\d{1,2})", pubdate)
        if not match:
            return None

        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        month = month_map.get(match.group("month")[:3].lower())
        if month is None:
            return None
        try:
            return date(int(match.group("year")), month, int(match.group("day")))
        except ValueError:
            return None

    def _extract_journal_publication_date(self, article: ET.Element) -> date | None:
        date_node = article.find(".//JournalIssue/PubDate")
        if date_node is None:
            return None

        year_text = (date_node.findtext("Year") or "").strip()
        month_text = (date_node.findtext("Month") or "").strip()
        day_text = (date_node.findtext("Day") or "").strip()

        if not year_text:
            medline_date = (date_node.findtext("MedlineDate") or "").strip()
            return self._extract_publication_date(medline_date)

        year = int(year_text) if year_text.isdigit() else None
        month = self._parse_month_token(month_text) if month_text else None
        day = int(day_text) if day_text.isdigit() else None

        if year is None or month is None or day is None:
            return None

        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _parse_month_token(self, token: str) -> int | None:
        month_map = {
            "1": 1,
            "01": 1,
            "jan": 1,
            "january": 1,
            "2": 2,
            "02": 2,
            "feb": 2,
            "february": 2,
            "3": 3,
            "03": 3,
            "mar": 3,
            "march": 3,
            "4": 4,
            "04": 4,
            "apr": 4,
            "april": 4,
            "5": 5,
            "05": 5,
            "may": 5,
            "6": 6,
            "06": 6,
            "jun": 6,
            "june": 6,
            "7": 7,
            "07": 7,
            "jul": 7,
            "july": 7,
            "8": 8,
            "08": 8,
            "aug": 8,
            "august": 8,
            "9": 9,
            "09": 9,
            "sep": 9,
            "sept": 9,
            "september": 9,
            "10": 10,
            "oct": 10,
            "october": 10,
            "11": 11,
            "nov": 11,
            "november": 11,
            "12": 12,
            "dec": 12,
            "december": 12,
        }
        return month_map.get(token.strip().lower())

    def _extract_keywords(self, article: ET.Element) -> list[str]:
        keywords: list[str] = []
        for node in article.findall(".//KeywordList/Keyword"):
            value = " ".join("".join(node.itertext()).split()).strip()
            if value and value not in keywords:
                keywords.append(value)
        for node in article.findall(".//MeshHeadingList/MeshHeading/DescriptorName"):
            value = " ".join("".join(node.itertext()).split()).strip()
            if value and value not in keywords:
                keywords.append(value)
        return keywords[:12]

    def _infer_keywords(self, title: str, abstract: str) -> list[str]:
        phrases: list[str] = []
        for segment in re.split(r"[:;,.()\-]", title):
            normalized = " ".join(segment.split()).strip()
            if len(normalized) >= 4 and normalized not in phrases:
                phrases.append(normalized)
        tokens: list[str] = []
        for candidate in re.findall(r"[a-zA-Z0-9-]+", f"{title} {abstract}".lower()):
            normalized = candidate.strip("-")
            if len(normalized) <= 3 or normalized in tokens:
                continue
            tokens.append(normalized)
            if len(tokens) >= 6:
                break
        return [*phrases[:6], *[token for token in tokens if token not in phrases]][:12]

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        with urlopen(f"{self._base_url}/{path}?{urlencode(params)}", timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_text(self, path: str, params: dict[str, Any]) -> str:
        with urlopen(f"{self._base_url}/{path}?{urlencode(params)}", timeout=20) as response:
            return response.read().decode("utf-8")
