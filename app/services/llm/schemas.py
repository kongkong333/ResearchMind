from __future__ import annotations


PAPER_ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "problem": {"type": "string"},
        "method": {"type": "string"},
        "innovation": {"type": "string"},
        "results": {"type": "string"},
        "limitations": {"type": "string"},
        "research_gap": {"type": "string"},
        "research_opportunity": {"type": "string"},
    },
}

RESEARCH_GAP_SCHEMA = {
    "type": "object",
    "required": ["gaps", "summary"],
    "additionalProperties": False,
    "properties": {
        "gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "description", "opportunity"],
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "opportunity": {"type": "string"},
                },
            },
        },
        "summary": {"type": "string"},
    },
}
