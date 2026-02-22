"""Base crawler class for all academic sources."""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator, List, Optional, Dict, Any

import aiohttp
from aiohttp import ClientTimeout

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class PaperData:
    """Data structure for crawled paper information."""
    # Required fields
    title: str
    source_type: str
    
    # Optional metadata
    title_ru: Optional[str] = None
    abstract: Optional[str] = None
    abstract_ru: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    
    # Authors
    authors: List[Dict[str, Any]] = None
    
    # Publication info
    journal: Optional[str] = None
    journal_ru: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publication_date: Optional[datetime] = None
    publication_year: Optional[int] = None
    
    # Content
    keywords: List[str] = None
    keywords_ru: List[str] = None
    full_text: Optional[str] = None
    
    # URLs and files
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_content: Optional[bytes] = None
    
    # Language
    language: str = "ru"
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []
        if self.keywords_ru is None:
            self.keywords_ru = []


class BaseCrawler(ABC):
    """Base class for all academic paper crawlers."""
    
    # Override in subclass
    SOURCE_NAME: str = "base"
    SOURCE_CODE: str = "BASE"
    BASE_URL: str = ""
    
    def __init__(self, delay: Optional[float] = None):
        self.delay = delay or settings.CRAWLER_DELAY_SECONDS
        self.max_retries = settings.CRAWLER_MAX_RETRIES
        self.timeout = ClientTimeout(total=30)
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_count = 0
        
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(
            limit=settings.CRAWLER_CONCURRENT_REQUESTS,
            limit_per_host=2,
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=self._get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get default HTTP headers."""
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
        }
    
    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with rate limiting and retries."""
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                if self._request_count > 0:
                    await asyncio.sleep(self.delay)
                
                self._request_count += 1
                
                async with self.session.request(
                    method, url, **kwargs
                ) as response:
                    response.raise_for_status()
                    return response
                    
            except aiohttp.ClientError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.delay * (attempt + 1))
        
        raise Exception("Max retries exceeded")
    
    async def _get_html(self, url: str) -> str:
        """Fetch HTML content from URL."""
        response = await self._make_request(url)
        return await response.text()
    
    async def _get_json(self, url: str, **kwargs) -> Dict:
        """Fetch JSON content from URL."""
        response = await self._make_request(url, **kwargs)
        return await response.json()
    
    @abstractmethod
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """
        Search for papers matching query.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            year_from: Filter by publication year (from)
            year_to: Filter by publication year (to)
            
        Yields:
            PaperData objects
        """
        pass
    
    @abstractmethod
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """
        Get paper details by ID.
        
        Args:
            paper_id: Paper identifier
            
        Returns:
            PaperData or None if not found
        """
        pass
    
    async def download_pdf(self, url: str) -> Optional[bytes]:
        """
        Download PDF from URL.
        
        Args:
            url: PDF URL
            
        Returns:
            PDF content as bytes or None
        """
        try:
            response = await self._make_request(url)
            content_type = response.headers.get('Content-Type', '')
            
            if 'pdf' not in content_type.lower():
                logger.warning(f"URL does not return PDF: {content_type}")
            
            return await response.read()
            
        except Exception as e:
            logger.error(f"Failed to download PDF from {url}: {e}")
            return None
    
    def normalize_doi(self, doi: str) -> Optional[str]:
        """Normalize DOI string."""
        if not doi:
            return None
        
        doi = doi.strip()
        
        # Remove common prefixes
        prefixes = ["doi:", "doi.org/", "https://doi.org/", "http://doi.org/"]
        for prefix in prefixes:
            if doi.lower().startswith(prefix):
                doi = doi[len(prefix):]
        
        return doi if doi else None
    
    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize text content."""
        if not text:
            return None
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        return text.strip() if text else None
