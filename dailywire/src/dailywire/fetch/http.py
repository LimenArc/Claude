"""Polite async HTTP: real User-Agent, robots.txt, per-domain rate limiting."""

from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from ..config import IngestConfig

log = logging.getLogger(__name__)


class Fetcher:
    """Shared HTTP client for every network call the pipeline makes.

    One instance per run. It keeps a robots.txt cache and a last-request
    timestamp per domain, so concurrent tasks hitting the same host queue up
    behind each other while different hosts proceed in parallel.
    """

    def __init__(self, cfg: IngestConfig, client: httpx.AsyncClient | None = None):
        self.cfg = cfg
        self._client = client
        self._own_client = client is None
        self._sem = asyncio.Semaphore(cfg.max_concurrency)
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self._robots_locks: dict[str, asyncio.Lock] = {}

    async def __aenter__(self) -> "Fetcher":
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "User-Agent": self.cfg.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml,"
                    "application/rss+xml,application/atom+xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=self.cfg.request_timeout,
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._own_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Fetcher must be used as an async context manager")
        return self._client

    # -- politeness -------------------------------------------------------

    @staticmethod
    def _domain(url: str) -> str:
        return urlsplit(url).netloc.lower()

    def _lock(self, domain: str) -> asyncio.Lock:
        return self._domain_locks.setdefault(domain, asyncio.Lock())

    async def _throttle(self, domain: str) -> None:
        delay = self.cfg.per_domain_delay
        if delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request.get(domain, 0.0)
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request[domain] = time.monotonic()

    async def allowed(self, url: str) -> bool:
        """Check robots.txt for our User-Agent. Failure to fetch means allowed."""
        if not self.cfg.respect_robots_txt:
            return True
        parts = urlsplit(url)
        domain = parts.netloc.lower()
        if not domain:
            return False
        lock = self._robots_locks.setdefault(domain, asyncio.Lock())
        async with lock:
            if domain not in self._robots:
                self._robots[domain] = await self._load_robots(f"{parts.scheme}://{parts.netloc}")
        parser = self._robots[domain]
        if parser is None:
            return True
        return parser.can_fetch(self.cfg.user_agent, url)

    async def _load_robots(self, origin: str) -> RobotFileParser | None:
        url = f"{origin}/robots.txt"
        try:
            await self._throttle(self._domain(url))
            resp = await self.client.get(url, timeout=min(10.0, self.cfg.request_timeout))
        except Exception as exc:  # network error, TLS failure, timeout...
            log.debug("robots.txt unavailable for %s (%s); assuming allowed", origin, exc)
            return None
        if resp.status_code >= 400:
            # 404 means no restrictions. 401/403 on robots.txt itself is
            # conventionally read as "stay out", so be conservative there.
            if resp.status_code in (401, 403):
                parser = RobotFileParser()
                parser.parse(["User-agent: *", "Disallow: /"])
                return parser
            return None
        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser

    # -- requests ---------------------------------------------------------

    async def get(self, url: str, *, check_robots: bool = True, **kwargs) -> httpx.Response | None:
        """GET a URL, or None if disallowed or the request failed."""
        domain = self._domain(url)
        if check_robots and not await self.allowed(url):
            log.info("robots.txt disallows %s", url)
            return None
        async with self._sem:
            async with self._lock(domain):
                await self._throttle(domain)
                try:
                    resp = await self.client.get(url, **kwargs)
                except Exception as exc:
                    log.warning("GET %s failed: %s", url, exc)
                    return None
        if resp.status_code >= 400:
            log.warning("GET %s returned %s", url, resp.status_code)
            return None
        return resp

    async def get_json(self, url: str, **kwargs) -> dict | list | None:
        resp = await self.get(url, **kwargs)
        if resp is None:
            return None
        try:
            return resp.json()
        except ValueError as exc:
            log.warning("GET %s returned non-JSON: %s", url, exc)
            return None

    async def get_text(self, url: str, **kwargs) -> str | None:
        resp = await self.get(url, **kwargs)
        return None if resp is None else resp.text
