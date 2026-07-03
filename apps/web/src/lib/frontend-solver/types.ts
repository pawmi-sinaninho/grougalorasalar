export type SolverRuntimeMode = "frontend" | "backend" | "hybrid";

export type CaptureRejectReason =
  | "arena_not_found"
  | "grid_coverage_too_low"
  | "player_not_found"
  | "glyph_detection_low_confidence"
  | "pillar_detection_low_confidence"
  | "solver_failed"
  | "frontend_not_implemented"
  | "unknown";

export type CaptureWarningCode =
  | "grid_partial"
  | "glyph_uncertain"
  | "pillar_uncertain"
  | "player_uncertain"
  | "used_cached_geometry"
  | "cache_invalidated"
  | "backend_fallback_used";

export interface PipelineTimingsMs {
  total_ms: number;
  image_decode_ms?: number;
  image_resize_ms?: number;
  arena_detect_ms?: number;
  grid_detect_ms?: number;
  glyph_detect_ms?: number;
  pillar_detect_ms?: number;
  player_detect_ms?: number;
  solver_ms?: number;
  worker_roundtrip_ms?: number;
  [stage: string]: number | undefined;
}

export interface CaptureWarning {
  code: CaptureWarningCode;
  message: string;
  confidence?: number;
}

export interface CaptureDebug {
  reason?: CaptureRejectReason;
  image_size?: { width: number; height: number };
  arena_bbox?: { x: number; y: number; width: number; height: number };
  cells_expected?: number;
  cells_detected?: number;
  white_glyphs_detected?: number;
  black_glyphs_detected?: number;
  pillars_detected?: number;
  player_detected?: boolean;
  confidence?: number;
  overlay_data_url?: string;
  notes?: string[];
}

export interface FrontendCaptureInput {
  file?: File;
  blob?: Blob;
  imageBitmap?: ImageBitmap;
  dataUrl?: string;
  debug?: boolean;
  preferCachedGeometry?: boolean;
}

export interface SolverActionStep {
  label: string;
  spell?: string;
  from?: string;
  to?: string;
  apCost?: number;
  note?: string;
}

export interface FrontendSolveResult {
  ok: boolean;
  source: "frontend" | "backend";
  status: "solved" | "warning" | "rejected" | "not_implemented";
  message?: string;
  actions?: SolverActionStep[];
  warnings: CaptureWarning[];
  debug: CaptureDebug;
  timings_ms: PipelineTimingsMs;
  raw?: unknown;
}

export interface FrontendSolverWorkerRequest {
  type: "analyze-and-solve";
  payload: FrontendCaptureInput;
}

export interface FrontendSolverWorkerResponse {
  type: "result" | "error";
  payload: FrontendSolveResult;
}
