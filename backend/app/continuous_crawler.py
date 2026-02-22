"""
ZNAYKA Continuous Crawler Engine
24/7 permanent crawling platform
"""
import asyncio
import sys
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import logging

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import aiohttp


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("continuous_crawler")


@dataclass
class CrawlConfig:
    """Configuration for continuous crawling"""
    # API endpoints
    api_url: str = "https://znayka-674193695957.europe-north1.run.app"
    
    # Crawling settings
    sources: List[str] = None
    queries: List[str] = None
    
    # Continuous mode
    continuous_mode: bool = True
    check_interval_minutes: int = 5  # Check for new work every 5 minutes
    
    # Per-source limits
    papers_per_query: int = 1000
    max_papers_per_day: int = 100000  # Safety limit
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 30
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = [
                "arxiv", "cyberleninka", "elibrary", "rsl_dissertations",
                "rusneb", "inion", "hse_scientometrics", 
                "presidential_library", "rosstat_emiss"
            ]
        if self.queries is None:
            self.queries = self._get_comprehensive_queries()
    
    def _get_comprehensive_queries(self) -> List[str]:
        """Get comprehensive list of queries to cover all topics"""
        return [
            # Core AI/ML
            "machine learning", "deep learning", "neural networks",
            "artificial intelligence", "reinforcement learning",
            "computer vision", "natural language processing",
            "transformers", "large language models", "generative AI",
            
            # Computer Science
            "algorithms", "data structures", "distributed systems",
            "cloud computing", "edge computing", "cybersecurity",
            "blockchain", "quantum computing", "IoT", "5G",
            
            # Data Science
            "big data", "data mining", "data analytics",
            "statistical learning", "predictive modeling",
            "time series analysis", "anomaly detection",
            
            # Mathematics
            "mathematical modeling", "optimization", "linear algebra",
            "probability theory", "stochastic processes",
            "differential equations", "numerical methods",
            
            # Physics
            "quantum mechanics", "condensed matter", "particle physics",
            "optics", "thermodynamics", "electromagnetism",
            
            # Engineering
            "robotics", "automation", "control systems",
            "signal processing", "image processing",
            
            # Biology/Medicine
            "bioinformatics", "computational biology",
            "medical imaging", "biomedical engineering",
            "genomics", "proteomics",
            
            # Economics/Social
            "econometrics", "financial modeling",
            "computational social science", "digital humanities",
            
            # Environment
            "climate modeling", "environmental science",
            "renewable energy", "sustainability",
            
            # Russian-specific
            "российская наука", "научные исследования",
            "инновации", "технологии", "разработки",
        ]


class ContinuousCrawler:
    """
    24/7 Continuous Crawler for ZNAYKA
    Runs forever, collecting all papers from all sources
    """
    
    def __init__(self, config: CrawlConfig = None):
        self.config = config or CrawlConfig()
        self.session: aiohttp.ClientSession = None
        self.is_running = False
        self.stats = {
            "started_at": datetime.now().isoformat(),
            "total_crawls": 0,
            "total_papers_found": 0,
            "papers_by_source": {},
            "errors": [],
            "current_job": None
        }
        self.completed_pairs: Set[str] = set()  # source:query pairs done
        self.daily_paper_count = 0
        self.last_reset_date = datetime.now().date()
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120),
            headers={"Content-Type": "application/json"}
        )
        return self
        
    async def __aexit__(self, *args):
        self.is_running = False
        if self.session:
            await self.session.close()
    
    def _make_pair_id(self, source: str, query: str) -> str:
        """Create unique ID for source+query pair"""
        return f"{source}:{query.lower().strip()}"
    
    def _check_daily_limit(self) -> bool:
        """Check if we've hit the daily paper limit"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_paper_count = 0
            self.last_reset_date = today
        return self.daily_paper_count < self.config.max_papers_per_day
    
    async def start_crawl(self, source: str, query: str) -> Dict:
        """Start a crawl job for single source"""
        url = f"{self.config.api_url}/api/v1/worker/crawl"
        
        try:
            async with self.session.post(
                url,
                json={
                    "source": source,
                    "query": query,
                    "limit": self.config.papers_per_query
                }
            ) as resp:
                if resp.status in [200, 202]:
                    return await resp.json()
                else:
                    text = await resp.text()
                    return {"error": f"HTTP {resp.status}: {text}"}
        except Exception as e:
            logger.error(f"Error starting crawl {source}/{query}: {e}")
            return {"error": str(e)}
    
    async def start_crawl_all(self, query: str) -> Dict:
        """Start crawling ALL 9 sources for a query"""
        url = f"{self.config.api_url}/api/v1/worker/crawl-all"
        params = {"query": query, "limit": self.config.papers_per_query}
        
        try:
            async with self.session.post(url, params=params) as resp:
                if resp.status in [200, 202]:
                    return await resp.json()
                else:
                    text = await resp.text()
                    return {"error": f"HTTP {resp.status}: {text}"}
        except Exception as e:
            logger.error(f"Error starting crawl-all for {query}: {e}")
            return {"error": str(e)}
    
    async def get_crawl_status(self) -> Dict:
        """Get current crawler workflow status"""
        try:
            async with self.session.get(
                f"{self.config.api_url}/api/v1/workflows/crawl-status"
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Error getting status: {e}")
        return {}
    
    async def get_db_stats(self) -> Dict:
        """Get current database stats"""
        try:
            async with self.session.get(
                f"{self.config.api_url}/api/v1/papers/stats/index"
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Error getting DB stats: {e}")
        return {}
    
    async def wait_for_batch(self, check_interval: int = 10):
        """Wait for current batch of crawls to complete"""
        logger.info(f"Waiting for batch to complete (checking every {check_interval}s)...")
        
        while True:
            status = await self.get_crawl_status()
            progress = status.get("progress", {})
            
            running = progress.get("running", 0)
            completed = progress.get("completed", 0)
            failed = progress.get("failed", 0)
            
            if running == 0:
                logger.info(f"Batch complete! {completed} finished, {failed} failed")
                return {"completed": completed, "failed": failed}
            
            logger.debug(f"Running: {running}, Completed: {completed}, Failed: {failed}")
            await asyncio.sleep(check_interval)
    
    async def run_single_query(self, query: str) -> Dict:
        """Run all 9 crawlers for a single query"""
        pair_id = self._make_pair_id("all", query)
        
        if pair_id in self.completed_pairs:
            logger.info(f"Skipping '{query}' - already completed")
            return {"skipped": True, "query": query}
        
        if not self._check_daily_limit():
            logger.warning("Daily paper limit reached! Pausing until tomorrow.")
            return {"paused": True, "reason": "daily_limit"}
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🚀 CRAWLING: '{query}'")
        logger.info(f"{'='*70}")
        
        self.stats["current_job"] = {"query": query, "started": datetime.now().isoformat()}
        
        # Start all 9 crawlers
        result = await self.start_crawl_all(query)
        
        if "error" in result:
            logger.error(f"Failed to start crawl: {result['error']}")
            self.stats["errors"].append({"query": query, "error": result["error"]})
            return {"error": result["error"], "query": query}
        
        jobs = result.get("jobs", [])
        logger.info(f"Started {len(jobs)} crawlers for '{query}'")
        
        # Wait for completion
        batch_result = await self.wait_for_batch(check_interval=15)
        
        # Get updated stats
        db_stats = await self.get_db_stats()
        total_papers = db_stats.get("total_papers", 0)
        
        self.stats["total_crawls"] += len(jobs)
        self.stats["total_papers_found"] = total_papers
        self.completed_pairs.add(pair_id)
        
        logger.info(f"✅ Query '{query}' complete. DB now has {total_papers:,} papers")
        
        return {
            "query": query,
            "jobs": len(jobs),
            "completed": batch_result.get("completed", 0),
            "total_papers": total_papers
        }
    
    async def run_full_round(self):
        """Run one full round through all queries"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🔄 STARTING FULL ROUND - {len(self.config.queries)} queries")
        logger.info(f"{'='*70}\n")
        
        results = []
        for i, query in enumerate(self.config.queries, 1):
            logger.info(f"\n[{i}/{len(self.config.queries)}] Processing: '{query}'")
            
            result = await self.run_single_query(query)
            results.append(result)
            
            # Brief pause between queries
            if i < len(self.config.queries):
                await asyncio.sleep(5)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🎉 FULL ROUND COMPLETE")
        logger.info(f"{'='*70}")
        
        return results
    
    async def continuous_loop(self):
        """Run forever in continuous mode"""
        logger.info("\n" + "="*70)
        logger.info("🤖 ZNAYKA CONTINUOUS CRAWLER - 24/7 MODE")
        logger.info("="*70)
        logger.info(f"API: {self.config.api_url}")
        logger.info(f"Sources: {len(self.config.sources)}")
        logger.info(f"Queries: {len(self.config.queries)}")
        logger.info(f"Papers per query: {self.config.papers_per_query}")
        logger.info(f"Daily limit: {self.config.max_papers_per_day:,}")
        logger.info("="*70 + "\n")
        
        self.is_running = True
        round_num = 0
        
        try:
            while self.is_running:
                round_num += 1
                
                logger.info(f"\n{'#'*70}")
                logger.info(f"# ROUND #{round_num} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'#'*70}\n")
                
                # Run full round
                await self.run_full_round()
                
                # Save progress
                self._save_progress()
                
                # Check if we should continue
                if not self.config.continuous_mode:
                    logger.info("Continuous mode disabled. Stopping.")
                    break
                
                # Wait before next round
                wait_minutes = self.config.check_interval_minutes
                logger.info(f"\n😴 Round {round_num} complete. Waiting {wait_minutes} minutes...")
                logger.info(f"   (Press Ctrl+C to stop)")
                
                # Sleep in small chunks to allow clean shutdown
                for _ in range(wait_minutes):
                    if not self.is_running:
                        break
                    await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            logger.info("\n🛑 Crawler cancelled")
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopped by user")
        finally:
            self.is_running = False
            self._save_progress()
    
    def _save_progress(self):
        """Save crawler progress to file"""
        progress_file = Path("crawler-progress.json")
        data = {
            "stats": self.stats,
            "completed_pairs": list(self.completed_pairs),
            "config": {
                "sources": self.config.sources,
                "queries": self.config.queries,
                "papers_per_query": self.config.papers_per_query
            }
        }
        with open(progress_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"💾 Progress saved to {progress_file}")
    
    def load_progress(self, progress_file: str = "crawler-progress.json"):
        """Load crawler progress from file"""
        path = Path(progress_file)
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            self.completed_pairs = set(data.get("completed_pairs", []))
            logger.info(f"📂 Loaded {len(self.completed_pairs)} completed pairs from {progress_file}")
            return True
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ZNAYKA Continuous Crawler")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--limit", type=int, default=1000, help="Papers per query")
    parser.add_argument("--interval", type=int, default=60, help="Minutes between rounds")
    parser.add_argument("--load-progress", action="store_true", help="Resume from saved progress")
    parser.add_argument("--queries", nargs="+", help="Specific queries to run")
    
    args = parser.parse_args()
    
    # Create config
    config = CrawlConfig(
        continuous_mode=not args.once,
        check_interval_minutes=args.interval,
        papers_per_query=args.limit
    )
    
    if args.queries:
        config.queries = args.queries
    
    async def run():
        async with ContinuousCrawler(config) as crawler:
            if args.load_progress:
                crawler.load_progress()
            
            if args.once:
                await crawler.run_full_round()
            else:
                await crawler.continuous_loop()
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n\n👋 Crawler stopped")
        print("Run with --load-progress to resume")


if __name__ == "__main__":
    main()
