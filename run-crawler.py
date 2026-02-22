#!/usr/bin/env python3
"""
Crawler runner with SSL workaround for macOS
Usage: python3 run-crawler.py <query> [--source <source>] [--limit <limit>]
"""
import asyncio
import sys
import os

# Add paths
sys.path.insert(0, 'backend')
sys.path.insert(0, '.')
os.environ.pop('USE_SQLITE', None)

import ssl
import certifi
from aiohttp import TCPConnector

# Monkey-patch SSL for crawlers
original_init = TCPConnector.__init__
def patched_init(self, *args, **kwargs):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    kwargs['ssl'] = ssl_context
    return original_init(self, *args, **kwargs)

TCPConnector.__init__ = patched_init

from crawlers.orchestrator import CrawlerOrchestrator

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run-crawler.py <query> [--source <source>] [--limit <limit>]")
        print("Sources: cyberleninka, arxiv, elibrary")
        print("Example: python3 run-crawler.py 'machine learning' --source cyberleninka --limit 10")
        return
    
    query = sys.argv[1]
    source = "all"
    limit = 10
    
    # Parse args
    for i, arg in enumerate(sys.argv):
        if arg == "--source" and i + 1 < len(sys.argv):
            source = sys.argv[i + 1]
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
    
    print(f"🔍 Crawling for: '{query}'")
    print(f"📡 Source: {source}")
    print(f"📊 Limit: {limit}")
    print()
    
    orchestrator = CrawlerOrchestrator()
    
    if source == "all":
        results = await orchestrator.crawl_academic_sources(query, limit_per_source=limit)
    else:
        papers = await orchestrator.crawl_source(source, query, limit=limit, store=True)
        print(f"✅ Crawled {len(papers)} papers from {source}")
        return
    
    print("\n=== RESULTS ===")
    total = 0
    for src, result in results.items():
        if result.get("success"):
            count = result.get("count", 0)
            total += count
            print(f"✅ {src}: {count} papers")
        else:
            print(f"❌ {src}: {result.get('error', 'Failed')}")
    
    print(f"\n📊 Total: {total} papers added to database")

if __name__ == "__main__":
    asyncio.run(main())
