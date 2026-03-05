#!/usr/bin/env python3
"""
Benchmark script for eLibrary.ru scraping bypass methods.
Run this on your actual server (Contabo/GCP) — not behind a proxy.

Usage:
    pip install scrapling[all] curl_cffi cloudscraper requests
    python3 scripts/benchmark_elibrary.py
"""
import time
import re
import json
import sys
from datetime import datetime


ELIBRARY_MAIN = "https://elibrary.ru"
ELIBRARY_SEARCH = "https://elibrary.ru/query_results.asp"
ELIBRARY_ITEM = "https://elibrary.ru/item.asp"

SEARCH_QUERY = "машинное обучение"
TEST_PAPER_ID = "49283012"  # known paper ID

HEADERS_RU = {
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def get_title(html):
    t = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    return t.group(1).strip()[:80] if t else "-"


def has_antibot(html):
    lower = html.lower()
    indicators = ["captcha", "robot", "challenge", "turnstile", "ddos-guard", "blocked"]
    found = [i for i in indicators if i in lower]
    return found


def has_content(html):
    """Check if we got actual eLibrary content."""
    return any(x in html for x in [
        "elibrary", "РИНЦ", "item.asp", "Научная электронная библиотека",
        "query_results", "author_profile"
    ])


def extract_paper_links(html):
    return re.findall(r'item\.asp\?id=(\d+)', html)


def run_test(name, fetch_fn, urls):
    print(f"\n{'=' * 70}")
    print(f"  METHOD: {name}")
    print(f"{'=' * 70}")

    results = {}
    for label, url in urls.items():
        t0 = time.time()
        try:
            status, text, cookies = fetch_fn(url)
            elapsed = time.time() - t0
            title = get_title(text)
            antibot = has_antibot(text)
            content = has_content(text)
            papers = extract_paper_links(text) if "search" in label else []

            result = {
                "status": status,
                "size": len(text),
                "time": round(elapsed, 2),
                "title": title,
                "antibot": antibot,
                "has_content": content,
                "papers_found": len(papers),
                "cookies": len(cookies) if cookies else 0,
            }
            results[label] = result

            status_icon = "OK" if status == 200 and content else "WARN" if status == 200 else "FAIL"
            print(f"  [{status_icon}] {label:<25} {status:>3} | {len(text):>7}c | {elapsed:.1f}s | papers:{len(papers):>3} | antibot:{antibot or 'none'}")

        except Exception as e:
            elapsed = time.time() - t0
            results[label] = {"error": str(e), "time": round(elapsed, 2)}
            print(f"  [ERR] {label:<25} {type(e).__name__}: {str(e)[:60]}")

    return results


# ---------------------------------------------------------------------------
# Method 1: curl_cffi with Chrome impersonation
# ---------------------------------------------------------------------------
def test_curl_cffi_chrome():
    from curl_cffi import requests as cffi_requests

    session = cffi_requests.Session(impersonate="chrome131")

    def fetch(url):
        r = session.get(url, headers=HEADERS_RU, timeout=20)
        return r.status_code, r.text, dict(r.cookies)

    return fetch


# ---------------------------------------------------------------------------
# Method 2: curl_cffi with Safari impersonation
# ---------------------------------------------------------------------------
def test_curl_cffi_safari():
    from curl_cffi import requests as cffi_requests

    session = cffi_requests.Session(impersonate="safari18_0")

    def fetch(url):
        r = session.get(url, headers=HEADERS_RU, timeout=20)
        return r.status_code, r.text, dict(r.cookies)

    return fetch


# ---------------------------------------------------------------------------
# Method 3: curl_cffi Chrome + session cookie persistence + 2-step
# ---------------------------------------------------------------------------
def test_curl_cffi_twostep():
    from curl_cffi import requests as cffi_requests

    session = cffi_requests.Session(impersonate="chrome131")

    def fetch(url):
        # Step 1: Visit main page first to get session cookies
        if not hasattr(fetch, '_initialized'):
            session.get(ELIBRARY_MAIN, headers=HEADERS_RU, timeout=20)
            time.sleep(1)
            fetch._initialized = True

        r = session.get(url, headers={
            **HEADERS_RU,
            "Referer": ELIBRARY_MAIN,
        }, timeout=20)
        return r.status_code, r.text, dict(r.cookies)

    return fetch


# ---------------------------------------------------------------------------
# Method 4: cloudscraper
# ---------------------------------------------------------------------------
def test_cloudscraper():
    import cloudscraper

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "linux", "desktop": True},
        delay=3,
    )

    def fetch(url):
        r = scraper.get(url, headers=HEADERS_RU, timeout=20)
        return r.status_code, r.text, dict(r.cookies)

    return fetch


# ---------------------------------------------------------------------------
# Method 5: cloudscraper + 2-step (visit main page first)
# ---------------------------------------------------------------------------
def test_cloudscraper_twostep():
    import cloudscraper

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "linux", "desktop": True},
        delay=3,
    )

    def fetch(url):
        if not hasattr(fetch, '_initialized'):
            scraper.get(ELIBRARY_MAIN, headers=HEADERS_RU, timeout=20)
            time.sleep(2)
            fetch._initialized = True

        r = scraper.get(url, headers={
            **HEADERS_RU,
            "Referer": ELIBRARY_MAIN,
        }, timeout=20)
        return r.status_code, r.text, dict(r.cookies)

    return fetch


# ---------------------------------------------------------------------------
# Method 6: Scrapling Fetcher
# ---------------------------------------------------------------------------
def test_scrapling():
    from scrapling import Fetcher

    fetcher = Fetcher()

    def fetch(url):
        page = fetcher.get(url)
        return page.status, str(page.body), {}

    return fetch


# ---------------------------------------------------------------------------
# Method 7: Scrapling StealthyFetcher
# ---------------------------------------------------------------------------
def test_scrapling_stealth():
    from scrapling import StealthyFetcher

    fetcher = StealthyFetcher()

    def fetch(url):
        page = fetcher.fetch(url)
        return page.status, str(page.body), {}

    return fetch


# ---------------------------------------------------------------------------
# Method 8: requests + full browser-like headers
# ---------------------------------------------------------------------------
def test_requests_stealth():
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        **HEADERS_RU,
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    })

    def fetch(url):
        if not hasattr(fetch, '_initialized'):
            session.get(ELIBRARY_MAIN, timeout=20)
            time.sleep(1)
            fetch._initialized = True

        r = session.get(url, timeout=20, headers={"Referer": ELIBRARY_MAIN})
        return r.status_code, r.text, dict(r.cookies)

    return fetch


def main():
    urls = {
        "main_page": ELIBRARY_MAIN,
        "search": f"{ELIBRARY_SEARCH}?query={SEARCH_QUERY}",
        "paper": f"{ELIBRARY_ITEM}?id={TEST_PAPER_ID}",
    }

    methods = {
        "curl_cffi (Chrome 131)": test_curl_cffi_chrome,
        "curl_cffi (Safari 18)": test_curl_cffi_safari,
        "curl_cffi Chrome + 2-step": test_curl_cffi_twostep,
        "cloudscraper": test_cloudscraper,
        "cloudscraper + 2-step": test_cloudscraper_twostep,
        "Scrapling Fetcher": test_scrapling,
        "Scrapling StealthyFetcher": test_scrapling_stealth,
        "requests + stealth headers": test_requests_stealth,
    }

    print(f"eLibrary.ru Bypass Benchmark")
    print(f"Run at: {datetime.now().isoformat()}")
    print(f"Testing {len(methods)} methods x {len(urls)} URLs")

    all_results = {}

    for name, factory in methods.items():
        try:
            fetch_fn = factory()
            results = run_test(name, fetch_fn, urls)
            all_results[name] = results
        except ImportError as e:
            print(f"\n  SKIP {name}: {e}")
        except Exception as e:
            print(f"\n  FAIL {name}: {type(e).__name__}: {e}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  {'Method':<35} {'Main':>6} {'Search':>6} {'Paper':>6} {'Papers#':>8}")
    print(f"  {'-' * 35} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 8}")

    for method, results in all_results.items():
        main_s = results.get("main_page", {}).get("status", "ERR")
        search_s = results.get("search", {}).get("status", "ERR")
        paper_s = results.get("paper", {}).get("status", "ERR")
        papers_n = results.get("search", {}).get("papers_found", 0)
        print(f"  {method:<35} {main_s:>6} {search_s:>6} {paper_s:>6} {papers_n:>8}")

    # Save results
    output_file = f"benchmark_elibrary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved to: {output_file}")


if __name__ == "__main__":
    main()
