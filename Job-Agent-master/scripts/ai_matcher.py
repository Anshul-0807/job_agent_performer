"""
scripts/ai_matcher.py
Scores every scraped job using the free Groq cloud API.
No local AI needed — just a free API key.
"""

import json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import MIN_SCORE_TO_APPLY
from scripts.groq_engine import score_job, test_groq
from scripts.stop_manager import stop_requested

SCRAPED_FILE = Path("output/scraped_jobs.json")
PROFILE_FILE = Path("config/profile.json")
SCORED_FILE  = Path("output/scored_jobs.json")


def load_profile() -> dict:
    if PROFILE_FILE.exists():
        return json.loads(PROFILE_FILE.read_text())
    return {
        "skills": {"primary": ["Python", "ML", "AI", "NLP", "LLM"], "secondary": []},
        "total_experience_years": 2,
        "job_preferences": {"roles": ["QA Engineer", "Manual Tester", "Test Engineer"]}
    }


def run_matcher() -> list:
    if not SCRAPED_FILE.exists():
        print("[ERROR] No scraped jobs found. Run job_scraper.py first.")
        return []

    jobs    = json.loads(SCRAPED_FILE.read_text())
    profile = load_profile()
    total   = len(jobs)

    if not test_groq():
        print("\n[ERROR] Groq API is not configured correctly. Please:")
        print("   1. Get a free key at https://console.groq.com/keys")
        print("   2. Paste it into GROQ_API_KEY in config/settings.py")
        print("   3. Run this script again")
        return []

    primary_skill = profile.get('skills',{}).get('primary',[])[0] if profile.get('skills',{}).get('primary') else 'QA'
    print(f"\n[INFO] Scoring {total} jobs with Groq AI ({primary_skill} profile) - 3 parallel workers...")
    print("   Runs on the free Groq cloud - fast, no local install!")

    scored = []
    apply_count = maybe_count = skip_count = 0

    # Score jobs concurrently (3 workers, auto-retry on rate limits),
    # checking for a stop request between batches of 25.
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = [None] * total
        done = 0
        pos = 0
        while pos < total:
            if stop_requested():
                print("\n[STOP] Stop requested - stopping scoring")
                break
            batch = jobs[pos:pos + 25]
            futures = {executor.submit(score_job, job, profile): i for i, job in enumerate(batch)}
            for fut in as_completed(futures):
                i = futures[fut]
                try:
                    results[pos + i] = fut.result()
                except Exception:
                    results[pos + i] = {"ai_score": 40, "ai_recommendation": "skip",
                                        "ai_reason": "scoring error", "ai_cover_note": ""}
                done += 1
                r = results[pos + i]
                icon = {"apply": "OK", "maybe": "?", "skip": "SKIP"}.get(r.get("ai_recommendation"), "?")
                print(f"  [{done:3}/{total}] {jobs[pos + i]['platform']:15} | {jobs[pos + i]['title'][:40]} -> [{icon}] {r.get('ai_score')}", flush=True)
            pos += 25

    scored = []
    apply_count = maybe_count = skip_count = 0

    for i, job in enumerate(jobs):
        if results[i] is None:
            continue
        job.update(results[i])
        job["scored_at"] = datetime.now().isoformat()

        rec = job.get("ai_recommendation", "maybe")
        score = job.get("ai_score", 50)

        if rec == "apply":
            apply_count += 1
        elif rec == "maybe":
            maybe_count += 1
        else:
            skip_count += 1

        scored.append(job)

    # Sort best first
    scored.sort(key=lambda x: x.get("ai_score", 0), reverse=True)

    SCORED_FILE.write_text(json.dumps(scored, indent=2, ensure_ascii=False))

    print(f"\n{'='*55}")
    print(f"  [OK] APPLY  -> {apply_count} jobs  (score >= {MIN_SCORE_TO_APPLY})")
    print(f"  [?] MAYBE  -> {maybe_count} jobs")
    print(f"  [SKIP] SKIP   -> {skip_count} jobs")
    print(f"{'='*55}")
    print(f"\n[TOP] TOP 10 BEST MATCHES:")
    for j in scored[:10]:
        icon = "[OK]" if j["ai_recommendation"] == "apply" else "[?]"
        print(f"  {icon} [{j['ai_score']:3}] {j['title'][:38]:38} | {j['platform']:15} | {j.get('company','?')[:18]}")

    print(f"\n[OK] Saved -> output/scored_jobs.json")
    return scored


if __name__ == "__main__":
    run_matcher()
