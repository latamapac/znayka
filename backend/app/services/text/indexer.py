"""Full-text indexer with hybrid search (BM25 + Vector)."""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result item."""
    paper_id: str
    title: str
    snippet: str
    score: float
    page: Optional[int] = None
    chunk_index: Optional[int] = None


class TextIndexer:
    """
    Full-text indexer supporting:
    - BM25 keyword search on PostgreSQL
    - Vector semantic search (if embeddings available)
    - Hybrid ranking
    """
    
    def __init__(self):
        self.use_bm25 = True
    
    async def setup_fulltext_index(self):
        """Setup PostgreSQL full-text search indexes."""
        async with AsyncSessionLocal() as db:
            try:
                # Add full-text search columns if not exist
                await db.execute(text("""
                    ALTER TABLE papers ADD COLUMN IF NOT EXISTS 
                    search_vector tsvector GENERATED ALWAYS AS (
                        setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(abstract, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(full_text, '')), 'C')
                    ) STORED
                """))
                
                # Create GIN index for fast search
                await db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_papers_search 
                    ON papers USING GIN(search_vector)
                """))
                
                await db.commit()
                logger.info("Full-text search index created")
                
            except Exception as e:
                logger.error(f"Failed to setup fulltext index: {e}")
                await db.rollback()
    
    async def fulltext_search(
        self, 
        query: str, 
        limit: int = 20,
        offset: int = 0
    ) -> List[SearchResult]:
        """
        BM25-style full-text search using PostgreSQL.
        
        Args:
            query: Search query
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of search results
        """
        async with AsyncSessionLocal() as db:
            try:
                # Convert query to tsquery
                ts_query = " & ".join(query.split())
                
                sql = text("""
                    SELECT 
                        id,
                        title,
                        abstract,
                        ts_rank_cd(search_vector, plainto_tsquery('english', :query), 32) as rank
                    FROM papers
                    WHERE search_vector @@ plainto_tsquery('english', :query)
                    ORDER BY rank DESC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = await db.execute(
                    sql, 
                    {"query": query, "limit": limit, "offset": offset}
                )
                
                results = []
                for row in result:
                    snippet = row.abstract or ""
                    if len(snippet) > 300:
                        snippet = snippet[:300] + "..."
                    
                    results.append(SearchResult(
                        paper_id=row.id,
                        title=row.title,
                        snippet=snippet,
                        score=float(row.rank),
                    ))
                
                return results
                
            except Exception as e:
                logger.error(f"Full-text search failed: {e}")
                return []
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        vector_weight: float = 0.3,
        keyword_weight: float = 0.7
    ) -> List[SearchResult]:
        """
        Hybrid search combining BM25 keyword + vector semantic search.
        
        Args:
            query: Search query
            limit: Max results
            vector_weight: Weight for semantic search (0-1)
            keyword_weight: Weight for keyword search (0-1)
        """
        # Get keyword results
        keyword_results = await self.fulltext_search(query, limit=limit * 2)
        
        # Get vector results (if available)
        vector_results = await self._vector_search(query, limit=limit * 2)
        
        # Merge and re-rank
        merged = self._merge_results(
            keyword_results, 
            vector_results,
            keyword_weight,
            vector_weight
        )
        
        return merged[:limit]
    
    async def _vector_search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Vector semantic search using pgvector."""
        try:
            from app.services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            query_embedding = await embedding_service.get_embedding(query)
            
            if not query_embedding:
                return []
            
            async with AsyncSessionLocal() as db:
                # pgvector cosine similarity search
                sql = text("""
                    SELECT 
                        id,
                        title,
                        abstract,
                        1 - (title_embedding <=> :embedding) as similarity
                    FROM papers
                    WHERE title_embedding IS NOT NULL
                    ORDER BY title_embedding <=> :embedding
                    LIMIT :limit
                """)
                
                result = await db.execute(
                    sql,
                    {"embedding": str(query_embedding), "limit": limit}
                )
                
                results = []
                for row in result:
                    snippet = row.abstract or ""
                    if len(snippet) > 300:
                        snippet = snippet[:300] + "..."
                    
                    results.append(SearchResult(
                        paper_id=row.id,
                        title=row.title,
                        snippet=snippet,
                        score=float(row.similarity),
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _merge_results(
        self,
        keyword_results: List[SearchResult],
        vector_results: List[SearchResult],
        kw_weight: float,
        vec_weight: float
    ) -> List[SearchResult]:
        """Merge and re-rank keyword + vector results."""
        # Normalize scores to 0-1
        all_results = {}
        
        # Keyword scores
        if keyword_results:
            max_kw = max(r.score for r in keyword_results)
            for r in keyword_results:
                normalized = r.score / max_kw if max_kw > 0 else 0
                all_results[r.paper_id] = {
                    "result": r,
                    "kw_score": normalized,
                    "vec_score": 0
                }
        
        # Vector scores
        if vector_results:
            max_vec = max(r.score for r in vector_results)
            for r in vector_results:
                normalized = r.score / max_vec if max_vec > 0 else 0
                if r.paper_id in all_results:
                    all_results[r.paper_id]["vec_score"] = normalized
                else:
                    all_results[r.paper_id] = {
                        "result": r,
                        "kw_score": 0,
                        "vec_score": normalized
                    }
        
        # Calculate combined scores
        combined = []
        for paper_id, data in all_results.items():
            combined_score = (
                kw_weight * data["kw_score"] +
                vec_weight * data["vec_score"]
            )
            result = data["result"]
            result.score = combined_score
            combined.append(result)
        
        # Sort by combined score
        combined.sort(key=lambda x: x.score, reverse=True)
        return combined
    
    async def index_paper_fulltext(
        self,
        paper_id: str,
        full_text: str,
        db: Optional[AsyncSession] = None
    ):
        """Index paper's full text for search."""
        should_close = False
        if db is None:
            db = AsyncSessionLocal()
            should_close = True
        
        try:
            await db.execute(
                text("UPDATE papers SET full_text = :text WHERE id = :id"),
                {"text": full_text, "id": paper_id}
            )
            await db.commit()
            logger.info(f"Indexed full text for {paper_id}")
            
        except Exception as e:
            logger.error(f"Failed to index full text: {e}")
            await db.rollback()
        finally:
            if should_close:
                await db.close()


# Singleton instance
_text_indexer: Optional[TextIndexer] = None


def get_text_indexer() -> TextIndexer:
    """Get or create text indexer."""
    global _text_indexer
    if _text_indexer is None:
        _text_indexer = TextIndexer()
    return _text_indexer
