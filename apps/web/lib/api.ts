import { solveScreenshotRuntime } from '../src/lib/frontend-solver';
export type AnalysisEnvelope = {
  session: {
    analysisId: string;
    stateVersion: number;
    state: string;
    gate: { status: string; blockingReasonCodes: string[] };
  };
  turnState?: unknown;
  observations?: Array<{ fieldPath: string; confidence: number; decisionState: string }>;
  recognition?: {
    status: string;
    matchedFixtureId?: string | null;
    metrics?: { path?: string; totalRecognitionMs?: number; ocrInvoked?: boolean };
    registration?: unknown;
    proposals?: unknown;
  } | null;
  performance?: {
    serverScreenshotToStateMs?: number;
    solverMs?: number;
    ingest?: Record<string, number>;
    recognition?: Record<string, number | boolean | string>;
  };
  fight?: {
    round: number;
    charges: Record<'indecision' | 'reflection' | 'repulsion' | 'attraction', number>;
    syncStatus: string;
    verifiedStartCell?: { x: number; y: number } | null;
    pendingTransition?: {
      expectedFinalCell: { x: number; y: number };
      nextCharges: Record<'indecision' | 'reflection' | 'repulsion' | 'attraction', number>;
    } | null;
  };
  recommendation?: {
    status: string;
    solverStatus?: string;
    statusReasonCodes: string[];
    actions: Array<{
      order: number; instruction: string; canonicalSignature: string; spell?: string;
      targetKind?: 'cell' | 'pillar'; targetPillarId?: string | null; targetCell?: { x: number; y: number };
      sourceCell?: { x: number; y: number }; destinationCell?: { x: number; y: number };
    }>;
    expected: {
      finalCell: { x: number; y: number } | null;
      raceOutcome: string;
      blackPillarIds?: string[];
      whitePillarIds?: string[];
      rechargedSpells?: string[];
      nextSpellState?: Record<'indecision' | 'reflection' | 'repulsion' | 'attraction', number | null> | null;
    };
    alternatives?: Array<{ sequence: string[]; finalCell: { x: number; y: number }; raceOutcome: string }>;
  } | null;
};

export const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000/api/v1';

// FRONTEND_ONLY_API_BOUNDARY_PATCH_START
// Browser-local migration layer. In frontend mode this file keeps the old UI API
// contract stable while avoiding backend calls in the normal screenshot flow.
type FrontendLocalEnvelope = Record<string, unknown> & {
  id?: string;
  analysisId?: string;
  accessToken?: string;
  token?: string;
  recognition?: unknown;
  recommendation?: unknown;
  performance?: Record<string, unknown>;
  frontendOnly?: boolean;
};

const FRONTEND_SOLVER_MODE = process.env.NEXT_PUBLIC_SOLVER_MODE ?? 'backend';
const frontendLocalAnalyses = new Map<string, FrontendLocalEnvelope>();
let frontendLocalSequence = 0;

function isFrontendOnlyApiMode() {
  return FRONTEND_SOLVER_MODE === 'frontend';
}

function newFrontendLocalId() {
  frontendLocalSequence += 1;
  return `frontend-local-${Date.now()}-${frontendLocalSequence}`;
}

function getBrowserNowMs() {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now();
  }
  return Date.now();
}

function getFrontendBlobLike(args: IArguments): Blob | File | null {
  for (const value of Array.from(args)) {
    if (typeof Blob !== 'undefined' && value instanceof Blob) return value;
    if (typeof File !== 'undefined' && value instanceof File) return value;
  }

  for (const value of Array.from(args)) {
    if (value && typeof value === 'object') {
      const candidate = value as { file?: unknown; blob?: unknown; image?: unknown };
      if (typeof Blob !== 'undefined' && candidate.file instanceof Blob) return candidate.file;
      if (typeof Blob !== 'undefined' && candidate.blob instanceof Blob) return candidate.blob;
      if (typeof Blob !== 'undefined' && candidate.image instanceof Blob) return candidate.image;
    }
  }

  return null;
}

function getFrontendAnalysisId(args: IArguments): string | null {
  for (const value of Array.from(args)) {
    if (typeof value === 'string' && value.length > 0) return value;
    if (value && typeof value === 'object') {
      const candidate = value as { analysisId?: unknown; id?: unknown };
      if (typeof candidate.analysisId === 'string') return candidate.analysisId;
      if (typeof candidate.id === 'string') return candidate.id;
    }
  }
  return null;
}

function makeFrontendLocalEnvelope(overrides: Partial<FrontendLocalEnvelope> = {}) {
  const id = typeof overrides.analysisId === 'string'
    ? overrides.analysisId
    : typeof overrides.id === 'string'
      ? overrides.id
      : newFrontendLocalId();

  const envelope: FrontendLocalEnvelope = {
    id,
    analysisId: id,
    accessToken: `local-${id}`,
    token: `local-${id}`,
    locale: 'fr',
    status: 'frontend_local',
    frontendOnly: true,
    image: null,
    recognition: null,
    recommendation: {
      status: 'blocked_missing_data',
      solverStatus: 'frontend_pipeline_pending',
      statusReasonCodes: ['frontend_pipeline_pending'],
      actions: [],
    },
    performance: {
      frontendOnly: true,
      apiBoundary: 'browser-local',
    },
    warnings: [
      'Frontend-only mode is active. Backend calls are bypassed at the web API boundary.',
    ],
    ...overrides,
  };

  frontendLocalAnalyses.set(id, envelope);
  return envelope;
}

function frontendResultToEnvelope(
  result: Awaited<ReturnType<typeof solveScreenshotRuntime>>,
  analysisId: string | null,
  startedAtMs: number,
  localImageUrl?: string,
) {
  const id = analysisId ?? newFrontendLocalId();
  const totalMs = Math.round((getBrowserNowMs() - startedAtMs) * 100) / 100;
  const status = result.ok ? 'provisional_solution' : 'blocked_missing_data';
  const reasonCode = result.ok ? 'frontend_local_result' : result.reason ?? 'frontend_local_failed';

  return makeFrontendLocalEnvelope({
    id,
    analysisId: id,
    status,
    image: localImageUrl
      ? {
          url: localImageUrl,
          originalUrl: localImageUrl,
          previewUrl: localImageUrl,
          annotatedUrl: null,
        }
      : null,
    recognition: {
      status: result.ok ? 'frontend_local_ready' : 'frontend_local_incomplete',
      confidence: result.confidence ?? 0,
      warnings: result.warnings ?? [],
      debug: result.debug ?? null,
    },
    recommendation: {
      status,
      solverStatus: result.ok ? 'frontend_local' : 'frontend_pipeline_pending',
      statusReasonCodes: [reasonCode],
      actions: result.actions ?? [],
    },
    performance: {
      frontendOnly: true,
      apiBoundary: 'browser-local',
      browserScreenshotToStateMs: totalMs,
      timings: result.timings ?? {},
    },
    debug: result.debug ?? null,
    warnings: [
      ...(result.warnings ?? []),
      ...(result.ok ? [] : ['Local frontend detector/solver stages are not fully ported yet.']),
    ],
  });
}

async function frontendOnlyCreateAnalysis(locale = 'fr') {
  return makeFrontendLocalEnvelope({ locale });
}

async function frontendOnlyUploadImage(args: IArguments) {
  const startedAtMs = getBrowserNowMs();
  const analysisId = getFrontendAnalysisId(args);
  const blob = getFrontendBlobLike(args);

  if (!blob) {
    return makeFrontendLocalEnvelope({
      analysisId: analysisId ?? undefined,
      status: 'invalid_screenshot',
      recommendation: {
        status: 'invalid_screenshot',
        solverStatus: 'frontend_missing_file',
        statusReasonCodes: ['frontend_missing_file'],
        actions: [],
      },
      warnings: ['Frontend-only upload was called without a File or Blob argument.'],
    });
  }

  const localImageUrl = typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function'
    ? URL.createObjectURL(blob)
    : undefined;

  const result = await solveScreenshotRuntime({
    file: typeof File !== 'undefined' && blob instanceof File ? blob : undefined,
    blob: !(typeof File !== 'undefined' && blob instanceof File) ? blob : undefined,
    debug: true,
    preferCachedGeometry: true,
  });

  return frontendResultToEnvelope(result, analysisId, startedAtMs, localImageUrl);
}

async function frontendOnlySolve(args: IArguments) {
  const analysisId = getFrontendAnalysisId(args);
  if (analysisId && frontendLocalAnalyses.has(analysisId)) {
    return frontendLocalAnalyses.get(analysisId);
  }
  return makeFrontendLocalEnvelope({
    analysisId: analysisId ?? undefined,
    recommendation: {
      status: 'blocked_missing_data',
      solverStatus: 'frontend_no_local_capture',
      statusReasonCodes: ['frontend_no_local_capture'],
      actions: [],
    },
    warnings: ['No local frontend capture exists for this analysis id. Paste/upload a screenshot again.'],
  });
}

async function frontendOnlyCommand(args: IArguments) {
  const analysisId = getFrontendAnalysisId(args);
  if (analysisId && frontendLocalAnalyses.has(analysisId)) {
    const envelope = frontendLocalAnalyses.get(analysisId)!;
    envelope.warnings = [
      ...((Array.isArray(envelope.warnings) ? envelope.warnings : []) as string[]),
      'Frontend-only command bridge is active. Manual correction commands still need a local reducer port.',
    ];
    return envelope;
  }
  return makeFrontendLocalEnvelope({
    analysisId: analysisId ?? undefined,
    warnings: ['Frontend-only command bridge received a command before a local capture existed.'],
  });
}

async function frontendOnlyDeleteAnalysis(args: IArguments) {
  const analysisId = getFrontendAnalysisId(args);
  if (analysisId) frontendLocalAnalyses.delete(analysisId);
  return { ok: true, frontendOnly: true, deleted: analysisId ?? null };
}
// FRONTEND_ONLY_API_BOUNDARY_PATCH_END


export async function createAnalysis(locale = 'fr') {
  if (isFrontendOnlyApiMode()) return await frontendOnlyCreateAnalysis(locale) as unknown as AnalysisEnvelope;

  const response = await fetch(`${API}/analyses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      schemaVersion: '0.8.0',
      locale,
      retentionConsent: 'ephemeral_only',
      qualityImprovementConsent: false
    })
  });
  if (!response.ok) throw new Error('Création impossible');
  return response.json() as Promise<{ session: AnalysisEnvelope['session']; accessToken: string }>;
}

export async function uploadImage(id: string, token: string, version: number, file: File): Promise<AnalysisEnvelope> {
  const body = new FormData();
  body.append('file', file);
  body.append('expectedStateVersion', String(version));
  const response = await fetch(`${API}/analyses/${id}/image`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body
  });
  if (!response.ok) throw new Error('Image refusée');
  return response.json();
}

export async function command(id: string, token: string, version: number, type: string, payload: object): Promise<AnalysisEnvelope> {
  const response = await fetch(`${API}/analyses/${id}/commands`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      schemaVersion: '0.6.0', commandId: `cmd_${crypto.randomUUID().replaceAll('-', '')}`,
      analysisId: id, expectedStateVersion: version, type, payload, issuedAt: new Date().toISOString()
    })
  });
  if (!response.ok) throw new Error((await response.json()).error?.code ?? 'Commande refusée');
  return response.json();
}

export async function solve(id: string, token: string, version: number): Promise<AnalysisEnvelope> {
  const response = await fetch(`${API}/analyses/${id}/solve`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ schemaVersion: '0.8.0', expectedStateVersion: version, mode: 'review', maxAlternatives: 2, confirmedSingleSourceRuleIds: [] })
  });
  if (!response.ok) throw new Error((await response.json()).error?.code ?? 'Solveur indisponible');
  return response.json();
}

export async function deleteAnalysis(id: string, token: string): Promise<void> {
  const response = await fetch(`${API}/analyses/${id}`, {
    method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok && response.status !== 404) throw new Error('Suppression impossible');
}


export async function fetchAssetUrl(id: string, token: string, kind: 'normalised' | 'thumbnail' | 'annotated'): Promise<string> {
  const response = await fetch(`${API}/analyses/${id}/asset/${kind}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store'
  });
  if (!response.ok) throw new Error(`Asset ${kind} indisponible`);
  return URL.createObjectURL(await response.blob());
}
