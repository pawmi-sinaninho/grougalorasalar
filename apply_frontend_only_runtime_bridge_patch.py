#!/usr/bin/env python3
"""
Frontend-only runtime bridge patch for the Grougalorasalar Solver.

Purpose:
- Adds a safe runtime bridge that can run the browser-local pipeline through a Web Worker.
- Adds an optional legacy backend adapter for explicit backend/hybrid mode only.
- Adds paste/clipboard helpers for the target UX: Ctrl+V screenshot -> local solve.
- Scans the frontend source for existing backend fetch/API call sites and writes a wiring report.

This patch does NOT blindly rewrite UI files. It gives us a stable local solver entrypoint and tells us
exactly which existing submit/fetch file must be changed next.

Run from repository root:
    python apply_frontend_only_runtime_bridge_patch.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from textwrap import dedent

ROOT_MARKERS = [".git", "package.json", "apps", "backend", "pyproject.toml"]
TEXT_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        score = sum((candidate / marker).exists() for marker in ROOT_MARKERS)
        if score >= 1 and ((candidate / "apps").exists() or (candidate / "package.json").exists() or (candidate / ".git").exists()):
            return candidate
    return current


def find_web_root(repo_root: Path) -> Path:
    candidates = [
        repo_root / "apps" / "web",
        repo_root / "web",
        repo_root / "frontend",
        repo_root,
    ]
    for candidate in candidates:
        if (candidate / "package.json").exists():
            return candidate
    return repo_root / "apps" / "web"


def write_file(path: Path, content: str, *, overwrite: bool = True) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return f"SKIP existing {path}"
    normalized = dedent(content).lstrip("\n")
    path.write_text(normalized, encoding="utf-8")
    return f"WRITE {path}"


def patch_index_exports(index_path: Path) -> str:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    existing = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    exports = [
        'export * from "./backend-adapter";',
        'export * from "./debug-format";',
        'export * from "./paste";',
        'export * from "./runtime";',
        'export * from "./worker-client";',
    ]
    changed = False
    for line in exports:
        if line not in existing:
            if existing and not existing.endswith("\n"):
                existing += "\n"
            existing += line + "\n"
            changed = True
    index_path.write_text(existing, encoding="utf-8")
    return ("PATCH" if changed else "SKIP") + f" exports {index_path}"


def scan_fetch_candidates(src_root: Path) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    if not src_root.exists():
        return candidates

    keyword_re = re.compile(
        r"fetch\s*\(|axios\.|FormData\s*\(|NEXT_PUBLIC_.*(?:API|BACKEND|SOLVER)|/api/|analy[sz]e|capture|solve|solver",
        re.IGNORECASE,
    )

    ignored_dirs = {"node_modules", ".next", "dist", "build", "coverage", ".turbo"}

    for path in sorted(src_root.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_EXTENSIONS:
            continue
        if any(part in ignored_dirs for part in path.parts):
            continue
        # Ignore the files this patch creates; we want legacy/current call sites.
        if "frontend-solver" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lines = text.splitlines()
        hits: list[tuple[int, str]] = []
        score = 0
        for i, line in enumerate(lines, start=1):
            if keyword_re.search(line):
                hits.append((i, line.strip()))
                lower = line.lower()
                if "fetch" in lower or "axios" in lower:
                    score += 5
                if "formdata" in lower or "file" in lower or "blob" in lower:
                    score += 3
                if "analyze" in lower or "analyse" in lower or "capture" in lower or "solve" in lower or "solver" in lower:
                    score += 3
                if "next_public" in lower or "/api/" in lower:
                    score += 2

        if hits:
            candidates.append({
                "path": path,
                "score": score,
                "hits": hits[:12],
            })

    candidates.sort(key=lambda item: int(item["score"]), reverse=True)
    return candidates


def write_wiring_report(repo_root: Path, web_root: Path, candidates: list[dict[str, object]]) -> str:
    docs_root = repo_root / "docs"
    report_path = docs_root / "FRONTEND_ONLY_WIRING_REPORT.md"
    docs_root.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Frontend-only Wiring Report")
    lines.append("")
    lines.append("Generated by `apply_frontend_only_runtime_bridge_patch.py`.")
    lines.append("")
    lines.append("## What this report is for")
    lines.append("")
    lines.append("The runtime bridge is now available here:")
    lines.append("")
    lines.append("```ts")
    lines.append('import { solveScreenshotRuntime } from "@/lib/frontend-solver";')
    lines.append("```")
    lines.append("")
    lines.append("The remaining manual/app-specific step is to replace the current screenshot submit/API call with that function.")
    lines.append("")
    lines.append("## Candidate files")
    lines.append("")

    if not candidates:
        lines.append("No likely frontend API/fetch call sites were found under `apps/web/src` / `src`.")
        lines.append("")
        lines.append("Run this manually and paste the output into ChatGPT:")
        lines.append("")
        lines.append("```powershell")
        lines.append('rg "fetch|axios|FormData|NEXT_PUBLIC|analyze|analyse|capture|solve|solver" apps/web/src src -n')
        lines.append("```")
    else:
        for idx, item in enumerate(candidates[:15], start=1):
            path = Path(str(item["path"]))
            try:
                rel = path.relative_to(repo_root)
            except ValueError:
                rel = path
            lines.append(f"### {idx}. `{rel}`")
            lines.append("")
            lines.append(f"Score: `{item['score']}`")
            lines.append("")
            lines.append("```ts")
            for line_no, snippet in item["hits"]:  # type: ignore[index]
                lines.append(f"{line_no}: {snippet}")
            lines.append("```")
            lines.append("")

    lines.append("## Target replacement pattern")
    lines.append("")
    lines.append("Where the UI currently uploads the screenshot to the backend, the frontend-mode path should call:")
    lines.append("")
    lines.append("```ts")
    lines.append('import { solveScreenshotRuntime } from "@/lib/frontend-solver";')
    lines.append("")
    lines.append("const result = await solveScreenshotRuntime({")
    lines.append("  file, // or blob")
    lines.append("  debug: true,")
    lines.append("  preferCachedGeometry: true,")
    lines.append("});")
    lines.append("```")
    lines.append("")
    lines.append("For now, the local pipeline returns `not_implemented` until the real detector/solver stages are ported. This is intentional: the API dependency is being removed in controlled layers, not by pretending the solver is already ported.")
    lines.append("")
    lines.append("## Next exact action")
    lines.append("")
    lines.append("Open the highest-scoring candidate file above and replace only the submit/analyze function, not the whole component.")
    lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"WRITE {report_path}"


def main() -> int:
    repo_root = find_repo_root(Path.cwd())
    web_root = find_web_root(repo_root)
    src_root = web_root / "src"
    lib_root = src_root / "lib" / "frontend-solver"

    actions: list[str] = []

    if not lib_root.exists():
        print("ERROR: frontend-solver scaffold is missing.")
        print("Run apply_frontend_only_migration_scaffold.py first.")
        return 2

    actions.append(write_file(
        lib_root / "backend-adapter.ts",
        r'''
        import { createStageTimer } from "./timing";
        import type { FrontendCaptureInput, FrontendSolveResult } from "./types";

        export interface BackendSolveOptions {
          endpoint?: string;
          fieldName?: string;
          extraFormFields?: Record<string, string>;
          headers?: Record<string, string>;
        }

        async function inputToBlob(input: FrontendCaptureInput): Promise<Blob> {
          if (input.blob) return input.blob;
          if (input.file) return input.file;

          if (input.dataUrl) {
            const response = await fetch(input.dataUrl);
            return await response.blob();
          }

          if (input.imageBitmap) {
            const canvas = document.createElement("canvas");
            canvas.width = input.imageBitmap.width;
            canvas.height = input.imageBitmap.height;
            const ctx = canvas.getContext("2d");
            if (!ctx) throw new Error("Could not create canvas for backend fallback.");
            ctx.drawImage(input.imageBitmap, 0, 0);
            return await new Promise<Blob>((resolve, reject) => {
              canvas.toBlob((blob) => {
                if (blob) resolve(blob);
                else reject(new Error("Could not convert canvas to blob."));
              }, "image/png");
            });
          }

          throw new Error("No screenshot input was provided for backend fallback.");
        }

        function getDefaultBackendEndpoint(): string | undefined {
          return (
            process.env.NEXT_PUBLIC_SOLVER_API_URL ||
            process.env.NEXT_PUBLIC_API_URL ||
            process.env.NEXT_PUBLIC_BACKEND_URL ||
            undefined
          );
        }

        function normalizeBackendResponse(raw: unknown, timings_ms: FrontendSolveResult["timings_ms"]): FrontendSolveResult {
          const rawRecord = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
          const ok = Boolean(rawRecord.ok ?? rawRecord.success ?? rawRecord.solution ?? rawRecord.actions);

          return {
            ok,
            source: "backend",
            status: ok ? "solved" : "warning",
            message: typeof rawRecord.message === "string" ? rawRecord.message : undefined,
            actions: Array.isArray(rawRecord.actions) ? (rawRecord.actions as FrontendSolveResult["actions"]) : undefined,
            warnings: [
              {
                code: "backend_fallback_used",
                message: "Legacy backend fallback was used. This path is not the frontend-only target architecture.",
              },
            ],
            debug: {
              notes: ["Raw backend response is available in result.raw."],
            },
            timings_ms,
            raw,
          };
        }

        export async function solveScreenshotBackend(
          input: FrontendCaptureInput,
          options: BackendSolveOptions = {},
        ): Promise<FrontendSolveResult> {
          const timer = createStageTimer();
          const endpoint = options.endpoint ?? getDefaultBackendEndpoint();

          if (!endpoint) {
            return {
              ok: false,
              source: "backend",
              status: "rejected",
              message: "Backend endpoint is not configured. Set NEXT_PUBLIC_SOLVER_API_URL/NEXT_PUBLIC_API_URL/NEXT_PUBLIC_BACKEND_URL or stay in frontend mode.",
              warnings: [],
              debug: { reason: "unknown" },
              timings_ms: timer.finish(),
            };
          }

          try {
            const blob = await timer.measureAsync("backend_prepare_ms", () => inputToBlob(input));
            const formData = new FormData();
            formData.append(options.fieldName ?? "file", blob, "capture.png");

            for (const [key, value] of Object.entries(options.extraFormFields ?? {})) {
              formData.append(key, value);
            }

            const response = await timer.measureAsync("backend_fetch_ms", () =>
              fetch(endpoint, {
                method: "POST",
                body: formData,
                headers: options.headers,
              }),
            );

            const contentType = response.headers.get("content-type") ?? "";
            const raw = contentType.includes("application/json") ? await response.json() : await response.text();
            const timings = timer.finish();

            if (!response.ok) {
              return {
                ok: false,
                source: "backend",
                status: "rejected",
                message: `Backend request failed with HTTP ${response.status}.`,
                warnings: [
                  {
                    code: "backend_fallback_used",
                    message: "Legacy backend fallback failed.",
                  },
                ],
                debug: { reason: "unknown" },
                timings_ms: timings,
                raw,
              };
            }

            return normalizeBackendResponse(raw, timings);
          } catch (error) {
            return {
              ok: false,
              source: "backend",
              status: "rejected",
              message: error instanceof Error ? error.message : "Unknown backend fallback error.",
              warnings: [
                {
                  code: "backend_fallback_used",
                  message: "Legacy backend fallback threw an exception.",
                },
              ],
              debug: { reason: "unknown" },
              timings_ms: timer.finish(),
            };
          }
        }
        ''',
    ))

    actions.append(write_file(
        lib_root / "worker-client.ts",
        r'''
        import { analyzeAndSolveFrontend } from "./pipeline";
        import { createStageTimer } from "./timing";
        import type { FrontendCaptureInput, FrontendSolveResult, FrontendSolverWorkerRequest, FrontendSolverWorkerResponse } from "./types";

        export interface FrontendWorkerOptions {
          useWorker?: boolean;
          timeoutMs?: number;
        }

        function canUseWorker(): boolean {
          return typeof window !== "undefined" && typeof Worker !== "undefined";
        }

        export async function solveScreenshotFrontendWorker(
          input: FrontendCaptureInput,
          options: FrontendWorkerOptions = {},
        ): Promise<FrontendSolveResult> {
          const useWorker = options.useWorker ?? true;
          const timeoutMs = options.timeoutMs ?? 30_000;

          if (!useWorker || !canUseWorker()) {
            return await analyzeAndSolveFrontend(input);
          }

          const timer = createStageTimer();

          return await new Promise<FrontendSolveResult>((resolve) => {
            let settled = false;
            const worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });

            const cleanup = () => {
              try {
                worker.terminate();
              } catch {
                // no-op
              }
            };

            const timeout = window.setTimeout(() => {
              if (settled) return;
              settled = true;
              cleanup();
              resolve({
                ok: false,
                source: "frontend",
                status: "rejected",
                message: `Frontend worker timed out after ${timeoutMs} ms.`,
                warnings: [],
                debug: { reason: "solver_failed" },
                timings_ms: timer.finish(),
              });
            }, timeoutMs);

            worker.onmessage = (event: MessageEvent<FrontendSolverWorkerResponse>) => {
              if (settled) return;
              settled = true;
              window.clearTimeout(timeout);
              cleanup();

              const result = event.data.payload;
              resolve({
                ...result,
                timings_ms: {
                  ...result.timings_ms,
                  worker_roundtrip_ms: timer.finish().total_ms,
                },
              });
            };

            worker.onerror = (event) => {
              if (settled) return;
              settled = true;
              window.clearTimeout(timeout);
              cleanup();
              resolve({
                ok: false,
                source: "frontend",
                status: "rejected",
                message: event.message || "Frontend worker failed.",
                warnings: [],
                debug: { reason: "solver_failed" },
                timings_ms: timer.finish(),
              });
            };

            const request: FrontendSolverWorkerRequest = {
              type: "analyze-and-solve",
              payload: input,
            };
            worker.postMessage(request);
          });
        }
        ''',
    ))

    actions.append(write_file(
        lib_root / "runtime.ts",
        r'''
        import { getSolverRuntimeMode } from "./config";
        import { solveScreenshotBackend, type BackendSolveOptions } from "./backend-adapter";
        import { solveScreenshotFrontendWorker, type FrontendWorkerOptions } from "./worker-client";
        import type { FrontendCaptureInput, FrontendSolveResult, SolverRuntimeMode } from "./types";

        export interface SolveScreenshotRuntimeOptions {
          mode?: SolverRuntimeMode;
          worker?: FrontendWorkerOptions;
          backend?: BackendSolveOptions;
          allowBackendFallback?: boolean;
        }

        export async function solveScreenshotRuntime(
          input: FrontendCaptureInput,
          options: SolveScreenshotRuntimeOptions = {},
        ): Promise<FrontendSolveResult> {
          const mode = options.mode ?? getSolverRuntimeMode();

          if (mode === "frontend") {
            return await solveScreenshotFrontendWorker(input, options.worker);
          }

          if (mode === "backend") {
            return await solveScreenshotBackend(input, options.backend);
          }

          const frontendResult = await solveScreenshotFrontendWorker(input, options.worker);
          if (frontendResult.ok) return frontendResult;

          if (options.allowBackendFallback === false) {
            return frontendResult;
          }

          const backendResult = await solveScreenshotBackend(input, options.backend);
          return {
            ...backendResult,
            warnings: [
              ...frontendResult.warnings,
              ...backendResult.warnings,
              {
                code: "backend_fallback_used",
                message: "Hybrid mode used backend because frontend did not return a solved result.",
              },
            ],
            debug: {
              ...backendResult.debug,
              notes: [
                ...(frontendResult.debug.notes ?? []),
                ...(backendResult.debug.notes ?? []),
                `Frontend status before fallback: ${frontendResult.status}`,
              ],
            },
          };
        }
        ''',
    ))

    actions.append(write_file(
        lib_root / "paste.ts",
        r'''
        export function getFirstImageFileFromClipboardEvent(event: ClipboardEvent): File | null {
          const items = event.clipboardData?.items;
          if (!items) return null;

          for (const item of Array.from(items)) {
            if (!item.type.startsWith("image/")) continue;
            const file = item.getAsFile();
            if (file) return file;
          }

          return null;
        }

        export function getFirstImageFileFromDragEvent(event: DragEvent): File | null {
          const files = event.dataTransfer?.files;
          if (!files?.length) return null;

          for (const file of Array.from(files)) {
            if (file.type.startsWith("image/")) return file;
          }

          return null;
        }

        export function isImageFile(file: File | Blob | null | undefined): boolean {
          return Boolean(file?.type?.startsWith("image/"));
        }
        ''',
    ))

    actions.append(write_file(
        lib_root / "debug-format.ts",
        r'''
        import type { FrontendSolveResult } from "./types";

        export function formatTimings(result: FrontendSolveResult): string {
          const entries = Object.entries(result.timings_ms)
            .filter(([, value]) => typeof value === "number")
            .sort(([a], [b]) => (a === "total_ms" ? -1 : b === "total_ms" ? 1 : a.localeCompare(b)));

          return entries.map(([key, value]) => `${key}: ${value} ms`).join("\n");
        }

        export function formatSolveDebugSummary(result: FrontendSolveResult): string {
          const lines: string[] = [];
          lines.push(`source: ${result.source}`);
          lines.push(`status: ${result.status}`);
          lines.push(`ok: ${result.ok}`);
          if (result.message) lines.push(`message: ${result.message}`);
          if (result.debug.reason) lines.push(`reason: ${result.debug.reason}`);
          if (result.debug.image_size) {
            lines.push(`image: ${result.debug.image_size.width}x${result.debug.image_size.height}`);
          }
          if (result.warnings.length) {
            lines.push("warnings:");
            for (const warning of result.warnings) {
              lines.push(`- ${warning.code}: ${warning.message}`);
            }
          }
          lines.push("timings:");
          lines.push(formatTimings(result));
          return lines.join("\n");
        }
        ''',
    ))

    actions.append(patch_index_exports(lib_root / "index.ts"))

    candidates = scan_fetch_candidates(src_root)
    actions.append(write_wiring_report(repo_root, web_root, candidates))

    print("Frontend-only runtime bridge patch")
    print(f"Repo root: {repo_root}")
    print(f"Web root:  {web_root}")
    print("")
    for action in actions:
        print(action)

    print("")
    print("Highest-confidence existing API call candidates:")
    if not candidates:
        print("  none found")
    else:
        for item in candidates[:5]:
            path = Path(str(item["path"]))
            try:
                rel = path.relative_to(repo_root)
            except ValueError:
                rel = path
            print(f"  score={item['score']:>3}  {rel}")

    print("")
    print("Next commands:")
    print("  git diff --stat")
    print("  git diff -- docs/FRONTEND_ONLY_WIRING_REPORT.md")
    print("  npm run lint   # if available")
    print("  npm run build  # if available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
