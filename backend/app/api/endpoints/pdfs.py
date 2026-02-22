"""API endpoints for PDF processing and full-text search."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from app.services.storage import get_storage_service
from app.services.pdf import get_pdf_processor
from app.services.text import get_text_indexer
from app.db.base import AsyncSessionLocal

router = APIRouter()


class PDFDownloadRequest(BaseModel):
    paper_id: str
    pdf_url: str
    filename: Optional[str] = "paper.pdf"


class PDFProcessRequest(BaseModel):
    paper_id: str
    extract_chunks: bool = True
    chunk_size: int = 1000


class FullTextSearchRequest(BaseModel):
    query: str
    limit: int = 20
    offset: int = 0
    hybrid: bool = True


class SearchResultItem(BaseModel):
    paper_id: str
    title: str
    snippet: str
    score: float
    page: Optional[int] = None


@router.post("/download")
async def download_pdf(request: PDFDownloadRequest, background_tasks: BackgroundTasks):
    """
    Download PDF from URL and store it.
    """
    storage = get_storage_service()
    
    try:
        # Download PDF
        pdf_data = await storage.download_from_url(request.pdf_url)
        if not pdf_data:
            raise HTTPException(status_code=404, detail="Could not download PDF")
        
        # Store it
        storage_url = await storage.store_pdf(
            request.paper_id, 
            pdf_data, 
            request.filename
        )
        
        # Update database
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            await db.execute(
                text("""
                    INSERT INTO pdf_storage (paper_id, storage_type, storage_key, storage_url, filename, size_bytes, is_downloaded)
                    VALUES (:paper_id, :storage_type, :key, :url, :filename, :size, 1)
                    ON CONFLICT (paper_id) DO UPDATE SET
                        storage_url = EXCLUDED.storage_url,
                        size_bytes = EXCLUDED.size_bytes,
                        is_downloaded = 1,
                        updated_at = NOW()
                """),
                {
                    "paper_id": request.paper_id,
                    "storage_type": "local" if "file://" in storage_url else "r2",
                    "key": request.paper_id + ".pdf",
                    "url": storage_url,
                    "filename": request.filename,
                    "size": len(pdf_data)
                }
            )
            await db.commit()
        
        return {
            "paper_id": request.paper_id,
            "storage_url": storage_url,
            "size_bytes": len(pdf_data),
            "status": "downloaded"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def process_pdf(request: PDFProcessRequest):
    """
    Process PDF - extract text, create Markdown, index chunks.
    """
    storage = get_storage_service()
    processor = get_pdf_processor()
    indexer = get_text_indexer()
    
    try:
        # Get PDF from storage
        pdf_data = await storage.get_pdf(request.paper_id)
        if not pdf_data:
            raise HTTPException(status_code=404, detail="PDF not found in storage")
        
        # Get paper metadata
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            result = await db.execute(
                text("SELECT title, abstract, authors, keywords, publication_year FROM papers WHERE id = :id"),
                {"id": request.paper_id}
            )
            paper = result.fetchone()
            
            if not paper:
                raise HTTPException(status_code=404, detail="Paper not found")
            
            metadata = {
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors or [],
                "keywords": paper.keywords or [],
                "publication_year": paper.publication_year
            }
        
        # Extract text
        extraction = await processor.extract_text(pdf_data)
        full_text = extraction["full_text"]
        
        # Convert to Markdown
        markdown = await processor.to_markdown(pdf_data, metadata)
        
        # Index full text
        await indexer.index_paper_fulltext(request.paper_id, full_text)
        
        # Extract and index chunks
        chunk_count = 0
        if request.extract_chunks:
            chunks = await processor.extract_chunks(
                pdf_data, 
                chunk_size=request.chunk_size
            )
            
            async with AsyncSessionLocal() as db:
                for chunk in chunks:
                    await db.execute(
                        text("""
                            INSERT INTO paper_chunks (paper_id, text, page_number, chunk_index, char_count)
                            VALUES (:paper_id, :text, :page, :index, :char_count)
                        """),
                        {
                            "paper_id": request.paper_id,
                            "text": chunk["text"],
                            "page": chunk["page"],
                            "index": chunk["chunk_index"],
                            "char_count": chunk["char_count"]
                        }
                    )
                    chunk_count += 1
                
                await db.commit()
        
        # Update paper status
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    UPDATE papers 
                    SET has_full_text = 1, is_processed = 1
                    WHERE id = :id
                """),
                {"id": request.paper_id}
            )
            await db.commit()
        
        return {
            "paper_id": request.paper_id,
            "text_length": len(full_text),
            "pages_extracted": len(extraction["pages"]),
            "chunks_created": chunk_count,
            "method_used": extraction["method_used"],
            "status": "processed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=List[SearchResultItem])
async def search_fulltext(request: FullTextSearchRequest):
    """
    Full-text search across all indexed papers.
    """
    indexer = get_text_indexer()
    
    try:
        if request.hybrid:
            results = await indexer.hybrid_search(request.query, limit=request.limit)
        else:
            results = await indexer.fulltext_search(
                request.query, 
                limit=request.limit,
                offset=request.offset
            )
        
        return [
            SearchResultItem(
                paper_id=r.paper_id,
                title=r.title,
                snippet=r.snippet,
                score=r.score,
                page=r.page
            )
            for r in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{paper_id}")
async def get_pdf_status(paper_id: str):
    """
    Get PDF processing status for a paper.
    """
    async with AsyncSessionLocal() as db:
        from sqlalchemy import text
        
        # Check paper status
        result = await db.execute(
            text("SELECT has_full_text, is_processed FROM papers WHERE id = :id"),
            {"id": paper_id}
        )
        paper = result.fetchone()
        
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Check PDF storage
        result = await db.execute(
            text("SELECT storage_type, is_downloaded, is_processed, size_bytes FROM pdf_storage WHERE paper_id = :id"),
            {"id": paper_id}
        )
        storage = result.fetchone()
        
        # Count chunks
        result = await db.execute(
            text("SELECT COUNT(*) FROM paper_chunks WHERE paper_id = :id"),
            {"id": paper_id}
        )
        chunk_count = result.scalar()
        
        return {
            "paper_id": paper_id,
            "has_full_text": bool(paper.has_full_text),
            "is_processed": bool(paper.is_processed),
            "pdf_downloaded": bool(storage.is_downloaded) if storage else False,
            "pdf_size_bytes": storage.size_bytes if storage else None,
            "storage_type": storage.storage_type if storage else None,
            "chunks_indexed": chunk_count
        }
