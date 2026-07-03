#!/usr/bin/env python3
"""
apply_frontend_only_deep_wiring_scan_patch.py

Purpose:
  Broadly scan the repo for the actual frontend screenshot/API wiring after the first
  runtime-bridge report failed to find call sites under apps/web/src / src.

What it changes:
  - Creates docs/FRONTEND_ONLY_DEEP_WIRING_REPORT.md
  - Creates docs/frontend_only_wiring_candidates.json

What it does NOT change:
  - No UI code is modified.
  - No backend code is modified.
  - No solver logic is modified.

Run from repo root:
  python apply_frontend_only_deep_wiring_scan_patch.py
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

ROOT = Path.cwd()

IGNORE_DIRS = {
    ".git",
    ".next",
    "node_modules",
    "dist",
    "build",
    "out",
    ".turbo",
    ".vercel",
    ".render",
    ".venv",
    "venv",
    "__pycache__",
    "coverage",
    ".pytest_cache",
}

TEXT_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".json", ".md", ".env", ".example", ".yml", ".yaml",
}

CODE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
}

PATTERNS = [
    ("fetch", re.compile(r"\bfetch\s*\("), 30),
    ("axios", re.compile(r"\baxios\b|\.post\s*\(|\.get\s*\("), 24),
    ("FormData", re.compile(r"\bFormData\s*\("), 26),
    ("XHR", re.compile(r"\bXMLHttpRequest\b"), 20),
    ("NEXT_PUBLIC", re.compile(r"\bNEXT_PUBLIC_[A-Z0-9_]+"), 22),
    ("API URL", re.compile(r"\b(API_URL|BACKEND_URL|BASE_URL|SERVER_URL)\b"), 24),
    ("process.env", re.compile(r"\bprocess\.env\."), 12),
    ("analyze/analyse", re.compile(r"\b(analy[sz]e|analyse|analysis|analyzer)\b", re.I), 14),
    ("capture", re.compile(r"\b(capture|screenshot|screenShot)\b", re.I), 14),
    ("solve/solver", re.compile(r"\b(solve|solver|solution|recommend|recommendation)\b", re.I), 14),
    ("upload/file", re.compile(r"\b(upload|dropzone|paste|clipboard|FileReader|Blob|File\b|image/png|image/jpeg)\b", re.I), 12),
    ("api route", re.compile(r"['\"]/api/[^'\"]+['\"]"), 20),
    ("backend host", re.compile(r"https?://[^'\"\s]+"), 8),
    ("worker", re.compile(r"\bWorker\s*\(|new URL\s*\("), 8),
]

HIGH_VALUE_CONTEXT = re.compile(
    r"(fetch|axios|FormData|NEXT_PUBLIC|API_URL|BACKEND_URL|capture|screenshot|paste|clipboard|analy[sz]e|analyse|solve|solver|recommend)",
    re.I,
)


@dataclass
class Candidate:
    path: str
    score: int
    line_count: int
    matched_patterns: list[str]
    snippets: list[str]


def is_ignored(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & IGNORE_DIRS)


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)

        # prune ignored dirs in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        if is_ignored(current):
            continue

        for filename in filenames:
            path = current / filename
            if is_ignored(path):
                continue
            if path.name.startswith(".") and path.suffix not in {".env"}:
                continue
            if path.suffix in TEXT_EXTENSIONS or ".env" in path.name:
                yield path


def safe_read(path: Path) -> str | None:
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def line_snippets(text: str, max_snippets: int = 10) -> list[str]:
    lines = text.splitlines()
    hits: list[int] = []
    for i, line in enumerate(lines, start=1):
        if HIGH_VALUE_CONTEXT.search(line):
            hits.append(i)

    snippets = []
    used: set[int] = set()
    for hit in hits[:max_snippets]:
        start = max(1, hit - 2)
        end = min(len(lines), hit + 2)
        block = []
        for line_no in range(start, end + 1):
            if line_no in used:
                continue
            used.add(line_no)
            block.append(f"{line_no:>5}: {lines[line_no - 1]}")
        if block:
            snippets.append("\n".join(block))
    return snippets


def score_file(path: Path, text: str) -> Candidate | None:
    score = 0
    matched: list[str] = []
    for name, regex, weight in PATTERNS:
        matches = regex.findall(text)
        if matches:
            count = len(matches)
            score += weight + min(count, 8) * 2
            matched.append(f"{name} x{count}")

    # UI files are more likely than docs/config.
    rel = path.relative_to(ROOT).as_posix()
    suffix = path.suffix.lower()

    if suffix in CODE_EXTENSIONS:
        score += 8
    if rel.startswith("apps/web/"):
        score += 16
    if "/app/" in rel or "/pages/" in rel or "/components/" in rel:
        score += 16
    if "/src/lib/frontend-solver/" in rel:
        # Avoid ranking our new scaffold as the target UI wiring.
        score -= 35
    if rel.endswith("FRONTEND_ONLY_WIRING_REPORT.md") or rel.endswith("FRONTEND_ONLY_DEEP_WIRING_REPORT.md"):
        score -= 80
    if "apply_frontend_only" in path.name:
        score -= 60

    if score < 18:
        return None

    snippets = line_snippets(text)
    if not snippets and suffix in CODE_EXTENSIONS:
        snippets = ["No compact high-value snippet found, but file matched broad patterns."]

    return Candidate(
        path=rel,
        score=score,
        line_count=len(text.splitlines()),
        matched_patterns=matched,
        snippets=snippets[:10],
    )


def write_report(candidates: list[Candidate]) -> None:
    docs = ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    json_path = docs / "frontend_only_wiring_candidates.json"
    json_path.write_text(
        json.dumps([asdict(c) for c in candidates], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# Frontend-only Deep Wiring Report")
    lines.append("")
    lines.append("Generated by `apply_frontend_only_deep_wiring_scan_patch.py`.")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("The first wiring report did not find frontend API/fetch call sites under `apps/web/src` / `src`.")
    lines.append("This report scans the broader repository while excluding heavy/generated folders.")
    lines.append("")
    lines.append("## Result")
    lines.append("")

    if not candidates:
        lines.append("No candidates found.")
        lines.append("")
        lines.append("Next manual command:")
        lines.append("")
        lines.append("```powershell")
        lines.append('rg "fetch|axios|FormData|NEXT_PUBLIC|analyze|analyse|capture|screenshot|paste|clipboard|solve|solver|recommend|backend|api" -n . -g "!node_modules" -g "!.next" -g "!dist" -g "!build"')
        lines.append("```")
    else:
        lines.append(f"Found **{len(candidates)}** candidate files.")
        lines.append("")
        lines.append("Open the highest-scoring UI component first. The target is the code that turns a pasted/uploaded screenshot into a backend/API call.")
        lines.append("")
        lines.append("## Ranked candidates")
        lines.append("")
        lines.append("| Rank | Score | File | Matched patterns |")
        lines.append("|---:|---:|---|---|")
        for idx, c in enumerate(candidates[:30], start=1):
            patterns = ", ".join(c.matched_patterns[:8]).replace("|", "\\|")
            lines.append(f"| {idx} | {c.score} | `{c.path}` | {patterns} |")

        lines.append("")
        lines.append("## Snippets")
        lines.append("")
        for idx, c in enumerate(candidates[:12], start=1):
            lines.append(f"### {idx}. `{c.path}` — score {c.score}")
            lines.append("")
            lines.append("Matched:")
            lines.append("")
            for m in c.matched_patterns:
                lines.append(f"- {m}")
            lines.append("")
            for sidx, snippet in enumerate(c.snippets[:5], start=1):
                lines.append(f"Snippet {sidx}:")
                lines.append("")
                lines.append("```ts")
                lines.append(snippet)
                lines.append("```")
                lines.append("")

    lines.append("")
    lines.append("## Target replacement")
    lines.append("")
    lines.append("When the UI currently uploads/sends the screenshot, the frontend-mode path should call:")
    lines.append("")
    lines.append("```ts")
    lines.append('import { solveScreenshotRuntime } from "@/lib/frontend-solver";')
    lines.append("")
    lines.append("const result = await solveScreenshotRuntime({")
    lines.append("  file,")
    lines.append("  debug: true,")
    lines.append("  preferCachedGeometry: true,")
    lines.append("});")
    lines.append("```")
    lines.append("")
    lines.append("Do not replace the whole component. Replace only the submit/analyze function.")
    lines.append("")
    lines.append("## JSON")
    lines.append("")
    lines.append(f"Machine-readable candidates written to `{json_path.relative_to(ROOT).as_posix()}`.")
    lines.append("")

    report_path = docs / "FRONTEND_ONLY_DEEP_WIRING_REPORT.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    candidates: list[Candidate] = []

    for path in iter_files(ROOT):
        text = safe_read(path)
        if text is None:
            continue
        candidate = score_file(path, text)
        if candidate:
            candidates.append(candidate)

    candidates.sort(key=lambda c: c.score, reverse=True)

    write_report(candidates)

    print("✅ Frontend-only deep wiring scan complete.")
    print("Created/updated:")
    print("  - docs/FRONTEND_ONLY_DEEP_WIRING_REPORT.md")
    print("  - docs/frontend_only_wiring_candidates.json")
    print("")
    if candidates:
        print("Top candidates:")
        for c in candidates[:10]:
            print(f"  {c.score:>4}  {c.path}")
    else:
        print("No candidates found. Run the manual rg command from the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
