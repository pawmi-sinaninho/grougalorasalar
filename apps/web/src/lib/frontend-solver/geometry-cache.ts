import { FRONTEND_SOLVER_CONFIG } from "./config";

export interface ArenaGeometryCacheEntry {
  imageWidth: number;
  imageHeight: number;
  arenaBBox?: { x: number; y: number; width: number; height: number };
  cellCenters?: Array<{ id: string; x: number; y: number }>;
  createdAt: number;
}

let cachedGeometry: ArenaGeometryCacheEntry | null = null;

export function getCachedGeometry(width: number, height: number): ArenaGeometryCacheEntry | null {
  if (!cachedGeometry) return null;

  const widthDelta = Math.abs(cachedGeometry.imageWidth - width) / Math.max(1, cachedGeometry.imageWidth);
  const heightDelta = Math.abs(cachedGeometry.imageHeight - height) / Math.max(1, cachedGeometry.imageHeight);

  if (
    widthDelta > FRONTEND_SOLVER_CONFIG.maxImageDimensionDeltaForCache ||
    heightDelta > FRONTEND_SOLVER_CONFIG.maxImageDimensionDeltaForCache
  ) {
    cachedGeometry = null;
    return null;
  }

  return cachedGeometry;
}

export function setCachedGeometry(entry: ArenaGeometryCacheEntry): void {
  cachedGeometry = entry;
}

export function resetCachedGeometry(): void {
  cachedGeometry = null;
}
