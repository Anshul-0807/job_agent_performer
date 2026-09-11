"""
scripts/groq_engine.py
FREE AI engine using the Groq cloud API (OpenAI-compatible).
No local install needed — just a free API key.
"""

import json, re, sys, time, httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_URL


def ask_groq(prompt: str, expect_json: bool = False, timeout: int = 120, max_tokens: int = 800,
             retries: int = 3) -> str:
    """
    Send a prompt to the Groq API and get a response.
    Uses the free tier — no local AI required.
    Auto-retries on rate limits (429) and temporary errors (5xx).
    """
    if not GROQ_API_KEY:
        print("\n[ERROR] GROQ_API_KEY is empty!")
        print("   Get a free key at https://console.groq.com/keys")
        print("   Then paste it into config/settings.py")
        return ""

    for attempt in range(1, retries + 1):
        try:
            response = httpx.post(
                f"{GROQ_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": "You reply with only the requested output, no extra text."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                    "stream": False,
                },
                timeout=timeout
            )
            if response.status_code == 429 and attempt < retries:
                print(f"   [WARN] Groq rate limit - waiting 20s (retry {attempt}/{retries})")
                time.sleep(20)
                continue
            if response.status_code >= 500 and attempt < retries:
                print(f"   [WARN] Groq server error {response.status_code} - waiting 10s (retry {attempt}/{retries})")
                time.sleep(10)
                continue
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()
            return result

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                print("\n[ERROR] Groq API key is INVALID.")
                print("   Check GROQ_API_KEY in config/settings.py")
                print("   Or get a new key at https://console.groq.com/keys")
            elif status == 429:
                if attempt < retries:
                    print(f"   [WARN] Groq rate limit - waiting 20s (retry {attempt}/{retries})")
                    time.sleep(20)
                    continue
                print("\n[ERROR] Groq rate limit reached (free tier).")
                print("   Wait a minute and try again, or reduce job count.")
            else:
                print(f"\n[ERROR] Groq API error ({status}): {e.response.text[:200]}")
            return ""
        except httpx.ConnectError:
            if attempt < retries:
                print(f"   [WARN] Cannot reach Groq API - waiting 10s (retry {attempt}/{retries})")
                time.sleep(10)
                continue
            print("\n[ERROR] Cannot reach Groq API. Check your internet connection.")
            return ""
        except Exception as e:
            print(f"   [WARN] Groq error: {e}")
            return ""

    return ""


def parse_json_response(text: str) -> dict:
    """Extract JSON from Groq response even if it adds extra text."""
    if not text:
        return {}
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # Try direct parse first
    try:
        return json.loads(text)
    except:
        pass
    # Balanced-brace extraction (handles nested JSON with arrays)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except:
            pass
    # Legacy fragment search
    patterns = [
        r'\{[^{}]*\}',           # Simple object
        r'\{.*?\}',              # Any object (non-greedy)
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
    return {}


def score_job(job: dict, profile: dict) -> dict:
    """
    Score a job against your profile using the Groq API.
    Returns score, recommendation, and a cover note.
    """
    skills = (
        profile.get("skills", {}).get("primary", []) +
        profile.get("skills", {}).get("secondary", [])
    )[:10]

    roles  = profile.get("job_preferences", {}).get("roles", [])[:5]
    exp    = profile.get("total_experience_years", 2)

    prompt = f"""You are a job matching assistant. Score this job for a candidate.

CANDIDATE:
Skills: {', '.join(skills)}
Target roles: {', '.join(roles)}
Experience: {exp} years

JOB:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Platform: {job.get('platform', '')}
Budget: {job.get('budget', 'not specified')}

Give a match score and short cover note.
Reply with ONLY this JSON, nothing else:
{{"score": 75, "recommendation": "apply", "reason": "good Python and ML match", "cover_note": "Your AI work matches my 3 years of ML experience perfectly."}}

recommendation must be: apply, maybe, or skip
score must be 0-100 integer"""

    raw = ask_groq(prompt, expect_json=True)
    result = parse_json_response(raw)

    # Apply safe defaults if parsing failed
    return {
        "ai_score":          result.get("score", 50),
        "ai_recommendation": result.get("recommendation", "maybe"),
        "ai_reason":         result.get("reason", ""),
        "ai_cover_note":     result.get("cover_note", ""),
    }


def parse_resume_text(text: str) -> dict:
    """
    Extract structured profile from resume text using Groq API.
    """
    prompt = f"""Extract information from this resume text.
Reply with ONLY this JSON structure, no other text:
{{
  "name": "",
  "email": "",
  "phone": "",
  "total_experience_years": 0,
  "skills": {{
    "primary": [],
    "secondary": [],
    "tools": []
  }},
  "current_title": "",
  "summary": ""
}}

RESUME TEXT:
{text[:2000]}"""

    raw = ask_groq(prompt, expect_json=True, timeout=180)
    result = parse_json_response(raw)

    # Fill in defaults for missing fields
    result.setdefault("name", "")
    result.setdefault("email", "")
    result.setdefault("phone", "")
    result.setdefault("total_experience_years", 2)
    result.setdefault("skills", {"primary": [], "secondary": [], "tools": []})
    result.setdefault("current_title", "QA Engineer")
    result.setdefault("summary", "")
    return result


def test_groq() -> bool:
    """Check that the Groq API key works and the model is available."""
    if not GROQ_API_KEY:
        print("\n[ERROR] GROQ_API_KEY is empty!")
        print("   Get a free key at https://console.groq.com/keys")
        print("   Then paste it into config/settings.py")
        return False
    try:
        r = httpx.get(
            f"{GROQ_URL}/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=15
        )
        if r.status_code == 401:
            print("[ERROR] Groq API key is INVALID.")
            print("   Check GROQ_API_KEY in config/settings.py")
            return False
        r.raise_for_status()
        models = [m["id"] for m in r.json().get("data", [])]
        if GROQ_MODEL not in models:
            print(f"[WARN] Model '{GROQ_MODEL}' not available on your Groq account.")
            print(f"   Available: {', '.join(models[:10])}")
            print("   Update GROQ_MODEL in config/settings.py")
            return False
        print(f"[OK] Groq API connected | Model: {GROQ_MODEL}")
        return True
    except Exception as e:
        print(f"[ERROR] Groq API check failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing Groq API connection...")
    if test_groq():
        print("\nSending test prompt...")
        result = ask_groq("Reply with only the word: WORKING")
        print(f"Response: {result}")