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
