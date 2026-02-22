"""Paper model for SQLite (without pgvector dependency)."""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, 
    Float, ForeignKey, Table, ARRAY, Index, JSON
)
from sqlalchemy.orm import relationship

from app.db.base import Base

# Association table for paper-author many-to-many relationship
paper_author = Table(
    "paper_author",
    Base.metadata,
    Column("paper_id", String(32), ForeignKey("papers.id", ondelete="CASCADE")),
    Column("author_id", String(32), ForeignKey("authors.id", ondelete="CASCADE")),
)


class Paper(Base):
    """Academic paper model (SQLite version without vector embeddings)."""
    
    __tablename__ = "papers"
    
    # Unique identifier: RSH-{SOURCE}-{YEAR}-{SEQUENCE}
    id = Column(String(32), primary_key=True, index=True)
    
    # Basic metadata
    title = Column(Text, nullable=False, index=True)
    title_ru = Column(Text, nullable=True)
    abstract = Column(Text, nullable=True)
    abstract_ru = Column(Text, nullable=True)
    
    # Publication info
    doi = Column(String(256), unique=True, nullable=True, index=True)
    arxiv_id = Column(String(50), unique=True, nullable=True, index=True)
    
    # Source information
    source_type = Column(String(50), nullable=False, index=True)
    source_url = Column(Text, nullable=True)
    source_id = Column(String(100), nullable=True)
    
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
    full_text = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # Store as JSON for SQLite
    keywords_ru = Column(JSON, nullable=True)
    
    # File storage
    pdf_path = Column(String(500), nullable=True)
    pdf_url = Column(Text, nullable=True)
    pdf_size_mb = Column(Float, nullable=True)
    
    # Citation metrics
    citation_count = Column(Integer, default=0)
    citation_count_rsci = Column(Integer, default=0)
    
    # Quality/Processing flags
    is_processed = Column(Integer, default=0)
    has_full_text = Column(Integer, default=0)
    language = Column(String(10), default="ru")
    
    # Embeddings stored as JSON (for SQLite compatibility)
    # In production with PostgreSQL+pgvector, use Vector type
    title_embedding = Column(JSON, nullable=True)
    abstract_embedding = Column(JSON, nullable=True)
    full_text_embedding = Column(JSON, nullable=True)
    
    # Relationships
    authors = relationship("Author", secondary=paper_author, back_populates="papers")
    
    __table_args__ = (
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
            "authors": [a.to_dict() for a in self.authors] if self.authors else [],
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
    rsci_id = Column(String(50), unique=True, nullable=True)
    elib_id = Column(String(50), unique=True, nullable=True)
    
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
