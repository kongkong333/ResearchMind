from __future__ import annotations

from pathlib import Path

from app.main import SimpleTestClient, create_app

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]


def _make_client():
    app = create_app()
    if TestClient is not None and type(app).__name__ == "FastAPI":
        return TestClient(app)
    return SimpleTestClient(app)


def test_root_route_serves_html_shell():
    client = _make_client()

    response = client.get("/")

    assert response.status_code == 200
    if hasattr(response, "text"):
        assert "ResearchMind" in response.text
    else:
        assert "ResearchMind" in response.json()["html"]


def test_index_html_contains_required_ui_mounts():
    html = Path(r"D:\ResearchMind\app\static\index.html").read_text(encoding="utf-8")

    assert "主题论文分析" in html
    assert "会议论文近期趋势" in html
    assert "settingsModal" in html
    assert "database-tabs" in html
    assert "即将上线" in html
    assert "stage-grid" in html
    assert "result-panel" in html
    assert "运行阶段" not in html
    assert "Run ID" not in html
    assert "报告预览" not in html
    assert "Semantic Scholar" not in html


def test_frontend_script_uses_run_polling_and_hides_markdown_preview():
    script = Path(r"D:\ResearchMind\app\static\app.js").read_text(encoding="utf-8")

    assert 'fetch("/research-runs"' in script
    assert "setInterval" in script
    assert "selectedDatabase" in script
    assert 'database: selectedDatabase' in script
    assert "sortPapersByPublishedDate" in script
    assert "report_markdown" not in script
    assert "Run ID" not in script
    assert "semanticScholarApiKey" not in script
    assert 'stage_label: "统计趋势"' not in script
    assert 'stage_label: "研究机会"' not in script


def test_frontend_script_allows_restart_after_selection_stage():
    script = Path(r"D:\ResearchMind\app\static\app.js").read_text(encoding="utf-8")

    assert 'payload.status === "awaiting_selection"' in script


def test_frontend_script_renders_keyword_and_venue_chips_with_chinese_date():
    script = Path(r"D:\ResearchMind\app\static\app.js").read_text(encoding="utf-8")
    html = Path(r"D:\ResearchMind\app\static\index.html").read_text(encoding="utf-8")

    assert "paper-chip-list" in script
    assert "paper-venue" in script
    assert "学科分类" in script
    assert 'paper.source === "arxiv"' in script
    assert "formatDateValueForDisplay" in script
    assert 'type="date"' in html
    assert 'id="startDateInput"' in html
    assert 'id="startDatePicker"' in html
    assert 'id="endDateInput"' in html
    assert 'id="endDatePicker"' in html
    assert 'type="text"' in html
    assert "placeholder=\"yy/mm/dd\"" in html
    assert "paper-title-zh" in script
    assert "end_date: normalizedEndDate.iso || null" in script
