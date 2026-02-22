"""626 Translation integration for Russian Science Hub."""
from datetime import datetime
from typing import List, Dict, Any
from temporalio import activity

import sys
from pathlib import Path

# Import 626 translator
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "translation_626"))

try:
    from translation_workflow import TranslationWorkflow as Workflow626
    from translation_workflow import translate_chunk_activity
    TRANSLATION_626_AVAILABLE = True
except ImportError:
    TRANSLATION_626_AVAILABLE = False
    print("626 translator not available")

from app.services.translation.service import TranslationService


@activity.defn
async def translate_abstract_activity(
    paper_id: str,
    text: str,
    source_lang: str = "en"
) -> Dict[str, Any]:
    """
    Translate paper abstract using 626 approach.
    
    Args:
        paper_id: Paper ID
        text: Text to translate
        source_lang: Source language
        
    Returns:
        Translation result
    """
    activity.logger.info(f"626-translate: {paper_id}")
    
    service = TranslationService()
    
    try:
        translated = await service.translate_text(
            text=text,
            source_lang=source_lang,
            target_lang="ru",
            context=f"Academic paper abstract"
        )
        
        return {
            "paper_id": paper_id,
            "original": text,
            "translated": translated,
            "source_lang": source_lang,
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "paper_id": paper_id,
            "original": text,
            "translated": None,
            "error": str(e),
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat()
        }


@activity.defn
async def batch_translate_activity(paper_ids: List[str]) -> Dict[str, Any]:
    """Batch translate papers using 626 workflow style."""
    from app.db.base import AsyncSessionLocal
    from app.models.paper import Paper
    from sqlalchemy import select
    
    activity.logger.info(f"626-batch-translate: {len(paper_ids)} papers")
    
    service = TranslationService()
    results = {"success": 0, "failed": 0, "translations": []}
    
    async with AsyncSessionLocal() as db:
        for pid in paper_ids:
            try:
                result = await db.execute(select(Paper).where(Paper.id == pid))
                paper = result.scalar_one_or_none()
                
                if not paper or not paper.abstract:
                    continue
                
                # Translate
                translated = await service.translate_text(
                    text=paper.abstract,
                    source_lang="en",
                    target_lang="ru",
                    context=f"Title: {paper.title[:100]}"
                )
                
                # Save
                paper.abstract_ru = translated
                await db.commit()
                
                results["success"] += 1
                results["translations"].append({
                    "paper_id": pid,
                    "translated_chars": len(translated)
                })
                
            except Exception as e:
                results["failed"] += 1
                activity.logger.error(f"Failed {pid}: {e}")
    
    return results
