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
