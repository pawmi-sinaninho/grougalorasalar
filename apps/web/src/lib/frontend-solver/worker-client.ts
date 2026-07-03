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
