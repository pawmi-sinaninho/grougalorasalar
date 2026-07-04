import { FRONTEND_SOLVER_CONFIG } from "./config";
import { getCachedGeometry } from "./geometry-cache";
import { imageBitmapToCanvas, inputToImageBitmap } from "./image";
import { localSolverResultToFrontendResult, solveLocalGiven, type LocalGivenState } from "./local-solver";
import { recogniseScreenshotToLocalState } from "./browser-vision";
import { createStageTimer } from "./timing";
import type { CaptureDebug, CaptureWarning, FrontendCaptureInput, FrontendSolveResult } from "./types";

function hasManualState(input: FrontendCaptureInput): input is FrontendCaptureInput & { manualState: LocalGivenState } {
  return Boolean(input.manualState && typeof input.manualState === "object");
}

function mergeWarnings(...groups: Array<CaptureWarning[] | undefined>): CaptureWarning[] {
  return groups.flatMap(group => group ?? []);
}

function makeRejectedResult(args: {
  message: string;
  reason: string;
  confidence?: number;
  warnings?: CaptureWarning[];
  debug?: CaptureDebug;
  timings: FrontendSolveResult["timings_ms"];
  raw?: unknown;
}): FrontendSolveResult {
  return {
    ok: false,
    source: "frontend",
    status: "rejected",
    message: args.message,
    reason: args.reason,
    confidence: args.confidence ?? 0,
    actions: [],
    warnings: args.warnings ?? [],
    debug: {
      reason: args.reason,
      cells_expected: FRONTEND_SOLVER_CONFIG.cellsExpected,
      ...(args.debug ?? {}),
    },
    timings_ms: args.timings,
    raw: args.raw,
  };
}

/**
 * Browser-local pipeline entrypoint.
 *
 * Hardened Patch B status:
 * - image stays in the browser;
 * - local Canvas detector attempts to create a logical state;
 * - local TypeScript tactical solver is executed only when state is complete;
 * - backend fallback is intentionally not used in the normal path.
 */
export async function analyzeAndSolveFrontend(input: FrontendCaptureInput): Promise<FrontendSolveResult> {
  const timer = createStageTimer();
  const warnings: CaptureWarning[] = [];

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
      return { ...result, warnings: mergeWarnings(warnings, result.warnings) };
    }

    const vision = timer.measure("browser_vision_ms", () => recogniseScreenshotToLocalState(canvasImage));

    if (!vision.ok) {
      return makeRejectedResult({
        message: "Local browser recognition could not build a complete tactical state yet.",
        reason: String(vision.reason ?? "frontend_vision_rejected"),
        confidence: vision.confidence,
        warnings: mergeWarnings(warnings, vision.warnings),
        debug: {
          ...vision.debug,
          reason: String(vision.reason ?? vision.debug.reason ?? "frontend_vision_rejected"),
          notes: [
            ...(vision.debug.notes ?? []),
            "Patch B stayed local; no Render/backend request was used.",
            "Next fix should target the detector named in the rejection reason.",
          ],
        },
        timings: timer.finish(),
        raw: { vision },
      });
    }

    const visionState = vision.state;
    if (!visionState) {
      return makeRejectedResult({
        message: "Local browser recognition returned ok=true without a tactical state.",
        reason: "frontend_vision_state_missing",
        confidence: vision.confidence,
        warnings: mergeWarnings(warnings, vision.warnings),
        debug: {
          ...vision.debug,
          reason: "frontend_vision_state_missing",
          image_size: { width: canvasImage.width, height: canvasImage.height },
          notes: [
            ...(vision.debug.notes ?? []),
            "Internal guard prevented solveLocalGiven(undefined).",
          ],
        },
        timings: timer.finish(),
        raw: { vision },
      });
    }

    const local = timer.measure("solver_ms", () => solveLocalGiven(visionState));
    const result = localSolverResultToFrontendResult(local, timer.finish(), {
      width: canvasImage.width,
      height: canvasImage.height,
    });

    return {
      ...result,
      source: "frontend",
      confidence: Math.min(result.confidence ?? 1, vision.confidence),
      warnings: mergeWarnings(warnings, vision.warnings, result.warnings),
      debug: {
        ...vision.debug,
        ...result.debug,
        reason: result.debug.reason ?? vision.debug.reason,
        confidence: Math.min(result.debug.confidence ?? 1, vision.confidence),
        notes: [
          ...(vision.debug.notes ?? []),
          ...(result.debug.notes ?? []),
          "Browser Patch B: recognition and solver both executed locally.",
        ],
      },
      raw: { vision, solver: result.raw },
    };
  } catch (error) {
    return makeRejectedResult({
      message: error instanceof Error ? error.message : "Unknown frontend pipeline error.",
      reason: "frontend_pipeline_exception",
      confidence: 0,
      warnings,
      debug: {
        reason: "frontend_pipeline_exception",
        cells_expected: FRONTEND_SOLVER_CONFIG.cellsExpected,
        notes: [error instanceof Error ? error.stack ?? error.message : String(error)],
      },
      timings: timer.finish(),
    });
  }
}
