from __future__ import annotations

from pydantic import BaseModel


class FrontendSettingsRead(BaseModel):
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = ""
    report_output_dir: str = "reports"


class FrontendSettingsUpdate(BaseModel):
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = ""
    report_output_dir: str = "reports"
