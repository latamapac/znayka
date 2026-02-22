"""
ZNAYKA PDF Download Manager
Smart PDF handling: metadata first, PDFs on-demand
"""
import asyncio
import aiohttp
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFManager:
    """
    Manages PDF downloads with smart caching and queue system
    
    Strategy:
    1. Metadata is downloaded instantly (fast, cheap)
    2. PDFs are queued for background download
    3. Popular papers get priority
    4. PDFs stored in Cloudflare R2 or local storage
    """
    
    def __init__(self, storage_type: str = "local"):
        self.storage_type = storage_type
        self.download_queue = asyncio.Queue()
        self.is_running = False
        
        # Local storage path
        self.storage_path = Path("/app/storage/pdfs")
        if storage_type == "local":
            self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def queue_pdf_download(self, paper_id: str, pdf_url: str, priority: int = 5):
        """
        Add PDF to download queue
        
        Priority levels:
        1 = User requested download (highest)
        5 = Recently crawled paper
        10 = Bulk background download (lowest)
        """
        await self.download_queue.put({
            "paper_id": paper_id,
            "pdf_url": pdf_url,
            "priority": priority,
            "queued_at": datetime.now().isoformat()
        })
        logger.info(f"Queued PDF download: {paper_id} (priority {priority})")
    
    async def download_pdf(self, paper_id: str, pdf_url: str) -> Optional[bytes]:
        """
        Download PDF from source
        
        Returns PDF bytes or None if failed
        """
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        # Verify it's a PDF
                        if content[:4] == b'%PDF':
                            logger.info(f"Downloaded PDF: {paper_id} ({len(content)} bytes)")
                            return content
                        else:
                            logger.warning(f"Downloaded content is not PDF: {paper_id}")
                            return None
                    else:
                        logger.warning(f"Failed to download PDF {paper_id}: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading PDF {paper_id}: {e}")
            return None
    
    async def store_pdf(self, paper_id: str, pdf_data: bytes) -> str:
        """
        Store PDF and return storage path/URL
        """
        if self.storage_type == "local":
            # Local file storage
            file_path = self.storage_path / f"{paper_id}.pdf"
            file_path.write_bytes(pdf_data)
            return str(file_path)
        
        elif self.storage_type == "r2":
            # Cloudflare R2 storage
            # TODO: Implement R2 upload
            from app.storage.r2 import upload_to_r2
            return await upload_to_r2(f"pdfs/{paper_id}.pdf", pdf_data)
        
        else:
            raise ValueError(f"Unknown storage type: {self.storage_type}")
    
    async def get_pdf(self, paper_id: str) -> Optional[bytes]:
        """
        Get PDF by paper ID
        Returns None if not downloaded yet
        """
        if self.storage_type == "local":
            file_path = self.storage_path / f"{paper_id}.pdf"
            if file_path.exists():
                return file_path.read_bytes()
        
        # TODO: Check R2 if not found locally
        return None
    
    async def process_queue(self):
        """
        Background worker that processes PDF download queue
        """
        self.is_running = True
        logger.info("PDF download worker started")
        
        while self.is_running:
            try:
                # Get item from queue (with timeout to allow checking is_running)
                item = await asyncio.wait_for(self.download_queue.get(), timeout=5.0)
                
                paper_id = item["paper_id"]
                pdf_url = item["pdf_url"]
                
                # Check if already downloaded
                existing = await self.get_pdf(paper_id)
                if existing:
                    logger.debug(f"PDF already exists: {paper_id}")
                    continue
                
                # Download
                pdf_data = await self.download_pdf(paper_id, pdf_url)
                
                if pdf_data:
                    # Store
                    storage_path = await self.store_pdf(paper_id, pdf_data)
                    
                    # Update database
                    await self.mark_pdf_downloaded(paper_id, storage_path)
                    
                    logger.info(f"PDF processed: {paper_id}")
                
                # Small delay to be nice to source servers
                await asyncio.sleep(1)
                
            except asyncio.TimeoutError:
                # No items in queue, continue loop
                continue
            except Exception as e:
                logger.error(f"Error in PDF worker: {e}")
                await asyncio.sleep(5)
        
        logger.info("PDF download worker stopped")
    
    async def mark_pdf_downloaded(self, paper_id: str, storage_path: str):
        """
        Update database to mark PDF as downloaded
        """
        # This will be implemented when we have real database
        # For now, just log it
        logger.info(f"Marked as downloaded: {paper_id} at {storage_path}")
    
    def stop(self):
        """Stop the background worker"""
        self.is_running = False


# Priority-based PDF download scheduler
class PDFPriorityScheduler:
    """
    Schedules PDF downloads based on priority criteria
    """
    
    def __init__(self, pdf_manager: PDFManager):
        self.pdf_manager = pdf_manager
    
    async def schedule_popular_papers(self, papers: list):
        """
        Schedule PDF downloads for most popular/viewed papers
        """
        # Sort by view count or citation count
        sorted_papers = sorted(
            papers,
            key=lambda p: p.get("citation_count", 0) + p.get("view_count", 0),
            reverse=True
        )
        
        # Queue top 100
        for paper in sorted_papers[:100]:
            if paper.get("pdf_url"):
                await self.pdf_manager.queue_pdf_download(
                    paper["id"],
                    paper["pdf_url"],
                    priority=3  # Medium-high priority
                )
    
    async def schedule_recent_papers(self, papers: list):
        """
        Schedule PDF downloads for recently crawled papers
        """
        for paper in papers:
            if paper.get("pdf_url") and paper.get("year", 0) >= 2023:
                await self.pdf_manager.queue_pdf_download(
                    paper["id"],
                    paper["pdf_url"],
                    priority=5  # Normal priority
                )


# Global PDF manager instance
pdf_manager = PDFManager(storage_type="local")


async def start_pdf_worker():
    """Start background PDF download worker"""
    await pdf_manager.process_queue()


async def queue_pdf_for_download(paper_id: str, pdf_url: str, priority: int = 5):
    """Public function to queue a PDF download"""
    await pdf_manager.queue_pdf_download(paper_id, pdf_url, priority)


async def get_pdf_content(paper_id: str) -> Optional[bytes]:
    """Public function to get PDF content"""
    return await pdf_manager.get_pdf(paper_id)
