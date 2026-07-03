import type { FrontendSolveResult } from "./types";

export function formatTimings(result: FrontendSolveResult): string {
  const entries = Object.entries(result.timings_ms)
    .filter(([, value]) => typeof value === "number")
    .sort(([a], [b]) => (a === "total_ms" ? -1 : b === "total_ms" ? 1 : a.localeCompare(b)));

  return entries.map(([key, value]) => `${key}: ${value} ms`).join("\n");
}

export function formatSolveDebugSummary(result: FrontendSolveResult): string {
  const lines: string[] = [];
  lines.push(`source: ${result.source}`);
  lines.push(`status: ${result.status}`);
  lines.push(`ok: ${result.ok}`);
  if (result.message) lines.push(`message: ${result.message}`);
  if (result.debug.reason) lines.push(`reason: ${result.debug.reason}`);
  if (result.debug.image_size) {
    lines.push(`image: ${result.debug.image_size.width}x${result.debug.image_size.height}`);
  }
  if (result.warnings.length) {
    lines.push("warnings:");
    for (const warning of result.warnings) {
      lines.push(`- ${warning.code}: ${warning.message}`);
    }
  }
  lines.push("timings:");
  lines.push(formatTimings(result));
  return lines.join("\n");
}
