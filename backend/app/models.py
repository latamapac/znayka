"""
ZNAYKA Database Models
For permanent crawling platform with deduplication
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, 
    Float, Boolean, ForeignKey, Index, UniqueConstraint,
    JSON, ARRAY
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Paper(Base):
    """Main paper model - stores everything from all sources"""
    __tablename__ = "papers"
    
    id = Column(String(32), primary_key=True)  # RSH-{SOURCE}-{YEAR}-{SEQ}
    
    # Core metadata
    title = Column(Text, nullable=False)
    title_ru = Column(Text)
    abstract = Column(Text)
    abstract_ru = Column(Text)
    
    # Source tracking
    source_type = Column(String(50), nullable=False, index=True)  # arxiv, cyberleninka, etc.
    source_id = Column(String(255), index=True)  # Original ID from source
    source_url = Column(Text)
    
    # Publication info
    journal = Column(String(500))
    journal_ru = Column(String(500))
    publisher = Column(String(255))
    volume = Column(String(50))
    issue = Column(String(50))
    pages = Column(String(50))
    publication_year = Column(Integer, index=True)
    publication_date = Column(DateTime)
    
    # Identifiers
    doi = Column(String(255), index=True)
    arxiv_id = Column(String(50), index=True)
    pmid = Column(String(20))  # PubMed ID
    
    # Content
    keywords = Column(ARRAY(String))
    keywords_ru = Column(ARRAY(String))
    language = Column(String(10), default="en")
    
    # Citations
    citation_count = Column(Integer, default=0)
    citation_count_rsci = Column(Integer, default=0)  # Russian citation index
    
    # Full text
    has_full_text = Column(Boolean, default=False)
    pdf_url = Column(Text)
    pdf_storage_path = Column(String(500))  # Path in R2/S3 storage
    full_text = Column(Text)  # Extracted text
    markdown_text = Column(Text)  # Converted to markdown
    
    # Search vectors (for PostgreSQL full-text search)
    search_vector = Column(Text)
    
    # Timestamps
    crawled_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_crawled = Column(DateTime)  # For tracking re-crawls
    
    # Crawl tracking
    crawl_job_id = Column(String(100))
    crawl_query = Column(String(500))  # What query found this paper
    
    # Status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, error
    processing_error = Column(Text)
    
    # Relationships
    authors = relationship("Author", secondary="paper_authors", back_populates="papers")
    
    __table_args__ = (
        # Prevent duplicates: same source + same source_id
        UniqueConstraint('source_type', 'source_id', name='uix_paper_source'),
        # Indexes for common queries
        Index('ix_papers_source_year', 'source_type', 'publication_year'),
        Index('ix_papers_status', 'processing_status'),
        Index('ix_papers_crawled', 'crawled_at'),
    )


class Author(Base):
    """Authors - deduplicated across papers"""
    __tablename__ = "authors"
    
    id = Column(String(32), primary_key=True)
    full_name = Column(String(255), nullable=False)
    full_name_ru = Column(String(255))
    
    # Affiliations (can change over time, store history)
    affiliations = Column(ARRAY(String))
    current_affiliation = Column(String(500))
    
    # Identifiers
    orcid = Column(String(50), unique=True, index=True)
    researcher_id = Column(String(50))
    scopus_id = Column(String(50))
    
    # Russian identifiers
    elibrary_author_id = Column(String(50))
    spin_code = Column(String(20))  # Russian citation index
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    papers = relationship("Paper", secondary="paper_authors", back_populates="authors")


class PaperAuthor(Base):
    """Many-to-many relationship between papers and authors"""
    __tablename__ = "paper_authors"
    
    paper_id = Column(String(32), ForeignKey("papers.id"), primary_key=True)
    author_id = Column(String(32), ForeignKey("authors.id"), primary_key=True)
    author_order = Column(Integer)  # Position in author list
    is_corresponding = Column(Boolean, default=False)


class CrawlJob(Base):
    """Track all crawl jobs for permanent crawling"""
    __tablename__ = "crawl_jobs"
    
    id = Column(String(100), primary_key=True)
    
    # What was crawled
    source = Column(String(50), nullable=False, index=True)
    query = Column(String(500))
    query_type = Column(String(50))  # keyword, author, category, etc.
    
    # Status
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    
    # Results
    papers_found = Column(Integer, default=0)
    papers_new = Column(Integer, default=0)  # Actually new (not duplicates)
    papers_updated = Column(Integer, default=0)  # Existing papers with new data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Progress tracking
    total_expected = Column(Integer)  # Expected papers from this crawl
    current_offset = Column(Integer, default=0)  # For resuming
    
    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Configuration
    limit = Column(Integer, default=1000)
    year_from = Column(Integer)
    year_to = Column(Integer)
    
    __table_args__ = (
        Index('ix_crawl_jobs_status', 'status'),
        Index('ix_crawl_jobs_source', 'source', 'status'),
    )


class CrawlSchedule(Base):
    """Schedule for continuous crawling"""
    __tablename__ = "crawl_schedules"
    
    id = Column(String(100), primary_key=True)
    
    # What to crawl
    source = Column(String(50), nullable=False)
    query = Column(String(500))
    
    # Schedule (cron-like or interval)
    schedule_type = Column(String(50), default="interval")  # interval, cron, once
    interval_hours = Column(Integer, default=24)  # Run every N hours
    cron_expression = Column(String(100))  # For complex schedules
    
    # Last run tracking
    last_run_at = Column(DateTime)
    last_run_job_id = Column(String(100))
    
    # Statistics
    total_runs = Column(Integer, default=0)
    total_papers_found = Column(Integer, default=0)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=5)  # 1-10, lower = higher priority
    config = Column(JSON)  # Extra configuration
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SourceStats(Base):
    """Statistics per source for monitoring"""
    __tablename__ = "source_stats"
    
    source = Column(String(50), primary_key=True)
    
    total_papers = Column(Integer, default=0)
    papers_with_fulltext = Column(Integer, default=0)
    papers_with_pdf = Column(Integer, default=0)
    
    earliest_paper = Column(Integer)  # Year
    latest_paper = Column(Integer)  # Year
    
    last_crawl_at = Column(DateTime)
    last_crawl_job_id = Column(String(100))
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessingQueue(Base):
    """Queue for PDF processing and text extraction"""
    __tablename__ = "processing_queue"
    
    id = Column(String(32), primary_key=True)
    paper_id = Column(String(32), ForeignKey("papers.id"), nullable=False)
    
    # What needs to be done
    task_type = Column(String(50))  # pdf_download, text_extract, embed, etc.
    priority = Column(Integer, default=5)
    
    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, error
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index('ix_processing_queue_status', 'status'),
        Index('ix_processing_queue_priority', 'status', 'priority'),
    )


# Migration helper
def create_all_tables(engine):
    """Create all tables"""
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """Drop all tables - USE WITH CAUTION"""
    Base.metadata.drop_all(engine)
