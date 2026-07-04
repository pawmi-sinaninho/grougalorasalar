import { FRONTEND_SOLVER_CONFIG } from "./config";
import { getCachedGeometry } from "./geometry-cache";
import { imageBitmapToCanvas, inputToImageBitmap } from "./image";
import { localSolverResultToFrontendResult, solveLocalGiven, type LocalGivenState } from "./local-solver";
import { createStageTimer } from "./timing";
import type { FrontendCaptureInput, FrontendSolveResult } from "./types";

function hasManualState(input: FrontendCaptureInput): input is FrontendCaptureInput & { manualState: LocalGivenState } {
  return Boolean(input.manualState && typeof input.manualState === "object");
}

/**
 * Browser-local pipeline entrypoint.
 *
 * Current status:
 * - image decode/canvas path runs locally;
 * - TypeScript tactical solver is ported and can solve a complete logical state;
 * - visual detection still has to produce that logical state from the screenshot.
 */
export async function analyzeAndSolveFrontend(input: FrontendCaptureInput): Promise<FrontendSolveResult> {
  const timer = createStageTimer();
  const warnings: FrontendSolveResult["warnings"] = [];

  try {
    const bitmap = await timer.measureAsync("image_decode_ms", () => inputToImageBitmap(input));
    const canvasImage = timer.measure("image_resize_ms", () => imageBitmapToCanvas(bitmap));

    const cached = input.preferCachedGeometry !== false
      ? getCachedGeometry(canvasImage.width, canvasImage.height)
      : null;

    if (cached) {
      warnings.push({
        code: "used_cached_geometry",
        message: "Cached arena geometry is available for this screenshot size.",
      });
    }

    if (hasManualState(input)) {
      const local = timer.measure("solver_ms", () => solveLocalGiven(input.manualState));
      const result = localSolverResultToFrontendResult(local, timer.finish(), {
        width: canvasImage.width,
        height: canvasImage.height,
      });
      return { ...result, warnings: [...warnings, ...result.warnings] };
    }

    return {
      ok: false,
      source: "frontend",
      status: "not_implemented",
      message: "Frontend-only image pipeline is installed. The local tactical solver is ported; visual detection must now feed it a logical state.",
      reason: "frontend_not_implemented",
      confidence: 0,
      actions: [],
      warnings,
      debug: {
        reason: "frontend_not_implemented",
        image_size: { width: canvasImage.width, height: canvasImage.height },
        cells_expected: FRONTEND_SOLVER_CONFIG.cellsExpected,
        confidence: 0,
        notes: [
          "Image stayed in the browser; no backend call is required.",
          "TypeScript tactical solver is available through solveLocalGiven(...).",
          "Next migration patch must port browser visual detection and pass manualState into this pipeline.",
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
      reason: "unknown",
      confidence: 0,
      actions: [],
      warnings,
      debug: { reason: "unknown" },
      timings_ms: timer.finish(),
    };
  }
}
