from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


PERF_RUNTIME_PY = r'''from __future__ import annotations

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
        from starlette.middleware.gzip import GZipMiddleware
        from starlette.responses import Response
    except Exception:
        return app

    try:
        app.add_middleware(GZipMiddleware, minimum_size=_env_int("GROUGAL_GZIP_MIN_BYTES", 512))
    except Exception:
        pass

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
'''


SOLVER_PERF_PY = r'''from __future__ import annotations

import functools
import os
import threading
from collections import OrderedDict
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def _enabled() -> bool:
    return os.getenv("GROUGAL_SOLVER_MEMOIZE", "1").strip().lower() not in {"0", "false", "no", "off"}


def _short_repr(value: Any, max_chars: int) -> str | None:
    try:
        text = repr(value)
    except Exception:
        return None
    if len(text) > max_chars:
        return None
    return text


def _fingerprint_self(obj: Any, max_chars: int) -> str | None:
    try:
        data = getattr(obj, "__dict__", None)
        if not isinstance(data, dict):
            return f"{type(obj).__module__}.{type(obj).__qualname__}:{id(obj)}"

        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if key.startswith(("_cache", "_memo", "_perf", "_logger")):
                continue
            if callable(value):
                continue
            cleaned[key] = value

        text = repr(cleaned)
        if len(text) > max_chars:
            return None
        return f"{type(obj).__module__}.{type(obj).__qualname__}:{text}"
    except Exception:
        return None


def solver_memoize(max_entries: int = 4096, max_key_chars: int = 16000) -> Callable[[F], F]:
    """Memoizer for deterministic geometry helpers; bypasses unsafe/huge keys."""
    def decorator(func: F) -> F:
        cache: OrderedDict[str, Any] = OrderedDict()
        lock = threading.RLock()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _enabled():
                return func(*args, **kwargs)

            key_parts: list[str] = [func.__module__, func.__qualname__]
            remaining = max_key_chars
            try:
                for index, arg in enumerate(args):
                    if index == 0 and hasattr(arg, "__dict__"):
                        part = _fingerprint_self(arg, max(1000, remaining // 2))
                    else:
                        part = _short_repr(arg, max(1000, remaining // 2))
                    if part is None:
                        return func(*args, **kwargs)
                    remaining -= len(part)
                    if remaining <= 0:
                        return func(*args, **kwargs)
                    key_parts.append(part)

                if kwargs:
                    kw_part = _short_repr(sorted(kwargs.items()), max(1000, remaining))
                    if kw_part is None:
                        return func(*args, **kwargs)
                    key_parts.append(kw_part)
                key = "\x1f".join(key_parts)
            except Exception:
                return func(*args, **kwargs)

            with lock:
                if key in cache:
                    cache.move_to_end(key)
                    return cache[key]

            result = func(*args, **kwargs)

            with lock:
                cache[key] = result
                cache.move_to_end(key)
                while len(cache) > max_entries:
                    cache.popitem(last=False)
            return result

        return wrapper  # type: ignore[return-value]
    return decorator
'''


PERF_FETCH_TS = r'''type StoredResponse = {
  ts: number;
  status: number;
  statusText: string;
  headers: Array<[string, string]>;
  body: ArrayBuffer;
};

const DEFAULT_TTL_MS = 45_000;
const DEFAULT_MAX_ENTRIES = 64;

const responseCache = new Map<string, StoredResponse>();
const inflight = new Map<string, Promise<Response>>();

function envNumber(name: string, fallback: number): number {
  const raw = typeof process !== "undefined" && process.env ? process.env[name] : undefined;
  const parsed = raw ? Number(raw) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function isEnabled(): boolean {
  const raw = typeof process !== "undefined" && process.env ? process.env.NEXT_PUBLIC_GROUGAL_FETCH_CACHE : undefined;
  return raw == null || !["0", "false", "no", "off"].includes(raw.toLowerCase());
}

function shouldCache(input: RequestInfo | URL, init?: RequestInit): boolean {
  if (!isEnabled()) return false;
  const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
  if (method !== "POST") return false;
  if (!init?.body && !(input instanceof Request && input.body)) return false;

  const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  const lowered = url.toLowerCase();
  if (!lowered.includes("/api/")) return false;

  return ["analyze", "analyse", "arena", "solve", "solver", "recommend", "recommendation", "action", "capture", "recognition"]
    .some((keyword) => lowered.includes(keyword));
}

function prune(): void {
  const maxEntries = envNumber("NEXT_PUBLIC_GROUGAL_FETCH_CACHE_ENTRIES", DEFAULT_MAX_ENTRIES);
  while (responseCache.size > maxEntries) {
    const first = responseCache.keys().next().value;
    if (!first) break;
    responseCache.delete(first);
  }
}

async function bodyToString(body: BodyInit | null | undefined): Promise<string> {
  if (body == null) return "";
  if (typeof body === "string") return body;
  if (body instanceof URLSearchParams) return body.toString();
  if (body instanceof Blob) return await body.text();
  if (body instanceof FormData) {
    const pairs: string[] = [];
    body.forEach((value, key) => pairs.push(`${key}=${typeof value === "string" ? value : value.name}:${value.size}`));
    return pairs.sort().join("&");
  }
  if (body instanceof ArrayBuffer) return Array.from(new Uint8Array(body)).join(",");
  if (ArrayBuffer.isView(body)) return Array.from(new Uint8Array(body.buffer)).join(",");
  return String(body);
}

async function stableKey(input: RequestInfo | URL, init?: RequestInit): Promise<string> {
  const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
  const raw = `${method}\n${url}\n${await bodyToString(init?.body ?? null)}`;

  if (typeof crypto !== "undefined" && crypto.subtle) {
    const encoded = new TextEncoder().encode(raw);
    const digest = await crypto.subtle.digest("SHA-256", encoded);
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  let hash = 2166136261;
  for (let i = 0; i < raw.length; i += 1) {
    hash ^= raw.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return String(hash >>> 0);
}

function responseFromStored(entry: StoredResponse, cacheState: string): Response {
  const headers = new Headers(entry.headers);
  headers.set("X-Grougal-Frontend-Cache", cacheState);
  return new Response(entry.body.slice(0), { status: entry.status, statusText: entry.statusText, headers });
}

export async function perfFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  if (!shouldCache(input, init)) return fetch(input, init);

  const ttlMs = envNumber("NEXT_PUBLIC_GROUGAL_FETCH_CACHE_TTL_MS", DEFAULT_TTL_MS);
  const key = await stableKey(input, init);
  const now = Date.now();
  const cached = responseCache.get(key);
  if (cached && now - cached.ts <= ttlMs) return responseFromStored(cached, "HIT");

  const running = inflight.get(key);
  if (running) return (await running).clone();

  const request = fetch(input, init).then(async (response) => {
    if (!response.ok) return response;
    const body = await response.clone().arrayBuffer();
    responseCache.set(key, {
      ts: Date.now(),
      status: response.status,
      statusText: response.statusText,
      headers: Array.from(response.headers.entries()),
      body,
    });
    prune();
    return response;
  });

  inflight.set(key, request);
  try {
    return await request;
  } finally {
    inflight.delete(key);
  }
}
'''


FRONTEND_SOLVER_PERF_TS = r'''export type MemoizeOptions = { ttlMs?: number; maxEntries?: number; name?: string };
type Entry<T> = { ts: number; value: T };
const DEFAULT_TTL_MS = 30_000;
const DEFAULT_MAX_ENTRIES = 128;

function stableStringify(value: unknown): string {
  const seen = new WeakSet<object>();
  return JSON.stringify(value, (_key, item) => {
    if (item && typeof item === "object") {
      if (seen.has(item)) return "[Circular]";
      seen.add(item);
      if (!Array.isArray(item)) {
        return Object.keys(item as Record<string, unknown>).sort().reduce<Record<string, unknown>>((acc, key) => {
          acc[key] = (item as Record<string, unknown>)[key];
          return acc;
        }, {});
      }
    }
    return item;
  });
}

function makeKey(args: unknown[]): string | null {
  try {
    const raw = stableStringify(args);
    if (raw.length > 250_000) return null;
    let hash = 2166136261;
    for (let i = 0; i < raw.length; i += 1) {
      hash ^= raw.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return String(hash >>> 0);
  } catch {
    return null;
  }
}

function prune<T>(cache: Map<string, Entry<T>>, maxEntries: number): void {
  while (cache.size > maxEntries) {
    const first = cache.keys().next().value;
    if (!first) break;
    cache.delete(first);
  }
}

export function memoizeSync<Args extends unknown[], Result>(fn: (...args: Args) => Result, options: MemoizeOptions = {}): (...args: Args) => Result {
  const ttlMs = options.ttlMs ?? DEFAULT_TTL_MS;
  const maxEntries = options.maxEntries ?? DEFAULT_MAX_ENTRIES;
  const cache = new Map<string, Entry<Result>>();
  return (...args: Args): Result => {
    const key = makeKey(args);
    if (!key) return fn(...args);
    const now = Date.now();
    const cached = cache.get(key);
    if (cached && now - cached.ts <= ttlMs) return cached.value;
    const value = fn(...args);
    cache.set(key, { ts: now, value });
    prune(cache, maxEntries);
    return value;
  };
}

export function memoizeAsync<Args extends unknown[], Result>(fn: (...args: Args) => Promise<Result>, options: MemoizeOptions = {}): (...args: Args) => Promise<Result> {
  const ttlMs = options.ttlMs ?? DEFAULT_TTL_MS;
  const maxEntries = options.maxEntries ?? DEFAULT_MAX_ENTRIES;
  const cache = new Map<string, Entry<Result>>();
  const inflight = new Map<string, Promise<Result>>();
  return async (...args: Args): Promise<Result> => {
    const key = makeKey(args);
    if (!key) return fn(...args);
    const now = Date.now();
    const cached = cache.get(key);
    if (cached && now - cached.ts <= ttlMs) return cached.value;
    const running = inflight.get(key);
    if (running) return running;
    const promise = fn(...args).then((value) => {
      cache.set(key, { ts: Date.now(), value });
      prune(cache, maxEntries);
      return value;
    });
    inflight.set(key, promise);
    try {
      return await promise;
    } finally {
      inflight.delete(key);
    }
  };
}
'''


BENCHMARK_PY = r'''from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path
from urllib import request

API_URL = "http://127.0.0.1:8000/api/v1"
CANDIDATE_ENDPOINTS = ["/analysis", "/analyze", "/arena/analyze", "/recommend", "/recommendations", "/solve"]


def post_json(url: str, payload: dict) -> tuple[int, bytes, dict[str, str]]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=120) as res:
        return res.status, res.read(), dict(res.headers.items())


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python tools/benchmark_recommendation_perf.py payload.json [endpoint]")
        return 2
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    endpoint = sys.argv[2] if len(sys.argv) >= 3 else None
    endpoints = [endpoint] if endpoint else CANDIDATE_ENDPOINTS
    found = None
    for ep in endpoints:
        try:
            status, body, headers = post_json(f"{API_URL}{ep}", payload)
            if status == 200:
                found = ep
                print(f"Endpoint OK: {ep} | bytes={len(body)} | perf={headers.get('X-Grougal-Perf')}")
                break
        except Exception as exc:
            print(f"Skip {ep}: {exc}")
    if not found:
        print("No candidate endpoint worked. Pass the exact endpoint as second argument.")
        return 1
    durations = []
    for i in range(8):
        start = time.perf_counter()
        status, body, headers = post_json(f"{API_URL}{found}", payload)
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)
        print(f"{i + 1:02d}: {duration_ms:8.1f} ms | status={status} | bytes={len(body)} | {headers.get('X-Grougal-Perf')}")
    print(f"median_ms={statistics.median(durations):.1f}")
    print(f"min_ms={min(durations):.1f}")
    print(f"max_ms={max(durations):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


DOC_MD = r'''# Recommendation Performance Patch v2

This patch is conservative. It accelerates duplicated recommendation/analyse calls without changing spell rules or solver scoring.

## Applied ideas

1. Backend POST response cache for identical analyse/solve/recommend payloads.
2. Backend single-flight lock: identical concurrent requests are calculated once.
3. Backend GZip for JSON responses.
4. Backend timing/cache headers: `X-Grougal-Perf`.
5. Runtime CPU tuning for OpenCV/numpy workloads on small free hosts.
6. Solver helper memoizer for deterministic geometry helpers when safe.
7. Frontend `perfFetch()` cache for duplicate API calls.
8. Frontend single-flight for duplicate API calls.
9. Frontend solver memoization helper module for local-only solver functions.
10. Local benchmark helper.

## Switches

Backend:

```bash
GROUGAL_RESPONSE_CACHE_ENABLED=1
GROUGAL_RESPONSE_CACHE_TTL_SECONDS=120
GROUGAL_RESPONSE_CACHE_ENTRIES=128
GROUGAL_SOLVER_MEMOIZE=1
GROUGAL_CV_THREADS=2
```

Frontend:

```bash
NEXT_PUBLIC_GROUGAL_FETCH_CACHE=1
NEXT_PUBLIC_GROUGAL_FETCH_CACHE_TTL_MS=45000
NEXT_PUBLIC_GROUGAL_FETCH_CACHE_ENTRIES=64
```

## Verify

Browser dev tools response headers:

- `X-Grougal-Perf: MISS` = calculated normally and cached.
- `X-Grougal-Perf: HIT` = backend cache hit.
- `X-Grougal-Frontend-Cache: HIT` = browser duplicate-call cache hit.

Rollback switches:

```bash
GROUGAL_RESPONSE_CACHE_ENABLED=0
NEXT_PUBLIC_GROUGAL_FETCH_CACHE=0
GROUGAL_SOLVER_MEMOIZE=0
```
'''


def run(cmd: list[str], cwd: Path) -> str:
    try:
        completed = subprocess.run(cmd, cwd=str(cwd), check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return completed.stdout.strip()
    except Exception as exc:
        return f"ERROR running {' '.join(cmd)}: {exc}"


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for path in [current, *current.parents]:
        if (path / ".git").exists():
            return path
    return current


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def backup(path: Path, backup_root: Path, repo: Path) -> None:
    if not path.exists():
        return
    rel = path.relative_to(repo)
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)


def add_or_replace_file(path: Path, content: str, report: list[str], backup_root: Path, repo: Path) -> None:
    old = read_text(path) if path.exists() else None
    if old == content:
        report.append(f"unchanged: {path.relative_to(repo)}")
        return
    backup(path, backup_root, repo)
    write_text(path, content)
    report.append(f"wrote: {path.relative_to(repo)}")


def add_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text
    lines = text.splitlines()
    idx = 0
    if lines and lines[0].startswith("#!"):
        idx = 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx < len(lines) and (lines[idx].startswith(chr(34) * 3) or lines[idx].startswith(chr(39) * 3)):
        quote = lines[idx][:3]
        idx += 1
        while idx < len(lines) and quote not in lines[idx]:
            idx += 1
        if idx < len(lines):
            idx += 1
    while idx < len(lines) and (
        lines[idx].startswith("from __future__ import")
        or lines[idx].startswith("import ")
        or lines[idx].startswith("from ")
        or not lines[idx].strip()
    ):
        idx += 1
    lines.insert(idx, import_line)
    return "\n".join(lines) + "\n"


def patch_fastapi_app(path: Path, report: list[str], backup_root: Path, repo: Path) -> None:
    text = read_text(path)
    if "install_fastapi_perf(app)" in text:
        report.append(f"already patched: {path.relative_to(repo)}")
        return
    if "FastAPI" not in text or not re.search(r"^\s*app\s*=\s*FastAPI\s*\(", text, re.M):
        report.append(f"skipped FastAPI patch, no app = FastAPI(...): {path.relative_to(repo)}")
        return
    text = add_import(text, "from .perf_runtime import install_fastapi_perf")
    lines = text.splitlines()
    inserted = False
    for i, line in enumerate(lines):
        if re.search(r"^\s*app\s*=\s*FastAPI\s*\(", line):
            depth = line.count("(") - line.count(")")
            j = i
            while depth > 0 and j + 1 < len(lines):
                j += 1
                depth += lines[j].count("(") - lines[j].count(")")
            indent = re.match(r"^(\s*)", line).group(1)
            lines.insert(j + 1, f"{indent}install_fastapi_perf(app)")
            inserted = True
            break
    if not inserted:
        report.append(f"skipped FastAPI call insertion: {path.relative_to(repo)}")
        return
    backup(path, backup_root, repo)
    write_text(path, "\n".join(lines) + "\n")
    report.append(f"patched FastAPI perf middleware: {path.relative_to(repo)}")


def decorate_functions(path: Path, import_line: str, decorator_by_name: dict[str, str], report: list[str], backup_root: Path, repo: Path) -> None:
    if not path.exists():
        return
    text = read_text(path)
    original = text
    text = add_import(text, import_line)
    lines = text.splitlines()
    patched: list[str] = []
    i = 0
    while i < len(lines):
        match = re.match(r"^(\s*)def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", lines[i])
        if not match:
            i += 1
            continue
        indent, name = match.group(1), match.group(2)
        decorator = decorator_by_name.get(name)
        if not decorator:
            i += 1
            continue
        prev_window = "\n".join(lines[max(0, i - 4):i])
        if "solver_memoize" in prev_window:
            i += 1
            continue
        lines.insert(i, f"{indent}{decorator}")
        patched.append(name)
        i += 2
    new_text = "\n".join(lines) + "\n"
    if new_text == original:
        report.append(f"unchanged decorators: {path.relative_to(repo)}")
        return
    backup(path, backup_root, repo)
    write_text(path, new_text)
    report.append(f"decorated {path.relative_to(repo)}: {', '.join(patched) if patched else 'import only'}")


def patch_frontend_api(path: Path, report: list[str], backup_root: Path, repo: Path) -> None:
    if not path.exists():
        return
    text = read_text(path)
    if "perfFetch" in text:
        report.append(f"already patched frontend api: {path.relative_to(repo)}")
        return
    if "fetch(" not in text:
        report.append(f"skipped frontend api, no fetch(): {path.relative_to(repo)}")
        return
    lines = text.splitlines()
    insert_idx = 0
    while insert_idx < len(lines) and (lines[insert_idx].startswith("import ") or lines[insert_idx].strip() == ""):
        insert_idx += 1
    lines.insert(insert_idx, 'import { perfFetch } from "./perfFetch";')
    text = "\n".join(lines) + "\n"
    text = re.sub(r"(?<![\w.])fetch\s*\(", "perfFetch(", text)
    backup(path, backup_root, repo)
    write_text(path, text)
    report.append(f"patched frontend API fetch cache: {path.relative_to(repo)}")


def patch_frontend_solver_index(index_path: Path, report: list[str], backup_root: Path, repo: Path) -> None:
    if not index_path.exists():
        return
    text = read_text(index_path)
    line = 'export * from "./perf";'
    if line in text:
        report.append(f"already exports frontend perf helpers: {index_path.relative_to(repo)}")
        return
    backup(index_path, backup_root, repo)
    write_text(index_path, text.rstrip() + "\n" + line + "\n")
    report.append(f"exported frontend perf helpers: {index_path.relative_to(repo)}")


def main() -> int:
    repo = find_repo_root(Path.cwd())
    report: list[str] = [f"repo: {repo}"]
    backup_root = repo / ".perf_patch_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")

    api_pkg = repo / "services" / "api" / "grougal_solver"
    web_root = repo / "apps" / "web"

    if not api_pkg.exists():
        report.append("WARNING: services/api/grougal_solver not found. Backend patches skipped.")
    else:
        add_or_replace_file(api_pkg / "perf_runtime.py", PERF_RUNTIME_PY, report, backup_root, repo)
        add_or_replace_file(api_pkg / "solver_perf.py", SOLVER_PERF_PY, report, backup_root, repo)

        app_candidates = [api_pkg / "app.py", api_pkg / "main.py", repo / "services" / "api" / "app.py", repo / "services" / "api" / "main.py"]
        app_candidates += [p for p in api_pkg.rglob("*.py") if p.name not in {"perf_runtime.py", "solver_perf.py"} and "FastAPI" in read_text(p)]
        seen_apps: set[Path] = set()
        for app_path in app_candidates:
            if app_path.exists() and app_path not in seen_apps:
                seen_apps.add(app_path)
                patch_fastapi_app(app_path, report, backup_root, repo)

        solver_decorators = {
            "_apply_movement_constraints": "@solver_memoize(max_entries=8192)",
            "_cells_between": "@solver_memoize(max_entries=8192)",
            "cells_between": "@solver_memoize(max_entries=8192)",
            "_line_clear": "@solver_memoize(max_entries=8192)",
            "_path_clear": "@solver_memoize(max_entries=8192)",
            "_has_line_of_sight": "@solver_memoize(max_entries=8192)",
            "_movement_clear": "@solver_memoize(max_entries=8192)",
            "_project_pattern": "@solver_memoize(max_entries=4096)",
            "_spell_targets": "@solver_memoize(max_entries=2048)",
            "_generate_spell_targets": "@solver_memoize(max_entries=2048)",
        }
        decorate_functions(api_pkg / "solver.py", "from .solver_perf import solver_memoize", solver_decorators, report, backup_root, repo)

        recognition_decorators = {
            "_fingerprint_image": "@solver_memoize(max_entries=256, max_key_chars=60000)",
            "fingerprint_image": "@solver_memoize(max_entries=256, max_key_chars=60000)",
            "_compute_fingerprint": "@solver_memoize(max_entries=256, max_key_chars=60000)",
            "compute_fingerprint": "@solver_memoize(max_entries=256, max_key_chars=60000)",
            "_classify_glyph": "@solver_memoize(max_entries=512, max_key_chars=60000)",
            "classify_glyph": "@solver_memoize(max_entries=512, max_key_chars=60000)",
            "_match_template": "@solver_memoize(max_entries=512, max_key_chars=60000)",
            "match_template": "@solver_memoize(max_entries=512, max_key_chars=60000)",
            "_scan_template": "@solver_memoize(max_entries=256, max_key_chars=60000)",
            "scan_template": "@solver_memoize(max_entries=256, max_key_chars=60000)",
        }
        decorate_functions(api_pkg / "fast_recognition.py", "from .solver_perf import solver_memoize", recognition_decorators, report, backup_root, repo)

    if not web_root.exists():
        report.append("WARNING: apps/web not found. Frontend patches skipped.")
    else:
        lib_dir = web_root / "lib" if (web_root / "lib").exists() else web_root / "src" / "lib"
        add_or_replace_file(lib_dir / "perfFetch.ts", PERF_FETCH_TS, report, backup_root, repo)
        for api_path in [web_root / "lib" / "api.ts", web_root / "src" / "lib" / "api.ts"]:
            patch_frontend_api(api_path, report, backup_root, repo)
        fs_dir = web_root / "src" / "lib" / "frontend-solver"
        if fs_dir.exists():
            add_or_replace_file(fs_dir / "perf.ts", FRONTEND_SOLVER_PERF_TS, report, backup_root, repo)
            patch_frontend_solver_index(fs_dir / "index.ts", report, backup_root, repo)
        else:
            report.append("frontend-solver directory not found; local solver perf helpers skipped.")

    add_or_replace_file(repo / "tools" / "benchmark_recommendation_perf.py", BENCHMARK_PY, report, backup_root, repo)
    add_or_replace_file(repo / "docs" / "PERF_RECOMMENDATION_ACTIONS.md", DOC_MD, report, backup_root, repo)

    report.append("")
    report.append("git status --short:")
    report.append(run(["git", "status", "--short"], repo))
    report.append("")
    report.append("git diff --stat:")
    report.append(run(["git", "diff", "--stat"], repo))

    report_text = "\n".join(report) + "\n"
    write_text(repo / "PERF_PATCH_REPORT.md", report_text)
    print(report_text)
    print("Report written to PERF_PATCH_REPORT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
