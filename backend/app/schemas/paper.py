"""Pydantic schemas for paper models."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AuthorBase(BaseModel):
    """Base author schema."""
    full_name: str
    full_name_ru: Optional[str] = None
    affiliations: Optional[List[str]] = None
    affiliations_ru: Optional[List[str]] = None
    orcid: Optional[str] = None


class AuthorCreate(AuthorBase):
    """Schema for creating an author."""
    pass


class AuthorResponse(AuthorBase):
    """Schema for author response."""
    id: str
    
    class Config:
        from_attributes = True


class PaperBase(BaseModel):
    """Base paper schema."""
    title: str
    title_ru: Optional[str] = None
    abstract: Optional[str] = None
    abstract_ru: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    journal: Optional[str] = None
    journal_ru: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publication_date: Optional[datetime] = None
    publication_year: Optional[int] = None
    keywords: Optional[List[str]] = None
    keywords_ru: Optional[List[str]] = None
    language: str = "ru"


class PaperCreate(PaperBase):
    """Schema for creating a paper."""
    source_type: str = Field(..., description="Source system (eLibrary, CyberLeninka, etc.)")
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    authors: List[AuthorCreate] = Field(default_factory=list)
    pdf_url: Optional[str] = None


class PaperResponse(PaperBase):
    """Schema for paper response."""
    id: str
    source_type: str
    source_url: Optional[str] = None
    citation_count: int = 0
    citation_count_rsci: int = 0
    authors: List[AuthorResponse] = Field(default_factory=list)
    crawled_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaperSearchRequest(BaseModel):
    """Schema for paper search request."""
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    filters: Optional[dict] = None


class SimilarPaperResponse(BaseModel):
    """Schema for similar paper response."""
    papers: List[PaperResponse]
    total: int


class IndexStats(BaseModel):
    """Schema for index statistics."""
    total_papers: int
    by_source: dict
    by_year: dict
    with_full_text: int
    processing_coverage: float
