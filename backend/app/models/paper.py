"""Paper model for storing academic papers."""
from datetime import datetime
from typing import Optional, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, 
    Float, ForeignKey, Table, ARRAY, Index, JSON
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.config import get_settings

settings = get_settings()

# Association table for paper-author many-to-many relationship
paper_author = Table(
    "paper_author",
    Base.metadata,
    Column("paper_id", String(32), ForeignKey("papers.id", ondelete="CASCADE")),
    Column("author_id", String(32), ForeignKey("authors.id", ondelete="CASCADE")),
)


class Paper(Base):
    """Academic paper model with full-text indexing and vector embeddings."""
    
    __tablename__ = "papers"
    
    # Unique identifier: RSH-{SOURCE}-{YEAR}-{SEQUENCE}
    id = Column(String(32), primary_key=True, index=True)
    
    # Basic metadata
    title = Column(Text, nullable=False, index=True)
    title_ru = Column(Text, nullable=True)  # Russian title if available
    abstract = Column(Text, nullable=True)
    abstract_ru = Column(Text, nullable=True)
    
    # Publication info
    doi = Column(String(256), unique=True, nullable=True, index=True)
    arxiv_id = Column(String(50), unique=True, nullable=True, index=True)
    
    # Source information
    source_type = Column(String(50), nullable=False, index=True)  # eLibrary, CyberLeninka, etc.
    source_url = Column(Text, nullable=True)
    source_id = Column(String(100), nullable=True)  # Original ID from source
    
    # Journal/Publisher info
    journal = Column(String(500), nullable=True, index=True)
    journal_ru = Column(String(500), nullable=True)
    publisher = Column(String(300), nullable=True)
    volume = Column(String(50), nullable=True)
    issue = Column(String(50), nullable=True)
    pages = Column(String(50), nullable=True)
    
    # Dates
    publication_date = Column(DateTime, nullable=True, index=True)
    publication_year = Column(Integer, nullable=True, index=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Content
    full_text = Column(Text, nullable=True)  # Extracted text from PDF
    keywords = Column(JSON, nullable=True)
    keywords_ru = Column(JSON, nullable=True)
    
    # File storage
    pdf_path = Column(String(500), nullable=True)  # Local path to PDF
    pdf_url = Column(Text, nullable=True)  # Original URL
    pdf_size_mb = Column(Float, nullable=True)
    
    # Citation metrics
    citation_count = Column(Integer, default=0)
    citation_count_rsci = Column(Integer, default=0)  # Russian Science Citation Index
    
    # Quality/Processing flags
    is_processed = Column(Integer, default=0)  # 0=raw, 1=processed, 2=verified
    has_full_text = Column(Integer, default=0)
    language = Column(String(10), default="ru")  # ru, en, or both
    
    # Vector embeddings for semantic search
    title_embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    abstract_embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    full_text_embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    
    # Relationships
    authors = relationship("Author", secondary=paper_author, back_populates="papers")
    
    # Indexes for vector similarity search
    __table_args__ = (
        Index('idx_papers_title_embedding', 'title_embedding', postgresql_using='ivfflat'),
        Index('idx_papers_abstract_embedding', 'abstract_embedding', postgresql_using='ivfflat'),
        Index('idx_papers_source_type_year', 'source_type', 'publication_year'),
    )
    
    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, title={self.title[:50]}...)>"
    
    def to_dict(self) -> dict:
        """Convert paper to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "title_ru": self.title_ru,
            "abstract": self.abstract,
            "doi": self.doi,
            "authors": [a.to_dict() for a in self.authors],
            "journal": self.journal,
            "publication_year": self.publication_year,
            "citation_count": self.citation_count,
            "keywords": self.keywords or [],
            "source_type": self.source_type,
            "source_url": self.source_url,
        }


class Author(Base):
    """Author model for paper authors."""
    
    __tablename__ = "authors"
    
    id = Column(String(32), primary_key=True, index=True)
    
    # Name variations
    full_name = Column(String(300), nullable=False, index=True)
    full_name_ru = Column(String(300), nullable=True)
    
    # Affiliations (can be multiple over time)
    affiliations = Column(JSON, nullable=True)
    affiliations_ru = Column(JSON, nullable=True)
    
    # IDs from various systems
    orcid = Column(String(50), unique=True, nullable=True, index=True)
    rsci_id = Column(String(50), unique=True, nullable=True)  # Russian SCI
    elib_id = Column(String(50), unique=True, nullable=True)  # eLibrary
    
    # Metadata
    email = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    papers = relationship("Paper", secondary=paper_author, back_populates="authors")
    
    def __repr__(self) -> str:
        return f"<Author(id={self.id}, name={self.full_name})>"
    
    def to_dict(self) -> dict:
        """Convert author to dictionary."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "full_name_ru": self.full_name_ru,
            "affiliations": self.affiliations or [],
            "orcid": self.orcid,
        }


class Citation(Base):
    """Citation relationships between papers."""
    
    __tablename__ = "citations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    citing_paper_id = Column(String(32), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    cited_paper_id = Column(String(32), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    citing_paper = relationship("Paper", foreign_keys=[citing_paper_id])
    cited_paper = relationship("Paper", foreign_keys=[cited_paper_id])
    
    __table_args__ = (
        Index('idx_citations_unique', 'citing_paper_id', 'cited_paper_id', unique=True),
    )
