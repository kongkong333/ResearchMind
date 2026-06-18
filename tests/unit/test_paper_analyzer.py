from app.services.collectors.base import CollectedPaper
from app.services.analyzers.paper_analyzer import PaperAnalyzer


class StubLLMClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_structured(self, *, prompt, schema):
        self.calls.append({"prompt": prompt, "schema": schema})
        return self.response


def test_paper_analyzer_uses_llm_and_returns_expected_sections() -> None:
    client = StubLLMClient(
        {
            "summary": "本文提出分层智能体规划框架，并结合记忆与工具反馈提升复杂任务稳定性。",
            "problem": "解决规划不稳定问题",
            "method": "提出分层 agent 框架",
            "innovation": "结合记忆与工具反馈",
            "results": "在基准上显著提升",
            "limitations": "仅在英文任务评测",
            "research_gap": "缺少真实业务环境验证",
            "research_opportunity": "面向企业 workflow 做长期评估",
        }
    )
    analyzer = PaperAnalyzer(llm_client=client)
    paper = CollectedPaper(
        source_id="p1",
        title="Agent Planning",
        authors=["Ada"],
        abstract="A planner for agents.",
        year=2026,
        venue="ICLR",
        url="https://example.com/p1",
        pdf_url="https://arxiv.org/pdf/2501.00001v1.pdf",
        keywords=["agent"],
    )

    result = analyzer.analyze(paper)

    assert result.summary == "本文提出分层智能体规划框架，并结合记忆与工具反馈提升复杂任务稳定性。"
    assert result.problem == "解决规划不稳定问题"
    assert result.limitations == "仅在英文任务评测"
    assert result.research_gap == "缺少真实业务环境验证"
    assert result.research_opportunity == "面向企业 workflow 做长期评估"
    assert client.calls
    assert "summary" in client.calls[0]["schema"]["properties"]
    assert "2-3句" in client.calls[0]["prompt"]
    assert "不要假设你访问了任何外部链接、PDF 或全文" in client.calls[0]["prompt"]
    assert "PDF链接" not in client.calls[0]["prompt"]
    assert "HTML链接" not in client.calls[0]["prompt"]


def test_paper_analyzer_fills_missing_fields_with_safe_defaults() -> None:
    client = StubLLMClient({"problem": "问题定义"})
    analyzer = PaperAnalyzer(llm_client=client)
    paper = CollectedPaper(
        source_id="p2",
        title="Sparse Analysis",
        authors=["Ada"],
        abstract="Minimal abstract.",
        year=2026,
        venue="ICLR",
        url="https://example.com/p2",
        keywords=[],
    )

    result = analyzer.analyze(paper)

    assert result.summary == ""
    assert result.problem == "问题定义"
    assert result.method == ""
    assert result.innovation == ""
    assert result.research_gap == ""
    assert result.research_opportunity == ""


def test_paper_analyzer_handles_invalid_payload_type_with_safe_fallback() -> None:
    client = StubLLMClient(["not", "a", "dict"])
    analyzer = PaperAnalyzer(llm_client=client)
    paper = CollectedPaper(
        source_id="p3",
        title="Invalid Payload",
        authors=["Ada"],
        abstract="Abstract",
        year=2026,
        venue="ICLR",
        url="https://example.com/p3",
        keywords=[],
    )

    result = analyzer.analyze(paper)

    assert result.summary == ""
    assert result.problem == ""
    assert result.method == ""
    assert result.limitations == ""
    assert result.research_gap == ""
    assert result.research_opportunity == ""
