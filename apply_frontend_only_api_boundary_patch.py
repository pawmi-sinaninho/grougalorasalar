#!/usr/bin/env python3
"""
GROUGALORASALAR SOLVER — Frontend-only API Boundary Patch

Purpose:
- Keep the existing UI component mostly untouched.
- Intercept the app-level API boundary in apps/web/lib/api.ts.
- In NEXT_PUBLIC_SOLVER_MODE=frontend, prevent normal create/upload/solve/delete calls
  from reaching the backend.
- Route screenshot upload to the browser-local frontend solver runtime.

This is a migration layer. It does not claim the vision/solver port is complete.
The local runtime will return its current result, including `not_implemented` until
real frontend detector/solver stages are wired.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path.cwd()
API_PATH = ROOT / "apps" / "web" / "lib" / "api.ts"
DOC_PATH = ROOT / "docs" / "FRONTEND_ONLY_API_BOUNDARY_PATCH.md"
ENV_LOCAL_PATH = ROOT / "apps" / "web" / ".env.local"

IMPORT_LINE = "import { solveScreenshotRuntime } from '../src/lib/frontend-solver';"
PATCH_MARKER = "// FRONTEND_ONLY_API_BOUNDARY_PATCH"

HELPER_BLOCK = r'''

// FRONTEND_ONLY_API_BOUNDARY_PATCH_START
// Browser-local migration layer. In frontend mode this file keeps the old UI API
// contract stable while avoiding backend calls in the normal screenshot flow.
type FrontendLocalEnvelope = Record<string, unknown> & {
  id?: string;
  analysisId?: string;
  accessToken?: string;
  token?: string;
  recognition?: unknown;
  recommendation?: unknown;
  performance?: Record<string, unknown>;
  frontendOnly?: boolean;
};

const FRONTEND_SOLVER_MODE = process.env.NEXT_PUBLIC_SOLVER_MODE ?? 'backend';
const frontendLocalAnalyses = new Map<string, FrontendLocalEnvelope>();
let frontendLocalSequence = 0;

function isFrontendOnlyApiMode() {
  return FRONTEND_SOLVER_MODE === 'frontend';
}

function newFrontendLocalId() {
  frontendLocalSequence += 1;
  return `frontend-local-${Date.now()}-${frontendLocalSequence}`;
}

function getBrowserNowMs() {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now();
  }
  return Date.now();
}

function getFrontendBlobLike(args: IArguments): Blob | File | null {
  for (const value of Array.from(args)) {
    if (typeof Blob !== 'undefined' && value instanceof Blob) return value;
    if (typeof File !== 'undefined' && value instanceof File) return value;
  }

  for (const value of Array.from(args)) {
    if (value && typeof value === 'object') {
      const candidate = value as { file?: unknown; blob?: unknown; image?: unknown };
      if (typeof Blob !== 'undefined' && candidate.file instanceof Blob) return candidate.file;
      if (typeof Blob !== 'undefined' && candidate.blob instanceof Blob) return candidate.blob;
      if (typeof Blob !== 'undefined' && candidate.image instanceof Blob) return candidate.image;
    }
  }

  return null;
}

function getFrontendAnalysisId(args: IArguments): string | null {
  for (const value of Array.from(args)) {
    if (typeof value === 'string' && value.length > 0) return value;
    if (value && typeof value === 'object') {
      const candidate = value as { analysisId?: unknown; id?: unknown };
      if (typeof candidate.analysisId === 'string') return candidate.analysisId;
      if (typeof candidate.id === 'string') return candidate.id;
    }
  }
  return null;
}

function makeFrontendLocalEnvelope(overrides: Partial<FrontendLocalEnvelope> = {}) {
  const id = typeof overrides.analysisId === 'string'
    ? overrides.analysisId
    : typeof overrides.id === 'string'
      ? overrides.id
      : newFrontendLocalId();

  const envelope: FrontendLocalEnvelope = {
    id,
    analysisId: id,
    accessToken: `local-${id}`,
    token: `local-${id}`,
    locale: 'fr',
    status: 'frontend_local',
    frontendOnly: true,
    image: null,
    recognition: null,
    recommendation: {
      status: 'blocked_missing_data',
      solverStatus: 'frontend_pipeline_pending',
      statusReasonCodes: ['frontend_pipeline_pending'],
      actions: [],
    },
    performance: {
      frontendOnly: true,
      apiBoundary: 'browser-local',
    },
    warnings: [
      'Frontend-only mode is active. Backend calls are bypassed at the web API boundary.',
    ],
    ...overrides,
  };

  frontendLocalAnalyses.set(id, envelope);
  return envelope;
}

function frontendResultToEnvelope(
  result: Awaited<ReturnType<typeof solveScreenshotRuntime>>,
  analysisId: string | null,
  startedAtMs: number,
  localImageUrl?: string,
) {
  const id = analysisId ?? newFrontendLocalId();
  const totalMs = Math.round((getBrowserNowMs() - startedAtMs) * 100) / 100;
  const status = result.ok ? 'provisional_solution' : 'blocked_missing_data';
  const reasonCode = result.ok ? 'frontend_local_result' : result.reason ?? 'frontend_local_failed';

  return makeFrontendLocalEnvelope({
    id,
    analysisId: id,
    status,
    image: localImageUrl
      ? {
          url: localImageUrl,
          originalUrl: localImageUrl,
          previewUrl: localImageUrl,
          annotatedUrl: null,
        }
      : null,
    recognition: {
      status: result.ok ? 'frontend_local_ready' : 'frontend_local_incomplete',
      confidence: result.confidence ?? 0,
      warnings: result.warnings ?? [],
      debug: result.debug ?? null,
    },
    recommendation: {
      status,
      solverStatus: result.ok ? 'frontend_local' : 'frontend_pipeline_pending',
      statusReasonCodes: [reasonCode],
      actions: result.actions ?? [],
    },
    performance: {
      frontendOnly: true,
      apiBoundary: 'browser-local',
      browserScreenshotToStateMs: totalMs,
      timings: result.timings ?? {},
    },
    debug: result.debug ?? null,
    warnings: [
      ...(result.warnings ?? []),
      ...(result.ok ? [] : ['Local frontend detector/solver stages are not fully ported yet.']),
    ],
  });
}

async function frontendOnlyCreateAnalysis(locale = 'fr') {
  return makeFrontendLocalEnvelope({ locale });
}

async function frontendOnlyUploadImage(args: IArguments) {
  const startedAtMs = getBrowserNowMs();
  const analysisId = getFrontendAnalysisId(args);
  const blob = getFrontendBlobLike(args);

  if (!blob) {
    return makeFrontendLocalEnvelope({
      analysisId: analysisId ?? undefined,
      status: 'invalid_screenshot',
      recommendation: {
        status: 'invalid_screenshot',
        solverStatus: 'frontend_missing_file',
        statusReasonCodes: ['frontend_missing_file'],
        actions: [],
      },
      warnings: ['Frontend-only upload was called without a File or Blob argument.'],
    });
  }

  const localImageUrl = typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function'
    ? URL.createObjectURL(blob)
    : undefined;

  const result = await solveScreenshotRuntime({
    file: typeof File !== 'undefined' && blob instanceof File ? blob : undefined,
    blob: !(typeof File !== 'undefined' && blob instanceof File) ? blob : undefined,
    debug: true,
    preferCachedGeometry: true,
  });

  return frontendResultToEnvelope(result, analysisId, startedAtMs, localImageUrl);
}

async function frontendOnlySolve(args: IArguments) {
  const analysisId = getFrontendAnalysisId(args);
  if (analysisId && frontendLocalAnalyses.has(analysisId)) {
    return frontendLocalAnalyses.get(analysisId);
  }
  return makeFrontendLocalEnvelope({
    analysisId: analysisId ?? undefined,
    recommendation: {
      status: 'blocked_missing_data',
      solverStatus: 'frontend_no_local_capture',
      statusReasonCodes: ['frontend_no_local_capture'],
      actions: [],
    },
    warnings: ['No local frontend capture exists for this analysis id. Paste/upload a screenshot again.'],
  });
}

async function frontendOnlyCommand(args: IArguments) {
  const analysisId = getFrontendAnalysisId(args);
  if (analysisId && frontendLocalAnalyses.has(analysisId)) {
    const envelope = frontendLocalAnalyses.get(analysisId)!;
    envelope.warnings = [
      ...((Array.isArray(envelope.warnings) ? envelope.warnings : []) as string[]),
      'Frontend-only command bridge is active. Manual correction commands still need a local reducer port.',
    ];
    return envelope;
  }
  return makeFrontendLocalEnvelope({
    analysisId: analysisId ?? undefined,
    warnings: ['Frontend-only command bridge received a command before a local capture existed.'],
  });
}

async function frontendOnlyDeleteAnalysis(args: IArguments) {
  const analysisId = getFrontendAnalysisId(args);
  if (analysisId) frontendLocalAnalyses.delete(analysisId);
  return { ok: true, frontendOnly: true, deleted: analysisId ?? null };
}
// FRONTEND_ONLY_API_BOUNDARY_PATCH_END
'''

DOC_TEXT = '''# Frontend-only API Boundary Patch

## What changed

This patch intercepts the existing `apps/web/lib/api.ts` boundary.

When `NEXT_PUBLIC_SOLVER_MODE=frontend`, the old UI functions stop calling the backend:

- `createAnalysis(...)` creates a browser-local analysis envelope.
- `uploadImage(...)` sends the pasted/uploaded `File`/`Blob` to `solveScreenshotRuntime(...)`.
- `solve(...)` returns the last browser-local result.
- `command(...)` is bridged as a safe no-op until a local correction reducer is ported.
- `deleteAnalysis(...)` clears the browser-local analysis map.

## Why this layer exists

The deep wiring scan identified `apps/web/app/page.tsx` as the strongest UI candidate and `apps/web/lib/api.ts` as the backend boundary. Patching the API boundary first is safer than rewriting the whole page component.

## Current limitation

This patch removes the backend from the normal route only at the web boundary. It does **not** magically port the detector/solver. The local runtime still returns its current result. If the pipeline still says `not_implemented`, the next patch must port the first real browser stage.

## Expected verification

Run:

```powershell
git diff -- apps/web/lib/api.ts docs/FRONTEND_ONLY_API_BOUNDARY_PATCH.md apps/web/.env.local
cd apps/web
npm run lint
npm run build
```

Then open the website, paste a screenshot and check the browser Network tab:

- no request should go to Render/backend during the normal upload path;
- the UI should return quickly;
- if the local pipeline is not ported yet, the result should explicitly say that instead of hanging for 15–20 seconds.
'''


@dataclass
class ReplacementResult:
    changed: bool
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def find_function_body_start(text: str, function_name: str) -> Optional[int]:
    pattern = re.compile(rf"export\s+async\s+function\s+{re.escape(function_name)}\s*\([^)]*\)\s*{{", re.MULTILINE)
    match = pattern.search(text)
    if not match:
      return None
    return match.end()


def insert_after_function_open(text: str, function_name: str, insertion: str) -> ReplacementResult:
    body_start = find_function_body_start(text, function_name)
    if body_start is None:
        return ReplacementResult(False, f"Function not found: {function_name}")

    lookahead = text[body_start:body_start + 500]
    if "isFrontendOnlyApiMode()" in lookahead:
        return ReplacementResult(False, f"Already patched: {function_name}")

    new_text = text[:body_start] + insertion + text[body_start:]
    return ReplacementResult(True, new_text)


def add_import(text: str) -> str:
    if IMPORT_LINE in text:
        return text
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and (lines[insert_at].startswith("import ") or lines[insert_at].strip() == ""):
        insert_at += 1
    lines.insert(insert_at, IMPORT_LINE)
    return "\n".join(lines) + "\n"


def add_helper_block(text: str) -> str:
    if "FRONTEND_ONLY_API_BOUNDARY_PATCH_START" in text:
        return text
    marker = re.search(r"export\s+const\s+API\s*=.*?;", text)
    if marker:
        return text[:marker.end()] + HELPER_BLOCK + text[marker.end():]

    first_export_fn = re.search(r"export\s+async\s+function\s+", text)
    if first_export_fn:
        return text[:first_export_fn.start()] + HELPER_BLOCK + "\n" + text[first_export_fn.start():]

    raise RuntimeError("Could not find insertion point for frontend-only helper block in apps/web/lib/api.ts")


def patch_api_ts() -> list[str]:
    if not API_PATH.exists():
        raise FileNotFoundError(f"Missing expected file: {API_PATH.relative_to(ROOT)}")

    text = read_text(API_PATH)
    original = text
    messages: list[str] = []

    text = add_import(text)
    text = add_helper_block(text)

    insertions = {
        "createAnalysis": "\n  if (isFrontendOnlyApiMode()) return await frontendOnlyCreateAnalysis(locale) as unknown as AnalysisEnvelope;\n",
        "uploadImage": "\n  if (isFrontendOnlyApiMode()) return await frontendOnlyUploadImage(arguments) as unknown as AnalysisEnvelope;\n",
        "solve": "\n  if (isFrontendOnlyApiMode()) return await frontendOnlySolve(arguments) as unknown as AnalysisEnvelope;\n",
        "command": "\n  if (isFrontendOnlyApiMode()) return await frontendOnlyCommand(arguments) as unknown as AnalysisEnvelope;\n",
        "deleteAnalysis": "\n  if (isFrontendOnlyApiMode()) return await frontendOnlyDeleteAnalysis(arguments);\n",
    }

    for fn_name, insertion in insertions.items():
        result = insert_after_function_open(text, fn_name, insertion)
        if result.changed:
            text = result.message
            messages.append(f"patched {fn_name}()")
        else:
            messages.append(result.message)

    if text != original:
        write_text(API_PATH, text)
    else:
        messages.append("no changes made to api.ts")

    return messages


def ensure_env_local() -> str:
    ENV_LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ENV_LOCAL_PATH.exists():
        text = read_text(ENV_LOCAL_PATH)
        if re.search(r"^\s*NEXT_PUBLIC_SOLVER_MODE\s*=", text, flags=re.MULTILINE):
            new_text = re.sub(
                r"^\s*NEXT_PUBLIC_SOLVER_MODE\s*=.*$",
                "NEXT_PUBLIC_SOLVER_MODE=frontend",
                text,
                flags=re.MULTILINE,
            )
            if new_text != text:
                write_text(ENV_LOCAL_PATH, new_text)
                return "updated apps/web/.env.local NEXT_PUBLIC_SOLVER_MODE=frontend"
            return "apps/web/.env.local already has NEXT_PUBLIC_SOLVER_MODE=frontend"
        write_text(ENV_LOCAL_PATH, text.rstrip() + "\nNEXT_PUBLIC_SOLVER_MODE=frontend\n")
        return "appended NEXT_PUBLIC_SOLVER_MODE=frontend to apps/web/.env.local"

    write_text(ENV_LOCAL_PATH, "NEXT_PUBLIC_SOLVER_MODE=frontend\n")
    return "created apps/web/.env.local with NEXT_PUBLIC_SOLVER_MODE=frontend"


def main() -> int:
    try:
        messages = patch_api_ts()
        env_message = ensure_env_local()
        write_text(DOC_PATH, DOC_TEXT)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Frontend-only API boundary patch applied.")
    for message in messages:
        print(f"- {message}")
    print(f"- {env_message}")
    print(f"- wrote {DOC_PATH.relative_to(ROOT)}")
    print("\nNext checks:")
    print("  git diff -- apps/web/lib/api.ts docs/FRONTEND_ONLY_API_BOUNDARY_PATCH.md apps/web/.env.local")
    print("  cd apps/web")
    print("  npm run lint")
    print("  npm run build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
