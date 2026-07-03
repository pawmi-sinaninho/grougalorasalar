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
