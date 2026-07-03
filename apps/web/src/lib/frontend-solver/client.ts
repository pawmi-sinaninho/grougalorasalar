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
