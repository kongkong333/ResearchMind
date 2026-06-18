from app.db.models.paper import Paper
from app.db.models.paper_analysis import PaperAnalysis
from app.db.models.report import Report
from app.db.models.trend_snapshot import TrendSnapshot
from app.db.models.workflow_run import WorkflowRun
from app.db.repositories.paper_analyses import PaperAnalysesRepository
from app.db.repositories.papers import PapersRepository
from app.db.repositories.reports import ReportsRepository
from app.db.repositories.trend_snapshots import TrendSnapshotsRepository
from app.db.repositories.workflow_runs import WorkflowRunsRepository


def test_paper_model_keeps_core_metadata() -> None:
    paper = Paper(
        source_id="openreview-1",
        title="Agentic Retrieval for Long Context QA",
        authors=["Ada", "Turing"],
        abstract="A study on retrieval.",
        year=2026,
        venue="ICLR",
        url="https://example.com/paper",
        keywords=["agent", "retrieval"],
    )

    assert paper.source_id == "openreview-1"
    assert paper.venue == "ICLR"
    assert paper.authors == ["Ada", "Turing"]


class DummySession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.items: dict[tuple[type[object], object], object] = {}

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def get(self, model: type[object], item_id: object) -> object | None:
        return self.items.get((model, item_id))

    def delete(self, instance: object) -> None:
        self.deleted.append(instance)


def test_repository_shells_support_basic_crud_shape() -> None:
    session = DummySession()
    paper = Paper(
        id=1,
        source_id="paper-1",
        title="Paper",
        authors=["A"],
        abstract="Abstract",
        year=2025,
        venue="NeurIPS",
        url="https://example.com/paper-1",
        keywords=["agent"],
    )
    analysis = PaperAnalysis(
        id=2,
        paper_id=1,
        topic="AI Agent",
        problem="problem",
        method="method",
        innovation="innovation",
        results="results",
        limitations="limitations",
        model_version="gpt-test",
    )
    run = WorkflowRun(id=3, topic="AI Agent", status="pending")
    snapshot = TrendSnapshot(
        id=4,
        workflow_run_id=3,
        hot_keywords=[{"keyword": "agent", "count": 1}],
        hot_topics=[{"topic": "planning", "count": 1}],
        growth_signals=[{"year": 2025, "paper_count": 1}],
        summary="summary",
    )
    report = Report(
        id=5,
        workflow_run_id=3,
        title="Report",
        content_markdown="# Report",
    )
    session.items = {
        (Paper, 1): paper,
        (PaperAnalysis, 2): analysis,
        (WorkflowRun, 3): run,
        (TrendSnapshot, 4): snapshot,
        (Report, 5): report,
    }

    paper_repo = PapersRepository(session)
    analysis_repo = PaperAnalysesRepository(session)
    run_repo = WorkflowRunsRepository(session)
    snapshot_repo = TrendSnapshotsRepository(session)
    report_repo = ReportsRepository(session)

    assert paper_repo.add(paper) is paper
    assert analysis_repo.add(analysis) is analysis
    assert run_repo.add(run) is run
    assert snapshot_repo.add(snapshot) is snapshot
    assert report_repo.add(report) is report

    assert paper_repo.get(1) is paper
    assert analysis_repo.get(2) is analysis
    assert run_repo.get(3) is run
    assert snapshot_repo.get(4) is snapshot
    assert report_repo.get(5) is report

    paper_repo.delete(paper)
    assert session.deleted == [paper]
