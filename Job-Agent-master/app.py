"""
app.py  —  AI Job Agent Web UI (Streamlit)

Run with:  venv\\Scripts\\streamlit run app.py
Then open http://localhost:8501

Features:
  - Enter credentials for each platform in the UI (saved to config/credentials.json)
  - Press RUN -> agent logs in + scrapes + scores + applies (browser opens visibly)
  - Live console + live report of companies applied to
  - LOOP mode keeps running new cycles until you press STOP
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import streamlit as st

import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from config.settings import (
    YOUR_NAME, YOUR_EMAIL, YOUR_PHONE, YOUR_LOCATION, AVAILABILITY,
    CURRENT_CTC, EXPECTED_CTC,
)

PROJECT_ROOT = Path(__file__).parent
CRED_FILE = PROJECT_ROOT / "config" / "credentials.json"
APPLIED_FILE = PROJECT_ROOT / "output" / "applied_jobs.json"
LOG_FILE = PROJECT_ROOT / "logs" / "apply_log.txt"

PLATFORMS = [
    "LinkedIn", "Naukri", "Indeed",
]

st.set_page_config(page_title="AI Job Agent", page_icon="🤖", layout="wide")
st.title("🤖 AI Job Agent — QA Edition")
st.caption("Groq-powered | Logs in with your credentials | Applies to QA jobs on 24 platforms")


# ───────────────────────── helpers ─────────────────────────

def load_applied():
    try:
        if APPLIED_FILE.exists():
            return json.loads(APPLIED_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def load_credentials():
    try:
        if CRED_FILE.exists():
            return json.loads(CRED_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_credentials(creds):
    CRED_FILE.parent.mkdir(exist_ok=True)
    CRED_FILE.write_text(json.dumps(creds, indent=2, ensure_ascii=False), encoding="utf-8")


def log_tail(n=40):
    try:
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            return lines[-n:]
    except Exception:
        pass
    return []


# ─────────────────────── sidebar ───────────────────────────

with st.sidebar:
    st.header("🔑 Platform Credentials")
    st.caption("Saved as plain text in config/credentials.json on your PC. "
               "Agent uses these to log in itself. Empty = skipped.")

    creds = load_credentials()
    form_creds = {}
    for p in PLATFORMS:
        saved = creds.get(p, {})
        with st.expander(p, expanded=False):
            u = st.text_input(f"{p} — email/username", value=saved.get("username", ""), key=f"u_{p}")
            pw = st.text_input(f"{p} — password", value=saved.get("password", ""), type="password", key=f"p_{p}")
            if u and pw:
                form_creds[p] = {"username": u, "password": pw}

    if st.button("💾 Save Credentials", use_container_width=True):
        save_credentials(form_creds)
        st.success(f"Saved for {len(form_creds)} platforms")

    st.divider()
    st.header("👤 Your Profile")
    st.write(f"**{YOUR_NAME}**")
    st.write(f"📧 {YOUR_EMAIL}")
    st.write(f"📱 {YOUR_PHONE}")
    st.write(f"📍 {YOUR_LOCATION}")
    st.write(f"⚡ {AVAILABILITY}")
    st.write(f"💰 Current: {CURRENT_CTC} | Expected: {EXPECTED_CTC}")
    st.caption("Edit in config/settings.py if needed.")


# ─────────────────────── run tab ───────────────────────────

def agent_running():
    """Agent counts as running only if its process is alive AND status says so
    (the venv shim lingers ~1 min after the agent exits)."""
    from scripts.stop_manager import load_pid, is_pid_alive, load_status
    if not is_pid_alive(load_pid()):
        return False
    return load_status().get("running") is True


def start_agent(flags):
    """Launch the agent DETACHED - it survives browser/UI closure."""
    from scripts.stop_manager import clear_stop, save_pid, update_status
    clear_stop()
    log_raw = PROJECT_ROOT / "logs" / "agent.log"
    log_raw.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_raw, "a", encoding="utf-8", errors="replace")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(
        [sys.executable, "-u", "main.py"] + flags,
        cwd=str(PROJECT_ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    save_pid(proc.pid)
    update_status(running=True,
                  started_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                  last_step="Starting...")


def stop_agent():
    """Request stop + kill the agent process tree."""
    from scripts.stop_manager import request_stop, load_pid, update_status
    request_stop()
    pid = load_pid()
    if pid:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    update_status(running=False, last_step="Stopped by user")


tab_run, tab_report = st.tabs(["▶️ Run Automation", "📊 Report"])

with tab_run:
    running = agent_running()

    st.info("**Background mode:** RUN dabao, phir ye browser tab band kar do — "
            "agent backend me chalta rahega jab tak **STOP** na dabao. "
            "Tab wapas kholo to live status dikhega (logs/agent.log + status.json).")

    c1, c2, c3, c4 = st.columns(4)
    dry_run = c1.toggle("Dry run (test, no submit)", value=True)
    min_score = c2.slider("Minimum match score", 50, 95, 75, 5)
    loop_mode = c3.toggle("Loop mode (run until STOP)", value=False)
    interval = c4.number_input("Minutes between cycles", 5, 180, 30)

    st.divider()

    col_btn, col_status = st.columns([1, 2])
    start = False

    if not running:
        start = col_btn.button("🚀 RUN AUTOMATION", type="primary", use_container_width=True)
    else:
        if col_btn.button("🛑 STOP", type="secondary", use_container_width=True):
            stop_agent()
            st.warning("Stop requested — agent shut down.")
            st.rerun()

    if start:
        flags = ["--dry-run"] if dry_run else []
        flags += ["--min-score", str(min_score)]
        if loop_mode:
            flags += ["--loop", "--interval", str(int(interval))]
        start_agent(flags)
        st.success("Agent started in background. Aap ab browser tab band kar sakte ho — "
                   "agent chalta rahega. 🛑 STOP se hi rukega.")
        st.rerun()

    st.divider()
    st.markdown("#### ⚡ Agent status")
    from scripts.stop_manager import load_status
    status = load_status()

    if running:
        st.markdown(f"🟢 **RUNNING** — {status.get('last_step', '...')}")
    else:
        st.markdown(f"⚪ **Idle** — last: {status.get('last_step', 'never')}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jobs found", status.get("jobs_found", 0) or 0)
    m2.metric("Jobs scored", status.get("jobs_scored", 0) or 0)
    m3.metric("Applied", status.get("applied_count", 0) or 0)
    m4.metric("Started", (status.get("started_at") or "-")[5:16])

    with st.expander("🖥️ Live console (logs/agent.log)", expanded=running):
        log_raw = PROJECT_ROOT / "logs" / "agent.log"
        try:
            if log_raw.exists():
                lines = log_raw.read_text(encoding="utf-8", errors="replace").splitlines()
                st.code("\n".join(lines[-60:]), language="text")
            else:
                st.code("(no log yet - agent log file created on first run)", language="text")
        except Exception:
            st.code("(cannot read log)", language="text")

    st.divider()
    st.markdown("#### ⚡ Live results")
    applied = load_applied()
    ok = [j for j in applied if j.get("apply_status") == "applied"]
    r1, r2, r3 = st.columns(3)
    r1.metric("Total applications", len(ok))
    r2.metric("Companies", len({j.get("company", "?") for j in ok}))
    r3.metric("Platforms used", len({j.get("platform", "?") for j in ok}))

    if running:
        time.sleep(2)
        st.rerun()


# ────────────────────── report tab ─────────────────────────

with tab_report:
    applied = load_applied()
    ok = [j for j in applied if j.get("apply_status") == "applied"]

    st.subheader("📊 Application Report")
    if not applied:
        st.info("No applications yet. Run the automation first — results appear here live.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total applications", len(ok))
        m2.metric("Companies", len({j.get("company", "?") for j in ok}))
        m3.metric("Platforms", len({j.get("platform", "?") for j in ok}))
        m4.metric("Avg match score", round(sum(j.get("score", 0) for j in ok) / len(ok), 1) if ok else 0)

        import pandas as pd
        df = pd.DataFrame(ok)
        show_cols = [c for c in ["platform", "company", "title", "score", "applied_at"] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, height=400)

        if "platform" in df.columns:
            by_platform = df["platform"].value_counts()
            st.bar_chart(by_platform)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, "applied_jobs.csv", "text/csv")

    st.divider()
    st.subheader("📋 Manual review needed (external apply / failed)")
    try:
        todo = Path(PROJECT_ROOT / "logs" / "manual_todo.txt")
        if todo.exists():
            lines = todo.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                st.code("\n".join(lines[-30:]), language="text")
                st.caption("Ye jobs agent auto-apply nahi kar paya — aap manually apply karo (link har line me hai).")
            else:
                st.info("Koi manual-review job nahi — sab kuch auto handle ho raha hai.")
        else:
            st.info("Abhi koi manual-review job nahi.")
    except Exception:
        pass

    st.divider()
    st.subheader("📜 Latest apply log")
    tail = log_tail()
    st.code("\n".join(tail) if tail else "(log empty)", language="text")
    st.caption(f"Files: output/applied_jobs.json • logs/apply_log.txt • config/credentials.json")

st.caption("Keep this browser tab open and your PC awake while the agent runs — it drives a real Chrome window.")