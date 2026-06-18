import app.services.llm.client as llm_client_module
from app.services.llm.client import LLMClient


def test_llm_client_passes_base_url_to_openai_constructor(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url or ""

    monkeypatch.setattr(llm_client_module, "OpenAI", FakeOpenAI)

    client = LLMClient(
        api_key="qwen-key",
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    assert captured == {
        "api_key": "qwen-key",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    assert client._model == "qwen-plus"
