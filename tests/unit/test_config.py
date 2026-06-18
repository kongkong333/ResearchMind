from app.core.config import Settings


def test_settings_use_expected_defaults() -> None:
    settings = Settings(
        openai_api_key="test-key",
        database_url="sqlite+pysqlite:///:memory:",
    )

    assert settings.app_name == "ResearchMind"
    assert settings.default_venues == ["ICLR", "NeurIPS", "ICML", "AAAI"]
    assert settings.report_output_dir == "reports"
    assert settings.openai_base_url is None
