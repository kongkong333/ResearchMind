from datetime import date

from app.schemas.papers import PaperRead
from app.schemas.research_runs import ResearchRunCreate, ResearchRunRead, ResearchRunStatusRead, StageStateRead
from app.schemas.settings import FrontendSettingsRead, FrontendSettingsUpdate


def test_research_run_create_defaults_to_empty_venues() -> None:
    payload = ResearchRunCreate(topic="AI Agent")

    assert payload.topic == "AI Agent"
    assert payload.venues == []
    assert payload.max_results == 5
    assert payload.openai_api_key is None
    assert payload.openai_model is None


def test_research_run_read_exposes_summary_fields() -> None:
    payload = ResearchRunRead(
        id=1,
        topic="RAG",
        status="completed",
        paper_count=12,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        error_message=None,
    )

    assert payload.paper_count == 12
    assert payload.status == "completed"


def test_stage_state_defaults_are_browser_friendly() -> None:
    payload = StageStateRead(stage_key="collect_papers", stage_label="抓取论文")

    assert payload.status == "pending"
    assert payload.message == ""
    assert payload.current == 0
    assert payload.total == 0


def test_research_run_status_exposes_stage_states_and_summary() -> None:
    payload = ResearchRunStatusRead(
        run_id="run-1",
        topic="AI Agent",
        status="running",
        current_message="正在抓取论文",
        stages=[StageStateRead(stage_key="collect_papers", stage_label="抓取论文", status="running")],
        errors=[],
        latest_report_path=None,
        report_artifact_path=None,
    )

    assert payload.status == "running"
    assert payload.current_message == "正在抓取论文"
    assert payload.stages[0].stage_key == "collect_papers"


def test_frontend_settings_models_are_plain_strings() -> None:
    update = FrontendSettingsUpdate(
        openai_api_key="sk-test",
        openai_model="qwen3-plus",
        openai_base_url="",
        report_output_dir="reports",
    )
    read = FrontendSettingsRead(**update.model_dump())

    assert update.openai_base_url == ""
    assert read.openai_api_key == "sk-test"
    assert read.report_output_dir == "reports"


def test_paper_read_supports_future_get_papers_contract() -> None:
    payload = PaperRead(
        id=1,
        source_id="openreview-1",
        title="Tool-Using AI Agents",
        authors=["Ada", "Turing"],
        abstract="Abstract",
        year=2026,
        venue="ICML",
        url="https://example.com/paper",
        pdf_url="https://arxiv.org/pdf/2501.00001v1.pdf",
        keywords=["agent"],
    )

    assert payload.venue == "ICML"
    assert payload.authors == ["Ada", "Turing"]
    assert payload.pdf_url == "https://arxiv.org/pdf/2501.00001v1.pdf"
