import { solveScreenshotRuntime } from '../src/lib/frontend-solver';
import type { CaptureWarning, FrontendSolveResult, SolverActionStep } from '../src/lib/frontend-solver';

type SpellKey = 'indecision' | 'reflection' | 'repulsion' | 'attraction';
type Availability = 'unknown' | 'available' | 'unavailable';
type Cell = { x: number; y: number };

type LocalImageAsset = {
  url?: string;
  originalUrl?: string;
  previewUrl?: string;
  annotatedUrl?: string | null;
};

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
    confidence?: number;
    warnings?: string[];
    debug?: unknown;
  } | null;
  performance?: {
    serverScreenshotToStateMs?: number;
    solverMs?: number;
    ingest?: Record<string, number>;
    recognition?: Record<string, number | boolean | string>;
    frontendOnly?: boolean;
    apiBoundary?: string;
    browserScreenshotToStateMs?: number;
    timings?: Record<string, number | undefined>;
  };
  fight?: {
    round: number;
    charges: Record<SpellKey, number>;
    syncStatus: string;
    verifiedStartCell?: Cell | null;
    pendingTransition?: {
      expectedFinalCell: Cell;
      nextCharges: Record<SpellKey, number>;
    } | null;
  };
  recommendation?: {
    status: string;
    solverStatus?: string;
    statusReasonCodes: string[];
    actions: Array<{
      order: number;
      instruction: string;
      canonicalSignature: string;
      spell?: string;
      targetKind?: 'cell' | 'pillar';
      targetPillarId?: string | null;
      targetCell?: Cell;
      sourceCell?: Cell;
      destinationCell?: Cell;
    }>;
    expected: {
      finalCell: Cell | null;
      raceOutcome: string;
      blackPillarIds?: string[];
      whitePillarIds?: string[];
      rechargedSpells?: string[];
      nextSpellState?: Record<SpellKey, number | null> | null;
    };
    alternatives?: Array<{ sequence: string[]; finalCell: Cell; raceOutcome: string }>;
  } | null;
  image?: LocalImageAsset | null;
  warnings?: Array<string | CaptureWarning>;
  debug?: unknown;
  frontendOnly?: boolean;
};

type CreateAnalysisResponse = { session: AnalysisEnvelope['session']; accessToken: string };
type Recommendation = NonNullable<AnalysisEnvelope['recommendation']>;
type RecommendationAction = Recommendation['actions'][number];

type FrontendLocalStoreEntry = {
  envelope: AnalysisEnvelope;
  accessToken: string;
  imageUrl?: string;
};

export const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000/api/v1';

const FRONTEND_SOLVER_MODE = process.env.NEXT_PUBLIC_SOLVER_MODE ?? 'backend';
const frontendLocalAnalyses = new Map<string, FrontendLocalStoreEntry>();
let frontendLocalSequence = 0;

function isFrontendOnlyApiMode(): boolean {
  return FRONTEND_SOLVER_MODE === 'frontend';
}

function newFrontendLocalId(): string {
  frontendLocalSequence += 1;
  return `frontend-local-${Date.now()}-${frontendLocalSequence}`;
}

function getBrowserNowMs(): number {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now();
  }
  return Date.now();
}

function makeCharges(value = 2): Record<SpellKey, number> {
  return {
    indecision: value,
    reflection: value,
    repulsion: value,
    attraction: value,
  };
}

function makeSpellResources(): Record<SpellKey, { availability: Availability; confirmed: boolean }> {
  return {
    indecision: { availability: 'available', confirmed: true },
    reflection: { availability: 'available', confirmed: true },
    repulsion: { availability: 'available', confirmed: true },
    attraction: { availability: 'available', confirmed: true },
  };
}

function makeDefaultRecommendation(
  status = 'blocked_missing_data',
  solverStatus = 'frontend_pipeline_pending',
  reasonCodes: string[] = ['frontend_pipeline_pending'],
  actions: RecommendationAction[] = [],
): Recommendation {
  return {
    status,
    solverStatus,
    statusReasonCodes: reasonCodes,
    actions,
    expected: {
      finalCell: null,
      raceOutcome: 'unknown',
      blackPillarIds: [],
      whitePillarIds: [],
      rechargedSpells: [],
      nextSpellState: null,
    },
    alternatives: [],
  };
}

function makeBaseEnvelope(options: {
  analysisId?: string;
  stateVersion?: number;
  state?: string;
  recommendation?: Recommendation;
  recognition?: AnalysisEnvelope['recognition'];
  performance?: AnalysisEnvelope['performance'];
  image?: LocalImageAsset | null;
  warnings?: Array<string | CaptureWarning>;
  debug?: unknown;
} = {}): AnalysisEnvelope {
  const analysisId = options.analysisId ?? newFrontendLocalId();
  const stateVersion = options.stateVersion ?? 1;

  return {
    session: {
      analysisId,
      stateVersion,
      state: options.state ?? 'frontend_local',
      gate: { status: 'ready', blockingReasonCodes: [] },
    },
    turnState: {
      player: { current: null },
      pillars: [],
      glyphs: { blackOffsets: [], whiteOffsets: [] },
      resources: { actionBudget: 12, spells: makeSpellResources() },
      flags: { criticalFieldsConfirmed: false, pillarSetComplete: false, anchorConfirmed: false },
    },
    observations: [],
    recognition: options.recognition ?? {
      status: 'frontend_local_pending',
      matchedFixtureId: null,
      metrics: { totalRecognitionMs: 0, ocrInvoked: false },
      registration: undefined,
      proposals: { player: null, pillars: [], glyphPattern: null },
      confidence: 0,
      warnings: [],
      debug: null,
    },
    performance: options.performance ?? {
      frontendOnly: true,
      apiBoundary: 'browser-local',
      browserScreenshotToStateMs: 0,
      timings: {},
    },
    fight: {
      round: 1,
      charges: makeCharges(2),
      syncStatus: 'frontend_local',
      verifiedStartCell: null,
      pendingTransition: null,
    },
    recommendation: options.recommendation ?? makeDefaultRecommendation(),
    image: options.image ?? null,
    warnings: options.warnings ?? [
      'Frontend-only mode is active. Backend calls are bypassed for the normal screenshot flow.',
    ],
    debug: options.debug ?? null,
    frontendOnly: true,
  };
}

function storeLocalEnvelope(envelope: AnalysisEnvelope, accessToken?: string, imageUrl?: string): AnalysisEnvelope {
  const token = accessToken ?? `local-${envelope.session.analysisId}`;
  frontendLocalAnalyses.set(envelope.session.analysisId, { envelope, accessToken: token, imageUrl });
  return envelope;
}

function getLocalEntry(analysisId: string): FrontendLocalStoreEntry | undefined {
  return frontendLocalAnalyses.get(analysisId);
}

function normaliseWarningText(warning: CaptureWarning | string): string {
  if (typeof warning === 'string') return warning;
  return warning.message || warning.code;
}

function getFrontendWarnings(result: FrontendSolveResult): CaptureWarning[] {
  return Array.isArray(result.warnings) ? result.warnings : [];
}

function getFrontendDebug(result: FrontendSolveResult): NonNullable<FrontendSolveResult['debug']> | Record<string, never> {
  return result.debug && typeof result.debug === 'object' ? result.debug : {};
}

function getFrontendConfidence(result: FrontendSolveResult): number {
  const debug = getFrontendDebug(result);
  const confidence = 'confidence' in debug ? debug.confidence : undefined;
  if (typeof confidence === 'number' && Number.isFinite(confidence)) return confidence;
  return result.ok ? 0.5 : 0;
}

function getFrontendFailureReason(result: FrontendSolveResult): string {
  const debug = getFrontendDebug(result);
  const reason = 'reason' in debug ? debug.reason : undefined;
  if (typeof reason === 'string' && reason.trim().length > 0) return reason;
  if (result.status === 'not_implemented') return 'frontend_pipeline_pending';
  if (result.status === 'rejected') return 'frontend_local_rejected';
  return 'frontend_local_failed';
}

function parseCell(value: string | undefined): Cell | undefined {
  if (!value) return undefined;
  const match = value.match(/-?\d+/g);
  if (!match || match.length < 2) return undefined;
  const x = Number(match[0]);
  const y = Number(match[1]);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return undefined;
  return { x, y };
}

function normaliseSpell(value: string | undefined): SpellKey | undefined {
  if (value === 'indecision' || value === 'reflection' || value === 'repulsion' || value === 'attraction') {
    return value;
  }
  return undefined;
}

function frontendActionToRecommendationAction(action: SolverActionStep, index: number): RecommendationAction {
  const spell = normaliseSpell(action.spell);
  const sourceCell = parseCell(action.from);
  const destinationCell = parseCell(action.to);
  const targetCell = destinationCell;
  const instruction = action.label || action.note || `Action ${index + 1}`;

  return {
    order: index + 1,
    instruction,
    canonicalSignature: `frontend-local:${index + 1}:${spell ?? 'action'}:${instruction}`,
    spell,
    targetKind: targetCell ? 'cell' : undefined,
    targetPillarId: null,
    targetCell,
    sourceCell,
    destinationCell,
  };
}

function normaliseFrontendActions(actions: FrontendSolveResult['actions']): RecommendationAction[] {
  return (actions ?? []).map(frontendActionToRecommendationAction);
}

function resultStatus(result: FrontendSolveResult): string {
  if (result.ok) return 'provisional_solution';
  if (result.status === 'rejected') return 'invalid_screenshot';
  return 'blocked_missing_data';
}

function frontendResultToEnvelope(
  result: FrontendSolveResult,
  analysisId: string,
  stateVersion: number,
  startedAtMs: number,
  imageUrl?: string,
): AnalysisEnvelope {
  const totalMs = Math.round((getBrowserNowMs() - startedAtMs) * 100) / 100;
  const status = resultStatus(result);
  const reasonCode = result.ok ? 'frontend_local_result' : getFrontendFailureReason(result);
  const warnings = getFrontendWarnings(result);
  const warningTexts = warnings.map(normaliseWarningText);
  const debug = getFrontendDebug(result);
  const actions = normaliseFrontendActions(result.actions);

  const envelope = makeBaseEnvelope({
    analysisId,
    stateVersion,
    state: status,
    image: imageUrl
      ? {
          url: imageUrl,
          originalUrl: imageUrl,
          previewUrl: imageUrl,
          annotatedUrl: null,
        }
      : null,
    recognition: {
      status: result.ok ? 'frontend_local_ready' : 'frontend_local_incomplete',
      matchedFixtureId: null,
      metrics: {
        totalRecognitionMs: result.timings_ms.total_ms,
        ocrInvoked: false,
      },
      registration: undefined,
      proposals: { player: null, pillars: [], glyphPattern: null },
      confidence: getFrontendConfidence(result),
      warnings: warningTexts,
      debug,
    },
    recommendation: makeDefaultRecommendation(
      status,
      result.ok ? 'frontend_local' : 'frontend_pipeline_pending',
      [reasonCode],
      actions,
    ),
    performance: {
      frontendOnly: true,
      apiBoundary: 'browser-local',
      browserScreenshotToStateMs: totalMs,
      solverMs: result.timings_ms.solver_ms,
      timings: result.timings_ms,
      recognition: {
        source: result.source,
        status: result.status,
        ok: result.ok,
      },
    },
    warnings: [
      ...warningTexts,
      ...(result.ok ? [] : ['Local frontend detector/solver stages are not fully ported yet.']),
    ],
    debug,
  });

  return storeLocalEnvelope(envelope, `local-${analysisId}`, imageUrl);
}

async function frontendOnlyCreateAnalysis(locale = 'fr'): Promise<CreateAnalysisResponse> {
  const analysisId = newFrontendLocalId();
  const accessToken = `local-${analysisId}`;
  const envelope = makeBaseEnvelope({
    analysisId,
    stateVersion: 1,
    warnings: [`Frontend-only session created for locale ${locale}.`],
  });
  storeLocalEnvelope(envelope, accessToken);

  return {
    session: envelope.session,
    accessToken,
  };
}

async function frontendOnlyUploadImage(
  analysisId: string,
  accessToken: string,
  version: number,
  file: File,
): Promise<AnalysisEnvelope> {
  const startedAtMs = getBrowserNowMs();
  const imageUrl = typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function'
    ? URL.createObjectURL(file)
    : undefined;

  const result = await solveScreenshotRuntime(
    {
      file,
      debug: true,
      preferCachedGeometry: true,
    },
    {
      mode: 'frontend',
      worker: { useWorker: false },
      allowBackendFallback: false,
    },
  );

  return frontendResultToEnvelope(result, analysisId, version + 1, startedAtMs, imageUrl);
}

async function frontendOnlyCommand(
  analysisId: string,
  _token: string,
  version: number,
  type: string,
  payload: object,
): Promise<AnalysisEnvelope> {
  const current = getLocalEntry(analysisId)?.envelope ?? makeBaseEnvelope({ analysisId, stateVersion: version });
  const warnings = [
    ...((current.warnings ?? []) as Array<string | CaptureWarning>),
    `Frontend-only command ignored until the local correction reducer is ported: ${type}`,
  ];

  const updated: AnalysisEnvelope = {
    ...current,
    session: {
      ...current.session,
      stateVersion: version + 1,
    },
    observations: [
      ...(current.observations ?? []),
      {
        fieldPath: `frontendOnly.commands.${type}`,
        confidence: 0,
        decisionState: 'ignored_until_frontend_reducer_ported',
      },
    ],
    warnings,
    debug: {
      previousDebug: current.debug,
      ignoredCommand: { type, payload },
    },
  };

  return storeLocalEnvelope(updated, getLocalEntry(analysisId)?.accessToken);
}

async function frontendOnlySolve(analysisId: string, _token: string, version: number): Promise<AnalysisEnvelope> {
  const current = getLocalEntry(analysisId)?.envelope;
  if (current) return current;

  const envelope = makeBaseEnvelope({
    analysisId,
    stateVersion: version + 1,
    recommendation: makeDefaultRecommendation(
      'blocked_missing_data',
      'frontend_no_local_capture',
      ['frontend_no_local_capture'],
    ),
    warnings: ['No local frontend capture exists for this analysis id. Paste/upload a screenshot again.'],
  });
  return storeLocalEnvelope(envelope);
}

async function frontendOnlyDeleteAnalysis(analysisId: string): Promise<void> {
  frontendLocalAnalyses.delete(analysisId);
}

async function frontendOnlyFetchAssetUrl(analysisId: string, kind: 'normalised' | 'thumbnail' | 'annotated'): Promise<string> {
  const entry = getLocalEntry(analysisId);
  const image = entry?.imageUrl ?? entry?.envelope.image?.url ?? entry?.envelope.image?.previewUrl;
  if (!image) throw new Error(`Frontend-only asset ${kind} is not available yet.`);
  return image;
}

export async function createAnalysis(locale = 'fr'): Promise<CreateAnalysisResponse> {
  if (isFrontendOnlyApiMode()) return frontendOnlyCreateAnalysis(locale);

  const response = await fetch(`${API}/analyses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      schemaVersion: '0.8.0',
      locale,
      retentionConsent: 'ephemeral_only',
      qualityImprovementConsent: false,
    }),
  });
  if (!response.ok) throw new Error('Création impossible');
  return response.json() as Promise<CreateAnalysisResponse>;
}

export async function uploadImage(id: string, token: string, version: number, file: File): Promise<AnalysisEnvelope> {
  if (isFrontendOnlyApiMode()) return frontendOnlyUploadImage(id, token, version, file);

  const body = new FormData();
  body.append('file', file);
  body.append('expectedStateVersion', String(version));
  const response = await fetch(`${API}/analyses/${id}/image`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body,
  });
  if (!response.ok) throw new Error('Image refusée');
  return response.json() as Promise<AnalysisEnvelope>;
}

export async function command(id: string, token: string, version: number, type: string, payload: object): Promise<AnalysisEnvelope> {
  if (isFrontendOnlyApiMode()) return frontendOnlyCommand(id, token, version, type, payload);

  const response = await fetch(`${API}/analyses/${id}/commands`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      schemaVersion: '0.6.0',
      commandId: `cmd_${crypto.randomUUID().replaceAll('-', '')}`,
      analysisId: id,
      expectedStateVersion: version,
      type,
      payload,
      issuedAt: new Date().toISOString(),
    }),
  });
  if (!response.ok) throw new Error((await response.json()).error?.code ?? 'Commande refusée');
  return response.json() as Promise<AnalysisEnvelope>;
}

export async function solve(id: string, token: string, version: number): Promise<AnalysisEnvelope> {
  if (isFrontendOnlyApiMode()) return frontendOnlySolve(id, token, version);

  const response = await fetch(`${API}/analyses/${id}/solve`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      schemaVersion: '0.8.0',
      expectedStateVersion: version,
      mode: 'review',
      maxAlternatives: 2,
      confirmedSingleSourceRuleIds: [],
    }),
  });
  if (!response.ok) throw new Error((await response.json()).error?.code ?? 'Solveur indisponible');
  return response.json() as Promise<AnalysisEnvelope>;
}

export async function deleteAnalysis(id: string, token: string): Promise<void> {
  if (isFrontendOnlyApiMode()) return frontendOnlyDeleteAnalysis(id);

  const response = await fetch(`${API}/analyses/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok && response.status !== 404) throw new Error('Suppression impossible');
}

export async function fetchAssetUrl(
  id: string,
  token: string,
  kind: 'normalised' | 'thumbnail' | 'annotated',
): Promise<string> {
  if (isFrontendOnlyApiMode()) return frontendOnlyFetchAssetUrl(id, kind);

  const response = await fetch(`${API}/analyses/${id}/asset/${kind}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });
  if (!response.ok) throw new Error(`Asset ${kind} indisponible`);
  return URL.createObjectURL(await response.blob());
}
