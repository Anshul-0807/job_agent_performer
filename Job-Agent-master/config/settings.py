# ============================================================
#  config/settings.py  —  AI Job Agent (FREE - Groq Version)
#  Free API tier. No local installs needed.
# ============================================================

# ── GROQ API (FREE cloud AI — no local install needed) ────────
# Get a free API key: https://console.groq.com/keys  (no credit card)
# Paste your key inside the quotes below:
GROQ_API_KEY = "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"

# Free models on Groq (as of 2026):
# llama-3.3-70b-versatile → best quality (default)
# llama-3.1-8b-instant    → faster, lighter
# qwen3-32b               → good alternative
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_URL   = "https://api.groq.com/openai/v1"

# ── YOUR PERSONAL DETAILS ────────────────────────────────────
# REPLACE THESE WITH YOUR ACTUAL DETAILS
YOUR_NAME       = "Gyaneshwar Chouhan"
YOUR_EMAIL      = "gyaneshwarchouhan123@gmail.com"
YOUR_PHONE      = "+91-8793024246"
YOUR_LOCATION   = "Surat, India"
YOUR_LINKEDIN   = "https://linkedin.com/in/gyaneshwar-chouhan-49bb85403"
YOUR_GITHUB     = ""
YOUR_PORTFOLIO  = ""
AVAILABILITY    = "Immediate Joiner"   # Used in cover letters + application forms
RESUME_PATH     = r"config\resume.pdf"

# ── YOUR LOCATION DETAILS (used in application forms) ────────
YOUR_CITY       = "Surat"
YOUR_STATE      = "Gujarat"
YOUR_COUNTRY    = "India"

# ── SALARY (used in application forms) ───────────────────────
CURRENT_CTC     = "6 LPA"    # Filled in "current salary" fields
EXPECTED_CTC    = "7 LPA"    # Filled in "expected/desired salary" fields

# ── JOB PREFERENCES ──────────────────────────────────────────
TARGET_ROLES = [
    "QA Engineer",
    "QA Analyst",
    "Software QA Engineer",
    "Software Test Engineer",
    "Test Engineer",
    "Manual Tester",
    "Manual QA Engineer",
    "QA Tester",
    "Software Tester",
    "API Tester",
    "API Test Engineer",
    "QA Automation Engineer",
    "Automation QA Engineer",
    "QA Automation Tester",
    "Automation Test Engineer",
    "Test Automation Engineer",
    "Automation Tester",
    "SDET",
    "Performance Test Engineer",
    "Mobile QA Engineer",
    "Quality Engineer",
    "Quality Assurance Engineer",
    "Test Analyst",
    "QA Engineer - Manual & Automation",
    "Software Test Analyst",
    "Software Quality Analyst",
    "QA",
    "Tester",
    "Quality Analyst",
    "Selenium Tester",
]

# ── PLATFORMS (True = enabled) ───────────────────────────────
PLATFORMS = {
    "linkedin":       True,
    "naukri":         True,
    "indeed":         True,
    "glassdoor":      False,
    "wellfound":      False,
    "weworkremotely": False,
    "remoteco":       False,
    "arcdev":         False,
    "yc_jobs":        False,
    "upwork":         False,
    "freelancer":     False,
    "peopleperhour":  False,
    "guru":           False,
    "timesjobs":      False,
    "shine":          False,
    "instahyre":      False,
    "cutshort":       False,
    "foundit":        False,
    "hirist":         False,
    "internshala":    False,
    "freshersworld":  False,
    "ambitionbox":    False,
    "hasjob":         False,
    "iimjobs":        False,
}

# ── CHROME PROFILE ───────────────────────────────────────────
# Open Chrome → go to chrome://version → copy "Profile Path"
# Remove "\Default" from the end
# Example: C:\Users\YourName\AppData\Local\Google\Chrome\User Data
CHROME_USER_DATA_DIR = r"C:\Users\91929\AppData\Local\Google\Chrome\User Data"
CHROME_PROFILE       = "Default"

# ── APPLY SETTINGS ───────────────────────────────────────────
MIN_SCORE_TO_APPLY   = 60     # Apply to jobs scoring 60+ (lower = more applications)
MAX_APPLY_PER_RUN    = 25     # Max per session (be safe)
DELAY_BETWEEN_APPLY  = 5      # Seconds between applications
DRY_RUN              = False  # True = don't actually submit
HEADLESS             = False  # False = watch browser work

# ── FREELANCE RATES ──────────────────────────────────────────
HOURLY_RATE_USD = "20"
FIXED_BID_MIN   = "50"

# ── COVER LETTER BASE ────────────────────────────────────────
COVER_LETTER_BASE = """
I am a passionate QA Engineer with hands-on experience in manual 
and automation testing. I specialize in test planning, test case 
design, API testing, and delivering bug-free, production-ready 
software. I am an immediate joiner and can start right away. 
I would love to contribute to your team.
"""
