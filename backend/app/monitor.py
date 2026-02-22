"""
ZNAYKA Live Monitor Module
Real-time monitoring, recent papers feed, and live stats
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class LiveStats:
    """Real-time statistics"""
    total_papers: int = 0
    papers_today: int = 0
    papers_this_hour: int = 0
    active_crawls: int = 0
    completed_crawls: int = 0
    last_updated: str = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()


@dataclass 
class RecentPaper:
    """Recent paper for live feed"""
    id: str
    title: str
    source: str
    authors: List[str]
    year: int
    added_at: str
    has_pdf: bool = False


class LiveMonitor:
    """
    Live monitoring system for ZNAYKA
    Tracks real-time stats and recent papers
    """
    
    def __init__(self):
        self.stats = LiveStats()
        self.recent_papers: List[RecentPaper] = []
        self.max_recent = 100  # Keep last 100 papers
        self.crawl_history: List[Dict] = []
        self._lock = asyncio.Lock()
        self._subscribers: List[asyncio.Queue] = []
        
    async def add_paper(self, paper_data: Dict):
        """Add a new paper to the live feed"""
        async with self._lock:
            paper = RecentPaper(
                id=paper_data.get("id", "unknown"),
                title=paper_data.get("title", "Untitled"),
                source=paper_data.get("source_type", "unknown"),
                authors=[a.get("full_name", "Unknown") for a in paper_data.get("authors", [])[:3]],
                year=paper_data.get("publication_year", 2024),
                added_at=datetime.now().isoformat(),
                has_pdf=bool(paper_data.get("pdf_url"))
            )
            
            self.recent_papers.insert(0, paper)
            if len(self.recent_papers) > self.max_recent:
                self.recent_papers.pop()
            
            # Update stats
            self.stats.total_papers += 1
            self.stats.papers_today += 1
            self.stats.papers_this_hour += 1
            self.stats.last_updated = datetime.now().isoformat()
            
            # Notify subscribers
            await self._notify_subscribers({
                "type": "new_paper",
                "data": asdict(paper)
            })
    
    async def update_crawl_status(self, running: int, completed: int):
        """Update crawl status"""
        async with self._lock:
            self.stats.active_crawls = running
            self.stats.completed_crawls = completed
            self.stats.last_updated = datetime.now().isoformat()
            
            await self._notify_subscribers({
                "type": "crawl_update",
                "data": {"running": running, "completed": completed}
            })
    
    async def record_crawl_complete(self, crawl_data: Dict):
        """Record a completed crawl"""
        async with self._lock:
            record = {
                "timestamp": datetime.now().isoformat(),
                "source": crawl_data.get("source"),
                "query": crawl_data.get("query"),
                "papers_found": crawl_data.get("papers_found", 0),
                "papers_new": crawl_data.get("papers_new", 0),
                "duration_seconds": crawl_data.get("duration", 0)
            }
            self.crawl_history.insert(0, record)
            if len(self.crawl_history) > 1000:
                self.crawl_history.pop()
    
    async def get_live_stats(self) -> Dict:
        """Get current live stats"""
        async with self._lock:
            return {
                "total_papers": self.stats.total_papers,
                "papers_today": self.stats.papers_today,
                "papers_this_hour": self.stats.papers_this_hour,
                "active_crawls": self.stats.active_crawls,
                "completed_crawls": self.stats.completed_crawls,
                "recent_papers_count": len(self.recent_papers),
                "last_updated": self.stats.last_updated
            }
    
    async def get_recent_papers(self, limit: int = 20) -> List[Dict]:
        """Get recent papers for live feed"""
        async with self._lock:
            return [asdict(p) for p in self.recent_papers[:limit]]
    
    async def get_crawl_history(self, limit: int = 50) -> List[Dict]:
        """Get crawl history"""
        async with self._lock:
            return self.crawl_history[:limit]
    
    async def reset_daily_stats(self):
        """Reset daily counters (call at midnight)"""
        async with self._lock:
            self.stats.papers_today = 0
            logger.info("Daily stats reset")
    
    async def reset_hourly_stats(self):
        """Reset hourly counters"""
        async with self._lock:
            self.stats.papers_this_hour = 0
    
    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to live updates (for SSE)"""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue
    
    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from updates"""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
    
    async def _notify_subscribers(self, message: Dict):
        """Notify all subscribers of an update"""
        dead_subscribers = []
        for queue in self._subscribers:
            try:
                await queue.put(message)
            except Exception:
                dead_subscribers.append(queue)
        
        # Clean up dead subscribers
        for queue in dead_subscribers:
            if queue in self._subscribers:
                self._subscribers.remove(queue)


# Global monitor instance
live_monitor = LiveMonitor()
