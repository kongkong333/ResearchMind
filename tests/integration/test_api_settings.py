from __future__ import annotations

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


def test_get_settings_returns_defaults() -> None:
    client = _make_client()

    response = client.get("/settings")

    assert response.status_code == 200
    assert response.json()["openai_model"]


def test_put_settings_persists_payload() -> None:
    client = _make_client()

    response = client.put(
        "/settings",
        json={
            "openai_api_key": "sk-test",
            "openai_model": "qwen3-plus",
            "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "report_output_dir": "reports",
        },
    )

    assert response.status_code == 200
    assert response.json()["openai_model"] == "qwen3-plus"
