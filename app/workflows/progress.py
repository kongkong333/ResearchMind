from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ProgressStatus = Literal["pending", "running", "completed"]


@dataclass(slots=True)
class ProgressEvent:
    stage_key: str
    stage_label: str
    status: ProgressStatus
    message: str
    current: int = 0
    total: int = 0
