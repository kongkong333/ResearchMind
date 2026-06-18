from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.services.research_service import ResearchService
from app.services.collectors.arxiv_source import ArxivPaperSource
from app.services.collectors.pubmed_source import PubMedPaperSource


@pytest.fixture(autouse=True)
def _stub_google_translate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.translators.google_translate.GoogleTranslateService.translate",
        lambda self, text, **kwargs: "",
    )


class _FakeLLMClient:
    def generate_structured(self, *, prompt: str, schema: dict) -> dict:
        del prompt
        if "gaps" in schema.get("required", []):
            return {
                "gaps": [
                    {
                        "title": "Long-term evaluation",
                        "description": "缺少持续性和部署场景下的验证。",
                        "opportunity": "补齐真实任务与长期记忆评估。",
                    }
                ],
                "summary": "可优先关注真实环境中的长期评测与鲁棒性。",
            }
        return {
            "problem": "研究复杂任务中的 agent 协作问题。",
            "method": "提出面向规划与记忆的工作流方法。",
            "innovation": "统一规划、记忆与执行回路。",
            "results": "在代表性任务上取得稳定增益。",
            "limitations": "缺少更长周期的线上评估。",
            "research_gap": "缺少真实场景和长期运行验证。",
            "research_opportunity": "面向真实工作流构建长期记忆与鲁棒性评测。",
        }


class _InspectablePubMedSource:
    def __init__(self) -> None:
        self.queries: list[tuple[str, dict[str, object]]] = []

    def _get_json(self, path: str, params: dict[str, object]) -> dict[str, object]:
        self.queries.append((path, params))
        if path == "esearch.fcgi":
            return {"esearchresult": {"idlist": []}}
        return {"result": {}}

    def _get_text(self, path: str, params: dict[str, object]) -> str:
        self.queries.append((path, params))
        return "<root />"

class _InlineGraph:
    def __init__(self, callback):
        self._callback = callback

    def invoke(self, state):
        self._callback(
            type(
                "Event",
                (),
                {
                    "stage_key": "collect_papers",
                    "stage_label": "抓取论文",
                    "status": "running",
                    "message": "已开始抓取",
                    "current": 0,
                    "total": 0,
                },
            )()
        )
        self._callback(
            type(
                "Event",
                (),
                {
                    "stage_key": "collect_papers",
                    "stage_label": "抓取论文",
                    "status": "completed",
                    "message": "抓取完成",
                    "current": 1,
                    "total": 1,
                },
            )()
        )
        return type(
            "Result",
            (),
            {
                "run_id": "ignored",
                "topic": state.topic,
                "venues": [],
                "report_markdown": "# 研究报告",
                "papers": [],
                "trend_snapshot": None,
                "research_gaps": [],
                "errors": [],
            },
        )()


def test_research_service_run_writes_weekly_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ResearchService(report_output_dir=tmp_path)
    monkeypatch.setattr(service, "_build_llm_client", lambda **kwargs: _FakeLLMClient())

    result = service.run(topic="agent systems", openai_api_key="test-key", openai_model="gpt-4.1-mini")

    report_path = tmp_path / "weekly_report.md"
    assert report_path.exists()
    assert Path(result["report_path"]).exists()
    assert Path(result["report_path"]).name != "weekly_report.md"
    assert report_path.read_text(encoding="utf-8") == result["report_markdown"]
    assert result["report_markdown"].startswith("# 研究报告")
    assert result["run_id"]


def test_research_service_run_keeps_unique_report_file_per_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ResearchService(report_output_dir=tmp_path)
    monkeypatch.setattr(service, "_build_llm_client", lambda **kwargs: _FakeLLMClient())

    first = service.run(topic="agent systems", openai_api_key="test-key", openai_model="gpt-4.1-mini")
    second = service.run(topic="agent systems", openai_api_key="test-key", openai_model="gpt-4.1-mini")

    assert first["report_path"] != second["report_path"]
    assert Path(first["report_path"]).exists()
    assert Path(second["report_path"]).exists()


def test_research_service_run_requires_openai_api_key(tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path)

    with pytest.raises(ValueError, match="OpenAI API key"):
        service.run(topic="agent systems", openai_api_key="", openai_model="gpt-4.1-mini")


def test_research_service_run_requires_openai_model(tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path)

    with pytest.raises(ValueError, match="OpenAI model"):
        service.run(topic="agent systems", openai_api_key="test-key", openai_model="")


def test_research_service_list_papers_has_no_hidden_run_side_effect(tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path)

    papers = service.list_papers()

    assert papers == []
    assert service._runs == {}
    assert not (tmp_path / "weekly_report.md").exists()


def test_research_service_build_llm_client_passes_explicit_base_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ResearchService(report_output_dir=tmp_path)
    captured: dict[str, str | None] = {}

    class FakeLLMClient:
        def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
            captured["api_key"] = api_key
            captured["model"] = model
            captured["base_url"] = base_url

    monkeypatch.setattr("app.services.research_service.LLMClient", FakeLLMClient)

    service._build_llm_client(
        openai_api_key="qwen-key",
        openai_model="qwen-plus",
        openai_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    assert captured == {
        "api_key": "qwen-key",
        "model": "qwen-plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }


def test_research_service_build_llm_client_uses_settings_base_url_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ResearchService(report_output_dir=tmp_path)
    service._settings.openai_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    captured: dict[str, str | None] = {}

    class FakeLLMClient:
        def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
            captured["api_key"] = api_key
            captured["model"] = model
            captured["base_url"] = base_url

    monkeypatch.setattr("app.services.research_service.LLMClient", FakeLLMClient)

    service._build_llm_client(
        openai_api_key="qwen-key",
        openai_model="qwen-plus",
    )

    assert captured["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_get_settings_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path / "reports", settings_path=tmp_path / "ui-settings.json")

    payload = service.get_settings()

    assert payload["openai_api_key"] == ""
    assert payload["openai_model"] == "gpt-4.1-mini"
    assert payload["report_output_dir"] == "reports"


def test_save_settings_persists_values(tmp_path: Path) -> None:
    settings_path = tmp_path / "ui-settings.json"
    service = ResearchService(report_output_dir=tmp_path / "reports", settings_path=settings_path)

    service.save_settings(
        {
            "openai_api_key": "sk-test",
            "openai_model": "qwen3-plus",
            "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "report_output_dir": "custom-reports",
        }
    )

    restored = service.get_settings()

    assert restored["openai_api_key"] == "sk-test"
    assert restored["openai_model"] == "qwen3-plus"
    assert restored["report_output_dir"] == "custom-reports"
    assert settings_path.exists()


def test_start_run_creates_pending_run_and_tracks_completion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path / "reports", settings_path=tmp_path / "settings.json")
    monkeypatch.setattr(service, "_build_llm_client", lambda **_: object())
    monkeypatch.setattr(
        ArxivPaperSource,
        "fetch",
        lambda self, topic, **kwargs: [
            __import__("app.services.collectors.base", fromlist=["CollectedPaper"]).CollectedPaper(
                source_id="1",
                title="AI Agent Planning",
                authors=["Ada"],
                abstract="Planning agents.",
                year=2026,
                venue="PubMed",
                url="https://example.com/1",
                keywords=["agent", "planning"],
            )
        ],
    )

    created = service.start_run(
        topic="AI Agent",
        database="arxiv",
        venues=[],
        date_range=(None, None),
        openai_api_key="sk-test",
        openai_model="qwen3-plus",
        openai_base_url="",
    )

    for _ in range(100):
        run = service.get_run(created["run_id"])
        if run and run["status"] == "awaiting_selection":
            break
        time.sleep(0.02)
    else:
        run = service.get_run(created["run_id"])

    assert run is not None
    assert run["topic"] == "AI Agent"
    assert run["database"] == "arxiv"
    assert run["status"] == "awaiting_selection"
    assert any(stage["stage_key"] == "collect_papers" for stage in run["stages"])


def test_start_run_translates_paper_titles_for_selection_stage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path / "reports", settings_path=tmp_path / "settings.json")
    monkeypatch.setattr(service, "_build_llm_client", lambda **_: object())
    monkeypatch.setattr(
        PubMedPaperSource,
        "fetch",
        lambda self, topic, **kwargs: [
            __import__("app.services.collectors.base", fromlist=["CollectedPaper"]).CollectedPaper(
                source_id="1",
                title="AI Agent Planning",
                authors=["Ada"],
                abstract="Planning agents.",
                year=2026,
                venue="PubMed",
                url="https://example.com/1",
                keywords=["agent", "planning"],
            )
        ],
    )
    monkeypatch.setattr(service, "_translate_title", lambda title: "AI 智能体规划" if title == "AI Agent Planning" else "")

    created = service.start_run(
        topic="AI Agent",
        venues=[],
        date_range=(None, None),
        openai_api_key="sk-test",
        openai_model="qwen3-plus",
        openai_base_url="",
    )

    for _ in range(100):
        run = service.get_run(created["run_id"])
        if run and run["status"] == "awaiting_selection":
            break
        time.sleep(0.02)
    else:
        run = service.get_run(created["run_id"])

    assert run is not None
    assert run["papers"][0].title_zh == "AI 智能体规划"


def test_start_run_translates_paper_abstracts_and_uses_title_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path / "reports", settings_path=tmp_path / "settings.json")
    monkeypatch.setattr(service, "_build_llm_client", lambda **_: object())
    monkeypatch.setattr(
        PubMedPaperSource,
        "fetch",
        lambda self, topic, **kwargs: [
            __import__("app.services.collectors.base", fromlist=["CollectedPaper"]).CollectedPaper(
                source_id="1",
                title="AI Agent Planning",
                authors=["Ada"],
                abstract="Planning agents.",
                year=2026,
                venue="PubMed",
                url="https://example.com/1",
                keywords=["agent", "planning"],
            )
        ],
    )

    def fake_translate(text: str, *, field: str) -> str:
        if field == "title":
            return ""
        if field == "abstract":
            return "智能体规划。"
        return ""

    monkeypatch.setattr(service, "_translate_text", fake_translate)

    created = service.start_run(
        topic="AI Agent",
        venues=[],
        date_range=(None, None),
        openai_api_key="sk-test",
        openai_model="qwen3-plus",
        openai_base_url="",
    )

    for _ in range(100):
        run = service.get_run(created["run_id"])
        if run and run["status"] == "awaiting_selection":
            break
        time.sleep(0.02)
    else:
        run = service.get_run(created["run_id"])

    assert run is not None
    assert run["papers"][0].title_zh == "中文标题翻译暂不可用"
    assert run["papers"][0].abstract_zh == "智能体规划。"


def test_list_papers_exposes_translated_title_when_available(tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path)
    paper = __import__("app.services.collectors.base", fromlist=["CollectedPaper"]).CollectedPaper(
        source_id="1",
        title="AI Agent Planning",
        title_zh="AI 智能体规划",
        abstract_zh="智能体规划。",
        authors=["Ada"],
        abstract="Planning agents.",
        year=2026,
        venue="PubMed",
        url="https://example.com/1",
        keywords=["agent", "planning"],
    )
    service._runs["run-1"] = {
        "papers": [paper],
    }

    papers = service.list_papers()

    assert papers[0]["title_zh"] == "AI 智能体规划"
    assert papers[0]["abstract_zh"] == "智能体规划。"


def test_list_papers_exposes_title_placeholder_when_translation_missing(tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path)
    paper = __import__("app.services.collectors.base", fromlist=["CollectedPaper"]).CollectedPaper(
        source_id="1",
        title="AI Agent Planning",
        title_zh="",
        abstract_zh="",
        authors=["Ada"],
        abstract="Planning agents.",
        year=2026,
        venue="PubMed",
        url="https://example.com/1",
        keywords=["agent", "planning"],
    )
    service._runs["run-1"] = {
        "papers": [paper],
    }

    papers = service.list_papers()

    assert papers[0]["title_zh"] == "中文标题翻译暂不可用"


def test_start_run_preserves_collection_errors_for_frontend(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path / "reports", settings_path=tmp_path / "settings.json")
    monkeypatch.setattr(service, "_build_llm_client", lambda **_: object())

    class FailingArxivSource:
        def __init__(self, limit: int = 5) -> None:
            self.limit = limit

        def fetch(self, topic, **kwargs):
            raise RuntimeError("HTTP Error 429")

    monkeypatch.setattr("app.workflows.nodes.ArxivPaperSource", FailingArxivSource)

    created = service.start_run(
        topic="AI Agent",
        database="arxiv",
        venues=[],
        date_range=(None, None),
        openai_api_key="sk-test",
        openai_model="qwen3-plus",
        openai_base_url="",
    )

    for _ in range(100):
        run = service.get_run(created["run_id"])
        if run and run["status"] == "awaiting_selection":
            break
        time.sleep(0.02)
    else:
        run = service.get_run(created["run_id"])

    assert run is not None
    assert run["errors"] == ["arxiv_fetch_failed: HTTP Error 429"]


def test_run_skips_unused_trend_and_gap_analysis(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = ResearchService(report_output_dir=tmp_path)
    monkeypatch.setattr(service, "_build_llm_client", lambda **kwargs: _FakeLLMClient())

    result = service.run(topic="agent systems", openai_api_key="test-key", openai_model="gpt-4.1-mini")

    assert not hasattr(__import__("app.services.research_service", fromlist=["unused"]), "run_trend_analysis")
    assert not hasattr(__import__("app.services.research_service", fromlist=["unused"]), "find_research_gaps")
    assert result["report_markdown"].startswith("# 研究报告")
