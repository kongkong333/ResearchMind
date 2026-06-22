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
        assert "/static/styles.css?v=" in response.text
        assert "/static/selection-state.js?v=" in response.text
        assert "/static/app.js?v=" in response.text
    else:
        assert "ResearchMind" in response.json()["html"]
        assert "/static/styles.css?v=" in response.json()["html"]
        assert "/static/selection-state.js?v=" in response.json()["html"]
        assert "/static/app.js?v=" in response.json()["html"]


def test_index_html_contains_required_ui_mounts():
    html = Path(r"D:\ResearchMind\app\static\index.html").read_text(encoding="utf-8")

    assert "主题论文分析" in html
    assert "会议论文近期趋势" in html
    assert "settingsModal" in html
    assert "database-tabs" in html
    assert 'id="conferenceSelect"' in html
    assert 'id="conferenceYearInput"' in html
    assert 'id="conferenceLimitInput"' in html
    assert 'id="conferenceRunButton"' in html
    assert 'id="conferenceTrackSection"' in html
    assert 'id="conferenceTrackList"' in html
    assert 'id="conference-stage-grid"' in html
    assert 'id="conference-result-panel"' in html
    assert "stage-grid" in html
    assert "result-panel" in html
    assert "运行阶段" not in html
    assert "Run ID" not in html
    assert "报告预览" not in html
    assert "Semantic Scholar" not in html
    assert "当前仅抓取 accepted 论文" not in html


def test_frontend_script_uses_run_polling_and_hides_markdown_preview():
    script = Path(r"D:\ResearchMind\app\static\app.js").read_text(encoding="utf-8")
    conference_script = Path(r"D:\ResearchMind\app\static\conference-trends.js").read_text(encoding="utf-8")

    assert 'fetch("/research-runs"' in script
    assert 'fetch("/conference-trends/runs"' in conference_script
    assert 'fetch("/conference-trends/tracks"' in conference_script
    assert "setInterval" in script
    assert "selectedDatabase" in script
    assert "selectedConference" in conference_script
    assert 'database: selectedDatabase' in script
    assert "sortPapersByPublishedDate" in script
    assert "report_markdown" not in script
    assert "Run ID" not in script
    assert "semanticScholarApiKey" not in script
    assert 'stage_label: "统计趋势"' not in script
    assert 'stage_label: "研究机会"' not in script
    assert "try {" in conference_script
    assert 'status: "failed"' in conference_script
    assert 'document.getElementById("conferenceRunButton").disabled = false' in conference_script
    assert 'document.getElementById("conferenceLimitInput")' in conference_script
    assert "limit: limitValue" in conference_script
    assert "tracks," in conference_script
    assert '"aaai"' in conference_script
    assert '"bibm"' not in conference_script
    assert "selectedTrackIds()" in conference_script


def test_conference_button_reuses_primary_run_button_styles():
    css = Path(r"D:\ResearchMind\app\static\styles.css").read_text(encoding="utf-8")

    assert "#runButton," in css
    assert "#conferenceRunButton" in css


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


def test_frontend_script_renders_paper_title_links_without_pdf_download_entry():
    script = Path(r"D:\ResearchMind\app\static\app.js").read_text(encoding="utf-8")

    assert "PDF下载" not in script
    assert "paper-links" not in script
    assert "paper-title-link" in script
    assert "paper-pdf-link" not in script
    assert "function resolvePaperUrl" in script
    assert "https://pubmed.ncbi.nlm.nih.gov/" in script
    assert "https://arxiv.org/abs/" in script


def test_conference_trend_schema_defaults_to_ten_items():
    schema = Path(r"D:\ResearchMind\app\schemas\conference_trends.py").read_text(encoding="utf-8")

    assert "default=100" in schema


def test_conference_view_lists_added_openreview_conferences():
    html = Path(r"D:\ResearchMind\app\static\index.html").read_text(encoding="utf-8")

    assert '<option value="aaai">AAAI</option>' in html
    assert '<option value="bibm">BIBM</option>' not in html
