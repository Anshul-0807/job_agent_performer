"""Smoke test: AI form mapping with a mock LinkedIn Easy Apply form."""
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.auto_applier import build_ai_answers
from scripts.groq_engine import ask_groq, parse_json_response

JOB = {"title": "QA Engineer", "company": "TCS", "platform": "LinkedIn"}

FIELDS = {
    "inputs": [
        {"name": "experience", "id": "exp", "ph": "Years of experience", "label": "Years of experience", "value": ""},
        {"name": "location", "id": "", "ph": "City", "label": "Current city", "value": ""},
        {"name": "expectedSalary", "id": "", "ph": "", "label": "Expected salary (LPA)", "value": ""},
        {"name": "currentSalary", "id": "", "ph": "", "label": "Current salary (LPA)", "value": ""},
    ],
    "selects": [
        {"name": "noticePeriod", "id": "", "label": "Notice period",
         "options": ["15 days", "30 days", "60 days", "90 days", "Immediate"], "value": ""},
        {"name": "heard", "id": "", "label": "How did you hear about us",
         "options": ["LinkedIn", "Naukri", "Referral", "Other"], "value": ""},
    ],
    "textareas": [
        {"name": "why", "id": "", "label": "Why do you want to join TCS?", "value": ""},
    ],
    "radios": {
        "relocate": [
            {"value": "true", "label": "Yes, I can relocate"},
            {"value": "false", "label": "No"},
        ],
        "auth": [
            {"value": "1", "label": "Authorized to work in India"},
            {"value": "0", "label": "Not authorized"},
        ],
    },
    "checkboxes": {
        "skills": [
            {"value": "manual", "label": "Manual Testing", "checked": False},
            {"value": "auto", "label": "Automation Testing (Selenium)", "checked": False},
            {"value": "devops", "label": "DevOps / Kubernetes", "checked": False},
            {"value": "api", "label": "API Testing (Postman)", "checked": False},
        ],
    },
}

def safe(s):
    return (s or "").encode("ascii", "replace").decode()

async def main():
    import importlib
    from scripts import auto_applier
    importlib.reload(auto_applier)
    answers = auto_applier.build_ai_answers(JOB)
    print("ANSWERS:", safe(json.dumps(answers, ensure_ascii=False)[:300]))

    prompt = f"""You fill job application forms for a candidate. Never invent data.

CANDIDATE ANSWERS (JSON):
{json.dumps(answers, ensure_ascii=False)}

JOB: {JOB['title']} at {JOB['company']} ({JOB['platform']})

EMPTY FORM FIELDS (JSON):
{json.dumps(FIELDS, ensure_ascii=False)}

Rules:
- Expected/desired salary question -> expected_ctc. Current salary question -> current_ctc.
- Location/city/state/country -> candidate values. Relocation -> relocation answer.
- "How did you hear" -> heard_about. Work authorization -> work_auth.
- Notice period / joining / availability -> notice_period.
- Yes/No questions -> "Yes" only if candidate clearly qualifies, else "No". If unsure -> "".
- Dropdown: reply with the EXACT option text from the options list that fits best.
- Radio questions: reply with the EXACT option label text from the radio group list.
- Checkboxes (select-all-that-apply): reply with an ARRAY of EXACT option labels the candidate
  clearly qualifies for (e.g. skills/tools they have). Select NONE if unsure. Never select all.
- Textareas: answer the question in 1-2 short professional sentences from candidate info
  (e.g. "Why interested in this role/company?" -> mention interest in the role). Leave "" if unsure.
- Any field you cannot answer confidently -> "" (empty). Never invent.

Reply ONLY this JSON:
{{"inputs": {{"<input index>": "value"}}, "selects": {{"<select index>": "exact option text"}},
  "textareas": {{"<textarea index>": "answer"}}, "radios": {{"<radio group name>": "exact option label or value"}},
  "checkboxes": {{"<checkbox group name>": ["exact option label", ...]}}}}
Inputs/selects/textareas indices start at 0 in the order listed above."""

    raw = ask_groq(prompt, expect_json=True, timeout=60, max_tokens=2000)
    Path("C:/Users/91929/AppData/Local/Temp/opencode/raw_form.json").write_text(raw or "", encoding="utf-8")
    print("\nRAW:", safe(raw[:500]))
    mapping = parse_json_response(raw)
    print("\nMAPPING:", json.dumps(mapping, ensure_ascii=False, indent=2))

    expected = [
        ("inputs", "0", "3"),
        ("inputs", "1", "Surat"),
        ("inputs", "2", "7"),
        ("inputs", "3", "6"),
        ("selects", "0", "Immediate"),
        ("selects", "1", "LinkedIn"),
        ("radios", "relocate", "relocate"),
        ("radios", "auth", "authorized"),
        ("checkboxes", "skills", "manual"),
    ]
    ok = True
    for cat, key, want in expected:
        got = None
        if cat == "inputs" and mapping.get("inputs"):
            got = mapping["inputs"].get(key)
        elif cat == "selects" and mapping.get("selects"):
            got = mapping["selects"].get(key)
        elif cat == "radios" and mapping.get("radios"):
            got = mapping["radios"].get(key)
        elif cat == "checkboxes" and mapping.get("checkboxes"):
            got = mapping["checkboxes"].get(key)
        if cat == "radios":
            status = "OK " if got else "FAIL"
        elif cat == "checkboxes":
            status = "OK " if (got and any(want.lower() in str(o).lower() for o in got)) else "FAIL"
        else:
            status = "OK " if (got and want.lower() in str(got).lower()) else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  [{status}] {cat}[{key}] -> got={got!r} want~{want!r}")
    print("\nRESULT:", "PASS" if ok else "PARTIAL (review above)")

asyncio.run(main())