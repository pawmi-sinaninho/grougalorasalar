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
  recommendation?: {
    status: string;
    statusReasonCodes: string[];
    actions: Array<{ order: number; instruction: string; canonicalSignature: string; spell?: string; targetPillarId?: string | null }>;
    expected: { finalCell: { x: number; y: number } | null; raceOutcome: string };
  } | null;
};

export const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000/api/v1';

export async function createAnalysis(locale = 'fr') {
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


export async function fetchAssetUrl(id: string, token: string, kind: 'normalised' | 'thumbnail' | 'annotated'): Promise<string> {
  const response = await fetch(`${API}/analyses/${id}/asset/${kind}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store'
  });
  if (!response.ok) throw new Error(`Asset ${kind} indisponible`);
  return URL.createObjectURL(await response.blob());
}
