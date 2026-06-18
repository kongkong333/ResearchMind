from __future__ import annotations

import json
import re

try:
    from openai import OpenAI
except ModuleNotFoundError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

class LLMClient:
    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required for real LLM calls.")
        if OpenAI is None:
            raise RuntimeError("OpenAI SDK is not installed.")
        normalized_base_url = (base_url or "").strip() or None
        self._client = OpenAI(api_key=api_key, base_url=normalized_base_url)
        self._model = model

    def generate_structured(self, *, prompt: str, schema: dict) -> dict:
        schema_text = json.dumps(schema, ensure_ascii=False)
        response = self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "你是一个严谨的科研分析助手。只输出一个 JSON 对象，不要输出解释、代码块或额外文本。",
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"{prompt}\n\n请严格遵守以下 JSON Schema：\n{schema_text}",
                        }
                    ],
                },
            ],
        )
        return json.loads(self._extract_json(response.output_text))

    def _extract_json(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        fenced = re.search(r"\{.*\}", stripped, re.DOTALL)
        if fenced:
            return fenced.group(0)
        raise ValueError("OpenAI response does not contain a valid JSON object.")
