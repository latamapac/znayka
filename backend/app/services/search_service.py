"""Search service with full-text and semantic search."""
import logging
import os
from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Paper, Author
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Check if using SQLite
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

if not USE_SQLITE:
    try:
        from pgvector.sqlalchemy import cosine_distance
        PGVECTOR_AVAILABLE = True
    except ImportError:
        PGVECTOR_AVAILABLE = False
else:
    PGVECTOR_AVAILABLE = False


class SearchService:
    """Service for searching papers with various strategies."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.use_sqlite = USE_SQLITE
    
    async def search_papers(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[dict] = None,
        search_type: str = "hybrid"  # "text", "semantic", "hybrid"
    ) -> Tuple[List[Paper], int]:
        """
        Search papers using specified search type.
        
        Args:
            query: Search query
            limit: Maximum results to return
            offset: Pagination offset
            filters: Optional filters (year, source, journal, etc.)
            search_type: Type of search to perform
            
        Returns:
            Tuple of (list of papers, total count)
        """
        # For SQLite, only text search works fully
        if self.use_sqlite and search_type in ["semantic", "hybrid"]:
            logger.info("SQLite mode: falling back to text search")
            search_type = "text"
        
        if search_type == "text":
            return await self._full_text_search(query, limit, offset, filters)
        elif search_type == "semantic" and PGVECTOR_AVAILABLE:
            return await self._semantic_search(query, limit, offset, filters)
        else:
            # Hybrid requires pgvector
            if PGVECTOR_AVAILABLE:
                return await self._hybrid_search(query, limit, offset, filters)
            else:
                return await self._full_text_search(query, limit, offset, filters)
    
    async def _full_text_search(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: Optional[dict]
    ) -> Tuple[List[Paper], int]:
        """Full-text search using PostgreSQL tsvector or SQLite LIKE."""
        
        # Build base query
        base_query = select(Paper).where(
            or_(
                Paper.title.ilike(f"%{query}%"),
                Paper.title_ru.ilike(f"%{query}%"),
                Paper.abstract.ilike(f"%{query}%"),
                Paper.abstract_ru.ilike(f"%{query}%"),
            )
        )
        
        # Apply filters
        base_query = self._apply_filters(base_query, filters)
        
        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        results_query = base_query.offset(offset).limit(limit)
        
        result = await self.db.execute(results_query)
        papers = result.scalars().all()
        
        return list(papers), total
    
    async def _semantic_search(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: Optional[dict]
    ) -> Tuple[List[Paper], int]:
        """Semantic search using vector embeddings (PostgreSQL+pgvector only)."""
        
        if not PGVECTOR_AVAILABLE:
            logger.warning("Semantic search requires pgvector, falling back to text search")
            return await self._full_text_search(query, limit, offset, filters)
        
        # Get query embedding
        query_embedding = await self.embedding_service.get_embedding(query)
        
        # Build query with vector similarity
        base_query = select(Paper).order_by(
            Paper.abstract_embedding.cosine_distance(query_embedding)
        )
        
        # Apply filters
        base_query = self._apply_filters(base_query, filters)
        
        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get results
        results_query = base_query.offset(offset).limit(limit)
        result = await self.db.execute(results_query)
        papers = result.scalars().all()
        
        return list(papers), total
    
    async def _hybrid_search(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: Optional[dict]
    ) -> Tuple[List[Paper], int]:
        """
        Hybrid search combining full-text and semantic search.
        Uses Reciprocal Rank Fusion (RRF) to combine results.
        """
        if not PGVECTOR_AVAILABLE:
            return await self._full_text_search(query, limit, offset, filters)
        
        # Get results from both methods
        text_papers, _ = await self._full_text_search(query, limit * 2, 0, filters)
        semantic_papers, _ = await self._semantic_search(query, limit * 2, 0, filters)
        
        # Reciprocal Rank Fusion
        k = 60  # RRF constant
        scores = {}
        
        # Score text search results
        for rank, paper in enumerate(text_papers):
            scores[paper.id] = scores.get(paper.id, 0) + 1 / (k + rank)
        
        # Score semantic search results
        for rank, paper in enumerate(semantic_papers):
            scores[paper.id] = scores.get(paper.id, 0) + 1 / (k + rank)
        
        # Get all unique paper IDs sorted by score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # Fetch full papers for top results
        if sorted_ids:
            papers_query = select(Paper).where(Paper.id.in_(sorted_ids[:limit]))
            result = await self.db.execute(papers_query)
            papers_map = {p.id: p for p in result.scalars().all()}
            
            # Maintain order
            papers = [papers_map[pid] for pid in sorted_ids[:limit] if pid in papers_map]
        else:
            papers = []
        
        return papers, len(sorted_ids)
    
    def _apply_filters(self, query, filters: Optional[dict]):
        """Apply filters to query."""
        if not filters:
            return query
        
        conditions = []
        
        if "year_from" in filters:
            conditions.append(Paper.publication_year >= filters["year_from"])
        if "year_to" in filters:
            conditions.append(Paper.publication_year <= filters["year_to"])
        if "source" in filters:
            conditions.append(Paper.source_type == filters["source"])
        if "journal" in filters:
            conditions.append(Paper.journal.ilike(f"%{filters['journal']}%"))
        if "has_full_text" in filters:
            conditions.append(Paper.has_full_text == 1)
        if "language" in filters:
            conditions.append(Paper.language == filters["language"])
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    async def get_similar_papers(
        self,
        paper_id: str,
        limit: int = 10
    ) -> List[Paper]:
        """Find papers similar to given paper."""
        
        if not PGVECTOR_AVAILABLE:
            logger.warning("Similar papers search requires pgvector")
            return []
        
        # Get the paper's embedding
        result = await self.db.execute(
            select(Paper).where(Paper.id == paper_id)
        )
        paper = result.scalar_one_or_none()
        
        if not paper or not paper.abstract_embedding:
            return []
        
        # Find papers with similar embeddings
        similar_query = select(Paper).where(
            Paper.id != paper_id
        ).order_by(
            Paper.abstract_embedding.cosine_distance(paper.abstract_embedding)
        ).limit(limit)
        
        result = await self.db.execute(similar_query)
        return list(result.scalars().all())
    
    async def search_by_author(
        self,
        author_name: str,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Paper], int]:
        """Search papers by author name."""
        
        # Find author
        author_result = await self.db.execute(
            select(Author).where(
                or_(
                    Author.full_name.ilike(f"%{author_name}%"),
                    Author.full_name_ru.ilike(f"%{author_name}%")
                )
            )
        )
        author = author_result.scalar_one_or_none()
        
        if not author:
            return [], 0
        
        # Get papers by author - SQLite compatible approach
        from sqlalchemy import select
        from app.models import paper_author
        
        # Query papers through association table
        result = await self.db.execute(
            select(Paper).join(
                paper_author,
                Paper.id == paper_author.c.paper_id
            ).where(
                paper_author.c.author_id == author.id
            )
        )
        papers = result.scalars().all()
        total = len(papers)
        
        return papers[offset:offset+limit], total
