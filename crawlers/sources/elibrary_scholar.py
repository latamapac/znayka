"""Crawler for eLibrary.ru papers via Google Scholar.

Bypasses eLibrary.ru's IP-based access restrictions by discovering papers
through Google Scholar (site:elibrary.ru), which returns titles, authors,
journals, citation counts, eLibrary IDs, and direct PDF URLs.

Usage:
    async with ElibraryScholarCrawler() as crawler:
        async for paper in crawler.search_papers("машинное обучение", limit=50):
            print(paper.title, paper.source_id)
"""
import asyncio
import logging
import random
import re
import time
from typing import AsyncGenerator, Dict, List, Optional
from urllib.parse import quote_plus, urlencode

from scrapling import Fetcher
from scrapling.parser import Adaptor

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)

# Google Scholar rate-limits aggressively. These delays help avoid blocks.
_MIN_DELAY = 3.0
_MAX_DELAY = 6.0
_CAPTCHA_BACKOFF = 30.0
_MAX_CAPTCHA_RETRIES = 3


class ElibraryScholarCrawler(BaseCrawler):
    """Discover eLibrary.ru papers via Google Scholar scraping with Scrapling."""

    SOURCE_NAME = "eLibrary_Scholar"
    SOURCE_CODE = "ELSC"
    BASE_URL = "https://scholar.google.com"

    def __init__(self, delay: Optional[float] = None):
        super().__init__(delay=delay or _MIN_DELAY)
        self._fetcher: Optional[Fetcher] = None
        self._request_count = 0

    async def __aenter__(self):
        self._fetcher = Fetcher()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._fetcher = None

    # ------------------------------------------------------------------
    # Core: fetch a Google Scholar page via Scrapling (sync, run in thread)
    # ------------------------------------------------------------------

    def _fetch_scholar(self, url: str) -> Optional[Adaptor]:
        """Fetch a Google Scholar page. Returns parsed page or None."""
        for attempt in range(_MAX_CAPTCHA_RETRIES):
            # Rate limit with jitter
            if self._request_count > 0:
                delay = random.uniform(self.delay, self.delay * 2)
                time.sleep(delay)
            self._request_count += 1

            try:
                page = self._fetcher.get(url)
            except Exception as e:
                logger.error(f"Fetch error: {e}")
                return None

            if page.status == 200:
                body = str(page.body)
                if "unusual traffic" in body.lower() or "/sorry/" in body.lower():
                    logger.warning(
                        f"CAPTCHA detected (attempt {attempt + 1}), "
                        f"backing off {_CAPTCHA_BACKOFF}s"
                    )
                    time.sleep(_CAPTCHA_BACKOFF * (attempt + 1))
                    continue
                return page

            if page.status == 429:
                logger.warning(f"Rate limited (429), backing off {_CAPTCHA_BACKOFF}s")
                time.sleep(_CAPTCHA_BACKOFF * (attempt + 1))
                continue

            logger.warning(f"HTTP {page.status} for {url}")
            return page

        logger.error(f"Failed after {_MAX_CAPTCHA_RETRIES} captcha retries: {url}")
        return None

    async def _async_fetch(self, url: str) -> Optional[Adaptor]:
        return await asyncio.to_thread(self._fetch_scholar, url)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> AsyncGenerator[PaperData, None]:
        """Search for eLibrary papers via Google Scholar."""

        scholar_query = f"site:elibrary.ru {query}"
        papers_found = 0
        start = 0
        page_size = 20  # Google Scholar max per page
        seen_ids = set()

        while papers_found < limit:
            params = {
                "q": scholar_query,
                "hl": "ru",
                "num": min(page_size, limit - papers_found),
                "start": start,
            }
            if year_from:
                params["as_ylo"] = year_from
            if year_to:
                params["as_yhi"] = year_to

            url = f"{self.BASE_URL}/scholar?{urlencode(params)}"
            logger.info(f"Fetching Scholar page start={start}")

            page = await self._async_fetch(url)
            if page is None:
                logger.error("Failed to fetch Scholar page, stopping")
                break

            results = self._parse_scholar_page(page)
            if not results:
                logger.info("No more results from Scholar")
                break

            for paper_data in results:
                if papers_found >= limit:
                    break

                # Deduplicate by eLibrary ID
                eid = paper_data.source_id
                if eid and eid in seen_ids:
                    continue
                if eid:
                    seen_ids.add(eid)

                yield paper_data
                papers_found += 1

            # Check if there's a next page
            has_next = bool(page.css('a[aria-label="Next"]') or page.css('.gs_ico_nav_next'))
            if not has_next:
                logger.info("No next page link, stopping")
                break

            start += page_size

        logger.info(f"Scholar crawl complete: {papers_found} papers found")

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_scholar_page(self, page) -> List[PaperData]:
        """Parse a Google Scholar results page into PaperData objects."""
        papers = []

        # Each result is in a .gs_r container
        entries = page.css(".gs_r.gs_or.gs_scl")
        if not entries:
            entries = page.css(".gs_r")

        for entry in entries:
            try:
                paper = self._parse_scholar_entry(entry)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"Error parsing Scholar entry: {e}")

        return papers

    def _parse_scholar_entry(self, entry) -> Optional[PaperData]:
        """Parse a single Google Scholar result."""

        # --- Title + URL ---
        title = None
        url = None
        title_links = entry.css(".gs_rt a")
        if title_links:
            title = self._clean(title_links[0].text)
            url = title_links[0].attrib.get("href", "")
        else:
            title_elems = entry.css(".gs_rt")
            if title_elems:
                title = self._clean(title_elems[0].text)

        if not title:
            return None

        # --- eLibrary ID ---
        elibrary_id = None
        pdf_url = None
        if url:
            id_match = re.search(r"item\.asp\?id=(\d+)", url)
            if id_match:
                elibrary_id = id_match.group(1)
            # Direct PDF link
            if url.endswith(".pdf") or "/download/" in url:
                pdf_url = url

        # Also check the right-side PDF link
        pdf_links = entry.css(".gs_ggs a")
        if pdf_links:
            pdf_href = pdf_links[0].attrib.get("href", "")
            if "elibrary" in pdf_href:
                pdf_url = pdf_href
                if not elibrary_id:
                    id_match = re.search(r"elibrary_(\d+)", pdf_href)
                    if id_match:
                        elibrary_id = id_match.group(1)

        # --- Authors / Journal / Year ---
        authors = []
        journal = None
        year = None

        meta_elems = entry.css(".gs_a")
        if meta_elems:
            meta_text = self._clean(meta_elems[0].text) or ""
            authors, journal, year = self._parse_scholar_meta(meta_text)

        # --- Snippet (use as abstract) ---
        abstract = None
        snippet_elems = entry.css(".gs_rs")
        if snippet_elems:
            abstract = self._clean(snippet_elems[0].text)

        # --- Citation count ---
        citations = 0
        cite_links = entry.css('a[href*="cites"]')
        if cite_links:
            cite_text = self._clean(cite_links[0].text) or ""
            cite_match = re.search(r"(\d+)", cite_text)
            if cite_match:
                citations = int(cite_match.group(1))

        # --- Build source URL ---
        source_url = url
        if elibrary_id and (not source_url or "elibrary" not in source_url):
            source_url = f"https://elibrary.ru/item.asp?id={elibrary_id}"

        is_russian = self._is_russian(title)

        return PaperData(
            title=title,
            title_ru=title if is_russian else None,
            source_type="elibrary",
            source_id=elibrary_id,
            source_url=source_url,
            abstract=abstract,
            abstract_ru=abstract if abstract and self._is_russian(abstract) else None,
            authors=[{"full_name": a} for a in authors],
            journal=journal,
            publication_year=year,
            keywords=[],
            pdf_url=pdf_url,
            language="ru" if is_russian else "en",
        )

    def _parse_scholar_meta(self, meta_text: str):
        """Parse the Scholar metadata line: 'Authors - Journal, Year - Publisher'."""
        authors = []
        journal = None
        year = None

        parts = [p.strip() for p in meta_text.split(" - ")]

        # First part: authors
        if parts:
            author_str = parts[0]
            # Remove trailing ellipsis
            author_str = re.sub(r"…$", "", author_str).strip()
            authors = [
                a.strip()
                for a in re.split(r",\s*", author_str)
                if a.strip() and len(a.strip()) > 1
            ]

        # Middle parts: journal + year
        if len(parts) >= 2:
            journal_part = parts[1]
            # Extract year
            year_match = re.search(r"(\d{4})", journal_part)
            if year_match:
                year = int(year_match.group(1))
                journal_part = journal_part[: year_match.start()].strip().rstrip(",").strip()
            if journal_part:
                journal = journal_part

        return authors, journal, year

    # ------------------------------------------------------------------
    # get_paper_by_id — look up a single paper on Scholar
    # ------------------------------------------------------------------

    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Look up a specific eLibrary paper via Google Scholar."""
        url = f'{self.BASE_URL}/scholar?q="elibrary.ru/item.asp?id={paper_id}"&hl=ru'
        page = await self._async_fetch(url)
        if page is None:
            return None

        results = self._parse_scholar_page(page)
        # Return the first result that matches the ID
        for paper in results:
            if paper.source_id == paper_id:
                return paper
        # If no exact match, return first result if any
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clean(self, text) -> Optional[str]:
        """Clean text from Scrapling element."""
        if text is None:
            return None
        if hasattr(text, "text"):
            text = text.text
        if not isinstance(text, str):
            text = str(text)
        text = re.sub(r"\s+", " ", text).strip()
        # Remove HTML tags that sometimes leak through
        text = re.sub(r"<[^>]+>", "", text)
        return text if text else None

    def _is_russian(self, text: str) -> bool:
        return bool(re.search(r"[а-яА-ЯёЁ]", text)) if text else False
