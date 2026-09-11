"""
scripts/stop_manager.py
Background-agent control: stop-file, PID, and status.json.
The agent runs detached from the UI; the UI and agent communicate
through files so closing the browser tab never stops the agent.
"""

import json
from datetime import datetime
from pathlib import Path

BASE        = Path(__file__).parent.parent
LOG_DIR     = BASE / "logs"
STOP_FILE   = LOG_DIR / "stop.txt"
PID_FILE    = LOG_DIR / "agent.pid"
STATUS_FILE = BASE / "output" / "status.json"


def stop_requested() -> bool:
    return STOP_FILE.exists()


def request_stop():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STOP_FILE.write_text("stop", encoding="utf-8")


def clear_stop():
    try:
        STOP_FILE.unlink()
    except FileNotFoundError:
        pass


def save_pid(pid: int):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid), encoding="utf-8")


def load_pid():
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def update_status(**kwargs):
    """Write/merge status so the UI can show progress without pipes."""
    data = {}
    try:
        if STATUS_FILE.exists():
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    data.update(kwargs)
    data["last_update"] = datetime.now().isoformat(timespec="seconds")
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def load_status() -> dict:
    try:
        if STATUS_FILE.exists():
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def is_pid_alive(pid) -> bool:
    """Windows-safe liveness check via OpenProcess (never kills the process)."""
    if not pid:
        return False
    import ctypes
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return False
    kernel32.CloseHandle(handle)
    return True