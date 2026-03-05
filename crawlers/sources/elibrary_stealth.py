"""Stealth crawler for eLibrary.ru using curl_cffi for TLS fingerprint impersonation.

Uses curl_cffi to impersonate Chrome's TLS/JA3/HTTP2 fingerprint, bypassing
eLibrary.ru's anti-bot detection. Falls back through multiple strategies:
1. curl_cffi Chrome session with cookie persistence
2. curl_cffi Safari fallback
3. cloudscraper as last resort
"""
import asyncio
import logging
import re
import time
from typing import AsyncGenerator, Dict, List, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class _StealthSession:
    """Sync HTTP session with browser TLS impersonation via curl_cffi."""

    IMPERSONATE_CHAIN = ["chrome131", "chrome126", "safari18_0"]

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self._session = None
        self._impersonate_idx = 0
        self._initialized = False
        self._last_request = 0.0

    def _get_session(self):
        if self._session is None:
            from curl_cffi import requests as cffi_requests
            imp = self.IMPERSONATE_CHAIN[self._impersonate_idx]
            logger.info(f"Creating stealth session with impersonate={imp}")
            self._session = cffi_requests.Session(impersonate=imp)
        return self._session

    def _rotate_impersonation(self):
        """Try next browser impersonation in the chain."""
        self._impersonate_idx = (self._impersonate_idx + 1) % len(self.IMPERSONATE_CHAIN)
        self._session = None
        self._initialized = False
        logger.info(f"Rotating to impersonation: {self.IMPERSONATE_CHAIN[self._impersonate_idx]}")

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.time()

    def get(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Fetch URL with retry and impersonation rotation."""
        session = self._get_session()

        # Warm up session with main page visit on first request
        if not self._initialized:
            try:
                logger.info("Warming up session with elibrary.ru main page")
                session.get("https://elibrary.ru", headers=self._headers(), timeout=20)
                time.sleep(1.5)
                self._initialized = True
            except Exception as e:
                logger.warning(f"Warmup failed: {e}")

        for attempt in range(max_retries):
            self._rate_limit()
            try:
                r = session.get(url, headers=self._headers(referer="https://elibrary.ru"), timeout=20)

                if r.status_code == 200:
                    return r.text

                if r.status_code == 403:
                    logger.warning(f"403 on attempt {attempt + 1}, rotating impersonation")
                    self._rotate_impersonation()
                    session = self._get_session()
                    continue

                if r.status_code == 503:
                    logger.warning(f"503 on attempt {attempt + 1}, waiting and retrying")
                    time.sleep(self.delay * (attempt + 1))
                    continue

                logger.warning(f"HTTP {r.status_code} for {url}")
                return r.text

            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.delay * (attempt + 1))
                    self._rotate_impersonation()
                    session = self._get_session()

        return None

    def _headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def close(self):
        if self._session:
            self._session.close()
            self._session = None


class ElibraryStealthCrawler(BaseCrawler):
    """Stealth crawler for eLibrary.ru with anti-bot bypass."""

    SOURCE_NAME = "eLibrary"
    SOURCE_CODE = "ELIB"
    BASE_URL = "https://elibrary.ru"

    def __init__(self, delay: Optional[float] = None):
        super().__init__(delay=delay or 3.0)
        self._stealth = _StealthSession(delay=self.delay)

    async def __aenter__(self):
        # Don't create aiohttp session - we use curl_cffi sync session
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._stealth.close()

    def _fetch(self, url: str) -> Optional[str]:
        """Sync fetch via stealth session (run in thread for async compat)."""
        return self._stealth.get(url)

    async def _get_html(self, url: str) -> Optional[str]:
        """Async wrapper around sync stealth fetch."""
        return await asyncio.to_thread(self._fetch, url)

    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search eLibrary for papers."""

        papers_found = 0
        page = 1

        while papers_found < limit:
            params = {
                "querybox": query,
                "order": "1",  # by relevance
                "part": "0",
                "pagenum": page,
            }

            if year_from:
                params["yf"] = year_from
            if year_to:
                params["yt"] = year_to

            search_url = f"{self.BASE_URL}/query_results.asp?{urlencode(params)}"

            html = await self._get_html(search_url)
            if not html:
                logger.error(f"Failed to fetch search page {page}")
                break

            soup = BeautifulSoup(html, 'html.parser')

            # Find paper links - eLibrary uses item.asp?id=NNNNN
            paper_ids = set()
            for link in soup.find_all('a', href=re.compile(r'item\.asp\?id=\d+')):
                href = link.get('href', '')
                match = re.search(r'id=(\d+)', href)
                if match:
                    paper_ids.add(match.group(1))

            if not paper_ids:
                logger.info(f"No papers found on page {page}, stopping")
                break

            logger.info(f"Found {len(paper_ids)} papers on page {page}")

            for paper_id in paper_ids:
                if papers_found >= limit:
                    break

                paper_data = await self.get_paper_by_id(paper_id)
                if paper_data:
                    yield paper_data
                    papers_found += 1

            page += 1

    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get paper details from eLibrary."""

        url = f"{self.BASE_URL}/item.asp?id={paper_id}"

        html = await self._get_html(url)
        if not html:
            return None

        try:
            return self._parse_paper(html, paper_id, url)
        except Exception as e:
            logger.error(f"Error parsing paper {paper_id}: {e}")
            return None

    def _parse_paper(self, html: str, paper_id: str, url: str) -> Optional[PaperData]:
        """Parse paper details from eLibrary HTML."""
        soup = BeautifulSoup(html, 'html.parser')

        # Title - try multiple selectors
        title = None
        for selector in ['h1', '.title', '[class*="title"]', 'font[color="#00008f"]']:
            elem = soup.select_one(selector)
            if elem:
                text = self.clean_text(elem.get_text())
                if text and len(text) > 5:
                    title = text
                    break

        if not title:
            # Try from meta tags
            meta = soup.find('meta', attrs={'name': 'title'})
            if meta:
                title = meta.get('content')

        if not title:
            logger.warning(f"No title found for paper {paper_id}")
            return None

        # Authors
        authors = []
        for selector in ['a[href*="author_profile.asp"]', '.author', '[class*="author"]']:
            author_elems = soup.select(selector)
            if author_elems:
                for elem in author_elems:
                    name = self.clean_text(elem.get_text())
                    if name and len(name) > 2 and name not in [a['full_name'] for a in authors]:
                        authors.append({"full_name": name})
                break

        # Abstract
        abstract = None
        for selector in ['[class*="abstract"]', '.abstract', '#abstract', 'p[id*="abstract"]']:
            elem = soup.select_one(selector)
            if elem:
                abstract = self.clean_text(elem.get_text())
                if abstract and len(abstract) > 20:
                    break
                abstract = None

        # Journal
        journal = None
        journal_elem = soup.select_one('a[href*="contents.asp"], a[href*="title_about.asp"]')
        if journal_elem:
            journal = self.clean_text(journal_elem.get_text())

        # Year
        year = None
        year_match = re.search(r'(?:год|year|©)\s*[:=]?\s*(20\d{2}|19\d{2})', html, re.I)
        if year_match:
            year = int(year_match.group(1))
        else:
            year_match = re.search(r'(20\d{2}|19\d{2})\s*(?:г\.?|год)', html)
            if year_match:
                year = int(year_match.group(1))

        # DOI
        doi = None
        doi_match = re.search(r'(10\.\d{4,}/[^\s"<>]+)', html)
        if doi_match:
            doi = self.normalize_doi(doi_match.group(1))

        # Keywords
        keywords = []
        kw_elem = soup.select_one('[class*="keyword"]')
        if kw_elem:
            kw_text = kw_elem.get_text()
            keywords = [k.strip() for k in re.split(r'[,;]', kw_text) if k.strip()]

        # PDF link
        pdf_url = None
        pdf_link = soup.select_one('a[href*=".pdf"], a[href*="download"], a[title*="PDF"], a[title*="pdf"]')
        if pdf_link:
            pdf_href = pdf_link.get('href')
            if pdf_href:
                pdf_url = urljoin(self.BASE_URL, pdf_href)

        is_russian = self._is_russian(title)

        return PaperData(
            title=title,
            title_ru=title if is_russian else None,
            source_type=self.SOURCE_NAME.lower(),
            source_id=paper_id,
            source_url=url,
            abstract=abstract,
            abstract_ru=abstract if abstract and self._is_russian(abstract) else None,
            authors=authors,
            journal=journal,
            publication_year=year,
            doi=doi,
            keywords=keywords,
            pdf_url=pdf_url,
            language="ru" if is_russian else "en"
        )

    def _is_russian(self, text: str) -> bool:
        """Check if text contains Russian characters."""
        return bool(re.search(r'[а-яА-ЯёЁ]', text)) if text else False
