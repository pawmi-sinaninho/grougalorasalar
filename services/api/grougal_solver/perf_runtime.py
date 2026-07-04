from __future__ import annotations

import asyncio
import hashlib
import os
import time
from collections import OrderedDict
from typing import Any

# Conservative CPU tuning for OpenCV/numpy workloads on small free hosts.
os.environ.setdefault("OMP_NUM_THREADS", os.getenv("GROUGAL_OMP_THREADS", "1"))
os.environ.setdefault("OPENBLAS_NUM_THREADS", os.getenv("GROUGAL_OPENBLAS_THREADS", "1"))
os.environ.setdefault("MKL_NUM_THREADS", os.getenv("GROUGAL_MKL_THREADS", "1"))
os.environ.setdefault("NUMEXPR_NUM_THREADS", os.getenv("GROUGAL_NUMEXPR_THREADS", "1"))

try:
    import cv2  # type: ignore
    cv2.setUseOptimized(True)
    cv2.setNumThreads(int(os.getenv("GROUGAL_CV_THREADS", "2")))
except Exception:
    pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


class _TTLResponseCache:
    def __init__(self, max_entries: int, ttl_seconds: int) -> None:
        self.max_entries = max(8, max_entries)
        self.ttl_seconds = max(1, ttl_seconds)
        self._items: OrderedDict[str, tuple[float, bytes, int, dict[str, str], str | None]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> tuple[bytes, int, dict[str, str], str | None] | None:
        now = time.monotonic()
        async with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            ts, body, status_code, headers, media_type = item
            if now - ts > self.ttl_seconds:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return body, status_code, dict(headers), media_type

    async def set(self, key: str, body: bytes, status_code: int, headers: dict[str, str], media_type: str | None) -> None:
        async with self._lock:
            self._items[key] = (time.monotonic(), body, status_code, dict(headers), media_type)
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)


_CACHE = _TTLResponseCache(
    max_entries=_env_int("GROUGAL_RESPONSE_CACHE_ENTRIES", 128),
    ttl_seconds=_env_int("GROUGAL_RESPONSE_CACHE_TTL_SECONDS", 120),
)
_LOCKS: dict[str, asyncio.Lock] = {}
_LOCKS_GUARD = asyncio.Lock()

_PATH_KEYWORDS = (
    "analyze", "analyse", "arena", "solve", "solver", "recommend",
    "recommendation", "action", "capture", "recognition",
)


def _headers_for_cache(headers: dict[str, str]) -> dict[str, str]:
    blocked = {"content-length", "content-encoding", "transfer-encoding", "connection", "keep-alive", "date", "server"}
    return {k: v for k, v in headers.items() if k.lower() not in blocked}


def _is_cacheable_request(method: str, path: str, content_length: str | None) -> bool:
    if not _env_bool("GROUGAL_RESPONSE_CACHE_ENABLED", True):
        return False
    if method.upper() != "POST":
        return False
    lowered = path.lower()
    if "/api/" not in lowered:
        return False
    if not any(k in lowered for k in _PATH_KEYWORDS):
        return False
    max_body = _env_int("GROUGAL_RESPONSE_CACHE_MAX_BODY_BYTES", 4_000_000)
    if content_length:
        try:
            if int(content_length) > max_body:
                return False
        except Exception:
            return False
    return True


def _cache_key(method: str, path: str, query: bytes, body: bytes) -> str:
    h = hashlib.blake2b(digest_size=20)
    h.update(method.upper().encode("utf-8"))
    h.update(b"\0")
    h.update(path.encode("utf-8", errors="ignore"))
    h.update(b"\0")
    h.update(query)
    h.update(b"\0")
    h.update(body)
    return h.hexdigest()


async def _singleflight_lock(key: str) -> asyncio.Lock:
    async with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _LOCKS[key] = lock
        return lock


def install_fastapi_perf(app: Any) -> Any:
    """Install conservative FastAPI speed guards."""
    if getattr(getattr(app, "state", object()), "_grougal_perf_installed", False):
        return app

    try:
        from fastapi import Request
        from starlette.responses import Response
    except Exception:
        return app

    # GZip is intentionally not installed here. The response cache stores raw JSON bytes;
    # caching compressed bytes breaks TestClient/response.json() on Windows/httpx stacks.

    @app.middleware("http")
    async def _grougal_perf_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        path = request.url.path
        content_length = request.headers.get("content-length")

        if not _is_cacheable_request(request.method, path, content_length):
            response = await call_next(request)
            response.headers["X-Grougal-Perf"] = f"BYPASS;dur_ms={(time.perf_counter() - start) * 1000:.1f}"
            return response

        body = await request.body()
        max_body = _env_int("GROUGAL_RESPONSE_CACHE_MAX_BODY_BYTES", 4_000_000)
        if len(body) > max_body:
            response = await call_next(request)
            response.headers["X-Grougal-Perf"] = f"BYPASS_BODY;dur_ms={(time.perf_counter() - start) * 1000:.1f}"
            return response

        key = _cache_key(request.method, path, request.url.query.encode("utf-8"), body)
        cached = await _CACHE.get(key)
        if cached is not None:
            raw, status_code, headers, media_type = cached
            out = Response(content=raw, status_code=status_code, headers=headers, media_type=media_type)
            out.headers["X-Grougal-Perf"] = "HIT"
            return out

        lock = await _singleflight_lock(key)
        async with lock:
            cached = await _CACHE.get(key)
            if cached is not None:
                raw, status_code, headers, media_type = cached
                out = Response(content=raw, status_code=status_code, headers=headers, media_type=media_type)
                out.headers["X-Grougal-Perf"] = "HIT_WAIT"
                return out

            async def receive():  # type: ignore[no-untyped-def]
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive
            response = await call_next(request)
            chunks = [chunk async for chunk in response.body_iterator]
            raw = b"".join(chunks)

            headers = _headers_for_cache(dict(response.headers))
            media_type = getattr(response, "media_type", None)
            content_type = response.headers.get("content-type", "")

            should_store = (
                response.status_code == 200
                and not response.headers.get("content-encoding")
                and len(raw) <= _env_int("GROUGAL_RESPONSE_CACHE_MAX_RESPONSE_BYTES", 8_000_000)
                and ("application/json" in content_type.lower() or media_type == "application/json")
            )
            if should_store:
                await _CACHE.set(key, raw, response.status_code, headers, media_type)

            out = Response(content=raw, status_code=response.status_code, headers=headers, media_type=media_type)
            out.headers["X-Grougal-Perf"] = f"MISS;dur_ms={(time.perf_counter() - start) * 1000:.1f}"
            return out

    try:
        app.state._grougal_perf_installed = True
    except Exception:
        pass
    return app
