#!/usr/bin/env python3
# Hotfix v3 for apply_recommendation_perf_patch_v2.py side effects.
#
# Problem fixed:
#   tests call response.json(), but cached API responses can contain gzip-compressed
#   bytes if the perf middleware caches output after GZipMiddleware touched it.
#   The cache then returns raw gzip bytes where tests/frontend expect JSON.
#
# Fix:
#   1) Remove automatic GZipMiddleware installation from perf_runtime.py.
#   2) Refuse to cache any response that already has Content-Encoding set.
#
# Run from repository root:
#   py repair_perf_patch_v3_disable_gzip.py

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
PERF_RUNTIME = ROOT / "services" / "api" / "grougal_solver" / "perf_runtime.py"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def remove_auto_gzip(text: str) -> str:
    # Replace combined import block from the original patch:
    #   from fastapi import Request
    #   from starlette.middleware.gzip import GZipMiddleware
    #   from starlette.responses import Response
    text = text.replace(
        "        from fastapi import Request\n"
        "        from starlette.middleware.gzip import GZipMiddleware\n"
        "        from starlette.responses import Response\n",
        "        from fastapi import Request\n"
        "        from starlette.responses import Response\n",
    )

    # Remove the try/pass app.add_middleware(GZipMiddleware, ...) block.
    text = re.sub(
        r"\n    try:\n\s+app\.add_middleware\(GZipMiddleware,\s*minimum_size=_env_int\(\"GROUGAL_GZIP_MIN_BYTES\",\s*512\)\)\n\s+except Exception:\n\s+pass\n",
        "\n    # GZip is intentionally not installed here. The response cache stores raw JSON bytes;\n"
        "    # caching compressed bytes breaks TestClient/response.json() on Windows/httpx stacks.\n",
        text,
        count=1,
    )

    # Defensive cleanup if a differently formatted leftover line exists.
    text = re.sub(r"^\s*from starlette\.middleware\.gzip import GZipMiddleware\s*\n", "", text, flags=re.M)
    text = re.sub(r"^\s*app\.add_middleware\(GZipMiddleware,.*\)\s*\n", "", text, flags=re.M)
    return text


def add_content_encoding_guard(text: str) -> str:
    if 'and not response.headers.get("content-encoding")' in text or "and not response.headers.get('content-encoding')" in text:
        return text

    old = (
        "            should_store = (\n"
        "                response.status_code == 200\n"
        "                and len(raw) <= _env_int(\"GROUGAL_RESPONSE_CACHE_MAX_RESPONSE_BYTES\", 8_000_000)\n"
        "                and (\"application/json\" in content_type.lower() or media_type == \"application/json\")\n"
        "            )\n"
    )
    new = (
        "            should_store = (\n"
        "                response.status_code == 200\n"
        "                and not response.headers.get(\"content-encoding\")\n"
        "                and len(raw) <= _env_int(\"GROUGAL_RESPONSE_CACHE_MAX_RESPONSE_BYTES\", 8_000_000)\n"
        "                and (\"application/json\" in content_type.lower() or media_type == \"application/json\")\n"
        "            )\n"
    )
    if old in text:
        return text.replace(old, new, 1)

    # More tolerant variant: insert guard right after status_code == 200 inside the should_store block.
    pattern = r"(should_store\s*=\s*\(\s*\n\s*response\.status_code\s*==\s*200\s*\n)"
    fixed, n = re.subn(pattern, r'\1                and not response.headers.get("content-encoding")\n', text, count=1)
    if n:
        return fixed

    # Last resort: do not alter unknown code silently.
    print("[warn] Could not find should_store block to add content-encoding guard.")
    return text


def run_check(cmd: list[str], cwd: Path) -> None:
    print(f"[check] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    except Exception as exc:
        print(f"[check-skip] {exc}")
        return
    if result.returncode == 0:
        print("[check-ok]")
    else:
        print("[check-failed]")
        if result.stdout:
            print(result.stdout[-4000:])
        if result.stderr:
            print(result.stderr[-4000:])


def main() -> int:
    if not PERF_RUNTIME.exists():
        print(f"[error] Missing {PERF_RUNTIME}")
        print("Run this from the repository root, not from services/api or apps/web.")
        return 2

    original = read_text(PERF_RUNTIME)
    text = remove_auto_gzip(original)
    text = add_content_encoding_guard(text)

    if text != original:
        write_text(PERF_RUNTIME, text)
        print(f"[fixed] Disabled perf-layer gzip and protected response cache: {PERF_RUNTIME}")
    else:
        print(f"[ok] No gzip/cache change needed: {PERF_RUNTIME}")

    run_check([sys.executable, "-m", "py_compile", str(PERF_RUNTIME)], ROOT)

    print("\nNext commands:")
    print(r'  cd "C:\Users\sinan\Documents\Grouga Dofus"')
    print(r'  cd services\api')
    print(r'  python -m pytest -q --basetemp "..\..\.pytest-tmp"')
    print(r'  cd ..\..\apps\web')
    print(r'  npm run typecheck')
    print(r'  npm run build')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
