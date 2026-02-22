"""API endpoints for 626 translation integration."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.temporal.worker import (
    submit_translation_workflow,
    submit_auto_translate_workflow
)

try:
    from app.services.translation.service import TranslationService
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False

router = APIRouter()


class TranslateRequest(BaseModel):
    paper_ids: List[str]
    source_lang: str = "en"
    target_lang: str = "ru"


class TranslateResponse(BaseModel):
    workflow_id: str
    message: str
    papers_count: int


class TranslateTextRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "ru"
    context: Optional[str] = None


class TranslateTextResponse(BaseModel):
    original: str
    translated: str
    source_lang: str
    target_lang: str


@router.post("/papers", response_model=TranslateResponse)
async def translate_papers(request: TranslateRequest):
    """
    Translate papers using 626 workflow.
    
    Translates title and abstract from source_lang to target_lang.
    """
    if not TRANSLATION_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Translation service not available"
        )
    
    try:
        workflow_id = await submit_translation_workflow(
            paper_ids=request.paper_ids,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
        return TranslateResponse(
            workflow_id=workflow_id,
            message=f"Translation workflow started for {len(request.paper_ids)} papers",
            papers_count=len(request.paper_ids)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto")
async def auto_translate(limit: int = 100):
    """
    Auto-translate papers that need translation.
    
    Finds papers without Russian translation and translates them.
    """
    if not TRANSLATION_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Translation service not available"
        )
    
    try:
        workflow_id = await submit_auto_translate_workflow(limit=limit)
        
        return {
            "workflow_id": workflow_id,
            "message": f"Auto-translation workflow started (limit: {limit})"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text", response_model=TranslateTextResponse)
async def translate_text(request: TranslateTextRequest):
    """
    Translate text directly (synchronous).
    
    Uses 626 translation service.
    """
    if not TRANSLATION_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Translation service not available"
        )
    
    try:
        service = TranslationService()
        translated = await service.translate_text(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            context=request.context or "Academic text"
        )
        
        return TranslateTextResponse(
            original=request.text,
            translated=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def translation_status():
    """Get translation service status."""
    return {
        "available": TRANSLATION_AVAILABLE,
        "service": "626-translator",
        "supported_languages": ["en", "ko", "zh", "de", "fr"],
        "target_languages": ["ru", "en"]
    }
