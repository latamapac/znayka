#!/usr/bin/env python3
"""
ZNAYKA Automatic Crawler Manager
Continuously crawls all 9 sources to build the unique database
"""
import asyncio
import aiohttp
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CrawlTask:
    source: str
    query: str
    limit: int
    priority: int = 1


class ZnaykaCrawlerManager:
    """
    Automatic Task/Progress Manager for ZNAYKA
    Manages continuous crawling across all 9 sources
    """
    
    # Deployment URLs
    FRONTEND_URL = "https://znayka-frontend.vercel.app"
    API_URL = "https://znayka-674193695957.europe-north1.run.app"
    
    # All 9 data sources
    SOURCES = [
        "arxiv", "cyberleninka", "elibrary", "rsl_dissertations",
        "rusneb", "inion", "hse_scientometrics", 
        "presidential_library", "rosstat_emiss"
    ]
    
    # Comprehensive query list for maximum coverage
    QUERIES = [
        # AI / ML
        "machine learning", "artificial intelligence", "deep learning", "neural networks",
        "computer vision", "natural language processing", "reinforcement learning",
        "transformers", "large language models", "generative AI",
        
        # Computer Science
        "algorithms", "distributed systems", "cloud computing", "cybersecurity",
        "blockchain", "quantum computing", "edge computing", "IoT",
        
        # Data Science
        "data mining", "big data", "statistical analysis", "predictive modeling",
        "time series analysis", "anomaly detection",
        
        # Russian Science Topics
        "российская наука", "научные исследования", "инновации", "технологии",
        "математическое моделирование", "вычислительная математика",
        
        # Interdisciplinary
        "bioinformatics", "computational biology", "medical informatics",
        "environmental science", "climate modeling", "renewable energy",
        
        # Physics & Engineering
        "condensed matter", "particle physics", "optics", "robotics",
        "automation", "control systems",
        
        # Social Sciences
        "econometrics", "computational social science", "digital humanities"
    ]
    
    def __init__(self):
        self.session: aiohttp.ClientSession = None
        self.stats = {
            "total_crawls": 0,
            "papers_found": 0,
            "sources_completed": {s: 0 for s in self.SOURCES},
            "queries_completed": [],
            "start_time": datetime.now().isoformat(),
            "errors": []
        }
        self.completed_pairs: Set[str] = set()  # Track completed source+query pairs
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"Content-Type": "application/json"}
        )
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def _make_id(self, source: str, query: str) -> str:
        return f"{source}:{query.lower().strip()}"
    
    async def get_current_stats(self) -> Dict:
        """Get current database stats from API"""
        try:
            async with self.session.get(f"{self.API_URL}/api/v1/papers/stats/index") as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"⚠️  Error getting stats: {e}")
        return {}
    
    async def start_crawl_all(self, query: str, limit: int = 50) -> Dict:
        """Start crawling ALL 9 sources for a query"""
        url = f"{self.API_URL}/api/v1/worker/crawl-all"
        params = {"query": query, "limit": limit}
        
        try:
            async with self.session.post(url, params=params) as resp:
                if resp.status in [200, 202]:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {"error": f"HTTP {resp.status}: {error_text}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_crawl_status(self) -> Dict:
        """Get current crawl workflow status"""
        try:
            async with self.session.get(f"{self.API_URL}/api/v1/workflows/crawl-status") as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"⚠️  Error getting status: {e}")
        return {}
    
    async def wait_for_completion(self, check_interval: int = 10):
        """Wait for all active crawls to complete"""
        print(f"⏳  Waiting for crawls to complete (checking every {check_interval}s)...")
        
        while True:
            status = await self.get_crawl_status()
            progress = status.get("progress", {})
            
            running = progress.get("running", 0)
            completed = progress.get("completed", 0)
            failed = progress.get("failed", 0)
            
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] Running: {running} | Completed: {completed} | Failed: {failed}")
            
            if running == 0:
                print(f"✅  Batch complete! {completed} crawls finished")
                break
                
            await asyncio.sleep(check_interval)
    
    async def run_batch(self, queries: List[str], limit: int = 30):
        """Run a batch of queries across all 9 sources"""
        print(f"\n🚀 Starting batch: {len(queries)} queries × 9 sources = {len(queries) * 9} total crawls\n")
        
        for i, query in enumerate(queries, 1):
            # Check if we've already done this query for all sources
            query_id = query.lower().strip()
            if all(self._make_id(s, query_id) in self.completed_pairs for s in self.SOURCES):
                print(f"⏭️  [{i}/{len(queries)}] Skipping '{query}' (already completed)")
                continue
            
            print(f"\n📚 [{i}/{len(queries)}] Query: '{query}'")
            print("-" * 60)
            
            # Start all 9 crawlers for this query
            result = await self.start_crawl_all(query, limit)
            
            if "error" in result:
                print(f"❌ Error starting crawl: {result['error']}")
                self.stats["errors"].append({"query": query, "error": result["error"]})
                continue
            
            jobs = result.get("jobs", [])
            print(f"🕷️   Started {len(jobs)} crawlers:")
            for job in jobs[:5]:  # Show first 5
                print(f"     • {job['source']}: {job['job_id'][:40]}...")
            if len(jobs) > 5:
                print(f"     ... and {len(jobs) - 5} more")
            
            # Wait for completion
            await self.wait_for_completion(check_interval=5)
            
            # Update stats
            current_stats = await self.get_current_stats()
            papers_found = current_stats.get("total_papers", 0)
            
            self.stats["total_crawls"] += len(jobs)
            self.stats["papers_found"] = papers_found
            self.stats["queries_completed"].append(query)
            
            for source in self.SOURCES:
                self.completed_pairs.add(self._make_id(source, query_id))
            
            print(f"📊 Current database: {papers_found} papers\n")
            
            # Brief pause between batches
            await asyncio.sleep(2)
    
    async def run_full_crawl(self, limit_per_query: int = 30):
        """Run complete crawl across all queries and sources"""
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 20 + "ZNAYKA AUTOMATIC CRAWLER MANAGER" + " " * 27 + "║")
        print("║" + " " * 78 + "║")
        print("║  Frontend:  https://znayka-frontend.vercel.app" + " " * 32 + "║")
        print("║  API:       https://znayka-674193695957.europe-north1.run.app" + " " * 17 + "║")
        print("╚" + "═" * 78 + "╝")
        
        print(f"\n📋 Configuration:")
        print(f"   • Sources:     {len(self.SOURCES)} (all available)")
        print(f"   • Queries:     {len(self.QUERIES)} topics")
        print(f"   • Total jobs:  {len(self.SOURCES) * len(self.QUERIES)} crawls")
        print(f"   • Limit/query: {limit_per_query} papers")
        print(f"   • Estimated:   {len(self.SOURCES) * len(self.QUERIES) * limit_per_query} papers")
        
        # Get initial stats
        initial_stats = await self.get_current_stats()
        initial_papers = initial_stats.get("total_papers", 0)
        print(f"\n📊 Initial database: {initial_papers} papers")
        print("=" * 80)
        
        # Run all batches
        await self.run_batch(self.QUERIES, limit_per_query)
        
        # Final summary
        print("\n" + "=" * 80)
        print("🎉 FULL CRAWL COMPLETE!")
        print("=" * 80)
        
        final_stats = await self.get_current_stats()
        final_papers = final_stats.get("total_papers", 0)
        
        print(f"\n📈 Results:")
        print(f"   • Total crawls:     {self.stats['total_crawls']}")
        print(f"   • Papers added:     {final_papers - initial_papers}")
        print(f"   • Total in DB:      {final_papers}")
        print(f"   • Queries done:     {len(self.stats['queries_completed'])}")
        print(f"   • Errors:           {len(self.stats['errors'])}")
        print(f"   • Duration:         {datetime.now() - datetime.fromisoformat(self.stats['start_time'])}")
        
        print(f"\n📊 By Source:")
        by_source = final_stats.get("by_source", {})
        for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(count / max(by_source.values()) * 30) if by_source else ""
            print(f"   {source:25s} │ {bar:<30s} │ {count:4d}")
        
        print(f"\n🌐 View your database:")
        print(f"   Frontend:  {self.FRONTEND_URL}")
        print(f"   Stats:     {self.FRONTEND_URL}/stats")
        print(f"   API:       {self.API_URL}/api/v1/papers/stats/index")
        
        # Save report
        report_file = f"crawl-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump({
                "stats": self.stats,
                "final_database": final_stats,
                "completed_pairs": list(self.completed_pairs)
            }, f, indent=2)
        print(f"\n💾 Report saved: {report_file}")
        
        return final_stats
    
    async def continuous_mode(self, interval_minutes: int = 60):
        """Run continuous crawling mode - repeats every N minutes"""
        print(f"🔄 CONTINUOUS MODE: Running every {interval_minutes} minutes")
        print("=" * 80)
        
        iteration = 0
        while True:
            iteration += 1
            print(f"\n{'='*80}")
            print(f"🔄 ITERATION #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            
            # Run full crawl
            await self.run_full_crawl(limit_per_query=20)
            
            print(f"\n😴 Sleeping for {interval_minutes} minutes...")
            print(f"   (Press Ctrl+C to stop)")
            await asyncio.sleep(interval_minutes * 60)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ZNAYKA Automatic Crawler Manager")
    parser.add_argument("--mode", choices=["once", "continuous"], default="once",
                       help="Run mode: once or continuous")
    parser.add_argument("--interval", type=int, default=60,
                       help="Interval in minutes for continuous mode (default: 60)")
    parser.add_argument("--limit", type=int, default=30,
                       help="Papers per query per source (default: 30)")
    parser.add_argument("--queries", nargs="+", 
                       help="Specific queries to run (default: all)")
    
    args = parser.parse_args()
    
    async def run():
        async with ZnaykaCrawlerManager() as manager:
            if args.queries:
                manager.QUERIES = args.queries
            
            if args.mode == "continuous":
                await manager.continuous_mode(args.interval)
            else:
                await manager.run_full_crawl(args.limit)
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
