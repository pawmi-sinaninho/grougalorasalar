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
