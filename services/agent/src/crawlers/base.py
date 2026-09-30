"""
Base crawler with proxy rotation, rate limiting, UA rotation, and retry logic.
"""

from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup

from src.common.logger import get_logger
from src.schemas.trend import TrendTopicSchema

logger = get_logger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


@dataclass
class ProxyConfig:
    """Proxy configuration."""

    http: str | None = None
    https: str | None = None

    def as_httpx_proxies(self) -> str | None:
        return self.https or self.http


class BaseCrawler(ABC):
    """Abstract base class for platform crawlers."""

    PLATFORM: str = ""
    BASE_URL: str = ""

    def __init__(
        self,
        proxies: list[ProxyConfig] | None = None,
        request_interval: tuple[float, float] = (1.0, 3.0),
        max_retries: int = 3,
        timeout: float = 15.0,
    ):
        self.proxies = proxies or []
        self.request_interval = request_interval
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_request_time: float = 0
        self._current_proxy_idx: int = 0
        # Sample data is opt-in; production must never present fixtures as live trends.
        from src.config import get_settings

        self.allow_sample_data = get_settings().crawl_use_sample_data

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def _get_proxy(self) -> ProxyConfig | None:
        if not self.proxies:
            return None
        proxy = self.proxies[self._current_proxy_idx % len(self.proxies)]
        self._current_proxy_idx += 1
        return proxy

    async def _rate_limit(self) -> None:
        """Enforce request interval."""
        now = time.time()
        elapsed = now - self._last_request_time
        min_interval = random.uniform(*self.request_interval)
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    async def _request(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with retry, proxy rotation, and rate limiting."""
        await self._rate_limit()

        merged_headers = self._get_headers()
        if headers:
            merged_headers.update(headers)

        proxy = self._get_proxy()
        proxy_mount = None
        if proxy and proxy.as_httpx_proxies():
            proxy_mount = httpx.AsyncHTTPTransport(proxy=proxy.as_httpx_proxies())

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    mounts={"all://": proxy_mount} if proxy_mount else None,
                ) as client:
                    resp = await client.request(
                        method, url, headers=merged_headers, params=params, json=json_data, **kwargs
                    )
                    resp.raise_for_status()
                    return resp
            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
                wait = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"[{self.PLATFORM}] Request failed (attempt {attempt + 1}/{self.max_retries}): {e}, "
                    f"retrying in {wait:.1f}s"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait)
                    # Rotate proxy on failure
                    if self.proxies:
                        proxy = self._get_proxy()
                        if proxy and proxy.as_httpx_proxies():
                            proxy_mount = httpx.AsyncHTTPTransport(proxy=proxy.as_httpx_proxies())
                else:
                    raise

        raise RuntimeError(f"Max retries exceeded for {url}")

    async def _get_json(self, url: str, **kwargs: Any) -> Any:
        resp = await self._request(url, **kwargs)
        return resp.json()

    async def _get_soup(self, url: str, **kwargs: Any) -> BeautifulSoup:
        resp = await self._request(url, **kwargs)
        return BeautifulSoup(resp.text, "lxml")

    @abstractmethod
    async def crawl_hot_list(self, category: str | None = None) -> list[TrendTopicSchema]:
        """Crawl hot/trending topics list."""
        ...

    async def crawl_video_detail(self, video_url: str) -> dict[str, Any]:
        """Crawl video metadata (optional override)."""
        raise NotImplementedError(f"{self.PLATFORM} does not support video detail crawl")

    def calculate_hot_value_growth(self, current: int, previous: int | None) -> float:
        """Calculate hot value growth rate."""
        if previous is None or previous == 0:
            return 0.0
        return (current - previous) / previous
