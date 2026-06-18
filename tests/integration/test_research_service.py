from __future__ import annotations

from pathlib import Path

import pytest

from app.services.research_service import ResearchService


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
