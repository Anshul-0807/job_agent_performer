# 🤖 AI Job Agent - (Groq API Powered)

**Zero cost. No local AI downloads. No credit card needed.**  
**Built for:** Windows | Chrome | QA Engineer / Manual Tester roles  

---

## 📁 All Files

```
job-agent-free/
├── SETUP.bat                    ← Run this FIRST (one time)
├── RUN.bat                      ← Run this every time
├── main.py                      ← Main Python script
├── config/
│   ├── settings.py              ← ⭐ FILL THIS IN FIRST
│   ├── profile.json             ← Auto-created from your resume
│   └── resume.pdf               ← Put your resume here
├── scripts/
│   ├── groq_engine.py            ← FREE AI brain (Groq cloud API)
│   ├── resume_parser.py         ← Reads your resume
│   ├── browser_manager.py       ← Opens Chrome with your logins
│   ├── job_scraper.py           ← Finds jobs on 13 platforms
│   ├── ai_matcher.py            ← Scores jobs with Groq
│   └── auto_applier.py          ← Applies automatically
├── output/
│   ├── scraped_jobs.json        ← All jobs found
│   ├── scored_jobs.json         ← Jobs ranked by AI
│   └── applied_jobs.json        ← Your applications log
└── logs/
    └── apply_log.txt            ← Text log of applications
```

---

## ⚡ Setup — Do This Once (About 15 Minutes)

### 1. Get a Free Groq API Key (takes 2 minutes)
1. Go to **https://console.groq.com/keys**
2. Sign up for a free account (no credit card needed)
3. Click **Create API Key** and copy it (starts with `gsk_`)
4. Open `config\settings.py` and paste it into `GROQ_API_KEY`

### 2. Run Setup
Double-click **SETUP.bat**  
This installs Python packages and sets up folders.

### 3. Fill in Your Details
Open `config\settings.py` in Notepad and fill in:

```python
GROQ_API_KEY = "gsk_your_key_here"    # From step 1
YOUR_NAME  = "Your Full Name"          # Your real name
YOUR_EMAIL = "your.email@example.com"  # Your email
YOUR_PHONE = "+91-9876543210"          # Your phone

# Find this: Open Chrome → type chrome://version → copy Profile Path
# Remove \Default from the end of the path
CHROME_USER_DATA_DIR = r"C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data"
```

### 4. Add Your Resume
Copy your resume PDF into the `config\` folder.  
Rename it to `resume.pdf`

### 5. Log Into Job Platforms in Chrome
Open Chrome and make sure you are logged into:
- LinkedIn (linkedin.com)
- Naukri (naukri.com)
- Indeed (indeed.com)
- Upwork (upwork.com) — if using
- Freelancer (freelancer.com) — if using

The agent uses your saved Chrome logins. No passwords stored anywhere.

---

## 🚀 Running The Agent

### Easy Way — Double-click RUN.bat
A menu appears:
```
[1] FULL RUN     → Scrape + Score + Apply
[2] DRY RUN      → Test run, no real applications  ← START HERE
[3] SCRAPE ONLY  → Just find jobs
[4] APPLY ONLY   → Apply from last results
[5] RE-SCORE     → Score jobs again
[6] HIGH QUALITY → Only score 75+ jobs
```

**Always choose [2] DRY RUN first!**  
Check `output\scored_jobs.json` to see what it found.  
Then choose [1] FULL RUN for real applications.

### Command Line
```batch
python main.py                              # Full run
python main.py --dry-run                    # Test only
python main.py --resume config\resume.pdf  # New resume
python main.py --scrape-only               # Find jobs only
python main.py --min-score 75              # High quality only
```

---

## 🌐 Platforms Covered (24 Total)

| Platform | Type | Auto-Apply |
|----------|------|-----------|
| LinkedIn | Jobs | ✅ Easy Apply |
| Naukri | Jobs | ✅ |
| Indeed | Jobs | ✅ |
| Glassdoor | Jobs | 🔍 Scrapes only |
| Wellfound | Startup Jobs | ✅ |
| YC Jobs | Startup Jobs | 🔍 Scrapes only |
| WeWorkRemotely | Remote | 🔍 Scrapes only |
| Remote.co | Remote | 🔍 Scrapes only |
| Arc.dev | Remote Dev | 🔍 Scrapes only |
| Upwork | Freelance | ✅ Proposal |
| Freelancer | Freelance | ✅ Bid |
| PeoplePerHour | Freelance | ✅ Bid |
| Guru | Freelance | ✅ Quote |
| TimesJobs | India Jobs | 🔍 Scrapes only |
| Shine.com | India Jobs | 🔍 Scrapes only |
| Instahyre | India Jobs | 🔍 Scrapes only |
| Cutshort | India Jobs | 🔍 Scrapes only |
| Foundit | India Jobs | 🔍 Scrapes only |
| Hirist | India IT Jobs | 🔍 Scrapes only |
| Internshala | India Fresher Jobs | 🔍 Scrapes only |
| Freshersworld | India Fresher Jobs | 🔍 Scrapes only |
| AmbitionBox | India Jobs | 🔍 Scrapes only |
| Hasjob | India Startup Jobs | 🔍 Scrapes only |
| iimjobs | India Jobs | 🔍 Scrapes only |

---

## 🧠 How the FREE AI Works

Instead of paying for ChatGPT or Claude API, this uses **Groq** — a free cloud AI that runs fast open-source models on their super-fast chips.

The model `llama-3.3-70b-versatile` is a strong model that:
- Reads your resume and extracts your skills
- Reads each job listing
- Gives a score 0-100 based on how well it matches you
- Writes a personalized cover note for each job

**No downloads, no local installs.** The free tier gives ~1,000 requests/day for this model — plenty for a full job hunt.

---

## ⚠️ Important 

- The default model is `llama-3.3-70b-versatile` — great quality and free
- If you hit rate limits, wait a minute and try again, or switch to `llama-3.1-8b-instant` in settings.py (faster, lighter)
- Scoring jobs is FAST with Groq — seconds, not minutes
- Free tier limits: ~30 requests/minute per model — normal usage is fine

---

## 🔧 Troubleshooting

**"GROQ_API_KEY is empty"**
→ Open config\settings.py and paste your key from https://console.groq.com/keys

**"API key is INVALID" (error 401)**
→ Double-check you copied the full key (starts with `gsk_`)
→ Generate a new key at https://console.groq.com/keys

**"Rate limit reached" (error 429)**
→ Free tier is limited — wait a minute and run again
→ Or switch to `llama-3.1-8b-instant` in settings.py

**Chrome profile not opening**
→ Make sure Chrome is fully closed before running the agent
→ Double-check CHROME_USER_DATA_DIR in settings.py

**"Login required" on LinkedIn/Naukri**
→ Open Chrome, log in manually, then close Chrome and run agent

**Low storage warning**
→ Delete `output\scraped_jobs.json` between runs (it regenerates)
→ Keep only `applied_jobs.json` permanently
