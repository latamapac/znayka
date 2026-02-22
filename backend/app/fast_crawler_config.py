"""
ZNAYKA Fast Crawler Configuration
Optimized for maximum speed and throughput
"""

FAST_CRAWL_CONFIG = {
    # Papers per query - increased for speed
    "papers_per_query": 5000,  # Was 1000
    
    # Concurrency settings
    "concurrent_sources": 9,     # All 9 sources at once
    "concurrent_queries": 5,     # Run 5 queries in parallel
    "max_concurrent_batches": 3,  # 3 batches running simultaneously
    
    # Timing - minimized delays
    "delay_between_queries": 0.5,      # Was 5s
    "delay_between_batches": 1,        # Was 15s
    "check_interval": 5,               # Was 15s
    "batch_completion_timeout": 300,   # 5 minutes max per batch
    
    # Daily limits (safety)
    "max_papers_per_day": 500000,  # 500k papers/day max
    
    # Retry settings
    "max_retries": 5,
    "retry_delay": 2,
    "retry_backoff": 2.0,  # Exponential backoff
}

# Priority-based query scheduling
HIGH_PRIORITY_QUERIES = [
    # These run every round
    "machine learning",
    "artificial intelligence", 
    "deep learning",
    "neural networks",
    "data science",
]

MEDIUM_PRIORITY_QUERIES = [
    # These run every 2nd round
    "computer vision",
    "natural language processing",
    "reinforcement learning",
    "quantum computing",
    "cybersecurity",
    "blockchain",
    "cloud computing",
    "IoT",
]

LOW_PRIORITY_QUERIES = [
    # These run every 5th round
    "robotics",
    "bioinformatics",
    "computational biology",
    "climate modeling",
    "renewable energy",
    "econometrics",
    "computational physics",
    "social network analysis",
    # Russian topics
    "российская наука",
    "научные исследования",
    "инновации",
    "разработки",
]

# All queries combined
ALL_QUERIES_FAST = HIGH_PRIORITY_QUERIES + MEDIUM_PRIORITY_QUERIES + LOW_PRIORITY_QUERIES

# Source-specific batch sizes (optimize for each source's speed)
SOURCE_BATCH_SIZES = {
    "arxiv": 5000,           # Fast API
    "cyberleninka": 3000,    # Moderate
    "elibrary": 5000,        # Can handle large batches
    "rusneb": 2000,
    "rsl_dissertations": 1500,
    "inion": 1000,
    "hse_scientometrics": 1000,
    "presidential_library": 500,
    "rosstat_emiss": 500,
}

# Expected yields (for realistic simulation)
REALISTIC_YIELDS = {
    "arxiv": 2500,           # Papers per query
    "cyberleninka": 1800,
    "elibrary": 3500,
    "rusneb": 800,
    "rsl_dissertations": 600,
    "inion": 400,
    "hse_scientometrics": 250,
    "presidential_library": 150,
    "rosstat_emiss": 100,
}
