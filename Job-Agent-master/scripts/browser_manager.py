"""
scripts/browser_manager.py
Two modes:
  1. CREDENTIALS MODE (default when config/credentials.json has entries)
     Fresh bot profile + logs into every platform with your saved
     credentials. Your real Chrome is NOT touched or killed.
  2. CHROME PROFILE MODE (fallback when no credentials saved)
     Opens YOUR existing Chrome Profile where you are already logged in.
"""

import sys, asyncio, subprocess, json
from pathlib import Path
from playwright.async_api import BrowserContext, Page

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    HEADLESS,
    CHROME_USER_DATA_DIR,
    CHROME_PROFILE
)

PROJECT_ROOT = Path(__file__).parent.parent
BOT_PROFILE_DIR = PROJECT_ROOT / "config" / "bot_profile"


def load_credentials():
    """Load saved credentials from config/credentials.json"""
    try:
        from scripts.login_manager import load_credentials as _load
        return _load()
    except Exception:
        return {}


def kill_chrome():
    """Kill all Chrome so we can open it fresh (profile mode only)."""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
        print("  [INFO] Killed existing Chrome")
    except:
        pass


async def get_browser_context(playwright) -> BrowserContext:
    creds = load_credentials()
    if creds:
        return await _credentials_context(playwright, creds)
    return await _user_chrome_context(playwright)


async def _credentials_context(playwright, creds) -> BrowserContext:
    """Fresh bot profile - your Chrome stays open and untouched."""
    print("  [INFO] CREDENTIALS MODE - bot profile (your Chrome is not touched)")
    try:
        BOT_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(BOT_PROFILE_DIR),
            headless=False,
            slow_mo=300,
            timeout=60000,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--window-size=1280,800",
            ],
            viewport={"width": 1280, "height": 800},
            ignore_default_args=["--enable-automation", "--no-sandbox"],
        )
        from scripts.login_manager import login_all
        await login_all(context, creds)
        print("  [OK] Bot profile ready - logged in where possible")
        return context
    except Exception as e:
        print(f"  [ERROR] Bot profile failed: {e}")
        print("  [WARN] Falling back to fresh Chromium (not logged in)")
        return await _fresh_browser(playwright)


async def _user_chrome_context(playwright) -> BrowserContext:
    # Step 1 — Kill any open Chrome
    kill_chrome()
    await asyncio.sleep(3)

    # Step 2 — Use paths from config/settings.py
    chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data  = CHROME_USER_DATA_DIR
    profile    = CHROME_PROFILE

    print(f"  [INFO] Opening YOUR Chrome Default...")

    try:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data,
            executable_path=chrome_exe,
            headless=False,
            slow_mo=300,
            timeout=60000,
            args=[
                f"--profile-directory={profile}",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--window-size=1280,800",
            ],
            viewport={"width": 1280, "height": 800},
            ignore_default_args=["--enable-automation", "--no-sandbox"],
        )
        print("  [OK] YOUR Chrome Default opened - logged in everywhere!")
        return context

    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        print("  [WARN] Falling back to fresh Chromium")
        return await _fresh_browser(playwright)


async def _fresh_browser(playwright) -> BrowserContext:
    """Fallback only — not logged in anywhere."""
    browser = await playwright.chromium.launch(
        headless=False,
        slow_mo=200,
        args=["--disable-blink-features=AutomationControlled", "--window-size=1280,800"],
    )
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    return context


async def new_stealth_page(context: BrowserContext) -> Page:
    """Create a page that hides automation."""
    page = await context.new_page()
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins',   {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-IN','en']});
        window.chrome = { runtime: {} };
    """)
    return page


async def safe_click(page: Page, selector: str, timeout: int = 5000) -> bool:
    try:
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        await page.click(selector)
        return True
    except:
        return False


async def safe_fill(page: Page, selector: str, value: str, timeout: int = 5000) -> bool:
    try:
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        await page.fill(selector, value)
        return True
    except:
        return False


async def safe_text(element_or_page, selector: str, default: str = "") -> str:
    try:
        el = await element_or_page.query_selector(selector)
        return (await el.inner_text()).strip() if el else default
    except:
        return default