from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


APP_URL = "http://127.0.0.1:8000"
PID_FILE = ".researchmind-web.pid"
START_LOG = ".researchmind-start.log"
OUT_LOG = ".researchmind-web.out.log"
ERR_LOG = ".researchmind-web.err.log"


def process_alive(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return str(pid) in result.stdout


def wait_for_url(url: str, timeout_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    pid_path = root / PID_FILE
    start_log_path = root / START_LOG
    out_log_path = root / OUT_LOG
    err_log_path = root / ERR_LOG

    def log(message: str) -> None:
        with start_log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{message}\n")

    start_log_path.write_text("", encoding="utf-8")

    if pid_path.exists():
        raw_pid = pid_path.read_text(encoding="utf-8").strip()
        if raw_pid.isdigit() and process_alive(int(raw_pid)):
            print("[ResearchMind] Web 应用已在运行，正在打开浏览器...")
            webbrowser.open(APP_URL)
            return 0
        pid_path.unlink(missing_ok=True)

    out_fh = out_log_path.open("w", encoding="utf-8")
    err_fh = err_log_path.open("w", encoding="utf-8")

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
    log(f"[ResearchMind] launching: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            cwd=root,
            stdout=out_fh,
            stderr=err_fh,
            creationflags=creationflags,
        )
    finally:
        out_fh.close()
        err_fh.close()

    pid_path.write_text(str(process.pid), encoding="utf-8")
    print("[ResearchMind] 等待 Web 应用就绪...")

    if not wait_for_url(APP_URL, timeout_seconds=30):
        print("[ResearchMind] 启动超时，请检查日志：")
        print(start_log_path)
        print(err_log_path)
        return 1

    print("[ResearchMind] 启动成功，正在打开浏览器...")
    webbrowser.open(APP_URL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
