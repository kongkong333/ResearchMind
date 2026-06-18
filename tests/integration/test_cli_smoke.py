from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_research_cli_writes_report(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    report_dir = tmp_path / "reports"
    command = [
        sys.executable,
        str(root / "scripts" / "run_research.py"),
        "--topic",
        "agent systems",
        "--report-dir",
        str(report_dir),
    ]

    completed = subprocess.run(command, cwd=root, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr
    assert (report_dir / "weekly_report.md").exists()


def test_start_batch_no_longer_references_streamlit() -> None:
    content = Path(r"D:\ResearchMind\start_researchmind.bat").read_text(encoding="utf-8")

    assert "streamlit" not in content.lower()
    assert "start_webapp.py" in content


def test_stop_batch_no_longer_references_stop_streamlit() -> None:
    content = Path(r"D:\ResearchMind\stop_researchmind.bat").read_text(encoding="utf-8")

    assert "stop_streamlit.py" not in content.lower()
    assert "stop_webapp.py" in content
