"""Base crawler class for academic paper sources."""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.services.indexing_service import IndexingService
from app.services.embedding_service import EmbeddingService
from crawlers.parsers.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class PaperData:
    """Data class for paper information."""
    
    def __init__(
        self,
        title: str,
        abstract: Optional[str] = None,
        authors: Optional[List[Dict]] = None,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        publication_date: Optional[datetime] = None,
        publication_year: Optional[int] = None,
        journal: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        pdf_url: Optional[str] = None,
        source_url: Optional[str] = None,
        source_id: Optional[str] = None,
        **kwargs
    ):
        self.title = title
        self.abstract = abstract
        self.authors = authors or []
        self.doi = doi
        self.arxiv_id = arxiv_id
        self.publication_date = publication_date
        self.publication_year = publication_year
        self.journal = journal
        self.keywords = keywords or []
        self.pdf_url = pdf_url
        self.source_url = source_url
        self.source_id = source_id
        self.extra_data = kwargs


class BaseCrawler(ABC):
    """Base class for all paper crawlers."""
    
    # Source identifier - override in subclasses
    SOURCE_NAME = "base"
    SOURCE_CODE = "BASE"
    
    # Rate limiting
    REQUEST_DELAY = 2  # seconds between requests
    MAX_RETRIES = 3
    CONCURRENT_REQUESTS = 5
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(self.CONCURRENT_REQUESTS)
        self.pdf_parser = PDFParser()
        self.embedding_service = EmbeddingService()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def crawl(
        self,
        query: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        limit: int = 100
    ) -> AsyncGenerator[PaperData, None]:
        """
        Main crawling method. Must be implemented by subclasses.
        
        Yields PaperData objects for each paper found.
        """
        pass
    
    async def fetch_page(self, url: str, retries: int = 0) -> Optional[str]:
        """
        Fetch a page with retry logic.
        
        Args:
            url: URL to fetch
            retries: Current retry count
            
        Returns:
            Page content as string or None if failed
        """
        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        await asyncio.sleep(self.REQUEST_DELAY)
                        return await response.text()
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
            
            # Retry logic
            if retries < self.MAX_RETRIES:
                await asyncio.sleep(self.REQUEST_DELAY * (retries + 1))
                return await self.fetch_page(url, retries + 1)
            
            return None
    
    async def download_pdf(self, url: str, save_path: str) -> bool:
        """
        Download PDF file.
        
        Args:
            url: PDF URL
            save_path: Local path to save
            
        Returns:
            True if successful
        """
        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        with open(save_path, 'wb') as f:
                            f.write(await response.read())
                        await asyncio.sleep(self.REQUEST_DELAY)
                        return True
            except Exception as e:
                logger.error(f"Error downloading PDF from {url}: {e}")
        
        return False
    
    async def save_paper(self, paper_data: PaperData) -> Optional[str]:
        """
        Save paper to database.
        
        Args:
            paper_data: Paper data to save
            
        Returns:
            Paper ID if saved successfully
        """
        async with AsyncSessionLocal() as db:
            try:
                indexing_service = IndexingService(db)
                
                # Check for duplicates
                is_duplicate, existing_id = await indexing_service.check_duplicate(
                    doi=paper_data.doi,
                    arxiv_id=paper_data.arxiv_id,
                    title=paper_data.title
                )
                
                if is_duplicate:
                    logger.info(f"Duplicate found: {existing_id}")
                    return existing_id
                
                # Generate unique ID
                paper_id = await indexing_service.generate_id(
                    source=self.SOURCE_NAME,
                    year=paper_data.publication_year
                )
                
                # Generate embeddings
                title_embedding = None
                abstract_embedding = None
                
                try:
                    title_embedding = await self.embedding_service.get_embedding(
                        paper_data.title
                    )
                    if paper_data.abstract:
                        abstract_embedding = await self.embedding_service.get_embedding(
                            paper_data.abstract
                        )
                except Exception as e:
                    logger.error(f"Embedding generation failed: {e}")
                
                # Create paper in database
                from app.models.paper import Paper, Author
                
                paper = Paper(
                    id=paper_id,
                    title=paper_data.title,
                    abstract=paper_data.abstract,
                    doi=paper_data.doi,
                    arxiv_id=paper_data.arxiv_id,
                    source_type=self.SOURCE_NAME,
                    source_url=paper_data.source_url,
                    source_id=paper_data.source_id,
                    journal=paper_data.journal,
                    publication_date=paper_data.publication_date,
                    publication_year=paper_data.publication_year,
                    keywords=paper_data.keywords,
                    pdf_url=paper_data.pdf_url,
                    title_embedding=title_embedding,
                    abstract_embedding=abstract_embedding,
                    is_processed=0
                )
                
                # Add authors
                for author_data in paper_data.authors:
                    # Check if author exists
                    author = None
                    if author_data.get('orcid'):
                        from sqlalchemy import select
                        result = await db.execute(
                            select(Author).where(Author.orcid == author_data['orcid'])
                        )
                        author = result.scalar_one_or_none()
                    
                    if not author:
                        # Generate author ID
                        author_id = await indexing_service.generate_id(
                            source="manual",
                            year=None
                        )
                        author = Author(
                            id=author_id,
                            full_name=author_data.get('full_name', 'Unknown'),
                            full_name_ru=author_data.get('full_name_ru'),
                            affiliations=author_data.get('affiliations'),
                            orcid=author_data.get('orcid')
                        )
                        db.add(author)
                    
                    paper.authors.append(author)
                
                db.add(paper)
                await db.commit()
                
                logger.info(f"Saved paper: {paper_id}")
                return paper_id
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error saving paper: {e}")
                return None
    
    async def run(
        self,
        query: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        limit: int = 100
    ) -> Dict:
        """
        Run the crawler and save results.
        
        Returns:
            Statistics dict with counts
        """
        stats = {
            "found": 0,
            "saved": 0,
            "duplicates": 0,
            "errors": 0
        }
        
        async with self:
            async for paper_data in self.crawl(query, year_from, year_to, limit):
                stats["found"] += 1
                
                paper_id = await self.save_paper(paper_data)
                
                if paper_id:
                    stats["saved"] += 1
                else:
                    stats["errors"] += 1
                
                if stats["saved"] >= limit:
                    break
        
        return stats
