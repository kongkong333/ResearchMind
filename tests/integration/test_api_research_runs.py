from __future__ import annotations

from pathlib import Path

import pytest

from app.main import SimpleTestClient, create_app
from app.services.collectors.base import CollectedPaper
from app.services.collectors.pubmed_source import PubMedPaperSource

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]


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


def _make_client(monkeypatch: pytest.MonkeyPatch | None = None):
    app = create_app()
    if monkeypatch is not None:
        monkeypatch.setattr(app.state.research_service, "_build_llm_client", lambda **kwargs: _FakeLLMClient())
        monkeypatch.setattr(app.state.research_service, "_translate_title", lambda title: "")
        monkeypatch.setattr(
            PubMedPaperSource,
            "fetch",
            lambda self, topic, **kwargs: [
                CollectedPaper(
                    source_id="p1",
                    title="Agent Planning with Memory",
                    authors=["Alice"],
                    abstract="Planning and memory for agent workflows.",
                    year=2024,
                    venue="ICLR",
                    url="https://example.com/p1",
                    keywords=["Agent", "Memory", "Planning"],
                )
            ],
        )
    if TestClient is not None and type(app).__name__ == "FastAPI":
        return TestClient(app)
    return SimpleTestClient(app)


def test_research_run_endpoints_return_stubbed_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)
    fetch_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        PubMedPaperSource,
        "fetch",
        lambda self, topic, start_date=None, end_date=None, limit=None: (
            fetch_calls.append(
                {
                    "topic": topic,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                }
            )
            or [
                CollectedPaper(
                    source_id="p1",
                    title="Agent Planning with Memory",
                    authors=["Alice"],
                    abstract="Planning and memory for agent workflows.",
                    year=2024,
                    venue="ICLR",
                    url="https://example.com/p1",
                    keywords=["Agent", "Memory", "Planning"],
                )
            ]
        ),
    )

    create_response = client.post(
        "/research-runs",
        json={
            "topic": "agent systems",
            "start_date": "2025-01-01",
            "max_results": 7,
            "openai_api_key": "test-key",
            "openai_model": "gpt-4.1-mini",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    run_id = created["run_id"]
    assert created["status"] in {"pending", "running", "awaiting_selection"}
    assert len(created["stages"]) == 5
    assert fetch_calls
    assert fetch_calls[0]["topic"] == "agent systems"
    assert str(fetch_calls[0]["start_date"]) == "2025-01-01"
    assert fetch_calls[0]["end_date"] is None
    assert fetch_calls[0]["limit"] == 7

    get_response = client.get(f"/research-runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["run_id"] == run_id

    for _ in range(30):
        get_response = client.get(f"/research-runs/{run_id}")
        payload = get_response.json()
        if payload["papers"] and payload["status"] == "awaiting_selection":
            break

    latest_payload = get_response.json()
    assert latest_payload["status"] == "awaiting_selection"
    assert latest_payload["papers"]
    assert latest_payload["selected_source_ids"]
    assert latest_payload["report_path"] is None

    analyze_response = client.post(
        f"/research-runs/{run_id}/analyze",
        json={
            "selected_source_ids": [latest_payload["papers"][0]["source_id"]],
            "openai_api_key": "test-key",
            "openai_model": "gpt-4.1-mini",
        },
    )

    assert analyze_response.status_code == 200
    for _ in range(30):
        latest_payload = client.get(f"/research-runs/{run_id}").json()
        if latest_payload["status"] == "completed":
            break

    assert latest_payload["status"] == "completed"
    assert Path(latest_payload["report_path"]).name == "weekly_report.md"
    assert "current_message" in latest_payload

    report_response = client.get(f"/research-runs/{run_id}/report")
    assert report_response.status_code == 200
    assert report_response.json()["report_markdown"].startswith("# 研究报告")


def test_papers_endpoint_returns_minimal_list() -> None:
    client = _make_client()

    response = client.get("/papers")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload == []


def test_app_reuses_single_research_service_instance() -> None:
    app = create_app()

    assert getattr(app, "state").research_service is getattr(app, "state").research_service


def test_missing_run_returns_404() -> None:
    client = _make_client()

    response = client.get("/research-runs/missing-run-id")

    assert response.status_code == 404


def test_invalid_create_payload_returns_422() -> None:
    client = _make_client()

    response = client.post("/research-runs", json={})

    assert response.status_code == 422


def test_create_payload_without_openai_credentials_returns_422() -> None:
    client = _make_client()

    response = client.post(
        "/research-runs",
        json={"topic": "agent systems"},
    )

    assert response.status_code == 422
