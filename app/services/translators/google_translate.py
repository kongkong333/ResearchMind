from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GoogleTranslateService:
    _BASE_URL = "https://translate.googleapis.com/translate_a/single"

    def translate(self, text: str, *, target_language: str = "zh-CN", source_language: str = "auto") -> str:
        normalized = text.strip()
        if not normalized:
            return ""
        params = urlencode(
            {
                "client": "gtx",
                "sl": source_language,
                "tl": target_language,
                "dt": "t",
                "q": normalized,
            }
        )
        request = Request(
            f"{self._BASE_URL}?{params}",
            headers={
                "User-Agent": "ResearchMind/0.1",
            },
        )
        with urlopen(request, timeout=8) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, list) or not payload:
            return ""
        segments = payload[0]
        if not isinstance(segments, list):
            return ""
        translated_segments: list[str] = []
        for segment in segments:
            if isinstance(segment, list) and segment and isinstance(segment[0], str):
                translated_segments.append(segment[0])
        return "".join(translated_segments).strip()
