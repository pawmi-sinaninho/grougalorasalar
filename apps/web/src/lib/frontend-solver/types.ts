export type SolverRuntimeMode = "frontend" | "backend" | "hybrid";

export type CaptureRejectReason =
  | "arena_not_found"
  | "grid_coverage_too_low"
  | "player_not_found"
  | "glyph_detection_low_confidence"
  | "pillar_detection_low_confidence"
  | "solver_failed"
  | "frontend_not_implemented"
  | "frontend_vision_rejected"
  | "frontend_vision_state_missing"
  | "frontend_pipeline_exception"
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
  reason?: CaptureRejectReason | string;
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
  [key: string]: unknown;
}

export interface FrontendCaptureInput {
  file?: File;
  blob?: Blob;
  imageBitmap?: ImageBitmap;
  dataUrl?: string;
  debug?: boolean;
  preferCachedGeometry?: boolean;
  /** Internal migration hook: lets tests/future recognition feed a complete logical state directly into the browser solver. */
  manualState?: unknown;
}

export interface SolverActionStep {
  label: string;
  instruction?: string;
  spell?: string;
  from?: string;
  to?: string;
  apCost?: number;
  note?: string;
  order?: number;
  sourceCell?: { x: number; y: number };
  destinationCell?: { x: number; y: number };
  targetKind?: "cell" | "pillar";
  targetCell?: { x: number; y: number };
  targetPillarId?: string | null;
  canonicalSignature?: string;
  pathCells?: Array<{ x: number; y: number }>;
  [key: string]: unknown;
}

export interface FrontendRecommendationExpected {
  finalCell: { x: number; y: number } | null;
  raceOutcome: string;
  blackPillarIds?: string[];
  whitePillarIds?: string[];
  rechargedSpells?: string[];
  directCenterEffect?: string;
  nextSpellState?: Record<string, number> | null;
}

export interface FrontendSolveResult {
  ok: boolean;
  source: "frontend" | "backend";
  status: "solved" | "warning" | "rejected" | "not_implemented" | "blocked_missing_data";
  message?: string;
  reason?: CaptureRejectReason | string;
  confidence?: number;
  actions?: SolverActionStep[];
  expected?: FrontendRecommendationExpected;
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
