"""
scripts/auto_applier.py
Auto-applies to jobs using your existing Chrome logins.
Handles LinkedIn Easy Apply, Naukri, Indeed, Wellfound,
Upwork proposals, Freelancer bids, PeoplePerHour, Guru.
"""

import asyncio, json, sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    YOUR_NAME, YOUR_EMAIL, YOUR_PHONE,
    YOUR_LINKEDIN, YOUR_GITHUB, YOUR_PORTFOLIO,
    YOUR_CITY, YOUR_STATE, YOUR_COUNTRY,
    CURRENT_CTC, EXPECTED_CTC,
    AVAILABILITY, RESUME_PATH, COVER_LETTER_BASE,
    HOURLY_RATE_USD, FIXED_BID_MIN,
    MIN_SCORE_TO_APPLY, MAX_APPLY_PER_RUN,
    DELAY_BETWEEN_APPLY, DRY_RUN
)
from scripts.browser_manager import get_browser_context, new_stealth_page
from scripts.groq_engine import ask_groq, parse_json_response
from scripts.stop_manager import stop_requested

SCORED_FILE  = Path("output/scored_jobs.json")
APPLIED_FILE = Path("output/applied_jobs.json")
LOG_FILE     = Path("logs/apply_log.txt")


# ── Logging ────────────────────────────────────────────────

def load_applied_urls() -> set:
    if APPLIED_FILE.exists():
        data = json.loads(APPLIED_FILE.read_text())
        return {j.get("url", "") for j in data}
    return set()

def save_result(job: dict, status: str, note: str = ""):
    APPLIED_FILE.parent.mkdir(exist_ok=True)
    LOG_FILE.parent.mkdir(exist_ok=True)
    existing = json.loads(APPLIED_FILE.read_text()) if APPLIED_FILE.exists() else []
    existing.append({**job, "apply_status": status, "note": note,
                     "applied_at": datetime.now().isoformat()})
    APPLIED_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        t = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"[{t}] {status.upper():8} | {job['platform']:15} | {job['title'][:40]} @ {job.get('company','?')[:20]}\n")


# ── Form helpers ───────────────────────────────────────────

async def fill_text_fields(page: Page):
    """Fill common text fields across any apply form."""
    mappings = [
        (["firstName", "first_name", "fname"],   YOUR_NAME.split()[0]),
        (["lastName",  "last_name",  "lname"],   YOUR_NAME.split()[-1] if len(YOUR_NAME.split()) > 1 else ""),
        (["fullName",  "full_name",  "name"],    YOUR_NAME),
        (["email"],                               YOUR_EMAIL),
        (["phone", "mobile", "phoneNumber"],      YOUR_PHONE),
        (["linkedin"],                            YOUR_LINKEDIN),
        (["github"],                              YOUR_GITHUB),
        (["portfolio", "website"],                YOUR_PORTFOLIO),
        (["notice", "joining", "availability", "join"], AVAILABILITY),
        (["currentSalary", "currentsalary", "currentCtc", "currentctc"], CURRENT_CTC),
        (["expectedSalary", "expectedsalary", "expectedCtc", "expectedctc", "desired"], EXPECTED_CTC),
        (["salary", "ctc", "compensation"],       EXPECTED_CTC),
        (["city"],                                YOUR_CITY),
        (["state"],                               YOUR_STATE),
        (["country"],                             YOUR_COUNTRY),
        (["location", "address"],                 f"{YOUR_CITY}, {YOUR_COUNTRY}"),
        (["experience", "years"],                 "3"),
    ]
    for keys, value in mappings:
        if not value:
            continue
        for key in keys:
            try:
                selectors = [
                    f"input[name*='{key}' i]",
                    f"input[id*='{key}' i]",
                    f"input[placeholder*='{key}' i]",
                ]
                for sel in selectors:
                    for el in await page.query_selector_all(sel):
                        if await el.is_visible() and not await el.input_value():
                            await el.fill(value)
                            break
            except:
                pass

async def fill_radios_and_selects(page: Page):
    """Auto-answer yes/no radio questions (dropdowns are handled by AI)."""
    try:
        for radio in await page.query_selector_all("input[type='radio']"):
            val = (await radio.get_attribute("value") or "").lower()
            if val in ["yes", "true", "1", "authorized", "eligible", "agree"]:
                if not await radio.is_checked():
                    await radio.check()
    except: pass

async def upload_resume(page: Page):
    try:
        fi = await page.query_selector("input[type='file']")
        if fi and Path(RESUME_PATH).exists():
            await fi.set_input_files(RESUME_PATH)
            await asyncio.sleep(1)
    except: pass

async def fill_cover_letter(page: Page, job: dict):
    note = job.get("ai_cover_note") or COVER_LETTER_BASE.strip()
    try:
        for ta in await page.query_selector_all("textarea"):
            if await ta.is_visible() and not await ta.input_value():
                await ta.fill(note)
                break
    except: pass


# ── AI-driven form filling ─────────────────────────────────

FORM_FIELDS_JS = """() => {
  const clean = s => (s || '').replace(/\\s+/g, ' ').trim().slice(0, 120);
  const labelOf = el => {
    try {
      if (el.labels && el.labels[0]) return clean(el.labels[0].innerText);
      const wrap = el.closest('label');
      if (wrap) return clean(wrap.innerText);
      const id = el.id;
      if (id) {
        const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
        if (lab) return clean(lab.innerText);
      }
    } catch (e) {}
    return clean(el.getAttribute('aria-label')) || clean(el.getAttribute('placeholder'));
  };
  const inputs = [], selects = [], textareas = [], radios = {}, checkboxes = {};
  document.querySelectorAll('input').forEach(el => {
    const t = (el.type || '').toLowerCase();
    if (['hidden','submit','button','file'].includes(t)) return;
    if (!el.offsetParent) return;
    if (t === 'radio') {
      const name = el.name || '';
      if (!radios[name]) radios[name] = [];
      radios[name].push({ value: clean(el.value), label: labelOf(el) });
      return;
    }
    if (t === 'checkbox') {
      const name = el.name || 'cb_' + (el.id || 'cb_' + (el.value || ''));
      if (!checkboxes[name]) checkboxes[name] = [];
      checkboxes[name].push({ value: clean(el.value), label: labelOf(el), checked: !!el.checked });
      return;
    }
    inputs.push({ name: el.name || '', id: el.id || '', ph: el.getAttribute('placeholder') || '', label: labelOf(el), value: el.value || '' });
  });
  document.querySelectorAll('select').forEach(el => {
    if (!el.offsetParent) return;
    const opts = [...el.options].slice(0, 25).map(o => clean(o.text)).filter(Boolean);
    selects.push({ name: el.name || '', id: el.id || '', label: labelOf(el), options: opts, value: el.value || '' });
  });
  document.querySelectorAll('textarea').forEach(el => {
    if (!el.offsetParent) return;
    textareas.push({ name: el.name || '', id: el.id || '', label: labelOf(el), value: el.value || '' });
  });
  return { inputs, selects, textareas, radios, checkboxes };
}"""


async def extract_form_fields(page: Page) -> dict:
    """Extract visible form fields (only empty ones) via JS."""
    try:
        fields = await page.evaluate(FORM_FIELDS_JS)
        empty = {
            "inputs":    [f for f in fields["inputs"]    if not f["value"]][:40],
            "selects":   [f for f in fields["selects"]   if not f["value"]][:15],
            "textareas": [f for f in fields["textareas"] if not f["value"]][:10],
            "radios":    {k: v[:8] for k, v in list(fields["radios"].items())[:10]},
            "checkboxes": {k: v[:8] for k, v in list(fields["checkboxes"].items())[:10]},
        }
        return empty
    except Exception:
        return {"inputs": [], "selects": [], "textareas": [], "radios": {}, "checkboxes": {}}


_AI_ANSWERS = None

def build_ai_answers(job: dict) -> dict:
    """Build the candidate answer bank used by the AI to fill forms."""
    global _AI_ANSWERS
    if _AI_ANSWERS is None:
        profile = {}
        try:
            f = Path("config/profile.json")
            if f.exists():
                profile = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
        skills = profile.get("skills", {}).get("primary", [])[:6]
        _AI_ANSWERS = {
            "name":           YOUR_NAME,
            "email":          YOUR_EMAIL,
            "phone":          YOUR_PHONE,
            "linkedin":       YOUR_LINKEDIN,
            "location":       f"{YOUR_CITY}, {YOUR_STATE}, {YOUR_COUNTRY}",
            "city":           YOUR_CITY,
            "state":          YOUR_STATE,
            "country":        YOUR_COUNTRY,
            "current_ctc":    CURRENT_CTC,
            "expected_ctc":   EXPECTED_CTC,
            "notice_period":  AVAILABILITY,
            "experience":     f"{profile.get('total_experience_years', 3)} years",
            "current_title":  profile.get("current_title", "QA Engineer"),
            "skills":         ", ".join(skills),
            "relocation":     "Yes, I am willing to relocate anywhere in India",
            "heard_about":    job.get("platform", "LinkedIn"),
            "work_auth":      "Yes, I am authorized to work in India",
            "employment":     "Currently employed, immediate joiner",
            "summary":        profile.get("summary", "")[:300],
        }
    return _AI_ANSWERS


# ── Validation guards (never fill a wrong answer) ───────────

def _norm(s):
    return str(s or "").strip().lower()


def _valid_text_value(value, bank):
    """Text answer is allowed ONLY if it comes from the candidate answer bank."""
    v = _norm(value)
    if not v:
        return False
    return any(v in b for b in bank)


def _valid_option_value(value, option_texts):
    """Dropdown/radio/checkbox answer is allowed ONLY if it matches the field's own options."""
    t = _norm(value)
    if not t:
        return False
    for o in option_texts:
        o = _norm(o)
        if not o:
            continue
        if t == o:
            return True
        if len(t) >= 3 and t in o:
            return True
        if len(o) >= 3 and o in t:
            return True
    return False


async def ai_fill_form(page: Page, job: dict):
    """Ask Groq to map remaining empty form fields to the candidate profile."""
    fields = await extract_form_fields(page)
    total = (len(fields["inputs"]) + len(fields["selects"]) + len(fields["textareas"])
             + len(fields["radios"]) + len(fields["checkboxes"]))
    if total == 0:
        return

    import json as _json
    prompt = f"""You fill job application forms for a candidate. Never invent data.

CANDIDATE ANSWERS (JSON):
{_json.dumps(build_ai_answers(job), ensure_ascii=False)}

JOB: {job.get('title','')} at {job.get('company','')} ({job.get('platform','')})

EMPTY FORM FIELDS (JSON):
{_json.dumps(fields, ensure_ascii=False)}

Rules:
- Use the EXACT candidate answer string from the answers JSON.
- Salary fields: if the field label mentions salary/CTC/compensation/LPA and the answer is a bare number, append " LPA" (e.g. "7 LPA"). Current salary -> current_ctc, expected/desired -> expected_ctc.
- Location/city/state/country -> candidate values. Relocation -> relocation answer.
- "How did you hear" -> heard_about. Work authorization -> work_auth.
- Notice period / joining / availability -> notice_period.
- Yes/No questions -> "Yes" only if candidate clearly qualifies, else "No". If unsure -> "".
- Dropdown: reply with the EXACT option text from the options list that fits best.
- Radio questions: reply with the EXACT option label text from the radio group list.
- Checkboxes (select-all-that-apply): reply with an ARRAY of EXACT option labels the candidate
  clearly qualifies for (e.g. skills/tools they have). Select NONE if unsure. Never select all.
- Textareas: answer the question in at most 2 short professional sentences (under 180 chars),
  using candidate info (e.g. "Why interested in this role/company?" -> mention interest in the role).
  Leave "" if unsure.
- Any field you cannot answer confidently -> "" (empty). Never invent.

Reply ONLY this JSON (complete, not truncated):
{{"inputs": {{"<input index>": "value"}}, "selects": {{"<select index>": "exact option text"}},
  "textareas": {{"<textarea index>": "answer"}}, "radios": {{"<radio group name>": "exact option label or value"}},
  "checkboxes": {{"<checkbox group name>": ["exact option label", ...]}}}}
Inputs/selects/textareas indices start at 0 in the order listed above."""

    try:
        raw = ask_groq(prompt, expect_json=True, timeout=60, max_tokens=2000)
    except Exception as e:
        print(f"     [WARN] AI form mapping failed: {e}")
        return
    if not raw:
        return

    mapping = parse_json_response(raw)
    if not mapping:
        print("     [WARN] AI form mapping: no usable reply")
        return

    answers = build_ai_answers(job)
    bank = [_norm(v) for v in answers.values() if v]
    filled = skipped = 0

    # Text inputs (value must come from the answer bank - no invented data)
    try:
        els = await page.query_selector_all("input")
        for idx, value in (mapping.get("inputs") or {}).items():
            if not value or not _valid_text_value(value, bank):
                if value:
                    skipped += 1
                continue
            i = int(idx)
            if i >= len(els):
                continue
            el = els[i]
            t = (await el.get_attribute("type") or "").lower()
            if t in ("hidden", "submit", "button", "checkbox", "file", "radio"):
                continue
            if await el.is_visible() and not await el.input_value():
                await el.fill(str(value))
                filled += 1
    except Exception as e:
        print(f"     [WARN] AI fill inputs: {e}")

    # Selects (must match one of the field's own options)
    try:
        els = await page.query_selector_all("select")
        for idx, value in (mapping.get("selects") or {}).items():
            if not value:
                continue
            i = int(idx)
            if i >= len(els):
                continue
            opts = fields["selects"][i].get("options", []) if i < len(fields["selects"]) else []
            if not _valid_option_value(value, opts):
                skipped += 1
                continue
            el = els[i]
            if not await el.is_visible() or await el.input_value():
                continue
            try:
                await el.select_option(label=str(value))
                filled += 1
            except Exception:
                try:
                    await el.select_option(value=str(value))
                    filled += 1
                except Exception:
                    pass
    except Exception as e:
        print(f"     [WARN] AI fill selects: {e}")

    # Textareas (only 2 max per step, skip cover-letter-like fields)
    try:
        els = await page.query_selector_all("textarea")
        done = 0
        for idx, value in (mapping.get("textareas") or {}).items():
            if not value or done >= 2:
                continue
            i = int(idx)
            if i >= len(els):
                continue
            el = els[i]
            if not await el.is_visible() or await el.input_value():
                continue
            label = ((await el.get_attribute("placeholder")) or "") + ((await el.get_attribute("aria-label")) or "")
            if any(k in label.lower() for k in ("cover", "letter", "message", "note")):
                continue
            await el.fill(str(value))
            filled += 1
            done += 1
    except Exception as e:
        print(f"     [WARN] AI fill textareas: {e}")

    # Radio groups (must match one of the group's own options)
    try:
        for group, option in (mapping.get("radios") or {}).items():
            if not option:
                continue
            group_opts = fields["radios"].get(group, [])
            texts = [o.get("value", "") for o in group_opts] + [o.get("label", "") for o in group_opts]
            if not _valid_option_value(option, texts):
                skipped += 1
                continue
            picked = await page.evaluate(
                """([g, opt]) => {
                    const radios = [...document.querySelectorAll(`input[type='radio'][name='${g}']`)];
                    const clean = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
                    const target = clean(opt);
                    const labOf = r => {
                        const l = r.closest('label');
                        return l ? clean(l.innerText) : '';
                    };
                    for (const r of radios) {
                        const lab = labOf(r);
                        if (clean(r.value) === target || (lab && (lab === target || lab.includes(target)))) {
                            if (!r.checked) r.click();
                            return true;
                        }
                    }
                    // Fallback: yes/authorized-style short answers
                    if (['yes','true','1','authorized','eligible','agree','can','willing'].includes(target)) {
                        for (const r of radios) {
                            const lab = labOf(r);
                            if (['yes','true','authorized','eligible','agree','can relocate','willing to relocate'].some(t => lab.includes(t))) {
                                if (!r.checked) r.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }""",
                [group, option],
            )
            if picked:
                filled += 1
    except Exception as e:
        print(f"     [WARN] AI fill radios: {e}")

    # Checkbox groups (select-all-that-apply, only options the candidate qualifies for)
    try:
        for group, options in (mapping.get("checkboxes") or {}).items():
            if not options:
                continue
            group_opts = fields["checkboxes"].get(group, [])
            texts = [o.get("value", "") for o in group_opts] + [o.get("label", "") for o in group_opts]
            valid = [o for o in options if _valid_option_value(o, texts)]
            if not valid:
                skipped += 1
                continue
            clicked = await page.evaluate(
                """([g, opts]) => {
                    const boxes = [...document.querySelectorAll(`input[type='checkbox'][name='${g}']`)];
                    const clean = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
                    const targets = opts.map(clean).filter(Boolean);
                    let n = 0;
                    for (const b of boxes) {
                        if (b.checked) continue;
                        let lab = '';
                        const l = b.closest('label');
                        if (l) lab = clean(l.innerText);
                        if (targets.some(t => clean(b.value) === t || (lab && (lab === t || lab.includes(t))))) {
                            b.click();
                            n++;
                        }
                    }
                    return n;
                }""",
                [group, valid],
            )
            if clicked:
                filled += clicked
    except Exception as e:
        print(f"     [WARN] AI fill checkboxes: {e}")

    if filled:
        print(f"     [AI] Filled {filled} fields via AI")
    if skipped:
        print(f"     [AI] Skipped {skipped} unknown fields - left empty (no guessing)")


async def log_manual_todo(job: dict):
    """Log external-apply / manual-review jobs so the user can apply by hand."""
    try:
        f = Path("logs/manual_todo.txt")
        f.parent.mkdir(exist_ok=True)
        line = (f"{datetime.now():%Y-%m-%d %H:%M} | {job['platform']:10} | "
                f"{job.get('company','?')[:25]:25} | {job['title'][:40]:40} | {job.get('url','')}\n")
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass

async def click_next_or_submit(page: Page) -> str:
    """Click Next/Submit button. Returns 'submit', 'next', or 'none'."""
    submit_keywords = ["submit application", "submit", "apply now", "send application", "finish"]
    next_keywords   = ["next", "continue", "review", "proceed", "save & next"]

    try:
        for btn in await page.query_selector_all("button, [role='button']"):
            if not await btn.is_visible():
                continue
            txt = (await btn.inner_text()).strip().lower()
            if any(k in txt for k in submit_keywords):
                await btn.click()
                return "submit"
            if any(k in txt for k in next_keywords):
                await btn.click()
                return "next"
    except: pass

    # LinkedIn-specific aria-labels
    for label, action in [
        ("Submit application", "submit"),
        ("Review your application", "next"),
        ("Continue to next step", "next"),
    ]:
        try:
            btn = await page.query_selector(f"button[aria-label='{label}']")
            if btn and await btn.is_visible():
                await btn.click()
                return action
        except: pass

    return "none"


# ── Platform appliers ──────────────────────────────────────

async def apply_linkedin(page: Page, job: dict) -> bool:
    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    btn = await page.query_selector(
        "button.jobs-apply-button, button[aria-label*='Easy Apply'], .jobs-s-apply button"
    )
    if not btn:
        ext = await page.query_selector(
            "a[data-tracking-control-name*='external'], a.jobs-apply-button, button[aria-label='Apply']"
        )
        if ext:
            await log_manual_todo(job)
            print("     [TODO] External apply - logged for manual review")
        return False   # External apply — skip

    await btn.click()
    await asyncio.sleep(2)

    for _ in range(10):
        await asyncio.sleep(1.5)
        await fill_text_fields(page)
        await fill_radios_and_selects(page)
        await upload_resume(page)
        await fill_cover_letter(page, job)
        await ai_fill_form(page, job)

        action = await click_next_or_submit(page)
        if action == "submit":
            await asyncio.sleep(2)
            return True
        elif action == "none":
            break
    return False


async def apply_naukri(page: Page, job: dict) -> bool:
    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    btn = await page.query_selector("button#apply-button, .apply-button, button[class*='apply']")
    if not btn:
        return False
    await btn.click()
    await asyncio.sleep(2)

    if await page.query_selector(".login-modal, #login-modal"):
        print("     [WARN] Naukri login required - log in on Chrome first")
        return False

    await fill_text_fields(page)
    await ai_fill_form(page, job)
    submit = await page.query_selector("button[type='submit'], button.btn-primary")
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        return True
    return False


async def apply_indeed(page: Page, job: dict) -> bool:
    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    btn = await page.query_selector("button#indeedApplyButton, .ia-IndeedApplyButton")
    if not btn:
        return False
    await btn.click()
    await asyncio.sleep(3)

    for _ in range(8):
        await asyncio.sleep(1.5)
        await fill_text_fields(page)
        await upload_resume(page)
        await fill_radios_and_selects(page)
        await fill_cover_letter(page, job)
        await ai_fill_form(page, job)
        action = await click_next_or_submit(page)
        if action == "submit":
            await asyncio.sleep(2)
            return True
        elif action == "none":
            break
    return False


async def apply_wellfound(page: Page, job: dict) -> bool:
    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    btn = await page.query_selector("button:has-text('Apply'), a:has-text('Apply')")
    if not btn:
        return False
    await btn.click()
    await asyncio.sleep(2)

    await fill_cover_letter(page, job)
    await fill_text_fields(page)

    submit = await page.query_selector("button[type='submit'], button:has-text('Submit')")
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        return True
    return False


async def apply_upwork(page: Page, job: dict) -> bool:
    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)

    btn = await page.query_selector("button:has-text('Apply Now'), .air3-btn:has-text('Apply')")
    if not btn:
        return False
    await btn.click()
    await asyncio.sleep(3)

    await fill_cover_letter(page, job)

    try:
        rate = await page.query_selector("input[name='rate'], input[placeholder*='rate']")
        if rate:
            await rate.fill(HOURLY_RATE_USD)
    except: pass

    try:
        for qa in await page.query_selector_all(".screening-questions textarea"):
            if not await qa.input_value():
                await qa.fill("Yes, I have relevant experience and can deliver high quality results.")
    except: pass

    submit = await page.query_selector("button:has-text('Submit Proposal'), button[type='submit']")
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        return True
    return False


async def apply_freelancer(page: Page, job: dict) -> bool:
    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)

    btn = await page.query_selector("button:has-text('Place a Bid'), a:has-text('Bid')")
    if not btn:
        return False
    await btn.click()
    await asyncio.sleep(2)

    await fill_cover_letter(page, job)

    try:
        amt = await page.query_selector("input[name='amount'], input[name='bid_amount']")
        if amt:
            await amt.fill(FIXED_BID_MIN)
    except: pass

    submit = await page.query_selector("button:has-text('Place Bid'), button[type='submit']")
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        return True
    return False


async def apply_peopleperhour(page: Page, job: dict) -> bool:
    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)

    btn = await page.query_selector("a:has-text('Place Bid'), button:has-text('Apply')")
    if not btn:
        return False
    await btn.click()
    await asyncio.sleep(2)

    await fill_cover_letter(page, job)

    try:
        price = await page.query_selector("input[name='price'], input[name='amount']")
        if price:
            await price.fill(FIXED_BID_MIN)
    except: pass

    submit = await page.query_selector("button[type='submit'], button:has-text('Submit')")
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        return True
    return False


async def apply_guru(page: Page, job: dict) -> bool:
    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)

    btn = await page.query_selector("a:has-text('Quote'), button:has-text('Apply')")
    if not btn:
        return False
    await btn.click()
    await asyncio.sleep(2)

    await fill_cover_letter(page, job)

    submit = await page.query_selector("button[type='submit']")
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        return True
    return False


# ── Dispatcher ─────────────────────────────────────────────

APPLIERS = {
    "LinkedIn":      apply_linkedin,
    "Naukri":        apply_naukri,
    "Indeed":        apply_indeed,
    "Wellfound":     apply_wellfound,
    "Upwork":        apply_upwork,
    "Freelancer":    apply_freelancer,
    "PeoplePerHour": apply_peopleperhour,
    "Guru":          apply_guru,
}


async def run_auto_apply(jobs: list = None, min_score: int = None, dry_run: bool = None):
    min_score = min_score if min_score is not None else MIN_SCORE_TO_APPLY
    dry_run   = dry_run   if dry_run   is not None else DRY_RUN

    if jobs is None:
        if not SCORED_FILE.exists():
            print("❌ No scored jobs. Run ai_matcher.py first.")
            return
        jobs = json.loads(SCORED_FILE.read_text())

    applied_urls = load_applied_urls()
    queue = [
        j for j in jobs
        if j.get("ai_score", 0) >= min_score
        and j.get("ai_recommendation") != "skip"
        and j.get("url", "") not in applied_urls
        and j.get("platform") in APPLIERS
    ][:MAX_APPLY_PER_RUN]

    print(f"\n[INFO] Auto-Apply: {len(queue)} jobs queued (score >= {min_score})")
    if dry_run:
        print("   [DRY RUN] - no real submissions")
    if not queue:
        print("   Nothing to apply to - skipping (no browser launch).")
        return

    ok = fail = skip = 0

    async with async_playwright() as p:
        context = await get_browser_context(p)
        page    = await new_stealth_page(context)

        for i, job in enumerate(queue):
            if stop_requested():
                print("\n  [STOP] Stop requested - stopping applications")
                break
            platform = job.get("platform", "")
            applier  = APPLIERS.get(platform)
            print(f"\n  [{i+1}/{len(queue)}] {platform:15} | Score:{job.get('ai_score','?'):3} | {job['title'][:38]}")

            if not applier:
                print(f"     ⏭️  No handler for {platform}")
                skip += 1
                continue

            if dry_run:
                print(f"     [OK] DRY RUN - would apply here")
                save_result(job, "dry_run")
                ok += 1
                continue

            try:
                result = await applier(page, job)
                if result:
                    print(f"     [OK] Applied!")
                    save_result(job, "applied")
                    ok += 1
                else:
                    print(f"     [WARN] Could not apply (no button or login issue)")
                    save_result(job, "failed", "No apply button")
                    fail += 1
            except Exception as e:
                print(f"     [ERROR] Error: {e}")
                save_result(job, "error", str(e))
                fail += 1

            await asyncio.sleep(DELAY_BETWEEN_APPLY)

        await context.close()

    print(f"\n{'='*50}")
    print(f"  [OK] Applied  : {ok}")
    print(f"  [ERROR] Failed   : {fail}")
    print(f"  [SKIP] Skipped  : {skip}")
    print(f"  [LOG] Log      : logs/apply_log.txt")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(run_auto_apply())
