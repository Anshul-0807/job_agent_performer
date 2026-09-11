"""
scripts/job_scraper.py
Scrapes jobs from enabled platforms (config/settings.py -> PLATFORMS).
Locations: India cities (Indore, Nagpur, Ahmedabad, Surat, Chandigarh,
           Noida, Gurugram, Delhi, New Delhi, Bangalore, Hyderabad, Pune)
           + Remote India.
- Only jobs posted in last 40 days (fresh jobs only!)
"""

import asyncio, json, sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import TARGET_ROLES, PLATFORMS
from scripts.browser_manager import get_browser_context, new_stealth_page, safe_text
from scripts.stop_manager import stop_requested

OUTPUT = Path("output/scraped_jobs.json")

# ── All Locations ───────────────────────────────────────────

LINKEDIN_LOCATIONS = [
    ("Indore",      "Indore%2C+Madhya+Pradesh%2C+India"),
    ("Nagpur",      "Nagpur%2C+Maharashtra%2C+India"),
    ("Ahmedabad",   "Ahmedabad%2C+Gujarat%2C+India"),
    ("Surat",       "Surat%2C+Gujarat%2C+India"),
    ("Chandigarh",  "Chandigarh%2C+India"),
    ("Noida",       "Noida%2C+Uttar+Pradesh%2C+India"),
    ("Gurugram",    "Gurugram%2C+Haryana%2C+India"),
    ("Delhi",       "Delhi%2C+India"),
    ("New Delhi",   "New+Delhi%2C+India"),
    ("Bangalore",   "Bengaluru%2C+Karnataka%2C+India"),
    ("Hyderabad",   "Hyderabad%2C+Telangana%2C+India"),
    ("Pune",        "Pune%2C+Maharashtra%2C+India"),
    ("Remote India","Remote%2C+India"),
]

NAUKRI_CITIES = [
    ("Indore",      "indore"),
    ("Nagpur",      "nagpur"),
    ("Ahmedabad",   "ahmedabad"),
    ("Surat",       "surat"),
    ("Chandigarh",  "chandigarh"),
    ("Noida",       "noida"),
    ("Gurugram",    "gurugram"),
    ("Delhi",       "delhi"),
    ("New Delhi",   "new-delhi"),
    ("Bangalore",   "bangalore"),
    ("Hyderabad",   "hyderabad"),
    ("Pune",        "pune"),
    ("Remote",      ""),
]

INDEED_LOCATIONS = [
    ("Indore",      "in.indeed.com", "Indore%2C+Madhya+Pradesh"),
    ("Nagpur",      "in.indeed.com", "Nagpur%2C+Maharashtra"),
    ("Ahmedabad",   "in.indeed.com", "Ahmedabad%2C+Gujarat"),
    ("Surat",       "in.indeed.com", "Surat%2C+Gujarat"),
    ("Chandigarh",  "in.indeed.com", "Chandigarh%2C+Chandigarh"),
    ("Noida",       "in.indeed.com", "Noida%2C+Uttar+Pradesh"),
    ("Gurugram",    "in.indeed.com", "Gurugram%2C+Haryana"),
    ("Delhi",       "in.indeed.com", "Delhi%2C+Delhi"),
    ("New Delhi",   "in.indeed.com", "New+Delhi%2C+Delhi"),
    ("Bangalore",   "in.indeed.com", "Bengaluru%2C+Karnataka"),
    ("Hyderabad",   "in.indeed.com", "Hyderabad%2C+Telangana"),
    ("Pune",        "in.indeed.com", "Pune%2C+Maharashtra"),
    ("Remote India","in.indeed.com", "Remote"),
]


# ── Helper ──────────────────────────────────────────────────

def make_job(platform, title, company, location, url, keyword, extra=None):
    entry = {
        "platform": platform,
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "url": url.strip() if url else "",
        "keyword": keyword,
        "scraped_at": datetime.now().isoformat(),
        "status": "new",
    }
    if extra:
        entry.update(extra)
    return entry

async def scroll_down(page, times=3, delay=2):
    for _ in range(times):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(delay)
        except:
            break


# ── LinkedIn ────────────────────────────────────────────────
# f_TPR=r3456000 = last 40 days

async def scrape_linkedin(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "%20")

    for city_name, city_encoded in LINKEDIN_LOCATIONS:
        try:
            url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={kw}"
                f"&location={city_encoded}"
                f"&f_TPR=r3456000"
                f"&sortBy=DD"
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await scroll_down(page, 2, 1.5)

            cards = await page.query_selector_all(".job-card-container, .base-card")
            city_jobs = 0
            for card in cards:
                try:
                    title   = await safe_text(card, ".job-card-list__title, .base-search-card__title")
                    company = await safe_text(card, ".job-card-container__primary-description, .base-search-card__subtitle")
                    loc     = await safe_text(card, ".job-card-container__metadata-item, .job-search-card__location") or city_name
                    posted  = await safe_text(card, ".job-search-card__listdate, time")
                    a       = await card.query_selector("a")
                    job_url = ((await a.get_attribute("href")) or "").split("?")[0] if a else ""
                    if title:
                        jobs.append(make_job("LinkedIn", title, company, loc, job_url, keyword,
                                             {"posted": posted, "search_location": city_name}))
                        city_jobs += 1
                except:
                    continue

            if city_jobs > 0:
                print(f"       {city_name}: {city_jobs} jobs")
            await asyncio.sleep(1.5)

        except Exception as e:
            if "closed" in str(e).lower():
                raise
            continue

    return jobs


# ── Naukri ──────────────────────────────────────────────────
# age=30 = last 30 days

async def scrape_naukri(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")

    for city_name, city_slug in NAUKRI_CITIES:
        try:
            if city_slug:
                url = f"https://www.naukri.com/{slug}-jobs-in-{city_slug}?age=30"
            else:
                url = f"https://www.naukri.com/{slug}-jobs?wfhType=1&age=30"

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            cards = await page.query_selector_all(".srp-jobtuple-wrapper, article.jobTuple")
            city_jobs = 0
            for card in cards:
                try:
                    title   = await safe_text(card, ".title, a.title")
                    company = await safe_text(card, ".comp-name, .subTitle")
                    loc     = await safe_text(card, ".locWdth, .loc") or city_name
                    posted  = await safe_text(card, ".job-post-day, .fleft.grey-text")
                    a       = await card.query_selector("a.title, a")
                    job_url = await a.get_attribute("href") if a else ""
                    if title:
                        jobs.append(make_job("Naukri", title, company, loc, job_url or "", keyword,
                                             {"posted": posted, "search_location": city_name}))
                        city_jobs += 1
                except:
                    continue

            if city_jobs > 0:
                print(f"       {city_name}: {city_jobs} jobs")
            await asyncio.sleep(1.5)

        except Exception as e:
            if "closed" in str(e).lower():
                raise
            continue

    return jobs


# ── Indeed ──────────────────────────────────────────────────
# fromage=40 = last 40 days

async def scrape_indeed(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")

    for city_name, domain, city_encoded in INDEED_LOCATIONS:
        try:
            url = f"https://{domain}/jobs?q={kw}&l={city_encoded}&fromage=40&sort=date"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            cards = await page.query_selector_all(".job_seen_beacon, .tapItem")
            city_jobs = 0
            for card in cards:
                try:
                    title   = await safe_text(card, "[data-testid='jobTitle'] span, h2 span")
                    company = await safe_text(card, "[data-testid='company-name'], .companyName")
                    loc     = await safe_text(card, "[data-testid='text-location'], .companyLocation") or city_name
                    posted  = await safe_text(card, "[data-testid='myJobsStateDate'], .date")
                    a       = await card.query_selector("a[data-jk], a")
                    jk      = await a.get_attribute("data-jk") if a else ""
                    job_url = f"https://{domain}/viewjob?jk={jk}" if jk else ""
                    if title:
                        jobs.append(make_job("Indeed", title, company, loc, job_url, keyword,
                                             {"posted": posted, "search_location": city_name}))
                        city_jobs += 1
                except:
                    continue

            if city_jobs > 0:
                print(f"       {city_name}: {city_jobs} jobs")
            await asyncio.sleep(1.5)

        except Exception as e:
            if "closed" in str(e).lower():
                raise
            continue

    return jobs


# ── Glassdoor ───────────────────────────────────────────────

async def scrape_glassdoor(page: Page, keyword: str) -> list:
    jobs = []
    kw_slug = keyword.replace(" ", "-").lower()
    kw_len  = len(keyword)

    searches = [
        ("India",   f"https://www.glassdoor.co.in/Job/india-{kw_slug}-jobs-SRCH_IL.0,5_IN115_KO6,{6+kw_len}.htm"),
        ("UK",      f"https://www.glassdoor.co.uk/Job/united-kingdom-{kw_slug}-jobs-SRCH_IL.0,14_IN2_KO15,{15+kw_len}.htm"),
        ("Germany", f"https://www.glassdoor.de/Job/germany-{kw_slug}-jobs-SRCH_IL.0,7_IN96_KO8,{8+kw_len}.htm"),
        ("USA",     f"https://www.glassdoor.com/Job/united-states-{kw_slug}-jobs-SRCH_IL.0,13_IN1_KO14,{14+kw_len}.htm"),
    ]

    for country, url in searches:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            cards = await page.query_selector_all("[data-test='jobListing'], li.react-job-listing")
            country_jobs = 0
            for card in cards:
                try:
                    title   = await safe_text(card, "[data-test='job-title'], .job-title")
                    company = await safe_text(card, ".employer-name, [data-test='employer-name']")
                    loc     = await safe_text(card, "[data-test='emp-location'], .location") or country
                    a       = await card.query_selector("a")
                    href    = await a.get_attribute("href") if a else ""
                    base    = url.split("/Job/")[0]
                    job_url = base + href if href and not href.startswith("http") else href
                    if title:
                        jobs.append(make_job("Glassdoor", title, company, loc, job_url, keyword,
                                             {"search_location": country}))
                        country_jobs += 1
                except:
                    continue

            if country_jobs > 0:
                print(f"       {country}: {country_jobs} jobs")
            await asyncio.sleep(2)

        except Exception as e:
            if "closed" in str(e).lower():
                raise
            continue

    return jobs


# ── Wellfound ───────────────────────────────────────────────

async def scrape_wellfound(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")

    for loc_name, loc_param in [
        ("Remote",  "remote"),
        ("India",   "india"),
        ("USA",     "united-states"),
        ("Europe",  "europe"),
    ]:
        try:
            url = f"https://wellfound.com/jobs?q={kw}&l={loc_param}"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            cards = await page.query_selector_all("[data-test='StartupResult'], .styles_component__")
            loc_jobs = 0
            for card in cards:
                try:
                    title   = await safe_text(card, "h2, .role")
                    company = await safe_text(card, "h3, .company")
                    a       = await card.query_selector("a")
                    href    = await a.get_attribute("href") if a else ""
                    job_url = "https://wellfound.com" + href if href and not href.startswith("http") else href
                    if title:
                        jobs.append(make_job("Wellfound", title, company, loc_name, job_url, keyword,
                                             {"search_location": loc_name}))
                        loc_jobs += 1
                except:
                    continue

            if loc_jobs > 0:
                print(f"       {loc_name}: {loc_jobs} jobs")
            await asyncio.sleep(1.5)

        except Exception as e:
            if "closed" in str(e).lower():
                raise
            continue

    return jobs


# ── WeWorkRemotely ──────────────────────────────────────────

async def scrape_weworkremotely(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")
    try:
        await page.goto(
            f"https://weworkremotely.com/remote-jobs/search?term={kw}",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(3)
        for card in await page.query_selector_all("ul.jobs li:not(.view-all)"):
            try:
                title   = await safe_text(card, ".title")
                company = await safe_text(card, ".company")
                a       = await card.query_selector("a")
                href    = await a.get_attribute("href") if a else ""
                job_url = "https://weworkremotely.com" + href if href and not href.startswith("http") else href
                if title:
                    jobs.append(make_job("WeWorkRemotely", title, company, "Remote (Global)", job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Remote.co ───────────────────────────────────────────────

async def scrape_remoteco(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")
    try:
        await page.goto(
            f"https://remote.co/remote-jobs/search/?search_keywords={kw}",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(3)
        for card in await page.query_selector_all(".job_listing, .card"):
            try:
                title   = await safe_text(card, "h2, .position h2")
                company = await safe_text(card, "h3, .company_and_location h3")
                a       = await card.query_selector("a")
                href    = await a.get_attribute("href") if a else ""
                job_url = "https://remote.co" + href if href and not href.startswith("http") else href
                if title:
                    jobs.append(make_job("Remote.co", title, company, "Remote (Global)", job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Arc.dev ─────────────────────────────────────────────────

async def scrape_arcdev(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")
    try:
        await page.goto(
            f"https://arc.dev/remote-jobs?q={kw}",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)
        for card in await page.query_selector_all("[data-cy='job-card'], .job-card"):
            try:
                title   = await safe_text(card, "h3, .title")
                company = await safe_text(card, "[data-cy='company-name'], .company")
                a       = await card.query_selector("a")
                href    = await a.get_attribute("href") if a else ""
                job_url = "https://arc.dev" + href if href and not href.startswith("http") else href
                if title:
                    jobs.append(make_job("Arc.dev", title, company, "Remote (Global)", job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── YC Jobs ─────────────────────────────────────────────────

async def scrape_ycjobs(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "%20")
    try:
        await page.goto(
            f"https://www.ycombinator.com/jobs?q={kw}&remote=true",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)
        for card in await page.query_selector_all("[class*='JobCard'], .job-card"):
            try:
                title   = await safe_text(card, "[class*='role'], h3, h2")
                company = await safe_text(card, "[class*='company'], h4")
                a       = await card.query_selector("a")
                href    = await a.get_attribute("href") if a else ""
                job_url = "https://www.ycombinator.com" + href if href and not href.startswith("http") else href
                if title:
                    jobs.append(make_job("YC Jobs", title, company, "Remote (Global)", job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Upwork ──────────────────────────────────────────────────

async def scrape_upwork(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "%20")
    try:
        await page.goto(
            f"https://www.upwork.com/nx/search/jobs/?q={kw}&sort=recency",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(5)
        for card in await page.query_selector_all("article.job-tile, section.air-card-hover"):
            try:
                title   = await safe_text(card, "h2, [data-test='job-tile-title']")
                budget  = await safe_text(card, "[data-test='budget'], .budget")
                desc    = await safe_text(card, "[data-test='job-description-text']")
                posted  = await safe_text(card, "[data-test='posted-on'], .posted-on")
                a       = await card.query_selector("a")
                href    = await a.get_attribute("href") if a else ""
                job_url = "https://www.upwork.com" + href if href and not href.startswith("http") else href
                if title:
                    jobs.append(make_job("Upwork", title, "Client", "Remote (Global)", job_url, keyword,
                                         {"budget": budget, "description": desc[:200], "posted": posted}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Freelancer ──────────────────────────────────────────────

async def scrape_freelancer(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    try:
        await page.goto(
            f"https://www.freelancer.com/jobs/{slug}/",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)
        for card in await page.query_selector_all(".JobSearchCard-item"):
            try:
                title   = await safe_text(card, ".JobSearchCard-primary-heading")
                budget  = await safe_text(card, ".JobSearchCard-primary-price")
                desc    = await safe_text(card, ".JobSearchCard-primary-description")
                posted  = await safe_text(card, ".JobSearchCard-primary-meta abbr")
                a       = await card.query_selector("a.JobSearchCard-primary-heading-link")
                href    = await a.get_attribute("href") if a else ""
                job_url = "https://www.freelancer.com" + href if href and not href.startswith("http") else href
                if title:
                    jobs.append(make_job("Freelancer", title, "Client", "Remote (Global)", job_url, keyword,
                                         {"budget": budget, "description": desc[:200], "posted": posted}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── PeoplePerHour ────────────────────────────────────────────

async def scrape_peopleperhour(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    try:
        await page.goto(
            f"https://www.peopleperhour.com/freelance-{slug}-jobs",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)
        for card in await page.query_selector_all(".list-item, .hourlie-item"):
            try:
                title   = await safe_text(card, ".item-title, h2")
                budget  = await safe_text(card, ".price")
                a       = await card.query_selector("a")
                href    = await a.get_attribute("href") if a else ""
                job_url = "https://www.peopleperhour.com" + href if href and not href.startswith("http") else href
                if title:
                    jobs.append(make_job("PeoplePerHour", title, "Client", "Remote (Global)", job_url, keyword,
                                         {"budget": budget}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Guru ─────────────────────────────────────────────────────

async def scrape_guru(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")
    try:
        await page.goto(
            f"https://www.guru.com/d/jobs/q/{kw}/",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)
        for card in await page.query_selector_all(".jobRecord, .serviceRecord"):
            try:
                title   = await safe_text(card, ".jobTitle, h3 a")
                budget  = await safe_text(card, ".budget, .price")
                a       = await card.query_selector("a.jobTitle, h3 a")
                href    = await a.get_attribute("href") if a else ""
                job_url = "https://www.guru.com" + href if href and not href.startswith("http") else href
                if title:
                    jobs.append(make_job("Guru", title, "Client", "Remote (Global)", job_url, keyword,
                                         {"budget": budget}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── TimesJobs (India) ────────────────────────────────────────

async def scrape_timesjobs(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")

    searches = [("All India", f"https://www.timesjobs.com/jobs/{slug}")]
    for city_name, city_slug in [
        ("Delhi",       "delhi"),
        ("Mumbai",      "mumbai"),
        ("Bangalore",   "bangalore"),
        ("Hyderabad",   "hyderabad"),
        ("Pune",        "pune"),
        ("Chennai",     "chennai"),
        ("Noida",       "noida"),
        ("Gurgaon",     "gurgaon"),
        ("Kolkata",     "kolkata"),
        ("Ahmedabad",   "ahmedabad"),
    ]:
        searches.append((city_name, f"https://www.timesjobs.com/jobs/{slug}-jobs-in-{city_slug}"))

    for city_name, url in searches:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            cards = await page.query_selector_all(".job-bx, .jobCard, .job-card")
            city_jobs = 0
            for card in cards:
                try:
                    title   = await safe_text(card, "h3 a, .job-title, a[href*='/jobs/']")
                    company = await safe_text(card, ".comp-name, .company-name, .comp-dtls-wrap h4")
                    loc     = await safe_text(card, ".location, .loc, .job-location") or city_name
                    posted  = await safe_text(card, ".posting-time, .job-posted, .days")
                    a       = await card.query_selector("h3 a, .job-title, a[href*='/jobs/']")
                    href    = await a.get_attribute("href") if a else ""
                    job_url = href if href and href.startswith("http") else "https://www.timesjobs.com" + (href or "")
                    if title:
                        jobs.append(make_job("TimesJobs", title, company, loc, job_url, keyword,
                                             {"posted": posted, "search_location": city_name}))
                        city_jobs += 1
                except:
                    continue

            if city_jobs > 0:
                print(f"       {city_name}: {city_jobs} jobs")
            await asyncio.sleep(1.5)

        except Exception as e:
            if "closed" in str(e).lower():
                raise
            continue

    return jobs


# ── Shine.com (India) ────────────────────────────────────────

async def scrape_shine(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    try:
        await page.goto(
            f"https://www.shine.com/job-search/{slug}",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all(".job_card, .jobCard, .job-card, .search-job"):
            try:
                title   = await safe_text(card, ".job_card__title, .job-title, h2 a, h3 a")
                company = await safe_text(card, ".job_card__company, .company-name, .company")
                loc     = await safe_text(card, ".job_card__location, .location, .loc") or "India"
                posted  = await safe_text(card, ".job_card__posted, .posted-date, .date")
                a       = await card.query_selector("a[href*='job']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://www.shine.com" + (href or "")
                if title:
                    jobs.append(make_job("Shine", title, company, loc, job_url, keyword,
                                         {"posted": posted}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Instahyre (India) ────────────────────────────────────────

async def scrape_instahyre(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")
    try:
        await page.goto(
            f"https://www.instahyre.com/job-search/?q={kw}",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all(".job-card, .job-listing, .job-item, [class*='job-card']"):
            try:
                title   = await safe_text(card, ".job-card-title, .job-title, h3 a, h4 a")
                company = await safe_text(card, ".job-card-company, .company-name, .company")
                loc     = await safe_text(card, ".job-card-location, .location, .loc") or "India"
                a       = await card.query_selector("a[href*='job']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://www.instahyre.com" + (href or "")
                if title:
                    jobs.append(make_job("Instahyre", title, company, loc, job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Cutshort (India) ─────────────────────────────────────────

async def scrape_cutshort(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")
    try:
        await page.goto(
            f"https://cutshort.io/jobs?keyword={kw}",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all("[data-test='job-card'], .job-card, .role-card, [class*='job-card']"):
            try:
                title   = await safe_text(card, ".role-title, .job-title, h3 a, h2 a")
                company = await safe_text(card, ".company-name, .company-info, .company")
                loc     = await safe_text(card, ".role-location, .location, .loc") or "India"
                a       = await card.query_selector("a[href*='job']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://cutshort.io" + (href or "")
                if title:
                    jobs.append(make_job("Cutshort", title, company, loc, job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Foundit (India) ──────────────────────────────────────────

async def scrape_foundit(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")
    try:
        await page.goto(
            f"https://www.foundit.in/srp/results?query={kw}",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all(".job-card-container, .jobCard, [class*='job-card'], .card"):
            try:
                title   = await safe_text(card, ".job-title, .jobTitle, h3 a, h2 a")
                company = await safe_text(card, ".company-name, .companyTitle, .company")
                loc     = await safe_text(card, ".location, .loc, .job-location") or "India"
                salary  = await safe_text(card, ".salary, .job-salary")
                a       = await card.query_selector("a[href*='/job/']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://www.foundit.in" + (href or "")
                if title:
                    jobs.append(make_job("Foundit", title, company, loc, job_url, keyword,
                                         {"budget": salary}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Hirist (India IT jobs) ───────────────────────────────────

async def scrape_hirist(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    try:
        await page.goto(
            f"https://www.hirist.tech/k/{slug}-jobs",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all(".job-card, [class*='job-card'], .card, article"):
            try:
                title   = await safe_text(card, ".job-title, .jobTitle, h3 a, h2 a")
                company = await safe_text(card, ".company-name, .companyTitle, .company")
                loc     = await safe_text(card, ".location, .loc, .job-location") or "India"
                salary  = await safe_text(card, ".salary, .job-salary, .ctc")
                a       = await card.query_selector("a[href*='/j/']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://www.hirist.tech" + (href or "")
                if title:
                    jobs.append(make_job("Hirist", title, company, loc, job_url, keyword,
                                         {"budget": salary}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Internshala (India fresher jobs) ─────────────────────────

async def scrape_internshala(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    try:
        await page.goto(
            f"https://internshala.com/jobs/keyword-{slug}/",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all(".individual_internship, .individual_job, .internship_meta, [class*='job']"):
            try:
                title   = await safe_text(card, ".heading_4_5, .job-title, h4 a, h3 a")
                company = await safe_text(card, ".company_name, .company-name, .company")
                loc     = await safe_text(card, ".location_name, .location, .loc") or "India"
                posted  = await safe_text(card, ".status-success, .posted, .time-ago")
                a       = await card.query_selector("a[href*='/job/']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://internshala.com" + (href or "")
                if title:
                    jobs.append(make_job("Internshala", title, company, loc, job_url, keyword,
                                         {"posted": posted}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Freshersworld (India fresher jobs) ───────────────────────

async def scrape_freshersworld(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    try:
        await page.goto(
            f"https://www.freshersworld.com/jobs/{slug}-jobs",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all(".job-container, .job-card, .jobCard, [class*='job-card']"):
            try:
                title   = await safe_text(card, ".job-title, h3 a, h2 a, .title")
                company = await safe_text(card, ".company-name, .company, .comp-name")
                loc     = await safe_text(card, ".location, .loc, .job-location") or "India"
                a       = await card.query_selector("a[href*='/job/'], a[href*='jobs/']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://www.freshersworld.com" + (href or "")
                if title:
                    jobs.append(make_job("Freshersworld", title, company, loc, job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── AmbitionBox (India) ──────────────────────────────────────

async def scrape_ambitionbox(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    try:
        await page.goto(
            f"https://www.ambitionbox.com/jobs/{slug}-jobs-prf",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all("[class*='job-card'], [class*='JobCard'], .card, .job-listing"):
            try:
                title   = await safe_text(card, "[class*='title'], h3 a, h2 a")
                company = await safe_text(card, "[class*='company'], [class*='Company']")
                loc     = await safe_text(card, "[class*='location'], [class*='Location']") or "India"
                salary  = await safe_text(card, "[class*='salary'], [class*='Salary'], [class*='ctc']")
                a       = await card.query_selector("a[href*='-jdp'], a[href*='/jobs/']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://www.ambitionbox.com" + (href or "")
                if title:
                    jobs.append(make_job("AmbitionBox", title, company, loc, job_url, keyword,
                                         {"budget": salary}))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Hasjob (hasgeek, India startup jobs) ─────────────────────

async def scrape_hasjob(page: Page, keyword: str) -> list:
    jobs = []
    kw = keyword.replace(" ", "+")
    try:
        await page.goto(
            f"https://hasjob.co/search?q={kw}",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all("li.job-list-item, .joblist li, .job, [class*='job']"):
            try:
                title   = await safe_text(card, "h2 a, h3 a, .job-heading a, .job-title")
                company = await safe_text(card, ".job-company, .company, .org")
                loc     = await safe_text(card, ".job-location, .location, .loc") or "India"
                a       = await card.query_selector("a[href*='/view/']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://hasjob.co" + (href or "")
                if title:
                    jobs.append(make_job("Hasjob", title, company, loc, job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── iimjobs (India) ──────────────────────────────────────────

async def scrape_iimjobs(page: Page, keyword: str) -> list:
    jobs = []
    slug = keyword.lower().replace(" ", "-")
    try:
        await page.goto(
            f"https://www.iimjobs.com/j/{slug}-jobs",
            wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(4)

        for card in await page.query_selector_all(".jobTuple, .job-card, .jobCard, [class*='job']"):
            try:
                title   = await safe_text(card, ".title, .job-title, h3 a, h2 a")
                company = await safe_text(card, ".company, .company-name, .comp-name")
                loc     = await safe_text(card, ".loc, .location, .job-location") or "India"
                a       = await card.query_selector("a[href*='job']")
                href    = await a.get_attribute("href") if a else ""
                job_url = href if href and href.startswith("http") else "https://www.iimjobs.com" + (href or "")
                if title:
                    jobs.append(make_job("iimjobs", title, company, loc, job_url, keyword))
            except:
                continue
    except Exception as e:
        if "closed" in str(e).lower():
            raise
    return jobs


# ── Dispatcher ───────────────────────────────────────────────

SCRAPERS = {
    "linkedin":       scrape_linkedin,
    "naukri":         scrape_naukri,
    "indeed":         scrape_indeed,
    "glassdoor":      scrape_glassdoor,
    "wellfound":      scrape_wellfound,
    "weworkremotely": scrape_weworkremotely,
    "remoteco":       scrape_remoteco,
    "arcdev":         scrape_arcdev,
    "yc_jobs":        scrape_ycjobs,
    "upwork":         scrape_upwork,
    "freelancer":     scrape_freelancer,
    "peopleperhour":  scrape_peopleperhour,
    "guru":           scrape_guru,
    "timesjobs":      scrape_timesjobs,
    "shine":          scrape_shine,
    "instahyre":      scrape_instahyre,
    "cutshort":       scrape_cutshort,
    "foundit":        scrape_foundit,
    "hirist":         scrape_hirist,
    "internshala":    scrape_internshala,
    "freshersworld":  scrape_freshersworld,
    "ambitionbox":    scrape_ambitionbox,
    "hasjob":         scrape_hasjob,
    "iimjobs":        scrape_iimjobs,
}


def _dedupe(jobs: list) -> list:
    seen, unique = set(), []
    for job in jobs:
        key = job.get("url") or f"{job['title']}-{job['company']}"
        if key and key not in seen and len(key) > 5:
            seen.add(key)
            unique.append(job)
    return unique


async def _scrape_platform(context, platform: str, keywords: list, sink: list):
    """Scrape one platform's keywords on its own page (runs in parallel)."""
    scraper = SCRAPERS[platform]
    page    = await new_stealth_page(context)
    platform_jobs = []
    print(f"\n  [SCRAPE] {platform.upper()}")

    for kw in keywords:
        if stop_requested():
            print(f"\n     [STOP] Stop requested - stopping {platform.upper()} scrape")
            break
        try:
            # Reopen page if browser crashed
            try:
                await page.title()
            except:
                print(f"     [REOPEN] Reopening browser page...")
                try:
                    page = await new_stealth_page(context)
                except:
                    return platform_jobs

            print(f"     [SEARCH] '{kw}'")
            found = await scraper(page, kw)
            platform_jobs.extend(found)
            print(f"        Total: {len(found)} jobs found")
            await asyncio.sleep(2)

        except Exception as e:
            print(f"     [WARN] Error on '{kw}': {e}")
            try:
                page = await new_stealth_page(context)
            except:
                pass

    sink.extend(platform_jobs)
    # Save progress after each platform (safe if run is interrupted)
    try:
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.write_text(json.dumps(_dedupe(sink), indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception:
        pass
    return platform_jobs


async def run_scraper() -> list:
    active   = [k for k, v in PLATFORMS.items() if v and k in SCRAPERS]
    keywords = TARGET_ROLES
    all_jobs = []

    print(f"\n[INFO] Scraping {len(active)} platforms (in parallel tabs)")
    print(f"   Keywords  : {', '.join(keywords)}")
    print(f"   Locations : India (Indore, Nagpur, Ahmedabad, Surat, Chandigarh, Noida, Gurugram, Delhi, New Delhi, Bangalore, Hyderabad, Pune) + Remote India")
    print(f"   Age filter: Last 40 days only - fresh jobs only!")

    async with async_playwright() as p:
        context = await get_browser_context(p)

        # Run all platforms concurrently - each on its own tab
        await asyncio.gather(
            *[_scrape_platform(context, platform, keywords, all_jobs) for platform in active]
        )

        await context.close()

    # Final deduplicate + save
    unique = _dedupe(all_jobs)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(unique, indent=2, ensure_ascii=True),
        encoding="utf-8"
    )
    return unique

    # Print location summary
    from collections import Counter
    loc_counts = Counter(
        j.get("search_location", j.get("location", "?")) for j in unique
    )
    print(f"\n[LOCATION] Jobs by location (top 15):")
    for loc, count in loc_counts.most_common(15):
        print(f"   {loc:25} : {count} jobs")

    print(f"\n[OK] Total fresh unique jobs: {len(unique)}")
    print(f"   Saved to: output/scraped_jobs.json")
    return unique


if __name__ == "__main__":
    asyncio.run(run_scraper())