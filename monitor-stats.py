#!/usr/bin/env python3
"""
ZNAYKA Stats Monitor
Real-time monitoring of database growth and crawler progress
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime


API_URL = "https://znayka-674193695957.europe-north1.run.app"
FRONTEND_URL = "https://znayka-frontend.vercel.app"


async def fetch_stats(session: aiohttp.ClientSession) -> dict:
    """Fetch current stats from API"""
    try:
        async with session.get(f"{API_URL}/api/v1/papers/stats/index") as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"❌ Error: {e}")
    return {}


async def fetch_crawl_status(session: aiohttp.ClientSession) -> dict:
    """Fetch crawler workflow status"""
    try:
        async with session.get(f"{API_URL}/api/v1/workflows/crawl-status") as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"❌ Error: {e}")
    return {}


def print_header():
    """Print monitor header"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "ZNAYKA STATS MONITOR" + " " * 33 + "║")
    print("╠" + "═" * 78 + "╣")
    print(f"║  Frontend:  {FRONTEND_URL:68s} ║")
    print(f"║  API:       {API_URL:68s} ║")
    print("╚" + "═" * 78 + "╝")


def print_stats(stats: dict, crawl_status: dict):
    """Print formatted stats"""
    total = stats.get("total_papers", 0)
    with_text = stats.get("with_full_text", 0)
    coverage = stats.get("processing_coverage", 0)
    by_source = stats.get("by_source", {})
    by_year = stats.get("by_year", {})
    
    # Workflow status
    wf = crawl_status.get("progress", {})
    wf_status = crawl_status.get("status", "UNKNOWN")
    
    print(f"\n📊 DATABASE STATS ({datetime.now().strftime('%H:%M:%S')})")
    print("─" * 80)
    print(f"  📄 Total Papers:       {total:>6}")
    print(f"  📑 With Full Text:     {with_text:>6} ({coverage:.1f}%)")
    print(f"  🌐 Sources:            {len(by_source):>6}")
    
    print(f"\n🕷️  CRAWLER STATUS: {wf_status}")
    print("─" * 80)
    print(f"  Running:   {wf.get('running', 0):>3} 🟡")
    print(f"  Completed: {wf.get('completed', 0):>3} ✅")
    print(f"  Failed:    {wf.get('failed', 0):>3} ❌")
    print(f"  Pending:   {wf.get('pending', 0):>3} ⏳")
    
    if by_source:
        print(f"\n📚 PAPERS BY SOURCE")
        print("─" * 80)
        max_count = max(by_source.values()) if by_source else 1
        for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
            bar_len = int((count / max_count) * 40)
            bar = "█" * bar_len
            print(f"  {source:25s} │ {bar:<40s} │ {count:>4}")
    
    if by_year:
        print(f"\n📅 PAPERS BY YEAR")
        print("─" * 80)
        max_year = max(by_year.values()) if by_year else 1
        for year, count in sorted(by_year.items(), key=lambda x: x[0], reverse=True)[:5]:
            bar_len = int((count / max_year) * 40)
            bar = "█" * bar_len
            print(f"  {year:>4s} │ {bar:<40s} │ {count:>4}")


async def monitor_loop(interval: int = 10):
    """Continuous monitoring loop"""
    print_header()
    
    prev_total = 0
    
    async with aiohttp.ClientSession() as session:
        while True:
            stats = await fetch_stats(session)
            crawl_status = await fetch_crawl_status(session)
            
            # Clear screen (optional)
            # print("\033[2J\033[H")
            
            print_stats(stats, crawl_status)
            
            # Show growth rate
            total = stats.get("total_papers", 0)
            if prev_total > 0 and total > prev_total:
                growth = total - prev_total
                print(f"\n📈 Growth: +{growth} papers since last check")
            prev_total = total
            
            print(f"\n⏱️  Next update in {interval}s... (Press Ctrl+C to exit)")
            await asyncio.sleep(interval)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=10, help="Update interval in seconds")
    args = parser.parse_args()
    
    try:
        asyncio.run(monitor_loop(args.interval))
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped")


if __name__ == "__main__":
    main()
