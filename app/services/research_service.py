from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from pathlib import Path

from app.core.config import get_settings
from app.services.analyzers.conference_trend_analyzer import ConferenceTrendAnalyzer
from app.services.collectors.base import CollectedPaper
from app.services.collectors.aaai_source import AAAIProceedingsSource
from app.services.collectors.coling_source import ColingProceedingsSource
from app.services.collectors.icme_source import IcmeProceedingsSource
from app.services.collectors.openreview_source import OpenReviewPaperSource
from app.services.llm.client import LLMClient
from app.services.translators.google_translate import GoogleTranslateService
from app.workflows.nodes import (
    STAGE_LABELS,
    analyze_papers,
    collect_papers,
    generate_report,
)
from app.workflows.progress import ProgressEvent
from app.workflows.state import ResearchState


DEFAULT_FRONTEND_SETTINGS = {
    "openai_api_key": "",
    "openai_model": "gpt-4.1-mini",
    "openai_base_url": "",
    "report_output_dir": "reports",
}

STAGE_ORDER = [
    "collect_papers",
    "analyze_papers",
    "generate_report",
]

TRANSLATION_MAX_ATTEMPTS = 3
CONFERENCE_STAGE_LABELS = {
    "collect_papers": "抓取 Accepted 论文",
    "analyze_trends": "归纳热点趋势",
}


class ResearchService:
    def __init__(
        self,
        report_output_dir: str | Path | None = None,
        settings_path: str | Path | None = None,
    ) -> None:
        settings = get_settings()
        self._settings = settings
        output_dir = report_output_dir or settings.report_output_dir
        self._report_output_dir = Path(output_dir)
        self._settings_path = Path(settings_path or Path.cwd() / ".researchmind-settings.json")
        self._runs: dict[str, dict[str, object]] = {}
        self._lock = threading.Lock()
        self._translator = GoogleTranslateService()
        self._translation_cache: dict[tuple[str, str], str] = {}

    def run(
        self,
        *,
        topic: str,
        database: str = "pubmed",
        venues: list[str] | None = None,
        date_range: tuple[object, object] = (None, None),
        max_results: int = 5,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        openai_base_url: str | None = None,
        progress_callback: Callable[[ProgressEvent], None] | None = None,
    ) -> dict[str, object]:
        run_id = uuid.uuid4().hex
        return self._run_workflow(
            run_id=run_id,
            topic=topic,
            database=database,
            venues=venues,
            date_range=date_range,
            max_results=max_results,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            openai_base_url=openai_base_url,
            progress_callback=progress_callback,
        )

    def start_run(
        self,
        *,
        topic: str,
        database: str = "pubmed",
        venues: list[str] | None = None,
        date_range: tuple[object, object] = (None, None),
        max_results: int = 5,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        openai_base_url: str | None = None,
    ) -> dict[str, object]:
        self._validate_llm_inputs(openai_api_key=openai_api_key, openai_model=openai_model)
        run_id = uuid.uuid4().hex
        run_state = self._empty_run_state(
            run_id=run_id,
            topic=topic,
            database=database,
            date_range=date_range,
            max_results=max_results,
        )
        with self._lock:
            self._runs[run_id] = run_state

        thread = threading.Thread(
            target=self._collect_papers_only,
            kwargs={
                "run_id": run_id,
                "topic": topic,
                "database": database,
                "venues": list(venues or []),
                "date_range": date_range,
                "max_results": max_results,
                "openai_api_key": openai_api_key,
                "openai_model": openai_model,
                "openai_base_url": openai_base_url,
            },
            daemon=True,
        )
        thread.start()
        return self.get_run(run_id) or run_state

    def start_conference_trend_run(
        self,
        *,
        conference: str,
        year: int,
        limit: int = 100,
        tracks: list[str] | None = None,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        openai_base_url: str | None = None,
    ) -> dict[str, object]:
        self._validate_llm_inputs(openai_api_key=openai_api_key, openai_model=openai_model)
        run_id = uuid.uuid4().hex
        run_state = self._empty_conference_trend_state(
            run_id=run_id,
            conference=conference,
            year=year,
            limit=limit,
        )
        with self._lock:
            self._runs[run_id] = run_state

        thread = threading.Thread(
            target=self._run_conference_trend,
            kwargs={
                "run_id": run_id,
                "conference": conference,
                "year": year,
                "limit": limit,
                "tracks": list(tracks or []),
                "openai_api_key": openai_api_key,
                "openai_model": openai_model,
                "openai_base_url": openai_base_url,
            },
            daemon=True,
        )
        thread.start()
        return self.get_run(run_id) or run_state

    def list_conference_tracks(self, *, conference: str, year: int) -> list[dict[str, str]]:
        alias = conference.strip().lower()
        if alias != "aaai":
            return []
        tracks = AAAIProceedingsSource().list_tracks(year)
        return [
            {
                "track_id": item.track_id,
                "title": item.title,
                "url": item.url,
                "theme": item.theme,
                "series": item.series,
            }
            for item in tracks
        ]

    def get_run(self, run_id: str) -> dict[str, object] | None:
        with self._lock:
            run = self._runs.get(run_id)
            return dict(run) if run is not None else None

    def get_report(self, run_id: str) -> dict[str, object] | None:
        run = self.get_run(run_id)
        if run is None or not run.get("report_markdown"):
            return None
        return {
            "run_id": run["run_id"],
            "topic": run["topic"],
            "report_markdown": run["report_markdown"],
            "report_path": run["latest_report_path"],
            "report_artifact_path": run["report_path"],
        }

    def set_selected_papers(self, run_id: str, source_ids: list[str]) -> dict[str, object] | None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            run["selected_source_ids"] = list(source_ids)
            selected = set(source_ids)
            run["selected_papers"] = [paper for paper in run.get("papers", []) if paper.source_id in selected]
            return dict(run)

    def analyze_selected_run(
        self,
        run_id: str,
        *,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        openai_base_url: str | None = None,
    ) -> dict[str, object] | None:
        self._validate_llm_inputs(openai_api_key=openai_api_key, openai_model=openai_model)
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            selected = list(run.get("selected_papers") or run.get("papers") or [])
            topic = str(run.get("topic", ""))
            database = str(run.get("database", "pubmed"))
            date_range = run.get("date_range", (None, None))
            max_results = int(run.get("max_results", 5))
            venues = list(run.get("venues", []))
        if not selected:
            with self._lock:
                run = self._runs.get(run_id)
                if run is not None:
                    run["status"] = "awaiting_selection"
                    run["current_message"] = "请先在前端勾选需要分析的论文。"
            return self.get_run(run_id)

        thread = threading.Thread(
            target=self._analyze_and_generate,
            kwargs={
                "run_id": run_id,
                "topic": topic,
                "database": database,
                "selected_papers": selected,
                "venues": venues,
                "date_range": date_range,
                "max_results": max_results,
                "openai_api_key": openai_api_key,
                "openai_model": openai_model,
                "openai_base_url": openai_base_url,
            },
            daemon=True,
        )
        thread.start()
        return self.get_run(run_id)

    def list_papers(self) -> list[dict[str, object]]:
        papers: list[dict[str, object]] = []
        with self._lock:
            runs = list(self._runs.values())
        for run in runs:
            for paper in run.get("papers", []):
                papers.append(
                    {
                        "source_id": paper.source_id,
                        "source": paper.source,
                        "title": paper.title,
                        "title_zh": self._display_title_translation(paper),
                        "authors": paper.authors,
                        "abstract": paper.abstract,
                        "abstract_zh": paper.abstract_zh,
                        "year": paper.year,
                        "venue": paper.venue,
                        "url": paper.url,
                        "pdf_url": paper.pdf_url,
                        "keywords": paper.keywords,
                        "published_at": paper.published_at,
                    }
                )
        return papers

    def get_settings(self) -> dict[str, str]:
        if not self._settings_path.exists():
            return dict(DEFAULT_FRONTEND_SETTINGS)
        payload = json.loads(self._settings_path.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_FRONTEND_SETTINGS)
        for key in merged:
            if key in payload:
                merged[key] = str(payload[key])
        return merged

    def save_settings(self, payload: dict[str, object]) -> dict[str, str]:
        merged = dict(DEFAULT_FRONTEND_SETTINGS)
        for key in merged:
            if key in payload:
                merged[key] = str(payload[key])
        self._settings_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return merged

    def _build_llm_client(
        self,
        *,
        openai_api_key: str | None,
        openai_model: str | None,
        openai_base_url: str | None = None,
    ):
        self._validate_llm_inputs(openai_api_key=openai_api_key, openai_model=openai_model)
        api_key = (openai_api_key or "").strip()
        model = (openai_model or "").strip()
        base_url = (openai_base_url or self._settings.openai_base_url or "").strip() or None
        return LLMClient(api_key=api_key, model=model, base_url=base_url)

    def _validate_llm_inputs(self, *, openai_api_key: str | None, openai_model: str | None) -> None:
        if not (openai_api_key or "").strip():
            raise ValueError("OpenAI API key is required.")
        if not (openai_model or "").strip():
            raise ValueError("OpenAI model is required.")

    def _run_workflow(
        self,
        *,
        run_id: str,
        topic: str,
        database: str,
        venues: list[str] | None,
        date_range: tuple[object, object],
        max_results: int,
        openai_api_key: str | None,
        openai_model: str | None,
        openai_base_url: str | None,
        progress_callback: Callable[[ProgressEvent], None] | None,
    ) -> dict[str, object]:
        llm_client = self._build_llm_client(
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            openai_base_url=openai_base_url,
        )
        state = ResearchState(
            topic=topic,
            database=database,
            venues=list(venues or []),
            date_range=date_range,
            max_results=max_results,
        )
        result = collect_papers(state, progress_callback=progress_callback)
        result.papers = self._attach_localized_metadata(result.papers)
        result = analyze_papers(result, llm_client=llm_client, progress_callback=progress_callback)
        result = generate_report(result, progress_callback=progress_callback)
        report_paths = self._write_report(run_id, result.report_markdown)
        payload = {
            "run_id": run_id,
            "topic": result.topic,
            "status": "completed" if not result.errors else "failed",
            "database": result.database,
            "venues": result.venues,
            "date_range": date_range,
            "start_date": date_range[0],
            "end_date": date_range[1],
            "max_results": max_results,
            "report_markdown": result.report_markdown,
            "report_path": str(report_paths["artifact"]),
            "latest_report_path": str(report_paths["latest"]),
            "papers": result.papers,
            "trend_snapshot": result.trend_snapshot,
            "research_gaps": result.research_gaps,
            "errors": result.errors,
        }
        with self._lock:
            existing = self._runs.get(run_id)
            if existing is not None and "stages" in existing:
                existing.update(payload)
                return dict(existing)
            self._runs[run_id] = payload
        return payload

    def _collect_papers_only(
        self,
        *,
        run_id: str,
        topic: str,
        database: str,
        venues: list[str],
        date_range: tuple[object, object],
        max_results: int,
        openai_api_key: str | None,
        openai_model: str | None,
        openai_base_url: str | None,
    ) -> None:
        def on_progress(event: ProgressEvent) -> None:
            with self._lock:
                run = self._runs[run_id]
                run["status"] = "running"
                run["current_message"] = event.message
                for stage in run["stages"]:
                    if stage["stage_key"] == event.stage_key:
                        stage["status"] = event.status
                        stage["message"] = event.message
                        stage["current"] = event.current
                        stage["total"] = event.total
                        break

        try:
            llm_client = self._build_llm_client(
                openai_api_key=openai_api_key,
                openai_model=openai_model,
                openai_base_url=openai_base_url,
            )
            state = ResearchState(
                topic=topic,
                database=database,
                venues=venues,
                date_range=date_range,
                max_results=max_results,
            )
            current = collect_papers(state, progress_callback=on_progress)
            current.papers = self._attach_localized_metadata(current.papers)
        except Exception as exc:
            with self._lock:
                run = self._runs[run_id]
                run["status"] = "failed"
                run["current_message"] = str(exc)
                run["errors"] = [str(exc)]
            return

        with self._lock:
            run = self._runs[run_id]
            run["status"] = "awaiting_selection"
            run["current_message"] = "论文抓取完成，请在前端勾选需要分析的论文。"
            run["papers"] = current.papers
            run["database"] = database
            run["errors"] = list(current.errors)
            run["selected_papers"] = list(current.papers)
            run["date_range"] = date_range
            run["start_date"] = date_range[0]
            run["end_date"] = date_range[1]
            run["max_results"] = max_results
            run["venues"] = venues
            run["selected_source_ids"] = [paper.source_id for paper in current.papers]
            for stage in run["stages"]:
                if stage["stage_key"] == "collect_papers":
                    stage["status"] = "completed"
                    stage["current"] = len(current.papers)
                    stage["total"] = len(current.papers)
                    stage["message"] = f"已抓取并筛选 {len(current.papers)} 篇论文"
                else:
                    stage["status"] = "pending"
                    stage["message"] = ""
                    stage["current"] = 0
                    stage["total"] = 0

    def _analyze_and_generate(
        self,
        *,
        run_id: str,
        topic: str,
        database: str,
        selected_papers: list[object],
        venues: list[str],
        date_range: tuple[object, object],
        max_results: int,
        openai_api_key: str | None,
        openai_model: str | None,
        openai_base_url: str | None,
    ) -> None:
        def on_progress(event: ProgressEvent) -> None:
            with self._lock:
                run = self._runs[run_id]
                run["status"] = "running"
                run["current_message"] = event.message
                for stage in run["stages"]:
                    if stage["stage_key"] == event.stage_key:
                        stage["status"] = event.status
                        stage["message"] = event.message
                        stage["current"] = event.current
                        stage["total"] = event.total
                        break

        try:
            llm_client = self._build_llm_client(
                openai_api_key=openai_api_key,
                openai_model=openai_model,
                openai_base_url=openai_base_url,
            )
            state = ResearchState(
                topic=topic,
                database=database,
                venues=venues,
                date_range=date_range,
                max_results=max_results,
            )
            state.papers = selected_papers  # type: ignore[assignment]
            state.papers = self._attach_localized_metadata(state.papers)
            current = analyze_papers(state, llm_client=llm_client, progress_callback=on_progress)
            current = generate_report(current, progress_callback=on_progress)
            report_paths = self._write_report(run_id, current.report_markdown)
        except Exception as exc:
            with self._lock:
                run = self._runs[run_id]
                run["status"] = "failed"
                run["current_message"] = str(exc)
                run["errors"] = [str(exc)]
            return

        with self._lock:
            run = self._runs[run_id]
            run["status"] = "completed" if not current.errors else "failed"
            run["current_message"] = "报告生成完成" if not current.errors else "运行失败"
            run["database"] = database
            run["report_markdown"] = current.report_markdown
            run["latest_report_path"] = str(report_paths["latest"])
            run["report_path"] = str(report_paths["artifact"])
            run["papers"] = current.papers
            run["trend_snapshot"] = current.trend_snapshot
            run["research_gaps"] = current.research_gaps
            run["errors"] = current.errors
            for stage in run["stages"]:
                if stage["stage_key"] in {"analyze_papers", "generate_report"}:
                    stage["status"] = "completed" if not current.errors else "failed"

    def _run_conference_trend(
        self,
        *,
        run_id: str,
        conference: str,
        year: int,
        limit: int,
        tracks: list[str],
        openai_api_key: str | None,
        openai_model: str | None,
        openai_base_url: str | None,
    ) -> None:
        def set_stage(stage_key: str, *, status: str, message: str, current: int = 0, total: int = 0) -> None:
            with self._lock:
                run = self._runs[run_id]
                run["status"] = "running" if status == "running" else run["status"]
                run["current_message"] = message
                for stage in run["stages"]:
                    if stage["stage_key"] == stage_key:
                        stage["status"] = status
                        stage["message"] = message
                        stage["current"] = current
                        stage["total"] = total
                        break

        try:
            set_stage("collect_papers", status="running", message="正在抓取会议 accepted 论文")
            papers = self._fetch_conference_papers(conference=conference, year=year, limit=limit, tracks=tracks)
            if not papers:
                raise ValueError("未抓取到任何 accepted 论文。")
            set_stage(
                "collect_papers",
                status="completed",
                message=f"已抓取 {len(papers)} 篇 accepted 论文",
                current=len(papers),
                total=len(papers),
            )
            set_stage("analyze_trends", status="running", message="正在归纳会议热点趋势")
            llm_client = self._build_llm_client(
                openai_api_key=openai_api_key,
                openai_model=openai_model,
                openai_base_url=openai_base_url,
            )
            result = ConferenceTrendAnalyzer(llm_client).analyze(
                conference=conference,
                year=year,
                papers=papers,
            )
        except Exception as exc:
            with self._lock:
                run = self._runs[run_id]
                run["status"] = "failed"
                run["current_message"] = str(exc)
                run["errors"] = [str(exc)]
            return

        with self._lock:
            run = self._runs[run_id]
            run["status"] = "completed"
            run["current_message"] = "会议趋势分析完成"
            run["papers"] = papers
            run["trend_snapshot"] = {
                "summary": result.summary,
                "hot_methods": result.hot_methods,
                "hot_applications": result.hot_applications,
                "emerging_signals": result.emerging_signals,
                "paper_count": len(papers),
            }
            for stage in run["stages"]:
                if stage["stage_key"] == "analyze_trends":
                    stage["status"] = "completed"
                    stage["message"] = "热点趋势归纳完成"
                    stage["current"] = len(papers)
                    stage["total"] = len(papers)

    def _empty_run_state(
        self,
        *,
        run_id: str,
        topic: str,
        database: str = "pubmed",
        date_range: tuple[object, object] = (None, None),
        max_results: int = 5,
    ) -> dict[str, object]:
        return {
            "run_id": run_id,
            "topic": topic,
            "database": database,
            "status": "pending",
            "current_message": "",
            "date_range": date_range,
            "start_date": date_range[0],
            "end_date": date_range[1],
            "max_results": max_results,
            "stages": [
                {
                    "stage_key": stage_key,
                    "stage_label": STAGE_LABELS[stage_key],
                    "status": "pending",
                    "message": "",
                    "current": 0,
                    "total": 0,
                }
                for stage_key in STAGE_ORDER
            ],
            "errors": [],
            "latest_report_path": None,
            "report_path": None,
            "report_markdown": "",
            "papers": [],
            "selected_papers": [],
            "selected_source_ids": [],
            "trend_snapshot": None,
            "research_gaps": [],
        }

    def _empty_conference_trend_state(
        self,
        *,
        run_id: str,
        conference: str,
        year: int,
        limit: int,
    ) -> dict[str, object]:
        return {
            "run_id": run_id,
            "run_kind": "conference_trend",
            "conference": conference,
            "year": year,
            "topic": f"{conference} {year}",
            "database": conference,
            "tracks": [],
            "status": "pending",
            "current_message": "",
            "max_results": limit,
            "stages": [
                {
                    "stage_key": stage_key,
                    "stage_label": stage_label,
                    "status": "pending",
                    "message": "",
                    "current": 0,
                    "total": 0,
                }
                for stage_key, stage_label in CONFERENCE_STAGE_LABELS.items()
            ],
            "errors": [],
            "papers": [],
            "trend_snapshot": None,
        }

    def _fetch_conference_papers(self, *, conference: str, year: int, limit: int, tracks: list[str]) -> list[CollectedPaper]:
        alias = conference.strip().lower()
        if alias == "aaai":
            if not tracks:
                raise ValueError("请先选择至少一个 AAAI track。")
            return AAAIProceedingsSource().fetch(year=year, track_ids=tracks, limit=limit)
        if alias == "coling":
            return ColingProceedingsSource().fetch(year=year, limit=limit)
        if alias == "icme":
            return IcmeProceedingsSource().fetch(year=year, limit=limit)
        return OpenReviewPaperSource().fetch(conference, year=year, limit=limit)

    def _write_report(self, run_id: str, report_markdown: str) -> dict[str, Path]:
        self._report_output_dir.mkdir(parents=True, exist_ok=True)
        latest_path = self._report_output_dir / "weekly_report.md"
        artifact_path = self._report_output_dir / f"weekly_report_{run_id}.md"
        latest_path.write_text(report_markdown, encoding="utf-8")
        artifact_path.write_text(report_markdown, encoding="utf-8")
        return {"latest": latest_path, "artifact": artifact_path}

    def _attach_translated_titles(self, papers: list[CollectedPaper]) -> list[CollectedPaper]:
        return self._attach_localized_metadata(papers)

    def _attach_localized_metadata(self, papers: list[CollectedPaper]) -> list[CollectedPaper]:
        for paper in papers:
            if paper.title_zh:
                paper.title_zh = paper.title_zh.strip()
            else:
                paper.title_zh = self._translate_title(paper.title)
            if not paper.abstract_zh:
                paper.abstract_zh = self._translate_abstract(paper.abstract)
            paper.title_zh = self._display_title_translation(paper)
            paper.abstract_zh = paper.abstract_zh.strip()
        return papers

    def _translate_title(self, title: str) -> str:
        return self._translate_text(title, field="title")

    def _translate_abstract(self, abstract: str) -> str:
        return self._translate_text(abstract, field="abstract")

    def _translate_text(self, text: str, *, field: str) -> str:
        normalized = text.strip()
        if not normalized:
            return ""
        if field == "title" and self._contains_cjk(normalized):
            return normalized
        cache_key = (field, normalized)
        cached = self._translation_cache.get(cache_key)
        if cached is not None:
            return cached
        translated = ""
        for _ in range(TRANSLATION_MAX_ATTEMPTS):
            try:
                translated = self._translator.translate(normalized)
                if translated.strip():
                    break
            except Exception:
                translated = ""
        translated = translated.strip()
        if translated == normalized:
            translated = ""
        self._translation_cache[cache_key] = translated
        return translated

    def _display_title_translation(self, paper: CollectedPaper) -> str:
        translated = paper.title_zh.strip()
        if translated:
            return translated
        if self._contains_cjk(paper.title):
            return paper.title.strip()
        return "中文标题翻译暂不可用"

    def _contains_cjk(self, text: str) -> bool:
        return any("\u4e00" <= char <= "\u9fff" for char in text)
