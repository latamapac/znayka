"""Service for managing paper indexing and unique identifiers."""
import hashlib
import logging
import re
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Paper

logger = logging.getLogger(__name__)


class IndexingService:
    """
    Service for generating unique identifiers and managing paper indexing.
    
    ID Format: RSH-{SOURCE}-{YEAR}-{SEQUENCE}
    Example: RSH-ELIB-2024-00012345
    """
    
    # Source code mapping
    SOURCE_CODES = {
        "elibrary": "ELIB",
        "cyberleninka": "CYBL",
        "rsci": "RSCI",
        "arxiv": "ARXV",
        "google_scholar": "GSCH",
        "semantic_scholar": "SEMS",
        "scopus": "SCOP",
        "wos": "WOS",
        "msu": "MSU",
        "spbu": "SPBU",
        "hse": "HSE",
        "mipt": "MIPT",
        "misis": "MISI",
        "manual": "MANL",
        "upload": "UPLD",
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_id(
        self,
        source: str,
        year: Optional[int] = None
    ) -> str:
        """
        Generate a unique paper ID.
        
        Args:
            source: Source system name
            year: Publication year (defaults to current year)
            
        Returns:
            Unique paper ID
        """
        source_code = self.SOURCE_CODES.get(source.lower(), "UNKN")
        year_str = str(year if year else datetime.now().year)
        
        # Get next sequence number
        sequence = await self._get_next_sequence(source_code, year_str)
        
        return f"RSH-{source_code}-{year_str}-{sequence:08d}"
    
    async def _get_next_sequence(
        self,
        source_code: str,
        year: str
    ) -> int:
        """Get the next sequence number for source/year combination."""
        
        pattern = f"RSH-{source_code}-{year}-%"
        
        # Count existing papers with this prefix
        result = await self.db.execute(
            select(func.count()).where(Paper.id.like(pattern))
        )
        count = result.scalar() or 0
        
        return count + 1
    
    async def check_duplicate(
        self,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        title: Optional[str] = None,
        authors: Optional[list] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if paper already exists in database.
        
        Args:
            doi: DOI if available
            arxiv_id: arXiv ID if available
            title: Paper title
            authors: List of author names
            
        Returns:
            Tuple of (is_duplicate, existing_paper_id)
        """
        # Check by DOI (most reliable)
        if doi:
            result = await self.db.execute(
                select(Paper).where(Paper.doi == doi)
            )
            paper = result.scalar_one_or_none()
            if paper:
                return True, paper.id
        
        # Check by arXiv ID
        if arxiv_id:
            result = await self.db.execute(
                select(Paper).where(Paper.arxiv_id == arxiv_id)
            )
            paper = result.scalar_one_or_none()
            if paper:
                return True, paper.id
        
        # Check by title similarity (if no DOI)
        if title:
            # Normalize title for comparison
            normalized_title = self._normalize_title(title)
            
            result = await self.db.execute(
                select(Paper).where(
                    func.lower(Paper.title) == normalized_title
                )
            )
            paper = result.scalar_one_or_none()
            if paper:
                return True, paper.id
        
        return False, None
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        # Convert to lowercase
        normalized = title.lower()
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        # Remove common punctuation for comparison
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized
    
    def generate_content_hash(
        self,
        title: str,
        abstract: Optional[str] = None,
        authors: Optional[list] = None
    ) -> str:
        """
        Generate a hash of paper content for deduplication.
        
        Args:
            title: Paper title
            abstract: Paper abstract
            authors: List of author names
            
        Returns:
            MD5 hash of content
        """
        content = title
        if abstract:
            content += abstract[:500]  # First 500 chars
        if authors:
            content += ''.join(sorted(authors))
        
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def update_citation_count(
        self,
        paper_id: str,
        new_count: int,
        source: str = "general"
    ):
        """
        Update citation count for a paper.
        
        Args:
            paper_id: Paper ID
            new_count: New citation count
            source: Source of citation data
        """
        result = await self.db.execute(
            select(Paper).where(Paper.id == paper_id)
        )
        paper = result.scalar_one_or_none()
        
        if paper:
            if source == "rsci":
                paper.citation_count_rsci = new_count
            else:
                paper.citation_count = new_count
            
            await self.db.commit()
    
    async def get_index_stats(self) -> dict:
        """Get indexing statistics."""
        
        # Total papers
        total_result = await self.db.execute(select(func.count()).select_from(Paper))
        total = total_result.scalar()
        
        # Papers by source
        source_result = await self.db.execute(
            select(Paper.source_type, func.count())
            .group_by(Paper.source_type)
        )
        by_source = dict(source_result.all())
        
        # Papers by year
        year_result = await self.db.execute(
            select(Paper.publication_year, func.count())
            .where(Paper.publication_year.isnot(None))
            .group_by(Paper.publication_year)
            .order_by(Paper.publication_year.desc())
        )
        by_year = dict(year_result.all())
        
        # Papers with full text
        fulltext_result = await self.db.execute(
            select(func.count()).where(Paper.has_full_text == 1)
        )
        with_fulltext = fulltext_result.scalar()
        
        return {
            "total_papers": total,
            "by_source": by_source,
            "by_year": by_year,
            "with_full_text": with_fulltext,
            "processing_coverage": round(with_fulltext / total * 100, 2) if total else 0
        }
