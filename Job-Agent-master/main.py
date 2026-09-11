"""
main.py  —  AI Job Agent (FREE Groq Version)
Runs the full pipeline:
  Step 1 → Parse resume with Groq AI
  Step 2 → Scrape 24 job platforms
  Step 3 → Score every job with Groq AI
  Step 4 → Auto-apply to best matches

USAGE:
  python main.py                              → Full run
  python main.py --resume config\resume.pdf  → Parse new resume first
  python main.py --scrape-only               → Only find jobs
  python main.py --match-only                → Only re-score jobs
  python main.py --apply-only                → Only apply to scored jobs
  python main.py --dry-run                   → Full run, don't submit
  python main.py --min-score 70              → Only apply score >= 70
"""

import asyncio, argparse, json, sys
from pathlib import Path
from datetime import datetime

from scripts.stop_manager import stop_requested, update_status


def print_banner():
    print("\n" + "=" * 58)
    print("  [AI]  AI JOB AGENT  -  100% FREE  (Groq API Powered)")
    print("  QA Engineer / Manual Tester Edition")
    print(f"  Started : {datetime.now().strftime('%d %b %Y  %H:%M')}")
    print("=" * 58)


def check_groq():
    """Make sure the Groq API key is set before we start."""
    from scripts.groq_engine import test_groq
    if not test_groq():
        print("\n[ERROR] Groq API is NOT configured!")
        print("   Please:")
        print("   1. Get a free key from https://console.groq.com/keys")
        print("   2. Paste it into GROQ_API_KEY in config/settings.py")
        print("   3. Then run this script again\n")
        sys.exit(1)


def check_settings():
    from config.settings import CHROME_USER_DATA_DIR, YOUR_NAME, GROQ_API_KEY
    warnings = []
    if "REPLACE_WITH_YOUR_USERNAME" in CHROME_USER_DATA_DIR:
        warnings.append("[WARN] CHROME_USER_DATA_DIR not set in config/settings.py")
        warnings.append("   Open Chrome -> go to chrome://version -> copy Profile Path")
    if YOUR_NAME == "Your Full Name":
        warnings.append("[WARN] YOUR_NAME not set in config/settings.py")
    if not GROQ_API_KEY:
        warnings.append("[WARN] GROQ_API_KEY is empty - get a free key at https://console.groq.com/keys")
    for w in warnings:
        print(w)


async def run_pipeline(args):
    # ── Step 1: Resume ──────────────────────────────────────
    if not (args.apply_only or args.match_only):
        update_status(last_step="Step 1: resume / profile")
        print("\n[INFO] STEP 1: Resume")
        if args.resume or not Path("config/profile.json").exists():
            check_groq()   # Need Groq API to parse resume
            from scripts.resume_parser import parse_resume
            parse_resume(args.resume)
        else:
            print("   Using existing profile [OK]  (use --resume to re-parse)")

    # ── Step 2: Scrape ──────────────────────────────────────
    if not (args.apply_only or args.match_only):
        if stop_requested():
            print("\n[STOP] Stop requested - skipping remaining steps")
            update_status(running=False, last_step="Stopped by user")
            return
        update_status(last_step="Step 2: scraping jobs (3 platforms, parallel)")
        print("\n[INFO] STEP 2: Scraping Jobs")
        from scripts.job_scraper import run_scraper
        jobs = await run_scraper()
        print(f"   Found {len(jobs)} unique jobs across all platforms")
        update_status(jobs_found=len(jobs))
    else:
        f = Path("output/scraped_jobs.json")
        jobs = json.loads(f.read_text()) if f.exists() else []
        print(f"\n[INFO] STEP 2: Loaded {len(jobs)} existing scraped jobs")

    # ── Step 3: AI Match ────────────────────────────────────
    if not (args.scrape_only or args.apply_only):
        if stop_requested():
            print("\n[STOP] Stop requested - skipping remaining steps")
            update_status(running=False, last_step="Stopped by user")
            return
        update_status(last_step="Step 3: AI scoring with Groq (3 parallel workers)")
        print("\n[INFO] STEP 3: AI Scoring with Groq")
        check_groq()
        from scripts.ai_matcher import run_matcher
        scored = run_matcher()
        update_status(jobs_scored=len(scored))
    else:
        f = Path("output/scored_jobs.json")
        scored = json.loads(f.read_text()) if f.exists() else []
        print(f"\n[INFO] STEP 3: Loaded {len(scored)} scored jobs")

    # ── Step 4: Apply ───────────────────────────────────────
    if not args.scrape_only and not args.match_only:
        if stop_requested():
            print("\n[STOP] Stop requested - skipping remaining steps")
            update_status(running=False, last_step="Stopped by user")
            return
        update_status(last_step="Step 4: auto-apply")
        print(f"\n[INFO] STEP 4: Auto-Apply {'(DRY RUN)' if args.dry_run else ''}")
        from scripts.auto_applier import run_auto_apply
        await run_auto_apply(
            jobs=scored or None,
            min_score=args.min_score,
            dry_run=args.dry_run,
        )

    # ── Summary ─────────────────────────────────────────────
    applied_file = Path("output/applied_jobs.json")
    if applied_file.exists():
        applied = json.loads(applied_file.read_text())
        ok = [j for j in applied if j.get("apply_status") == "applied"]
        print(f"\n[OK] Session complete! {len(ok)} applications submitted.")
        print(f"   Full log: logs/apply_log.txt\n")
        update_status(applied_count=len(ok))
    update_status(running=False, last_step="Finished (full cycle)" if not stop_requested() else "Stopped by user")


async def main():
    parser = argparse.ArgumentParser(description="AI Job Agent — Free Groq Edition")
    parser.add_argument("--resume",      type=str,  help="Path to your resume PDF")
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape jobs")
    parser.add_argument("--match-only",  action="store_true", help="Only score jobs")
    parser.add_argument("--apply-only",  action="store_true", help="Only apply to scored jobs")
    parser.add_argument("--dry-run",     action="store_true", help="Don't actually submit")
    parser.add_argument("--min-score",   type=int,  default=None)
    parser.add_argument("--loop",        action="store_true", help="Run cycles forever until stopped")
    parser.add_argument("--interval",    type=int,  default=30, help="Minutes between cycles (loop mode)")
    args = parser.parse_args()

    print_banner()
    check_settings()

    from scripts.stop_manager import clear_stop
    clear_stop()
    update_status(running=True, started_at=datetime.now().isoformat(timespec="seconds"),
                  last_step="Starting...", mode="loop" if args.loop else "single")

    cycle = 0
    while True:
        cycle += 1
        if cycle > 1:
            if not args.loop:
                break
            print(f"\n{'=' * 58}")
            print(f"  [LOOP] Cycle #{cycle} - waiting {args.interval} minutes...")
            print("  (stop anytime with Ctrl+C or the Stop button in the UI)")
            print(f"{'=' * 58}")
            update_status(last_step=f"Loop mode - waiting {args.interval} min for next cycle")
            waited = 0
            while waited < args.interval * 60:
                if stop_requested():
                    print("\n[STOP] Stop requested - exiting")
                    update_status(running=False, last_step="Stopped by user")
                    return
                await asyncio.sleep(5)
                waited += 5
        try:
            await run_pipeline(args)
        except KeyboardInterrupt:
            print("\n[STOP] Stopped by user.")
            update_status(running=False, last_step="Stopped by user")
            break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"\n[ERROR] Pipeline failed: {e}")
            update_status(running=False, last_step=f"Error: {e}")
            if args.loop:
                print("   (continuing loop...)\n")
            else:
                break
        if stop_requested():
            print("\n[STOP] Stop requested - exiting")
            update_status(running=False, last_step="Stopped by user")
            break


if __name__ == "__main__":
    asyncio.run(main())
