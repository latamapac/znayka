"""Temporal workflows for translation - 626 integration."""
from datetime import timedelta
from typing import List, Dict, Any, Optional
import asyncio
from dataclasses import dataclass

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.services.translation.service import TranslationService
    from app.db.base import AsyncSessionLocal
    from app.models.paper import Paper
    from sqlalchemy import select


@dataclass
class TranslationTask:
    """Single translation task."""
    paper_id: str
    title: str
    abstract: str
    keywords: List[str]
    source_lang: str
    target_lang: str


@dataclass
class TranslationResult:
    """Result of translation."""
    paper_id: str
    success: bool
    title_translated: Optional[str]
    abstract_translated: Optional[str]
    keywords_translated: List[str]
    error: Optional[str] = None


@activity.defn
async def translate_paper_activity(task: TranslationTask) -> TranslationResult:
    """
    Activity: Translate a single paper.
    Based on 626 translator workflow.
    """
    activity.logger.info(f"Translating paper {task.paper_id}")
    
    try:
        service = TranslationService()
        result = await service.translate_paper_fields(
            title=task.title,
            abstract=task.abstract,
            keywords=task.keywords,
            source_lang=task.source_lang,
            target_lang=task.target_lang
        )
        
        return TranslationResult(
            paper_id=task.paper_id,
            success=True,
            title_translated=result["title_translated"],
            abstract_translated=result["abstract_translated"],
            keywords_translated=result["keywords_translated"]
        )
        
    except Exception as e:
        activity.logger.error(f"Translation failed for {task.paper_id}: {e}")
        return TranslationResult(
            paper_id=task.paper_id,
            success=False,
            title_translated=None,
            abstract_translated=None,
            keywords_translated=[],
            error=str(e)
        )


@activity.defn
async def translate_batch_activity(paper_ids: List[str]) -> Dict[str, Any]:
    """
    Activity: Translate a batch of papers from DB.
    """
    activity.logger.info(f"Translating batch of {len(paper_ids)} papers")
    
    results = {"success": 0, "failed": 0, "errors": []}
    
    async with AsyncSessionLocal() as db:
        for paper_id in paper_ids:
            try:
                # Get paper from DB
                result = await db.execute(
                    select(Paper).where(Paper.id == paper_id)
                )
                paper = result.scalar_one_or_none()
                
                if not paper:
                    results["failed"] += 1
                    results["errors"].append(f"Paper {paper_id} not found")
                    continue
                
                # Create translation task
                task = TranslationTask(
                    paper_id=paper_id,
                    title=paper.title,
                    abstract=paper.abstract or "",
                    keywords=paper.keywords or [],
                    source_lang="en",
                    target_lang="ru"
                )
                
                # Translate
                translation = await translate_paper_activity(task)
                
                if translation.success:
                    # Save to DB (add translated fields)
                    paper.title_translated = translation.title_translated
                    paper.abstract_translated = translation.abstract_translated
                    await db.commit()
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{paper_id}: {translation.error}")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{paper_id}: {str(e)}")
    
    return results


@activity.defn
async def detect_language_activity(text: str) -> str:
    """
    Activity: Detect language of text.
    Returns language code (en, ru, ko, etc.)
    """
    try:
        import langdetect
        return langdetect.detect(text)
    except:
        # Simple fallback detection
        cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04ff')
        korean = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
        total = len(text.replace(" ", ""))
        
        if korean > 0:
            return "ko"
        elif cyrillic / max(total, 1) > 0.3:
            return "ru"
        else:
            return "en"


@workflow.defn
class TranslationWorkflow:
    """
    Translation workflow for papers.
    Based on 626 translation workflow.
    """
    
    @workflow.run
    async def run(
        self,
        paper_ids: List[str],
        source_lang: str = "en",
        target_lang: str = "ru"
    ) -> Dict[str, Any]:
        """
        Translate multiple papers.
        
        Args:
            paper_ids: List of paper IDs to translate
            source_lang: Source language
            target_lang: Target language
            
        Returns:
            Translation results summary
        """
        workflow.logger.info(f"Starting translation workflow for {len(paper_ids)} papers")
        
        total = len(paper_ids)
        completed = 0
        results = []
        
        # Process in batches of 5 for rate limiting
        batch_size = 5
        for i in range(0, len(paper_ids), batch_size):
            batch = paper_ids[i:i + batch_size]
            
            # Process batch
            batch_result = await workflow.execute_activity(
                translate_batch_activity,
                args=(batch,),
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=5)
                )
            )
            
            completed += len(batch)
            results.append(batch_result)
            
            workflow.logger.info(f"Progress: {completed}/{total}")
        
        # Aggregate results
        total_success = sum(r["success"] for r in results)
        total_failed = sum(r["failed"] for r in results)
        all_errors = [e for r in results for e in r.get("errors", [])]
        
        return {
            "total_papers": total,
            "successful": total_success,
            "failed": total_failed,
            "errors": all_errors[:10],  # First 10 errors
            "status": "completed"
        }


@workflow.defn  
class AutoTranslateWorkflow:
    """
    Auto-translate workflow - detects non-Russian papers and translates them.
    """
    
    @workflow.run
    async def run(self, limit: int = 100) -> Dict[str, Any]:
        """
        Auto-translate papers that need translation.
        
        Args:
            limit: Max papers to check
            
        Returns:
            Translation results
        """
        workflow.logger.info("Starting auto-translation workflow")
        
        # Get papers needing translation (from activity)
        paper_ids = await workflow.execute_activity(
            get_untranslated_papers_activity,
            args=(limit,),
            start_to_close_timeout=timedelta(minutes=2),
        )
        
        if not paper_ids:
            return {"message": "No papers need translation", "translated": 0}
        
        # Run translation workflow
        result = await workflow.execute_child_workflow(
            TranslationWorkflow.run,
            paper_ids,
            "auto",
            "ru",
            id=f"auto-translate-{workflow.now().isoformat()}"
        )
        
        return result


@activity.defn
async def get_untranslated_papers_activity(limit: int) -> List[str]:
    """Get papers that need translation."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select, or_
        
        result = await db.execute(
            select(Paper.id)
            .where(or_(
                Paper.title_translated.is_(None),
                Paper.abstract_translated.is_(None)
            ))
            .limit(limit)
        )
        
        return [row[0] for row in result.all()]
