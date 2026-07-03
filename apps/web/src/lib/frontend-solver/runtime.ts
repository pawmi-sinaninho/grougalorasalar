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
