"""Rotating proxy manager with health tracking and automatic ban recovery.

Supports:
- Round-robin rotation across a pool of proxies
- Per-proxy health scoring (success/fail/ban tracking)
- Automatic cooldown for banned or failing proxies
- Configurable via PROXY_LIST env var or direct list
- Thread-safe for use with asyncio.to_thread()

Usage:
    rotator = ProxyRotator.from_env()       # loads PROXY_LIST from env
    rotator = ProxyRotator(["socks5://...", "http://..."])

    proxy = rotator.get_proxy()             # next healthy proxy
    rotator.report_success(proxy)           # mark success
    rotator.report_failure(proxy)           # mark failure (soft)
    rotator.report_ban(proxy)               # mark ban (cooldown)
"""
import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Proxy health thresholds
_BAN_COOLDOWN_SECONDS = 300       # 5 min cooldown after ban
_FAIL_COOLDOWN_SECONDS = 60       # 1 min cooldown after repeated failures
_MAX_CONSECUTIVE_FAILS = 3        # failures before temporary cooldown
_HEALTH_DECAY_INTERVAL = 600      # reset failure counts every 10 min


@dataclass
class _ProxyState:
    """Health state for a single proxy."""
    url: str
    consecutive_fails: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_bans: int = 0
    last_success: float = 0.0
    last_failure: float = 0.0
    last_ban: float = 0.0
    cooldown_until: float = 0.0

    @property
    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    @property
    def success_rate(self) -> float:
        total = self.total_successes + self.total_failures
        if total == 0:
            return 1.0  # untested = optimistic
        return self.total_successes / total

    def reset_consecutive(self):
        self.consecutive_fails = 0


class ProxyRotator:
    """Thread-safe rotating proxy manager with health tracking."""

    def __init__(self, proxy_urls: List[str], shuffle: bool = True):
        if not proxy_urls:
            raise ValueError("proxy_urls must not be empty")

        urls = list(set(proxy_urls))  # deduplicate
        if shuffle:
            random.shuffle(urls)

        self._proxies: Dict[str, _ProxyState] = {
            url: _ProxyState(url=url) for url in urls
        }
        self._order: List[str] = urls
        self._index = 0
        self._lock = threading.Lock()
        self._last_decay = time.time()

        logger.info(f"ProxyRotator initialized with {len(urls)} proxies")

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, env_var: str = "PROXY_LIST") -> Optional["ProxyRotator"]:
        """Create rotator from environment variable.

        PROXY_LIST should be comma-separated or newline-separated proxy URLs:
            PROXY_LIST=socks5://u:p@host1:1080,http://u:p@host2:8080
        """
        raw = os.getenv(env_var, "").strip()
        if not raw:
            logger.info(f"No {env_var} env var set — proxy rotation disabled")
            return None

        # Support comma, newline, semicolon as separators
        urls = []
        for sep in [",", "\n", ";"]:
            if sep in raw:
                urls = [u.strip() for u in raw.split(sep) if u.strip()]
                break
        if not urls:
            urls = [raw]  # single proxy

        logger.info(f"Loaded {len(urls)} proxies from {env_var}")
        return cls(urls)

    @classmethod
    def from_file(cls, path: str) -> Optional["ProxyRotator"]:
        """Load proxies from a file (one per line)."""
        try:
            with open(path) as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            if urls:
                logger.info(f"Loaded {len(urls)} proxies from {path}")
                return cls(urls)
        except FileNotFoundError:
            logger.warning(f"Proxy file not found: {path}")
        return None

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def get_proxy(self) -> Optional[str]:
        """Get next available proxy via round-robin, skipping unhealthy ones.

        Returns None if all proxies are in cooldown.
        """
        with self._lock:
            self._maybe_decay()

            n = len(self._order)
            for _ in range(n):
                url = self._order[self._index % n]
                self._index = (self._index + 1) % n
                state = self._proxies[url]
                if state.is_available:
                    return url

            # All in cooldown — return the one with shortest remaining cooldown
            best = min(self._proxies.values(), key=lambda s: s.cooldown_until)
            wait = best.cooldown_until - time.time()
            if wait > 0:
                logger.warning(
                    f"All {n} proxies in cooldown. Best available in {wait:.0f}s: "
                    f"{self._mask(best.url)}"
                )
            return best.url

    def report_success(self, proxy_url: str):
        """Mark a successful request through this proxy."""
        with self._lock:
            state = self._proxies.get(proxy_url)
            if state:
                state.total_successes += 1
                state.last_success = time.time()
                state.consecutive_fails = 0

    def report_failure(self, proxy_url: str):
        """Mark a failed request (network error, timeout, etc.)."""
        with self._lock:
            state = self._proxies.get(proxy_url)
            if state:
                state.total_failures += 1
                state.consecutive_fails += 1
                state.last_failure = time.time()

                if state.consecutive_fails >= _MAX_CONSECUTIVE_FAILS:
                    state.cooldown_until = time.time() + _FAIL_COOLDOWN_SECONDS
                    state.consecutive_fails = 0
                    logger.warning(
                        f"Proxy {self._mask(proxy_url)} cooldown "
                        f"{_FAIL_COOLDOWN_SECONDS}s after {_MAX_CONSECUTIVE_FAILS} consecutive fails"
                    )

    def report_ban(self, proxy_url: str):
        """Mark a ban/CAPTCHA detection — longer cooldown."""
        with self._lock:
            state = self._proxies.get(proxy_url)
            if state:
                state.total_bans += 1
                state.last_ban = time.time()
                state.cooldown_until = time.time() + _BAN_COOLDOWN_SECONDS
                state.consecutive_fails = 0
                logger.warning(
                    f"Proxy {self._mask(proxy_url)} BANNED — "
                    f"cooldown {_BAN_COOLDOWN_SECONDS}s (total bans: {state.total_bans})"
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def pool_size(self) -> int:
        return len(self._order)

    @property
    def available_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._proxies.values() if s.is_available)

    def get_stats(self) -> List[dict]:
        """Get health stats for all proxies."""
        with self._lock:
            return [
                {
                    "proxy": self._mask(s.url),
                    "available": s.is_available,
                    "success_rate": round(s.success_rate, 3),
                    "successes": s.total_successes,
                    "failures": s.total_failures,
                    "bans": s.total_bans,
                    "cooldown_remaining": max(0, round(s.cooldown_until - time.time(), 1)),
                }
                for s in self._proxies.values()
            ]

    def _maybe_decay(self):
        """Periodically reset consecutive failure counters."""
        now = time.time()
        if now - self._last_decay > _HEALTH_DECAY_INTERVAL:
            for state in self._proxies.values():
                state.reset_consecutive()
            self._last_decay = now

    @staticmethod
    def _mask(url: str) -> str:
        """Mask credentials in proxy URL for logging."""
        # socks5://user:pass@host:port -> socks5://***@host:port
        if "@" in url:
            scheme_and_creds, host = url.rsplit("@", 1)
            scheme = scheme_and_creds.split("://")[0] if "://" in scheme_and_creds else "proxy"
            return f"{scheme}://***@{host}"
        return url
