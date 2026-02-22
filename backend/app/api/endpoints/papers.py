"""API endpoints for papers."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.schemas.paper import PaperResponse, PaperSearchRequest, PaperCreate
from app.services.search_service import SearchService
from app.services.indexing_service import IndexingService

router = APIRouter()


@router.get("/search", response_model=dict)
async def search_papers(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search_type: str = Query("hybrid", enum=["text", "semantic", "hybrid"]),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    journal: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for papers using various criteria.
    
    - **q**: Search query string
    - **limit**: Maximum number of results (1-100)
    - **offset**: Pagination offset
    - **search_type**: Type of search (text, semantic, hybrid)
    - **year_from**: Filter by publication year (from)
    - **year_to**: Filter by publication year (to)
    - **source**: Filter by source (eLibrary, CyberLeninka, etc.)
    - **journal**: Filter by journal name
    """
    search_service = SearchService(db)
    
    filters = {}
    if year_from:
        filters["year_from"] = year_from
    if year_to:
        filters["year_to"] = year_to
    if source:
        filters["source"] = source
    if journal:
        filters["journal"] = journal
    
    papers, total = await search_service.search_papers(
        query=q,
        limit=limit,
        offset=offset,
        filters=filters if filters else None,
        search_type=search_type
    )
    
    return {
        "papers": [p.to_dict() for p in papers],
        "total": total,
        "limit": limit,
        "offset": offset,
        "search_type": search_type
    }


@router.post("/semantic-search", response_model=dict)
async def semantic_search(
    request: PaperSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Perform semantic search using natural language.
    
    This endpoint uses vector embeddings to find papers semantically
    similar to the query, even if they don't contain the exact keywords.
    """
    search_service = SearchService(db)
    
    papers, total = await search_service.search_papers(
        query=request.query,
        limit=request.limit,
        offset=request.offset,
        filters=request.filters,
        search_type="semantic"
    )
    
    return {
        "papers": [p.to_dict() for p in papers],
        "total": total,
        "limit": request.limit,
        "offset": request.offset
    }


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific paper by ID."""
    from sqlalchemy import select
    from app.models import Paper
    
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper with ID {paper_id} not found"
        )
    
    return paper.to_dict()


@router.get("/{paper_id}/similar", response_model=dict)
async def get_similar_papers(
    paper_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get papers similar to the specified paper."""
    search_service = SearchService(db)
    
    # Verify paper exists
    from sqlalchemy import select
    from app.models import Paper
    
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper with ID {paper_id} not found"
        )
    
    similar_papers = await search_service.get_similar_papers(paper_id, limit)
    
    return {
        "papers": [p.to_dict() for p in similar_papers],
        "total": len(similar_papers)
    }


@router.get("/stats/index", response_model=dict)
async def get_index_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get indexing statistics."""
    indexing_service = IndexingService(db)
    return await indexing_service.get_index_stats()


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    paper: PaperCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new paper to the database (manual entry).
    
    This endpoint is for manual paper entry. For bulk ingestion,
    use the crawler system.
    """
    indexing_service = IndexingService(db)
    
    # Check for duplicates
    is_duplicate, existing_id = await indexing_service.check_duplicate(
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        title=paper.title
    )
    
    if is_duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paper already exists with ID: {existing_id}"
        )
    
    # Generate unique ID
    paper_id = await indexing_service.generate_id(
        source=paper.source_type,
        year=paper.publication_year
    )
    
    # Create paper in database
    from app.models import Paper as PaperModel
    
    db_paper = PaperModel(
        id=paper_id,
        **paper.model_dump()
    )
    
    db.add(db_paper)
    await db.commit()
    await db.refresh(db_paper)
    
    return db_paper.to_dict()
