# bot/utils/web_client.py
"""
Проверки web-сервиса для бота.

Идея:
- bot НЕ должен падать, если web недоступен
- проверки health/ready должны быть быстрыми и с таймаутами
- добавляем небольшой TTL-кэш, чтобы не долбить web на каждую команду
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple

import aiohttp


@dataclass(frozen=True)
class WebCheckResult:
    ok: bool
    status: Optional[int]
    error: Optional[str]
    duration_ms: int
    request_id: str


class WebClient:
    def __init__(self, base_url: str, timeout_s: float = 1.5, cache_ttl_s: float = 3.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.cache_ttl_s = cache_ttl_s

        # cache: (ts, health_res, ready_res)
        self._cache: Optional[Tuple[float, WebCheckResult, WebCheckResult]] = None
        self._lock = asyncio.Lock()

    async def _get(self, path: str, request_id: str) -> WebCheckResult:
        url = f"{self.base_url}{path}"
        t0 = time.perf_counter()
        timeout = aiohttp.ClientTimeout(total=self.timeout_s)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={"X-Request-ID": request_id}) as r:
                    # Нам важен сам статус. Тело можно не читать полностью.
                    await r.release()
                    ok = 200 <= r.status < 300
                    dt = int((time.perf_counter() - t0) * 1000)
                    return WebCheckResult(ok=ok, status=r.status, error=None, duration_ms=dt, request_id=request_id)
        except Exception as e:
            dt = int((time.perf_counter() - t0) * 1000)
            return WebCheckResult(ok=False, status=None, error=str(e), duration_ms=dt, request_id=request_id)

    async def check_health_ready(self, force: bool = False) -> Tuple[WebCheckResult, WebCheckResult]:
        """
        Возвращает (health, ready). Использует TTL-кэш.
        """
        now = time.time()

        async with self._lock:
            if not force and self._cache:
                ts, health, ready = self._cache
                if (now - ts) <= self.cache_ttl_s:
                    return health, ready

            request_id = str(uuid.uuid4())
            health_task = self._get("/health", request_id=request_id)
            ready_task = self._get("/ready", request_id=request_id)
            health, ready = await asyncio.gather(health_task, ready_task)

            self._cache = (now, health, ready)
            return health, ready
