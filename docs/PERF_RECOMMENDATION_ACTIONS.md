# Recommendation Performance Patch v2

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
