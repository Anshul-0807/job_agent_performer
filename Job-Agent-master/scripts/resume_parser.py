"""
scripts/resume_parser.py
Parses your resume PDF using the free Groq cloud API.
No local AI needed — just a free API key.
"""

import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import RESUME_PATH, TARGET_ROLES, YOUR_NAME, YOUR_EMAIL, YOUR_PHONE
from scripts.groq_engine import parse_resume_text, test_groq

PROFILE_OUT = Path("config/profile.json")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from PDF resume."""
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except ImportError:
        print("   Installing pypdf...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "pypdf", "--quiet"], check=True)
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"   [WARN] PDF read error: {e}")
        return ""


def parse_resume(pdf_path: str = None) -> dict:
    path = Path(pdf_path or RESUME_PATH)

    if not path.exists():
        print(f"[WARN] Resume not found at: {path}")
        print("   Using your settings.py details as profile instead.")
        return _manual_profile()

    print(f"[INFO] Reading resume: {path.name}")
    text = extract_text_from_pdf(str(path))

    if not text:
        print("   Could not read PDF text. Using manual profile.")
        return _manual_profile()

    print(f"   Extracted {len(text)} characters")
    print("   Asking Groq AI to parse your resume... (takes a few seconds)")

    if not test_groq():
        print("   [WARN] Groq API not configured — using manual profile")
        return _manual_profile()

    profile = parse_resume_text(text)

    # Override with settings.py values if Groq missed them
    if not profile.get("name"):
        profile["name"] = YOUR_NAME
    if not profile.get("email"):
        profile["email"] = YOUR_EMAIL
    if not profile.get("phone"):
        profile["phone"] = YOUR_PHONE

    # Always add job preferences from settings
    profile["job_preferences"] = {
        "roles": TARGET_ROLES,
        "type": ["remote", "full-time", "contract", "freelance"],
    }

    PROFILE_OUT.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    print("[OK] Profile saved -> config/profile.json")
    print(f"   Name     : {profile.get('name', '?')}")
    print(f"   Skills   : {', '.join(profile.get('skills', {}).get('primary', [])[:5])}")
    print(f"   Exp      : {profile.get('total_experience_years', '?')} years")
    return profile


def _manual_profile() -> dict:
    """
    Build profile manually from settings.py when no resume PDF exists.
    Edit config/settings.py to update your skills.
    """
    profile = {
        "name":  YOUR_NAME,
        "email": YOUR_EMAIL,
        "phone": YOUR_PHONE,
        "total_experience_years": 2,
        "current_title": "QA Engineer",
        "skills": {
            "primary":   ["Manual Testing", "API Testing", "Test Cases", "Bug Reporting", "Test Planning"],
            "secondary": ["Selenium", "Postman", "JIRA", "SQL", "JMeter"],
            "tools":     ["Git", "TestRail", "Browser DevTools", "Swagger", "Charles Proxy"],
        },
        "job_preferences": {
            "roles": TARGET_ROLES,
            "type":  ["remote", "full-time", "contract", "freelance"],
        }
    }
    PROFILE_OUT.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    print("[OK] Default QA profile created -> config/profile.json")
    print("   Edit config/profile.json to add your real skills!")
    return profile


if __name__ == "__main__":
    parse_resume(sys.argv[1] if len(sys.argv) > 1 else None)
