"""
scripts/login_manager.py
Logs into job platforms using credentials entered in the Streamlit UI.
Credentials are stored in config/credentials.json (plain text - keep safe).

Best-effort login flows. If a platform shows a CAPTCHA or changes its
login page, the login fails gracefully and the run continues without it.
"""

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
CRED_FILE  = CONFIG_DIR / "credentials.json"

# Platform login definitions (selectors are best-effort with fallbacks)
PLATFORM_LOGINS = {
    "LinkedIn": {
        "login_url": "https://www.linkedin.com/login",
        "email": ["#session_key", "input[name='session_key']"],
        "password": ["#session_password", "input[name='session_password']"],
        "submit": ["button[type='submit']"],
        "logged_in_urls": ["/feed", "/checkpoint/challenge"],
    },
    "Naukri": {
        "login_url": "https://www.naukri.com/nlogin/login",
        "email": ["#usernameField", "input[name='email']"],
        "password": ["#passwordField", "input[name='password']"],
        "submit": ["button[type='submit']"],
        "logged_in_marker": "a.nI-gNb-sb__userName, .nI-gNb-sb__userName, a[href*='/mnj/user/profile']",
    },
    "Indeed": {
        "login_url": "https://www.indeed.com/account/login",
        "email": ["#ifl-email", "input[name='email']"],
        "password": ["#ifl-password", "input[name='password']"],
        "submit": ["#ifl-submit", "button[type='submit']"],
        "logged_in_urls": ["/account", "/dashboard"],
    },
    "Wellfound": {
        "login_url": "https://wellfound.com/login",
        "email": ["input[name='user[email]']", "input[type='email']"],
        "password": ["input[name='user[password]']", "input[type='password']"],
        "submit": ["button[type='submit']"],
        "logged_in_urls": ["/dashboard", "/home"],
    },
    "Upwork": {
        "login_url": "https://www.upwork.com/ab/account-security/login",
        "email": ["#login_username", "input[name='login[username]']", "input[type='email']"],
        "password": ["#login_password", "input[name='login[password]']", "input[type='password']"],
        "submit": ["#login_control_1", "button[type='submit']"],
        "logged_in_urls": ["/ab/find-work", "/nx/find-work", "/dashboard"],
    },
    "Freelancer": {
        "login_url": "https://www.freelancer.com/login",
        "email": ["input[name='username']", "input[type='email']"],
        "password": ["input[name='password']", "input[type='password']"],
        "submit": ["button[type='submit']"],
        "logged_in_urls": ["/dashboard"],
    },
    "PeoplePerHour": {
        "login_url": "https://www.peopleperhour.com/login",
        "email": ["input[name='email']", "input[type='email']", "#email"],
        "password": ["input[name='password']", "input[type='password']", "#password"],
        "submit": ["button[type='submit']"],
        "logged_in_urls": ["/dashboard", "/freelancer"],
    },
    "Guru": {
        "login_url": "https://www.guru.com/login",
        "email": ["input[name='email']", "input[type='email']"],
        "password": ["input[name='password']", "input[type='password']"],
        "submit": ["button[type='submit']"],
        "logged_in_urls": ["/members/home", "/jobs"],
    },
}


def load_credentials():
    """Load saved credentials from config/credentials.json"""
    try:
        if CRED_FILE.exists():
            data = json.loads(CRED_FILE.read_text(encoding="utf-8"))
            return {k: v for k, v in data.items()
                    if isinstance(v, dict) and v.get("password") and (v.get("username") or v.get("email"))}
    except Exception:
        pass
    return {}


def save_credentials(creds):
    """Save credentials to config/credentials.json"""
    CONFIG_DIR.mkdir(exist_ok=True)
    CRED_FILE.write_text(json.dumps(creds, indent=2, ensure_ascii=False), encoding="utf-8")


async def _fill_first(page, selectors, value):
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                await el.fill(value)
                return True
        except Exception:
            continue
    return False


async def _already_logged_in(page, cfg):
    try:
        url = page.url.lower()
        for marker in cfg.get("logged_in_urls", []):
            if marker.lower() in url:
                return True
        marker = cfg.get("logged_in_marker", "")
        if marker:
            el = await page.query_selector(marker)
            if el:
                return True
    except Exception:
        pass
    return False


async def _submit(page, cfg):
    for sel in cfg["submit"]:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                return True
        except Exception:
            continue
    return False


async def ensure_login(page, platform, creds):
    """Log into one platform. Returns 'ok' | 'already' | 'failed'"""
    cfg = PLATFORM_LOGINS.get(platform)
    if not cfg:
        return "failed"
    username = creds.get("username") or creds.get("email") or ""
    try:
        await page.goto(cfg["login_url"], timeout=45000, wait_until="domcontentloaded")
    except Exception:
        pass
    await page.wait_for_timeout(2500)

    if await _already_logged_in(page, cfg):
        return "already"

    ok_u = await _fill_first(page, cfg["email"], username)
    ok_p = await _fill_first(page, cfg["password"], creds.get("password", ""))
    if not (ok_u and ok_p):
        return "failed"

    await page.wait_for_timeout(500)
    if not await _submit(page, cfg):
        return "failed"

    await page.wait_for_timeout(4000)
    if await _already_logged_in(page, cfg):
        return "ok"
    return "failed"


async def login_all(context, creds):
    """Log into every platform that has saved credentials."""
    results = {}
    for platform in PLATFORM_LOGINS:
        if platform not in creds:
            results[platform] = "skipped"
            continue
        try:
            page = await context.new_page()
            status = await ensure_login(page, platform, creds[platform])
            await page.close()
        except Exception as e:
            status = "failed"
        results[platform] = status
        print(f"  [LOGIN] {platform:<14} -> {status}")
    return results