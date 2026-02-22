"""Orchestrator for running multiple crawlers and storing results."""
import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

# Import crawlers
from crawlers.sources.base import BaseCrawler, PaperData
from crawlers.sources import CRAWLER_REGISTRY, get_crawler_class

# Import database models and services
from app.db.base import AsyncSessionLocal
from app.models.paper import Paper, Author
from app.services.indexing_service import IndexingService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class CrawlerOrchestrator:
    """Orchestrates multiple crawlers and manages data ingestion."""
    
    CRAWLERS = CRAWLER_REGISTRY
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    async def crawl_source(
        self,
        source: str,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        store: bool = True
    ) -> List[PaperData]:
        """
        Crawl a specific source for papers.
        
        Args:
            source: Source name (elibrary, cyberleninka, arxiv, rsl_dissertations, etc.)
            query: Search query
            limit: Maximum papers to fetch
            year_from: Filter by year (from)
            year_to: Filter by year (to)
            store: Whether to store in database
            
        Returns:
            List of PaperData objects
        """
        if source not in self.CRAWLERS:
            raise ValueError(f"Unknown source: {source}. Available: {list(self.CRAWLERS.keys())}")
        
        crawler_class = self.CRAWLERS[source]
        papers = []
        
        async with crawler_class() as crawler:
            async for paper_data in crawler.search_papers(
                query=query,
                limit=limit,
                year_from=year_from,
                year_to=year_to
            ):
                papers.append(paper_data)
                
                if store:
                    await self._store_paper(paper_data)
        
        return papers
    
    async def crawl_all_sources(
        self,
        query: str,
        limit_per_source: int = 50,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        store: bool = True,
        sources: Optional[List[str]] = None
    ) -> dict:
        """
        Crawl all available sources for papers.
        
        Args:
            query: Search query
            limit_per_source: Max papers per source
            year_from: Filter by year (from)
            year_to: Filter by year (to)
            store: Whether to store in database
            sources: Specific sources to crawl (None = all)
            
        Returns:
            Dictionary with results per source
        """
        sources_to_crawl = sources or list(self.CRAWLERS.keys())
        results = {}
        
        for source in sources_to_crawl:
            logger.info(f"Crawling {source} for: {query}")
            try:
                papers = await self.crawl_source(
                    source=source,
                    query=query,
                    limit=limit_per_source,
                    year_from=year_from,
                    year_to=year_to,
                    store=store
                )
                results[source] = {
                    "success": True,
                    "count": len(papers),
                    "papers": papers if not store else None
                }
            except Exception as e:
                logger.error(f"Error crawling {source}: {e}")
                results[source] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def crawl_academic_sources(
        self,
        query: str,
        limit_per_source: int = 50,
        store: bool = True
    ) -> dict:
        """
        Crawl only academic sources (excluding government/statistical).
        
        Args:
            query: Search query
            limit_per_source: Max papers per source
            store: Whether to store in database
            
        Returns:
            Dictionary with results per source
        """
        academic_sources = [
            "elibrary",
            "cyberleninka", 
            "arxiv",
            "rsl_dissertations",
            "rusneb",
            "inion",
            "hse_scientometrics",
            "presidential_library",
        ]
        return await self.crawl_all_sources(
            query=query,
            limit_per_source=limit_per_source,
            store=store,
            sources=academic_sources
        )
    
    async def crawl_government_sources(
        self,
        query: str,
        limit_per_source: int = 30,
        store: bool = True
    ) -> dict:
        """
        Crawl government and statistical sources.
        
        Args:
            query: Search query
            limit_per_source: Max papers per source
            store: Whether to store in database
            
        Returns:
            Dictionary with results per source
        """
        gov_sources = ["rosstat"]
        return await self.crawl_all_sources(
            query=query,
            limit_per_source=limit_per_source,
            store=store,
            sources=gov_sources
        )
    
    async def _store_paper(self, paper_data: PaperData) -> Optional[str]:
        """
        Store a paper in the database.
        
        Args:
            paper_data: Paper data to store
            
        Returns:
            Paper ID if stored, None if duplicate/error
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
                    logger.info(f"Duplicate paper found: {existing_id}")
                    return existing_id
                
                # Generate unique ID
                paper_id = await indexing_service.generate_id(
                    source=paper_data.source_type,
                    year=paper_data.publication_year
                )
                
                # Generate embeddings
                title_embedding = await self.embedding_service.get_embedding(
                    paper_data.title or ""
                )
                abstract_embedding = await self.embedding_service.get_embedding(
                    paper_data.abstract or ""
                )
                
                # Create paper
                paper = Paper(
                    id=paper_id,
                    title=paper_data.title,
                    title_ru=paper_data.title_ru,
                    abstract=paper_data.abstract,
                    abstract_ru=paper_data.abstract_ru,
                    doi=paper_data.doi,
                    arxiv_id=paper_data.arxiv_id,
                    source_type=paper_data.source_type,
                    source_url=paper_data.source_url,
                    source_id=paper_data.source_id,
                    journal=paper_data.journal,
                    journal_ru=paper_data.journal_ru,
                    publisher=paper_data.publisher,
                    volume=paper_data.volume,
                    issue=paper_data.issue,
                    pages=paper_data.pages,
                    publication_year=paper_data.publication_year,
                    keywords=paper_data.keywords,
                    keywords_ru=paper_data.keywords_ru,
                    pdf_url=paper_data.pdf_url,
                    language=paper_data.language,
                    title_embedding=title_embedding,
                    abstract_embedding=abstract_embedding,
                    is_processed=1,
                )
                
                # Handle authors
                for author_data in paper_data.authors or []:
                    author = await self._get_or_create_author(db, author_data)
                    paper.authors.append(author)
                
                db.add(paper)
                await db.commit()
                
                logger.info(f"Stored paper: {paper_id}")
                return paper_id
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error storing paper: {e}")
                return None
    
    async def _get_or_create_author(
        self,
        db: AsyncSession,
        author_data: dict
    ) -> Author:
        """Get existing author or create new one."""
        from sqlalchemy import select
        
        full_name = author_data.get("full_name", "")
        
        # Try to find existing author
        result = await db.execute(
            select(Author).where(Author.full_name == full_name)
        )
        author = result.scalar_one_or_none()
        
        if author:
            return author
        
        # Create new author
        from app.services.indexing_service import IndexingService
        
        author_id = await IndexingService(db).generate_id("manual")
        
        author = Author(
            id=author_id,
            full_name=full_name,
            full_name_ru=author_data.get("full_name_ru"),
            affiliations=author_data.get("affiliations"),
            affiliations_ru=author_data.get("affiliations_ru"),
            orcid=author_data.get("orcid"),
        )
        
        db.add(author)
        await db.flush()
        
        return author
    
    async def update_embeddings(self, batch_size: int = 100):
        """
        Update embeddings for papers that don't have them.
        
        Args:
            batch_size: Number of papers to process at once
        """
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Paper).where(
                    Paper.abstract_embedding.is_(None)
                ).limit(batch_size)
            )
            papers = result.scalars().all()
            
            for paper in papers:
                try:
                    paper.title_embedding = await self.embedding_service.get_embedding(
                        paper.title or ""
                    )
                    paper.abstract_embedding = await self.embedding_service.get_embedding(
                        paper.abstract or ""
                    )
                except Exception as e:
                    logger.error(f"Error generating embedding for {paper.id}: {e}")
            
            await db.commit()
            
            return len(papers)


async def main():
    """CLI entry point for testing crawlers."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Crawl academic papers from Russian sources")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--source", default="all", 
                       help="Source to crawl (elibrary, cyberleninka, arxiv, rsl_dissertations, rusneb, inion, hse_scientometrics, presidential_library, rosstat, all)")
    parser.add_argument("--limit", type=int, default=20, help="Max papers to fetch")
    parser.add_argument("--year-from", type=int, help="Filter from year")
    parser.add_argument("--year-to", type=int, help="Filter to year")
    parser.add_argument("--no-store", action="store_true", help="Don't store in database")
    parser.add_argument("--academic-only", action="store_true", help="Only crawl academic sources")
    parser.add_argument("--gov-only", action="store_true", help="Only crawl government sources")
    
    args = parser.parse_args()
    
    orchestrator = CrawlerOrchestrator()
    
    if args.academic_only:
        results = await orchestrator.crawl_academic_sources(
            query=args.query,
            limit_per_source=args.limit,
            store=not args.no_store
        )
        print("\n=== Academic Sources Results ===")
        for source, result in results.items():
            if result["success"]:
                print(f"✓ {source}: {result['count']} papers")
            else:
                print(f"✗ {source}: {result.get('error', 'Unknown error')}")
    
    elif args.gov_only:
        results = await orchestrator.crawl_government_sources(
            query=args.query,
            limit_per_source=args.limit,
            store=not args.no_store
        )
        print("\n=== Government Sources Results ===")
        for source, result in results.items():
            if result["success"]:
                print(f"✓ {source}: {result['count']} papers")
            else:
                print(f"✗ {source}: {result.get('error', 'Unknown error')}")
    
    elif args.source == "all":
        results = await orchestrator.crawl_all_sources(
            query=args.query,
            limit_per_source=args.limit,
            year_from=args.year_from,
            year_to=args.year_to,
            store=not args.no_store
        )
        
        print("\n=== All Sources Results ===")
        for source, result in results.items():
            if result["success"]:
                print(f"✓ {source}: {result['count']} papers")
            else:
                print(f"✗ {source}: {result.get('error', 'Unknown error')}")
    else:
        papers = await orchestrator.crawl_source(
            source=args.source,
            query=args.query,
            limit=args.limit,
            year_from=args.year_from,
            year_to=args.year_to,
            store=not args.no_store
        )
        
        print(f"\nFound {len(papers)} papers from {args.source}")
        for paper in papers[:5]:
            print(f"\n- {paper.title[:80]}...")
            print(f"  Authors: {', '.join(a['full_name'] for a in paper.authors[:3])}")


if __name__ == "__main__":
    asyncio.run(main())
