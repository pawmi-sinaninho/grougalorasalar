import { perfFetch } from "./perfFetch";
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
async function apiError(response: Response, fallback: string): Promise<Error> {
  let body = '';
  try {
    body = await response.text();
  } catch {
    body = '';
  }

  let detail = body;
  try {
    const parsed = JSON.parse(body);
    detail = JSON.stringify(parsed.detail ?? parsed.error ?? parsed);
  } catch {
    // keep raw body
  }

  return new Error(`${fallback} [HTTP ${response.status}] ${detail}`);
}
export async function createAnalysis(locale = 'fr') {
  const response = await perfFetch(`${API}/analyses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      schemaVersion: '0.8.0',
      locale,
      retentionConsent: 'ephemeral_only',
      qualityImprovementConsent: false
    })
  });
  if (!response.ok) throw await apiError(response, 'Création impossible');
  return response.json() as Promise<{ session: AnalysisEnvelope['session']; accessToken: string }>;
}

export async function uploadImage(id: string, token: string, version: number, file: File): Promise<AnalysisEnvelope> {
  const body = new FormData();
  body.append('file', file);
  body.append('expectedStateVersion', String(version));
  const response = await fetch(`${API}/analyses/${id}/image`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` },
  body,
  cache: 'no-store',
});
if (!response.ok) throw await apiError(response, 'Image refusée');
  return response.json();
}

export async function command(id: string, token: string, version: number, type: string, payload: object): Promise<AnalysisEnvelope> {
  const response = await perfFetch(`${API}/analyses/${id}/commands`, {
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
  const response = await perfFetch(`${API}/analyses/${id}/solve`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ schemaVersion: '0.8.0', expectedStateVersion: version, mode: 'review', maxAlternatives: 2, confirmedSingleSourceRuleIds: [] })
  });
  if (!response.ok) throw new Error((await response.json()).error?.code ?? 'Solveur indisponible');
  return response.json();
}

export async function deleteAnalysis(id: string, token: string): Promise<void> {
  const response = await perfFetch(`${API}/analyses/${id}`, {
    method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok && response.status !== 404) throw new Error('Suppression impossible');
}


export async function fetchAssetUrl(id: string, token: string, kind: 'normalised' | 'thumbnail' | 'annotated'): Promise<string> {
  const response = await perfFetch(`${API}/analyses/${id}/asset/${kind}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store'
  });
  if (!response.ok) throw new Error(`Asset ${kind} indisponible`);
  return URL.createObjectURL(await response.blob());
}
