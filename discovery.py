"""Local Chrome discovery providers for public web-search result pages."""
from __future__ import annotations

import base64
import html
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import sleep
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.parse import urlencode
from urllib.request import urlopen

from query_matrix import DEFAULT_JOB_FAMILIES, DEFAULT_LOCATIONS, QueryMatrixGenerator
from tracker_engine import JobResult, canonical_url


class DiscoveryError(RuntimeError):
    pass


def _decode_bing_redirect(value: str) -> str:
    parsed = urlparse(html.unescape(value))
    if parsed.netloc.casefold().endswith("bing.com") and parsed.path.startswith("/ck/"):
        encoded = parse_qs(parsed.query).get("u", [""])[0]
        if encoded.startswith("a1"):
            try:
                return base64.b64decode(encoded[2:] + "===").decode("utf-8")
            except Exception:
                return value
    return value


def extract_linkedin_job_urls(values: list[str]) -> list[str]:
    """Extract only canonical LinkedIn job links from anchors, redirects, or rendered HTML."""
    found: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(r"https?://(?:[a-z]{2,3}\.)?(?:www\.)?linkedin\.com/jobs/view/[^\s\"'<>]+", re.I)
    for value in values:
        if not value:
            continue
        decoded = _decode_bing_redirect(html.unescape(value))
        candidates = [decoded] + pattern.findall(html.unescape(value)) + pattern.findall(decoded)
        for candidate in candidates:
            canonical, job_id = canonical_url(candidate)
            if job_id and job_id not in seen:
                seen.add(job_id)
                found.append(canonical)
    return found


class JobDiscoveryProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int) -> list[JobResult]: ...

    @abstractmethod
    def close(self) -> None: ...


@dataclass(frozen=True)
class BrowserSettings:
    engine: str = "google"
    max_pages: int = 5
    headless: bool = False
    verbose: bool = False


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as file:
        for line in file:
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ.setdefault(key, value.strip().strip('"'))


def _configured_values(name: str, defaults: list[str]) -> tuple[str, ...]:
    values = [value.strip() for value in os.getenv(name, "").split("||") if value.strip()]
    return tuple(values or defaults)


def discovery_queries(max_queries: int | None = None) -> list[str]:
    load_env()
    return QueryMatrixGenerator(
        company=os.getenv("COMPANY_NAME", "Dexcom"),
        locations=_configured_values("DISCOVERY_LOCATIONS", DEFAULT_LOCATIONS),
        job_families=_configured_values("DISCOVERY_JOB_FAMILIES", DEFAULT_JOB_FAMILIES),
    ).generate(max_queries or int(os.getenv("MAX_SEARCH_QUERIES", "75")))


def configured_provider(verbose: bool = False, engine: str | None = None) -> JobDiscoveryProvider:
    load_env()
    settings = BrowserSettings(
        engine=(engine or os.getenv("SEARCH_ENGINE", "google")).casefold(),
        max_pages=int(os.getenv("MAX_SEARCH_PAGES", "5")),
        headless=os.getenv("BROWSER_HEADLESS", "false").casefold() == "true",
        verbose=verbose,
    )
    if settings.engine not in {"google", "bing"}:
        raise ValueError("SEARCH_ENGINE must be google or bing.")
    return ChromeSearchProvider(settings)


class ChromeSearchProvider(JobDiscoveryProvider):
    """Uses local Chrome only for public search-engine result pages."""

    def __init__(self, settings: BrowserSettings):
        self.settings = settings
        self.driver = None
        self.profile_dir = None
        self.debug_port = None
        self.last_links_inspected = 0
        self.last_sample_destinations: list[str] = []

    @staticmethod
    def _free_port() -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def _start(self) -> None:
        if self.driver:
            return
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except ImportError as error:
            raise DiscoveryError("Selenium is not installed. Run: pip install -r requirements.txt") from error
        chrome_binary = os.getenv("CHROME_BINARY", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" if sys.platform == "darwin" else "/usr/bin/chromium")
        if not os.path.exists(chrome_binary):
            raise DiscoveryError(f"Chrome could not be started at {chrome_binary}. Please install Google Chrome and make sure it is available on this machine. No API key is required.")
        self.profile_dir = tempfile.mkdtemp(prefix="dexcom_chrome_")
        self.debug_port = self._free_port()
        try:
            # Launch an ordinary visible local Chrome process, then attach only to its local
            # DevTools port so result collection remains automatic.
            browser_args = [chrome_binary, f"--remote-debugging-port={self.debug_port}", f"--user-data-dir={self.profile_dir}", "--disable-notifications", "--lang=en-US"]
            if self.settings.headless:
                browser_args.extend(["--headless=new", "--no-sandbox", "--disable-dev-shm-usage"])
            if sys.platform == "darwin" and chrome_binary.endswith("Google Chrome"):
                subprocess.run(["open", "-na", "Google Chrome", "--args", *browser_args[1:]], check=True, capture_output=True, text=True)
            else:
                subprocess.Popen(browser_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(25):
                try:
                    with urlopen(f"http://127.0.0.1:{self.debug_port}/json/version", timeout=1):
                        break
                except Exception:
                    sleep(0.2)
            else:
                raise RuntimeError("Chrome DevTools endpoint did not become available")
            options = Options()
            options.debugger_address = f"127.0.0.1:{self.debug_port}"
            driver_path = os.getenv("CHROMEDRIVER_PATH", "")
            if driver_path:
                from selenium.webdriver.chrome.service import Service
                self.driver = webdriver.Chrome(service=Service(executable_path=driver_path), options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
        except Exception as error:
            shutil.rmtree(self.profile_dir, ignore_errors=True)
            self.profile_dir = None
            raise DiscoveryError("Chrome could not be started. Install Google Chrome and ensure ChromeDriver/Selenium Manager can access it. No API key is required.") from error

    @staticmethod
    def _direct_url(href: str) -> str:
        parsed = urlparse(href)
        if parsed.netloc.endswith("google.com") and parsed.path == "/url":
            href = parse_qs(parsed.query).get("q", [href])[0]
        return _decode_bing_redirect(href)

    @staticmethod
    def _metadata(title: str, text: str, url: str) -> JobResult:
        combined = f"{title}\n{text}"
        title_match = re.search(r"Dexcom(?:[^\n]*?)\s+hiring\s+(.+?)\s+in\s+.+?(?:\s+\|\s+LinkedIn|$)", title, re.I)
        location = re.search(r"\bin\s+([^|\n]+?)(?:\s+\|\s+LinkedIn|$)", title, re.I)
        if not location:
            location = re.search(r"Dexcom(?:\s+[^,.]+)?\s+([A-Z][^\n]+?,\s*[^\n]+)", text)
        posted = re.search(r"\b(?:just now|\d+\s+(?:minutes?|hours?|days?|weeks?)\s+ago)\b", combined, re.I)
        return JobResult(
            direct_url=url,
            title=title_match.group(1).strip() if title_match else title.replace(" | LinkedIn", "").strip(),
            company="Dexcom" if re.match(r"^Dexcom(?:\s|$)", title, re.I) else "",
            location=location.group(1).strip() if location else "",
            posted_date=posted.group(0) if posted else "",
            snippet=text,
        )

    def _page_url(self, query: str, page: int) -> str:
        if self.settings.engine == "bing":
            return f"https://www.bing.com/search?q={quote_plus(query)}&first={page * 10 + 1}"
        return f"https://www.google.com/search?q={quote_plus(query)}&start={page * 10}&num=10"

    def search(self, query: str, max_results: int) -> list[JobResult]:
        self._start()
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        results, seen = [], set()
        self.last_links_inspected = 0
        self.last_sample_destinations = []
        for page in range(self.settings.max_pages):
            if len(results) >= max_results:
                break
            if self.settings.verbose:
                print(f"  {self.settings.engine.title()} page {page + 1}: {query}")
            self.driver.get(self._page_url(query, page))
            WebDriverWait(self.driver, 12).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href]")))
            body = self.driver.find_element(By.TAG_NAME, "body").text
            if "unusual traffic" in body.casefold() or "captcha" in body.casefold():
                raise DiscoveryError(f"{self.settings.engine.title()} blocked automated search traffic. Try SEARCH_ENGINE=bing or wait and retry.")
            before = len(results)
            # Snapshot the rendered result containers in one browser-side operation. Bing mutates
            # result nodes during load, making iterative WebElement access stale and unreliable.
            containers = self.driver.execute_script("""
                return [...document.querySelectorAll('li.b_algo')].map(container => ({
                  title: container.querySelector('h2')?.innerText || '',
                  text: container.innerText || '',
                  html: container.outerHTML || '',
                  hrefs: [...container.querySelectorAll('a[href]')].map(anchor => anchor.href || '')
                }));
            """)
            for container in containers:
                self.last_links_inspected += 1
                values = container["hrefs"] + [container["html"]]
                for value in container["hrefs"]:
                    destination = self._direct_url(value)
                    if destination and len(self.last_sample_destinations) < 3:
                        self.last_sample_destinations.append(destination[:180])
                urls = extract_linkedin_job_urls(values)
                link_text, context = container["title"].strip(), container["text"]
                for href in urls:
                    _, job_id = canonical_url(href)
                    if job_id in seen:
                        continue
                    seen.add(job_id)
                    results.append(self._metadata(link_text, context, href))
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break
            if len(results) == before:
                break
            sleep(0.4)
        return results

    def close(self) -> None:
        if self.driver:
            try:
                self.driver.execute_cdp_cmd("Browser.close", {})
            except Exception:
                pass
            self.driver.quit()
            self.driver = None
        if self.profile_dir:
            shutil.rmtree(self.profile_dir, ignore_errors=True)
            self.profile_dir = None


class LinkedInPublicJobsProvider(ChromeSearchProvider):
    """Collects only the job cards publicly rendered by LinkedIn's unauthenticated Jobs page."""

    FILTER_MAP = {"7days": "r604800", "24hours": "r86400"}

    def __init__(self, settings: BrowserSettings, filter_name: str):
        super().__init__(settings)
        self.filter_name = filter_name
        self.last_cards_seen = 0

    def _url(self) -> str:
        return "https://www.linkedin.com/jobs/search/?" + urlencode({
            "keywords": os.getenv("COMPANY_NAME", "Dexcom"),
            "location": "Worldwide",
            "f_TPR": self.FILTER_MAP[self.filter_name],
        })

    def search(self, query: str, max_results: int) -> list[JobResult]:
        self._start()
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        self.driver.get(self._url())
        WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        body = self.driver.find_element(By.TAG_NAME, "body").text
        lowered = body.casefold()
        if any(marker in lowered for marker in ("captcha", "security verification", "verify your identity", "unusual activity")):
            raise DiscoveryError("LinkedIn public job search could not be accessed due to a verification or CAPTCHA page. No access-control bypass was attempted.")
        WebDriverWait(self.driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".base-card, .job-search-card")))
        stable_rounds = 0
        previous = 0
        for _ in range(8):
            cards = self.driver.execute_script("return document.querySelectorAll('.base-card, .job-search-card').length")
            if cards >= max_results or cards == previous:
                stable_rounds += 1
            else:
                stable_rounds = 0
            if stable_rounds >= 2:
                break
            previous = cards
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            buttons = self.driver.find_elements(By.CSS_SELECTOR, ".infinite-scroller__show-more-button, button[aria-label*='more'], button[aria-label*='More']")
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    self.driver.execute_script("arguments[0].click()", button)
                    break
            sleep(1)
        snapshots = self.driver.execute_script("""
          return [...document.querySelectorAll('.base-card, .job-search-card')].map(card => ({
            href: card.querySelector('a.base-card__full-link, a[href*="/jobs/view/"]')?.href || '',
            title: card.querySelector('.base-search-card__title, h3')?.innerText || '',
            company: card.querySelector('.base-search-card__subtitle, h4')?.innerText || '',
            location: card.querySelector('.job-search-card__location')?.innerText || '',
            posted: card.querySelector('time.job-search-card__listdate, time')?.getAttribute('datetime') || card.querySelector('time.job-search-card__listdate, time')?.innerText || '',
            text: card.innerText || ''
          }));
        """)
        self.last_cards_seen = len(snapshots)
        self.last_links_inspected = len(snapshots)
        self.last_sample_destinations = []
        results, seen = [], set()
        for card in snapshots:
            urls = extract_linkedin_job_urls([card["href"]])
            if card["href"] and len(self.last_sample_destinations) < 3:
                self.last_sample_destinations.append(card["href"][:180])
            for href in urls:
                _, job_id = canonical_url(href)
                if job_id in seen:
                    continue
                seen.add(job_id)
                results.append(JobResult(href, card["title"].strip(), card["company"].strip(), card["location"].strip(), card["posted"].strip(), card["text"]))
                if len(results) >= max_results:
                    return results
        return results


def configured_linkedin_provider(filter_name: str, verbose: bool = False) -> LinkedInPublicJobsProvider:
    load_env()
    return LinkedInPublicJobsProvider(BrowserSettings(headless=os.getenv("BROWSER_HEADLESS", "false").casefold() == "true", verbose=verbose), filter_name)
