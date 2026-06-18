from __future__ import annotations

from datetime import date
from importlib import import_module

from app.services.collectors.base import CollectedPaper


class ArxivPaperSource:
    SOURCE_NAME = "arxiv"
    _MIN_QUERY_DATE = "000101010000"
    _MAX_QUERY_DATE = "300001010000"

    def __init__(self, limit: int = 5) -> None:
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

        arxiv = self._load_arxiv_module()
        effective_limit = limit or self._limit
        client = arxiv.Client()
        search = arxiv.Search(
            query=self._build_query(normalized_topic, start_date=start_date, end_date=end_date),
            max_results=effective_limit,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers: list[CollectedPaper] = []
        for result in client.results(search):
            paper = self._build_paper(result)
            if paper is None:
                continue
            papers.append(paper)
            if len(papers) >= effective_limit:
                break
        return papers

    def _load_arxiv_module(self):
        try:
            return import_module("arxiv")
        except ModuleNotFoundError as exc:
            raise RuntimeError("arXiv support requires the 'arxiv' package. Please install the 'arxiv' package and try again.") from exc

    def _build_query(
        self,
        topic: str,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> str:
        topic_query = self._build_topic_query(topic)
        if start_date is None and end_date is None:
            return topic_query

        range_start = self._format_query_date(start_date, is_end=False) if start_date is not None else self._MIN_QUERY_DATE
        range_end = self._format_query_date(end_date, is_end=True) if end_date is not None else self._MAX_QUERY_DATE
        return f"{topic_query} AND submittedDate:[{range_start} TO {range_end}]"

    def _build_topic_query(self, topic: str) -> str:
        terms = [" ".join(part.split()) for part in topic.split() if part.strip()]
        if not terms:
            return topic
        if len(terms) == 1:
            return f"all:{terms[0]}"
        return "(" + " AND ".join(f"all:{term}" for term in terms) + ")"

    def _format_query_date(self, value: date, *, is_end: bool) -> str:
        suffix = "2359" if is_end else "0000"
        return f"{value:%Y%m%d}{suffix}"

    def _build_paper(self, result) -> CollectedPaper | None:
        entry_id = str(getattr(result, "entry_id", "")).strip()
        title = " ".join(str(getattr(result, "title", "")).split()).strip()
        abstract = " ".join(str(getattr(result, "summary", "")).split()).strip()
        if not entry_id or not title or not abstract:
            return None

        published_raw = getattr(result, "published", None)
        published_at = published_raw if isinstance(published_raw, date) else None
        authors = []
        for item in getattr(result, "authors", []) or []:
            name = str(getattr(item, "name", "")).strip()
            if name:
                authors.append(name)
        categories = []
        for item in getattr(result, "categories", []) or []:
            category = str(getattr(item, "category", item)).strip()
            if category and category not in categories:
                categories.append(category)

        source_id = entry_id.rsplit("/", 1)[-1]
        return CollectedPaper(
            source_id=source_id,
            title=title,
            authors=authors,
            abstract=abstract,
            year=published_at.year if published_at is not None else 0,
            venue="arXiv",
            url=entry_id,
            pdf_url=f"https://arxiv.org/pdf/{source_id}.pdf",
            keywords=categories[:12],
            source=self.SOURCE_NAME,
            published_at=published_at,
        )
