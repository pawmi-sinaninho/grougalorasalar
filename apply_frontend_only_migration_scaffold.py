#!/usr/bin/env python3
"""
Safe scaffold patch for migrating the Grougalorasalar Solver to a frontend-only architecture.

What it does:
- Creates documentation that makes frontend-only the official target architecture.
- Adds TypeScript scaffolding for a browser-local capture/solver pipeline.
- Adds a Web Worker contract so heavy image processing can run off the UI thread.
- Adds a central runtime mode flag: NEXT_PUBLIC_SOLVER_MODE=frontend|backend|hybrid.
- Does NOT delete or rewrite existing backend/API logic.
- Does NOT claim the solver is already fully ported.

Run from repository root:
    python apply_frontend_only_migration_scaffold.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from textwrap import dedent


ROOT_MARKERS = [".git", "package.json", "apps", "backend", "pyproject.toml"]


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
    # Fall back to the usual monorepo path, but create it if needed.
    return repo_root / "apps" / "web"


def write_file(path: Path, content: str, *, overwrite: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return f"SKIP existing {path}"
    normalized = dedent(content).lstrip("\n")
    path.write_text(normalized, encoding="utf-8")
    return f"WRITE {path}"


def append_once(path: Path, marker: str, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in existing:
        return f"SKIP marker already present in {path}"
    with path.open("a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write("\n" + dedent(content).strip() + "\n")
    return f"APPEND {path}"


def main() -> int:
    repo_root = find_repo_root(Path.cwd())
    web_root = find_web_root(repo_root)
    src_root = web_root / "src"
    lib_root = src_root / "lib" / "frontend-solver"
    docs_root = repo_root / "docs"

    actions: list[str] = []

    actions.append(write_file(
        docs_root / "FRONTEND_ONLY_MIGRATION.md",
        """
        # GROUGALORASALAR SOLVER — Frontend-only Migration

        ## Decision

        The official target architecture is now **frontend-only**:

        ```text
        screenshot paste/upload
        -> browser canvas/image pipeline
        -> browser-local arena/cell/glyph/pillar/player detection
        -> browser-local solver
        -> result UI
        ```

        The backend is no longer part of the product-critical path. It may remain temporarily as a compatibility fallback while the browser pipeline is being ported.

        ## Why this change exists

        Current production behaviour is not acceptable for the intended end-user workflow:

        - screenshots can take roughly 15–20 seconds to process in deployed backend mode;
        - backend cold starts / free-tier CPU / upload roundtrips make latency unstable;
        - "Capture incomplete" failures are too expensive because each retry costs another backend request;
        - the product goal is: **Ctrl+V screenshot -> solution with minimal delay**.

        ## Non-negotiable UX target

        ```text
        User pastes screenshot
        -> UI remains responsive
        -> local analysis starts immediately
        -> solution or actionable warning is displayed
        ```

        ## Migration phases

        ### Phase 1 — Add frontend runtime shell

        - Create a frontend pipeline contract.
        - Add a Web Worker boundary for heavy work.
        - Add timing and debug objects to every local run.
        - Keep backend path available only as fallback.

        ### Phase 2 — Port deterministic solver logic

        - Move action simulation, spell rules, charge handling and scoring to TypeScript.
        - Add parity tests against existing known fixtures.
        - Keep all confirmed mechanics in one shared rules module.

        ### Phase 3 — Port image extraction

        Preferred route:

        - avoid generic OCR/ML;
        - use canvas + cached arena geometry + known cell centres;
        - sample expected cell regions directly;
        - detect glyphs/pillars/player with deterministic colour/shape heuristics where possible;
        - keep confidence/warnings instead of hard rejecting minor uncertainty.

        Heavy library route if needed:

        - OpenCV.js or WASM module, loaded client-side;
        - executed inside a Web Worker;
        - lazy-loaded only when screenshot analysis starts.

        ### Phase 4 — Remove backend dependency from UI

        - `NEXT_PUBLIC_SOLVER_MODE=frontend` becomes default.
        - API calls are disabled by default.
        - Backend deployment becomes optional or deleted.

        ## Runtime modes

        ```text
        frontend = only browser-local processing
        backend  = legacy API mode
        hybrid   = try frontend first, backend only as explicit fallback
        ```

        ## Acceptance criteria

        A migration step is not done unless:

        - the UI can process a pasted screenshot without calling Render/backend;
        - the browser main thread does not freeze during analysis;
        - every local run returns timings;
        - every uncertain capture returns structured warnings/debug info;
        - known fixture screenshots produce the same or better decisions than backend mode.
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "types.ts",
        """
        export type SolverRuntimeMode = "frontend" | "backend" | "hybrid";

        export type CaptureRejectReason =
          | "arena_not_found"
          | "grid_coverage_too_low"
          | "player_not_found"
          | "glyph_detection_low_confidence"
          | "pillar_detection_low_confidence"
          | "solver_failed"
          | "frontend_not_implemented"
          | "unknown";

        export type CaptureWarningCode =
          | "grid_partial"
          | "glyph_uncertain"
          | "pillar_uncertain"
          | "player_uncertain"
          | "used_cached_geometry"
          | "cache_invalidated"
          | "backend_fallback_used";

        export interface PipelineTimingsMs {
          total_ms: number;
          image_decode_ms?: number;
          image_resize_ms?: number;
          arena_detect_ms?: number;
          grid_detect_ms?: number;
          glyph_detect_ms?: number;
          pillar_detect_ms?: number;
          player_detect_ms?: number;
          solver_ms?: number;
          worker_roundtrip_ms?: number;
          [stage: string]: number | undefined;
        }

        export interface CaptureWarning {
          code: CaptureWarningCode;
          message: string;
          confidence?: number;
        }

        export interface CaptureDebug {
          reason?: CaptureRejectReason;
          image_size?: { width: number; height: number };
          arena_bbox?: { x: number; y: number; width: number; height: number };
          cells_expected?: number;
          cells_detected?: number;
          white_glyphs_detected?: number;
          black_glyphs_detected?: number;
          pillars_detected?: number;
          player_detected?: boolean;
          confidence?: number;
          overlay_data_url?: string;
          notes?: string[];
        }

        export interface FrontendCaptureInput {
          file?: File;
          blob?: Blob;
          imageBitmap?: ImageBitmap;
          dataUrl?: string;
          debug?: boolean;
          preferCachedGeometry?: boolean;
        }

        export interface SolverActionStep {
          label: string;
          spell?: string;
          from?: string;
          to?: string;
          apCost?: number;
          note?: string;
        }

        export interface FrontendSolveResult {
          ok: boolean;
          source: "frontend" | "backend";
          status: "solved" | "warning" | "rejected" | "not_implemented";
          message?: string;
          actions?: SolverActionStep[];
          warnings: CaptureWarning[];
          debug: CaptureDebug;
          timings_ms: PipelineTimingsMs;
          raw?: unknown;
        }

        export interface FrontendSolverWorkerRequest {
          type: "analyze-and-solve";
          payload: FrontendCaptureInput;
        }

        export interface FrontendSolverWorkerResponse {
          type: "result" | "error";
          payload: FrontendSolveResult;
        }
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "config.ts",
        """
        import type { SolverRuntimeMode } from "./types";

        export const FRONTEND_SOLVER_CONFIG = {
          cellsExpected: 338,
          hardRejectGridCoverage: 0.85,
          warningGridCoverage: 0.95,
          maxImageDimensionDeltaForCache: 0.02,
          defaultDebug: false,
        } as const;

        export function getSolverRuntimeMode(): SolverRuntimeMode {
          const raw = process.env.NEXT_PUBLIC_SOLVER_MODE?.toLowerCase();
          if (raw === "frontend" || raw === "backend" || raw === "hybrid") return raw;
          return "frontend";
        }
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "timing.ts",
        """
        import type { PipelineTimingsMs } from "./types";

        function nowMs(): number {
          if (typeof performance !== "undefined" && typeof performance.now === "function") {
            return performance.now();
          }
          return Date.now();
        }

        export interface StageTimer {
          measure<T>(stage: keyof PipelineTimingsMs | string, fn: () => T): T;
          measureAsync<T>(stage: keyof PipelineTimingsMs | string, fn: () => Promise<T>): Promise<T>;
          finish(): PipelineTimingsMs;
        }

        export function createStageTimer(): StageTimer {
          const startedAt = nowMs();
          const timings: PipelineTimingsMs = { total_ms: 0 };

          return {
            measure<T>(stage: keyof PipelineTimingsMs | string, fn: () => T): T {
              const t0 = nowMs();
              try {
                return fn();
              } finally {
                timings[stage] = Math.round((nowMs() - t0) * 100) / 100;
              }
            },

            async measureAsync<T>(stage: keyof PipelineTimingsMs | string, fn: () => Promise<T>): Promise<T> {
              const t0 = nowMs();
              try {
                return await fn();
              } finally {
                timings[stage] = Math.round((nowMs() - t0) * 100) / 100;
              }
            },

            finish(): PipelineTimingsMs {
              timings.total_ms = Math.round((nowMs() - startedAt) * 100) / 100;
              return timings;
            },
          };
        }
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "image.ts",
        """
        import type { FrontendCaptureInput } from "./types";

        export interface CanvasImage {
          canvas: HTMLCanvasElement | OffscreenCanvas;
          ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D;
          width: number;
          height: number;
        }

        export async function inputToImageBitmap(input: FrontendCaptureInput): Promise<ImageBitmap> {
          if (input.imageBitmap) return input.imageBitmap;

          if (input.blob) {
            return await createImageBitmap(input.blob);
          }

          if (input.file) {
            return await createImageBitmap(input.file);
          }

          if (input.dataUrl) {
            const response = await fetch(input.dataUrl);
            const blob = await response.blob();
            return await createImageBitmap(blob);
          }

          throw new Error("No screenshot input was provided.");
        }

        export function imageBitmapToCanvas(bitmap: ImageBitmap): CanvasImage {
          const hasOffscreen = typeof OffscreenCanvas !== "undefined";
          const canvas = hasOffscreen
            ? new OffscreenCanvas(bitmap.width, bitmap.height)
            : Object.assign(document.createElement("canvas"), { width: bitmap.width, height: bitmap.height });

          const ctx = canvas.getContext("2d", { willReadFrequently: true });
          if (!ctx) throw new Error("Could not create 2D canvas context.");
          ctx.drawImage(bitmap, 0, 0);

          return { canvas, ctx, width: bitmap.width, height: bitmap.height };
        }

        export function getImageData(canvasImage: CanvasImage): ImageData {
          return canvasImage.ctx.getImageData(0, 0, canvasImage.width, canvasImage.height);
        }
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "geometry-cache.ts",
        """
        import { FRONTEND_SOLVER_CONFIG } from "./config";

        export interface ArenaGeometryCacheEntry {
          imageWidth: number;
          imageHeight: number;
          arenaBBox?: { x: number; y: number; width: number; height: number };
          cellCenters?: Array<{ id: string; x: number; y: number }>;
          createdAt: number;
        }

        let cachedGeometry: ArenaGeometryCacheEntry | null = null;

        export function getCachedGeometry(width: number, height: number): ArenaGeometryCacheEntry | null {
          if (!cachedGeometry) return null;

          const widthDelta = Math.abs(cachedGeometry.imageWidth - width) / Math.max(1, cachedGeometry.imageWidth);
          const heightDelta = Math.abs(cachedGeometry.imageHeight - height) / Math.max(1, cachedGeometry.imageHeight);

          if (
            widthDelta > FRONTEND_SOLVER_CONFIG.maxImageDimensionDeltaForCache ||
            heightDelta > FRONTEND_SOLVER_CONFIG.maxImageDimensionDeltaForCache
          ) {
            cachedGeometry = null;
            return null;
          }

          return cachedGeometry;
        }

        export function setCachedGeometry(entry: ArenaGeometryCacheEntry): void {
          cachedGeometry = entry;
        }

        export function resetCachedGeometry(): void {
          cachedGeometry = null;
        }
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "pipeline.ts",
        """
        import { FRONTEND_SOLVER_CONFIG } from "./config";
        import { getCachedGeometry } from "./geometry-cache";
        import { imageBitmapToCanvas, inputToImageBitmap } from "./image";
        import { createStageTimer } from "./timing";
        import type { FrontendCaptureInput, FrontendSolveResult } from "./types";

        /**
         * Browser-local pipeline entrypoint.
         *
         * This file intentionally starts as a strict contract and safe shell.
         * The next migration patch should wire existing arena/grid/glyph/player detection
         * logic into the marked stages below.
         */
        export async function analyzeAndSolveFrontend(input: FrontendCaptureInput): Promise<FrontendSolveResult> {
          const timer = createStageTimer();
          const warnings = [];

          try {
            const bitmap = await timer.measureAsync("image_decode_ms", () => inputToImageBitmap(input));
            const canvasImage = timer.measure("image_resize_ms", () => imageBitmapToCanvas(bitmap));

            const cached = input.preferCachedGeometry !== false
              ? getCachedGeometry(canvasImage.width, canvasImage.height)
              : null;

            if (cached) {
              warnings.push({
                code: "used_cached_geometry" as const,
                message: "Cached arena geometry is available for this screenshot size.",
              });
            }

            // TODO phase 2/3:
            // 1. arena_detect_ms: locate or reuse arena bbox
            // 2. grid_detect_ms: generate/reuse 338 cell centres
            // 3. glyph_detect_ms: classify white/black glyphs per known cell
            // 4. pillar_detect_ms: classify pillar cells
            // 5. player_detect_ms: locate player cell
            // 6. solver_ms: run local TypeScript solver

            return {
              ok: false,
              source: "frontend",
              status: "not_implemented",
              message: "Frontend-only pipeline shell is installed. Port detection and solver stages next.",
              warnings,
              debug: {
                reason: "frontend_not_implemented",
                image_size: { width: canvasImage.width, height: canvasImage.height },
                cells_expected: FRONTEND_SOLVER_CONFIG.cellsExpected,
                notes: [
                  "This is the migration shell, not the final solver.",
                  "Next patch must wire concrete browser-local detection and solver logic into pipeline.ts.",
                ],
              },
              timings_ms: timer.finish(),
            };
          } catch (error) {
            return {
              ok: false,
              source: "frontend",
              status: "rejected",
              message: error instanceof Error ? error.message : "Unknown frontend pipeline error.",
              warnings,
              debug: { reason: "unknown" },
              timings_ms: timer.finish(),
            };
          }
        }
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "worker.ts",
        """
        import { analyzeAndSolveFrontend } from "./pipeline";
        import type { FrontendSolverWorkerRequest, FrontendSolverWorkerResponse } from "./types";

        self.onmessage = async (event: MessageEvent<FrontendSolverWorkerRequest>) => {
          if (event.data?.type !== "analyze-and-solve") return;

          try {
            const result = await analyzeAndSolveFrontend(event.data.payload);
            const response: FrontendSolverWorkerResponse = { type: "result", payload: result };
            self.postMessage(response);
          } catch (error) {
            const response: FrontendSolverWorkerResponse = {
              type: "error",
              payload: {
                ok: false,
                source: "frontend",
                status: "rejected",
                message: error instanceof Error ? error.message : "Unknown worker error.",
                warnings: [],
                debug: { reason: "unknown" },
                timings_ms: { total_ms: 0 },
              },
            };
            self.postMessage(response);
          }
        };
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "client.ts",
        """
        import { getSolverRuntimeMode } from "./config";
        import { analyzeAndSolveFrontend } from "./pipeline";
        import type { FrontendCaptureInput, FrontendSolveResult } from "./types";

        export async function solveScreenshot(input: FrontendCaptureInput): Promise<FrontendSolveResult> {
          const mode = getSolverRuntimeMode();

          if (mode === "frontend") {
            return await analyzeAndSolveFrontend(input);
          }

          if (mode === "hybrid") {
            const frontendResult = await analyzeAndSolveFrontend(input);
            if (frontendResult.ok) return frontendResult;
            return {
              ...frontendResult,
              status: frontendResult.status === "not_implemented" ? "not_implemented" : frontendResult.status,
              message:
                frontendResult.message ??
                "Frontend solver did not produce a valid result. Backend fallback is intentionally not wired in this scaffold.",
              warnings: [
                ...frontendResult.warnings,
                {
                  code: "backend_fallback_used",
                  message: "Hybrid mode requested, but backend fallback must be wired by the app-specific integration layer.",
                },
              ],
            };
          }

          return {
            ok: false,
            source: "backend",
            status: "not_implemented",
            message: "Backend mode is legacy. Wire the existing API call in the app-specific integration layer if still required.",
            warnings: [],
            debug: { reason: "frontend_not_implemented" },
            timings_ms: { total_ms: 0 },
          };
        }
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "index.ts",
        """
        export * from "./client";
        export * from "./config";
        export * from "./geometry-cache";
        export * from "./pipeline";
        export * from "./types";
        """,
        overwrite=True,
    ))

    actions.append(write_file(
        lib_root / "README.md",
        """
        # Frontend Solver Scaffold

        This folder is the migration boundary for the frontend-only solver.

        ## Current state

        The scaffold is installed, but the real detection and solver stages still need to be wired.

        ## Intended import

        ```ts
        import { solveScreenshot } from "@/lib/frontend-solver";
        ```

        ## Required next wiring

        1. Replace the current API-submit path in the screenshot UI with `solveScreenshot(...)` when `NEXT_PUBLIC_SOLVER_MODE=frontend`.
        2. Port or wrap existing solver mechanics in TypeScript.
        3. Port arena/grid/glyph/pillar/player extraction to canvas/Web Worker code.
        4. Keep backend only as explicit fallback while parity tests are being built.
        """,
        overwrite=True,
    ))

    actions.append(append_once(
        web_root / ".env.example",
        "NEXT_PUBLIC_SOLVER_MODE",
        """
        # Solver runtime mode:
        # frontend = browser-local target architecture
        # hybrid   = try browser-local first, then app-specific backend fallback
        # backend  = legacy API path
        NEXT_PUBLIC_SOLVER_MODE=frontend
        """,
    ))

    print("Frontend-only migration scaffold patch")
    print(f"Repo root: {repo_root}")
    print(f"Web root:  {web_root}")
    print("")
    for action in actions:
        print(action)
    print("")
    print("Next commands:")
    print("  git diff --stat")
    print("  git diff")
    print("  npm run lint   # if available")
    print("  npm run build  # if available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
