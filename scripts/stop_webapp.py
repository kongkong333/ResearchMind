from __future__ import annotations

import subprocess
from pathlib import Path


PID_FILE = ".researchmind-web.pid"


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    pid_path = root / PID_FILE

    if not pid_path.exists():
        print("[ResearchMind] 当前没有记录中的运行实例。")
        return 0

    raw_pid = pid_path.read_text(encoding="utf-8").strip()
    if not raw_pid.isdigit():
        pid_path.unlink(missing_ok=True)
        print("[ResearchMind] PID 文件无效，已清理。")
        return 0

    result = subprocess.run(
        ["taskkill", "/PID", raw_pid, "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    pid_path.unlink(missing_ok=True)

    if result.returncode == 0:
        print("[ResearchMind] Web 应用已停止。")
        return 0

    print("[ResearchMind] 未能确认进程状态，PID 文件已清理。")
    if result.stderr.strip():
        print(result.stderr.strip())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
