'use client';

import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { command, createAnalysis, deleteAnalysis, solve, uploadImage, type AnalysisEnvelope } from '../lib/api';


type FightSnapshot = NonNullable<AnalysisEnvelope['fight']>;
const FIGHT_RESUME_KEY = 'grougalorasalar:fight-resume:v1';

function loadFightSnapshot(): FightSnapshot | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(FIGHT_RESUME_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { fight?: FightSnapshot };
    return parsed.fight ?? null;
  } catch {
    return null;
  }
}

function saveFightSnapshot(fight?: AnalysisEnvelope['fight'] | null): void {
  if (typeof window === 'undefined' || !fight) return;
  try {
    window.sessionStorage.setItem(FIGHT_RESUME_KEY, JSON.stringify({
      schemaVersion: 1,
      savedAt: new Date().toISOString(),
      fight,
    }));
  } catch {
    // Session resume is best-effort only.
  }
}

function clearFightSnapshot(): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(FIGHT_RESUME_KEY);
  } catch {
    // ignore
  }
}

function isSessionLostError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return message.includes('API-AUTH-NOT-FOUND') || message.includes('API-STATE-EXPIRED');
}


const spellKeys = ['indecision', 'reflection', 'repulsion', 'attraction'] as const;
type SpellKey = (typeof spellKeys)[number];
type Availability = 'unknown' | 'available' | 'unavailable';
type Cell = { x: number; y: number };
type Point = { x: number; y: number };
type CorrectionMode = 'player' | 'glyph-black' | 'glyph-white' | null;

const spellLabels: Record<SpellKey, string> = {
  indecision: 'Indécision', reflection: 'Reflet', repulsion: 'Rejet', attraction: 'Attrait',
};

type TurnState = {
  player?: { current?: Cell | null };
  pillars?: Array<{ id: string; cell: Cell; spellType: SpellKey }>;
  glyphs?: { blackOffsets?: Array<{ dx: number; dy: number }>; whiteOffsets?: Array<{ dx: number; dy: number }> };
  resources?: {
    actionBudget?: number | null;
    spells?: Record<SpellKey, { availability: Availability; confirmed: boolean }>;
  };
  flags?: { criticalFieldsConfirmed?: boolean; pillarSetComplete?: boolean; anchorConfirmed?: boolean };
};

type Registration = { originImage?: Point; basisXImage?: Point; basisYImage?: Point };
type RecommendationAction = NonNullable<AnalysisEnvelope['recommendation']>['actions'][number];
type PillarProposal = { id: string; cell: Cell; spellType: SpellKey; confidence?: number; snapResidualCell?: number };
type Recognition = NonNullable<AnalysisEnvelope['recognition']> & {
  registration?: Registration;
  proposals?: {
    player?: { cell: Cell; confidence?: number } | null;
    pillars?: PillarProposal[];
    glyphPattern?: { anchorCell?: Cell; unknownCandidateCells?: Cell[] } | null;
  };
};

type WorkerStage = { stage: string; elapsedMs: number };
const stageLabels: Record<string, string> = {
  preview_ready: 'Aperçu local prêt', decode_started: 'Décodage local', decode_complete: 'Image décodée',
  working_copy_ready: 'Copie de travail créée', preprocessing_complete: 'Prétraitement terminé',
  session_created: 'Session privée créée', upload_running: 'Chargement de l’arène (30–35 s au premier chargement)',
  recognition_complete: 'Éléments détectés — vérification requise',
};

function project(cell: Cell, registration?: Registration): Point | null {
  const o = registration?.originImage;
  const bx = registration?.basisXImage;
  const by = registration?.basisYImage;
  if (!o || !bx || !by) return null;
  return { x: o.x + cell.x * bx.x + cell.y * by.x, y: o.y + cell.x * bx.y + cell.y * by.y };
}

function polygon(cell: Cell, registration?: Registration): string | null {
  const c = project(cell, registration);
  const bx = registration?.basisXImage;
  const by = registration?.basisYImage;
  if (!c || !bx || !by) return null;
  return [
    [c.x - (bx.x + by.x) / 2, c.y - (bx.y + by.y) / 2],
    [c.x + (bx.x - by.x) / 2, c.y + (bx.y - by.y) / 2],
    [c.x + (bx.x + by.x) / 2, c.y + (bx.y + by.y) / 2],
    [c.x + (-bx.x + by.x) / 2, c.y + (-bx.y + by.y) / 2],
  ].map(point => point.join(',')).join(' ');
}

function unproject(point: Point, registration?: Registration): Cell | null {
  const o = registration?.originImage;
  const bx = registration?.basisXImage;
  const by = registration?.basisYImage;
  if (!o || !bx || !by) return null;
  const determinant = bx.x * by.y - by.x * bx.y;
  if (Math.abs(determinant) < 0.0001) return null;
  const dx = point.x - o.x;
  const dy = point.y - o.y;
  return {
    x: Math.round((dx * by.y - dy * by.x) / determinant),
    y: Math.round((bx.x * dy - bx.y * dx) / determinant),
  };
}

function layoutActionPins(
  actions: RecommendationAction[],
  registration: Registration | undefined,
  imageSize: { width: number; height: number },
  finalCell?: Cell | null,
): Array<Point | null> {
  const offsets = [
    { x: 0, y: -42 }, { x: 44, y: -28 }, { x: -44, y: -28 },
    { x: 44, y: 28 }, { x: -44, y: 28 }, { x: 0, y: 42 },
    { x: 72, y: 0 }, { x: -72, y: 0 },
  ];
  const occupied: Point[] = [];
  const finalPoint = finalCell ? project(finalCell, registration) : null;
  if (finalPoint) occupied.push(finalPoint);
  return actions.map(action => {
    const target = action.targetCell && project(action.targetCell, registration);
    if (!target) return null;
    const candidates = offsets
      .map(offset => ({ x: target.x + offset.x, y: target.y + offset.y }))
      .filter(point => point.x >= 28 && point.x <= imageSize.width - 28 && point.y >= 28 && point.y <= imageSize.height - 28);
    const fallback = {
      x: Math.max(28, Math.min(imageSize.width - 28, target.x)),
      y: Math.max(28, Math.min(imageSize.height - 28, target.y - 42)),
    };
    const pin = (candidates.length ? candidates : [fallback]).reduce((best, candidate) => {
      const clearance = Math.min(...occupied.map(point => Math.hypot(candidate.x - point.x, candidate.y - point.y)), Number.POSITIVE_INFINITY);
      const bestClearance = Math.min(...occupied.map(point => Math.hypot(best.x - point.x, best.y - point.y)), Number.POSITIVE_INFINITY);
      return clearance > bestClearance ? candidate : best;
    });
    occupied.push(pin);
    return pin;
  });
}

function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob | null> {
  return new Promise(resolve => canvas.toBlob(resolve, type, quality));
}

export default function Home() {
  const [token, setToken] = useState('');
  const [data, setData] = useState<AnalysisEnvelope | null>(null);
  const [imageUrl, setImageUrl] = useState('');
  const [imageSize, setImageSize] = useState({ width: 1, height: 1 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState<WorkerStage>({ stage: 'preview_ready', elapsedMs: 0 });
  const [elapsedMs, setElapsedMs] = useState(0);
  const [correctionMode, setCorrectionMode] = useState<CorrectionMode>(null);
  const [pillarOverlayReviewed, setPillarOverlayReviewed] = useState(false);
  const [debug, setDebug] = useState(false);
  const [captureActive, setCaptureActive] = useState(false);
  const startedAt = useRef<number | null>(null);
  const requestSequence = useRef(0);
  const captureStream = useRef<MediaStream | null>(null);
  const captureVideo = useRef<HTMLVideoElement | null>(null);

  const turn = (data?.turnState ?? {}) as TurnState;
  const fight = data?.fight;
  const recognition = (data?.recognition ?? {}) as Recognition;
  const registration = recognition.registration;
  const pillars = turn.pillars ?? [];
  const player = turn.player?.current ?? null;
  const glyphAnchor = recognition.proposals?.glyphPattern?.anchorCell ?? { x: 0, y: 0 };
  const blackCells = (turn.glyphs?.blackOffsets ?? []).map(item => ({ x: glyphAnchor.x + item.dx, y: glyphAnchor.y + item.dy }));
  const whiteCells = (turn.glyphs?.whiteOffsets ?? []).map(item => ({ x: glyphAnchor.x + item.dx, y: glyphAnchor.y + item.dy }));
  const glyphCount = blackCells.length + whiteCells.length;
  const proposalById = useMemo(() => new Map((recognition.proposals?.pillars ?? []).map(item => [item.id, item])), [recognition]);
  const doubtfulPillars = pillars.filter(item => (proposalById.get(item.id)?.confidence ?? 0) < 0.8);
  const spells = turn.resources?.spells;
  const spellsKnown = Boolean(spells && spellKeys.every(key => spells[key]?.confirmed && spells[key]?.availability !== 'unknown'));
  const checks = [
    { label: 'Joueur reconnu', ok: Boolean(player) },
    { label: 'Piliers complets', ok: Boolean(turn.flags?.pillarSetComplete) },
    { label: 'Motif reconnu', ok: glyphCount > 0 && Boolean(turn.flags?.anchorConfirmed) },
    { label: 'Budget d’actions connu', ok: turn.resources?.actionBudget !== null && turn.resources?.actionBudget !== undefined },
    { label: 'État des sorts connu', ok: spellsKnown },
  ];
  const ready = checks.every(item => item.ok) && Boolean(turn.flags?.criticalFieldsConfirmed);

  useEffect(() => {
    setDebug(new URLSearchParams(window.location.search).get('debug') === '1');
  }, []);

  useEffect(() => {
    if (!busy || startedAt.current === null) return;
    const timer = window.setInterval(() => setElapsedMs(performance.now() - (startedAt.current ?? performance.now())), 100);
    return () => window.clearInterval(timer);
  }, [busy]);

  useEffect(() => () => { if (imageUrl.startsWith('blob:')) URL.revokeObjectURL(imageUrl); }, [imageUrl]);

  useEffect(() => () => captureStream.current?.getTracks().forEach(track => track.stop()), []);


  function startLocalWorker(file: File) {
    if (typeof Worker === 'undefined') return;
    const worker = new Worker('/workers/analysis-worker.js');
    worker.onmessage = (event: MessageEvent<WorkerStage & { type: string }>) => {
      if (event.data.type === 'stage') setProgress(event.data);
      if (event.data.type === 'complete' || event.data.type === 'error') worker.terminate();
    };
    worker.postMessage({ file });
  }

  function stopWindowCapture() {
    captureStream.current?.getTracks().forEach(track => track.stop());
    captureStream.current = null;
    if (captureVideo.current) captureVideo.current.srcObject = null;
    setCaptureActive(false);
  }

  async function chooseGameWindow() {
    setError('');
    if (!navigator.mediaDevices?.getDisplayMedia) {
      setError('La capture de fenetre n est pas disponible dans ce navigateur. Choisissez une fenetre compatible ou utilisez un autre navigateur.');
      return;
    }
    try {
      stopWindowCapture();
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'window' }, audio: false,
      });
      captureStream.current = stream;
      if (captureVideo.current) {
        captureVideo.current.srcObject = stream;
        await captureVideo.current.play();
      }
      stream.getVideoTracks()[0]?.addEventListener('ended', stopWindowCapture, { once: true });
      setCaptureActive(true);
    } catch (reason) {
      if ((reason as DOMException)?.name !== 'NotAllowedError') {
        setError('La fenetre Dofus n a pas pu etre ouverte. Reessayez puis choisissez la fenetre Dofus.');
      }
    }
  }

  async function captureGameWindow() {
    const video = captureVideo.current;
    if (!captureStream.current || !video || !video.videoWidth || !video.videoHeight) {
      setError('La fenêtre de jeu n’est pas encore prête. Réessayez dans un instant.');
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0, canvas.width, canvas.height);
    const webp = await canvasToBlob(canvas, 'image/webp', 0.94);
    const blob = webp ?? await canvasToBlob(canvas, 'image/png');
    if (!blob) {
      setError('La capture n a pas pu etre creee.');
      return;
    }
    const extension = webp ? 'webp' : 'png';
    const mimeType = webp ? 'image/webp' : 'image/png';
    await begin(new File([blob], `tour-${(fight?.round ?? 0) + 1}.${extension}`, { type: mimeType }));
  }

  async function begin(file: File) {
    const requestId = ++requestSequence.current;
    startedAt.current = performance.now();
    const continuingFight = Boolean(data && token && data.recommendation);
    setElapsedMs(0); setBusy(true); setError(''); setCorrectionMode(null); setPillarOverlayReviewed(false);
    if (!continuingFight) setData(null);
    if (imageUrl.startsWith('blob:')) URL.revokeObjectURL(imageUrl);
    setImageUrl(URL.createObjectURL(file));
    setProgress({ stage: 'preview_ready', elapsedMs: 0 });
    if (debug) startLocalWorker(file);
    try {
      let analysisId: string;
      let accessToken: string;
      let stateVersion: number;
      if (continuingFight && data) {
        analysisId = data.session.analysisId;
        accessToken = token;
        stateVersion = data.session.stateVersion;
      } else {
        const created = await createAnalysis('fr');
        analysisId = created.session.analysisId;
        accessToken = created.accessToken;
        stateVersion = created.session.stateVersion;
        setToken(created.accessToken);
        setProgress({ stage: 'session_created', elapsedMs: performance.now() - (startedAt.current ?? performance.now()) });
      }
      const uploaded = await uploadImage(analysisId, accessToken, stateVersion, file);
      if (requestId !== requestSequence.current) return;
      setData(uploaded);
      saveFightSnapshot(uploaded.fight);
      if (uploaded.fight?.syncStatus === 'player_mismatch') {
        setError('La position du joueur ne correspond pas à la fin calculée du tour précédent. Le combat n’a pas été avancé.');
      }
      setProgress({ stage: 'recognition_complete', elapsedMs: performance.now() - (startedAt.current ?? performance.now()) });
    } catch (error) {
      console.error('Capture analysis failed', error);
      if (requestId === requestSequence.current) {
        const message = error instanceof Error ? error.message : String(error);
        if (isSessionLostError(error)) {
          const resumeFight = data?.fight ?? loadFightSnapshot();
          if (resumeFight) {
            try {
              const recovered = await createAnalysis('fr', resumeFight);
              setToken(recovered.accessToken);
              setProgress({ stage: 'session_created', elapsedMs: performance.now() - (startedAt.current ?? performance.now()) });
              const uploaded = await uploadImage(
                recovered.session.analysisId,
                recovered.accessToken,
                recovered.session.stateVersion,
                file,
              );
              if (requestId !== requestSequence.current) return;
              setData(uploaded);
              saveFightSnapshot(uploaded.fight);
              if (uploaded.fight?.syncStatus === 'player_mismatch') {
                setError('La position du joueur ne correspond pas a la fin calculee du tour precedent. Le combat n a pas ete avance.');
              } else {
                setError('');
              }
              setProgress({ stage: 'recognition_complete', elapsedMs: performance.now() - (startedAt.current ?? performance.now()) });
              return;
            } catch (recoveryError) {
              console.error('Session recovery failed', recoveryError);
            }
          }

          setToken('');
          setData(null);
          clearFightSnapshot();
          setError('La session du combat a expire ou le serveur a redemarre. Lancez un nouveau combat.');
        } else {
          setError(message);
        }
      }
    } finally {
      if (requestId === requestSequence.current) {
        setBusy(false); setElapsedMs(performance.now() - (startedAt.current ?? performance.now()));
      }
    }
  }

  async function newFight() {
    requestSequence.current += 1;
    if (data && token) await deleteAnalysis(data.session.analysisId, token).catch(() => undefined);
    if (imageUrl.startsWith('blob:')) URL.revokeObjectURL(imageUrl);
    setData(null); setToken(''); setImageUrl(''); setError(''); setBusy(false); clearFightSnapshot();
  }

  async function send(type: string, payload: object) {
    if (!data) return null;
    setBusy(true); setError('');
    try {
      const updated = await command(data.session.analysisId, token, data.session.stateVersion, type, payload);
      setData(updated);
      saveFightSnapshot(updated.fight);
      return updated;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'La modification n a pas pu etre enregistree. Reessayez.');
      return null;
    } finally { setBusy(false); }
  }

  async function runSolver() {
    if (!data || !ready) return;
    setBusy(true); setError('');
    try {
      const updated = await solve(data.session.analysisId, token, data.session.stateVersion);
      setData(updated);
      saveFightSnapshot(updated.fight);
    }
    catch (error) { setError(error instanceof Error ? error.message : 'Le calcul n a pas abouti. Reessayez.'); }
    finally { setBusy(false); }
  }

  async function handleBoardClick(event: MouseEvent<SVGSVGElement>) {
    if (!correctionMode || !registration || busy) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const cell = unproject({
      x: (event.clientX - rect.left) * imageSize.width / rect.width,
      y: (event.clientY - rect.top) * imageSize.height / rect.height,
    }, registration);
    if (!cell) return;
    if (correctionMode === 'player') await send('set_player_cell', { cell });
    else await send('paint_glyph_cell', {
      colour: correctionMode === 'glyph-black' ? 'black' : 'white',
      offset: { dx: cell.x - glyphAnchor.x, dy: cell.y - glyphAnchor.y },
    });
    setCorrectionMode(null);
  }

  const recommendation = data?.recommendation ? {
    ...data.recommendation,
    actions: data.recommendation.actions.map((action, index) => ({
      ...action,
      order: index + 1,
      // Public canonical signatures describe mechanics and may repeat when a
      // spell targets the same pillar twice. React keys must remain unique.
      canonicalSignature: `${action.canonicalSignature}::display-${index + 1}`,
    })),
  } : undefined;
  const actionPins = layoutActionPins(
    recommendation?.actions ?? [],
    registration,
    imageSize,
    recommendation?.expected.finalCell,
  );
  const castCounts = recommendation?.actions.reduce<Record<string, number>>((counts, action) => {
    if (action.spell) counts[action.spell] = (counts[action.spell] ?? 0) + 1;
    return counts;
  }, {}) ?? {};

  return (
    <main>
      <header>
        <p className="eyebrow">ASSISTANT DE TOUR</p>
        <h1>Grougalorasalar Solver</h1>
        <p>Selectionnez votre fenetre Dofus, puis capturez chaque debut de tour.</p>
        {fight && data && <p className="turn-label">Tour {fight.round}</p>}
        <div className="capture-controls">
          <button type="button" className="choose-window" onClick={chooseGameWindow} disabled={busy}>{captureActive ? 'Changer la fenêtre Dofus' : 'Choisir la fenêtre Dofus'}</button>
          <button type="button" className="capture-turn" onClick={captureGameWindow} disabled={!captureActive || busy}>Capturer ce tour</button>
          {captureActive && <button type="button" className="stop-window" onClick={stopWindowCapture} disabled={busy}>Arrêter</button>}
          {error && <p className="capture-error" role="alert">{error}</p>}
        </div>
        <video ref={captureVideo} className="capture-source" muted playsInline aria-hidden="true" />
      </header>

      {busy && <div className="loading-banner" role="status" aria-live="polite"><span className="spinner" aria-hidden="true" /><strong>{data ? 'Analyse de la capture…' : 'Analyse de l’arène…'}</strong></div>}
      {!imageUrl && <section className="upload">
        <div className="setup-guide" aria-label="Instructions de capture">
          <p className="step">MODE D'EMPLOI</p>
          <h2>Capturer chaque tour</h2>
          <ol className="setup-steps">
            <li><span>1</span><p><strong>Choisissez votre fenetre Dofus.</strong><br />Cliquez sur Choisir la fenetre Dofus, puis selectionnez le jeu.</p></li>
            <li><span>2</span><p><strong>Masquez les modules.</strong><br />En combat, ouvrez les trois points &quot;...&quot; en haut a droite, puis cliquez sur &quot;Masquer tous les modules&quot;.</p></li>
            <li><span>3</span><p><strong>Capturez chaque debut de tour.</strong><br />A chaque debut de tour, cliquez sur Capturer ce tour.</p></li>
          </ol>
        </div>
        {debug && <label>Fixture locale<input aria-label="Capture du combat (debug)" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={event => event.target.files?.[0] && begin(event.target.files[0])} /></label>}
      </section>}

      {imageUrl && <div className={data ? 'workspace' : 'workspace preview-only'}>
        <section className="board-card">
          <div className={`board-image ${correctionMode ? 'is-correcting' : ''}`}>
            <img src={imageUrl} alt="Capture du combat à vérifier" onLoad={event => setImageSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })} />
            {data && registration?.originImage && <svg data-testid="detection-overlay" className="overlay" viewBox={`0 0 ${imageSize.width} ${imageSize.height}`} onClick={handleBoardClick} role="img" aria-label="Repères détectés sur la capture">
              {debug && pillars.map(item => {
                const centre = project(item.cell, registration); const points = polygon(item.cell, registration);
                const doubtful = doubtfulPillars.some(candidate => candidate.id === item.id);
                if (!centre || !points) return null;
                return <g key={item.id} data-testid="pillar-overlay">
                  <polygon points={points} className={doubtful ? 'pillar-cell doubtful' : 'pillar-cell'} />
                  <text x={centre.x} y={centre.y - 2} className="overlay-label">{item.id}</text>
                  <text x={centre.x} y={centre.y + 14} className="overlay-sub">{spellLabels[item.spellType].slice(0, 3).toUpperCase()}</text>
                </g>;
              })}
              {debug && blackCells.map((cell, index) => { const centre = project(cell, registration); return centre && <circle key={`b-${index}`} data-testid="glyph-overlay" cx={centre.x} cy={centre.y} r="15" className="glyph black" />; })}
              {debug && whiteCells.map((cell, index) => { const centre = project(cell, registration); return centre && <circle key={`w-${index}`} data-testid="glyph-overlay" cx={centre.x} cy={centre.y} r="15" className="glyph white" />; })}
              {debug && player && (() => { const centre = project(player, registration); const points = polygon(player, registration); return centre && points && <g data-testid="player-overlay"><polygon points={points} className="player-cell" /><circle cx={centre.x} cy={centre.y} r="9" className="player-dot" /><text x={centre.x} y={centre.y - 18} className="player-label">JOUEUR</text></g>; })()}
              {recommendation?.actions.map((action, index) => {
                const target = action.targetCell && project(action.targetCell, registration);
                const source = action.sourceCell && project(action.sourceCell, registration);
                const destination = action.destinationCell && project(action.destinationCell, registration);
                return <g key={`solution-path-${index}-${action.canonicalSignature}`}>
                  {source && target && action.targetKind === 'pillar' && <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} className="target-line" />}
                  {source && destination && <line x1={source.x} y1={source.y} x2={destination.x} y2={destination.y} className="movement-line" />}
                </g>;
              })}
              {recommendation?.expected.finalCell && (() => { const centre = project(recommendation.expected.finalCell, registration); return centre && <circle data-testid="final-cell-marker" cx={centre.x} cy={centre.y} r="30" className="final-cell" />; })()}
              {(recommendation?.expected.whitePillarIds ?? []).map(id => { const pillar = pillars.find(item => item.id === id); const centre = pillar && project(pillar.cell, registration); return centre && <text key={`white-hit-${id}`} x={centre.x + 22} y={centre.y - 28} className="white-hit">+</text>; })}
              {(recommendation?.expected.blackPillarIds ?? []).map(id => { const pillar = pillars.find(item => item.id === id); const centre = pillar && project(pillar.cell, registration); return centre && <text key={`black-hit-${id}`} x={centre.x + 22} y={centre.y - 28} className="black-hit">×</text>; })}
              {recommendation?.actions.map((action, index) => {
                const target = action.targetCell && project(action.targetCell, registration);
                const pin = actionPins[index];
                const displayOrder = index + 1;
                return target && pin && <g key={`solution-pin-${displayOrder}-${action.canonicalSignature}`} data-testid="action-target-marker" data-action-order={displayOrder}>
<circle cx={pin.x} cy={pin.y} r="22" className="action-pin" />
                  <text data-testid="action-number" x={pin.x} y={pin.y + 8} className="action-number">{displayOrder}</text>
                </g>;
              })}
            </svg>}
          </div>
          {data && debug && <div className="summary-grid">
            <div className={player ? 'summary ok' : 'summary warn'}><strong>{player ? 'Joueur détecté' : 'Joueur à corriger'}</strong><span>Repère cyan sur la capture</span></div>
            <div className={pillars.length ? 'summary ok' : 'summary warn'}><strong>{pillars.length} piliers proposés</strong><span>{doubtfulPillars.length ? `${doubtfulPillars.length} à vérifier en orange` : 'Tous clairement positionnés'}</span></div>
            <div className={glyphCount ? 'summary ok' : 'summary warn'}><strong>{glyphCount ? `${glyphCount} cases du motif` : 'Motif à corriger'}</strong><span>{glyphCount ? 'Noires et blanches sur la capture' : 'Le motif central n’a pas été détecté.'}</span></div>
          </div>}
          {correctionMode && <p className="click-hint">Cliquez directement sur la bonne case de la capture.</p>}
        </section>

        {data && !debug && <aside className="player-panel">{recommendation ? <><p className="step">VOTRE TOUR</p><h2>{recommendation.status === 'ambiguous_input' ? 'Nouvelle capture nécessaire' : recommendation.status === 'invalid_screenshot' && !((data.turnState as any)?.player?.current) ? 'Joueur introuvable' : recommendation.status === 'invalid_screenshot' ? 'Capture illisible' : recommendation.status === 'no_safe_solution' ? 'Aucun coup sûr' : recommendation.status === 'capacity_error' ? 'Calcul interrompu' : recommendation.status === 'blocked_missing_data' ? 'Capture incomplète' : recommendation.status === 'blocked_unverified_rule' ? 'Correction nécessaire' : 'Actions à exécuter'}</h2>{recommendation.actions.length > 0 && <ol className="action-list">{recommendation.actions.map(action => <li key={action.canonicalSignature}><span>{action.order}</span><strong>{spellLabels[action.spell as SpellKey]}</strong><small>cible marquée {action.order}</small></li>)}<li className="end-turn"><span>{recommendation.actions.length + 1}</span><strong>Terminez le tour</strong></li></ol>}{recommendation.expected.finalCell && <div className="outcome"><p><strong>Position finale</strong><br />Anneau vert sur la capture</p><p><strong>Glyphes noirs</strong><br />{recommendation.expected.blackPillarIds?.length ? `${recommendation.expected.blackPillarIds.length} collision(s) marquée(s)` : 'Aucune collision'}</p><p><strong>Glyphes blancs</strong><br />{recommendation.expected.whitePillarIds?.length ? `${recommendation.expected.whitePillarIds.length} recharge(s) marquée(s)` : 'Aucune recharge'}</p><p><strong>Progression</strong><br />{recommendation.expected.raceOutcome === 'crocoburio_advance' ? 'Crocoburio avance' : recommendation.expected.raceOutcome === 'dragon_advance' ? 'Grougalorasalar avance' : 'Neutre'}</p></div>}{recommendation.expected.nextSpellState && <div className="charges"><strong>Charges : maintenant → prochain tour</strong>{spellKeys.map(spell => <span key={spell}>{spellLabels[spell]} {fight?.charges[spell] ?? '–'} → {recommendation.expected.nextSpellState?.[spell] ?? '–'}<small>{castCounts[spell] ? ` (${castCounts[spell]} utilisée${castCounts[spell] > 1 ? 's' : ''})` : ''}</small></span>)}</div>}{Boolean(recommendation.alternatives?.length) && <details className="alternatives"><summary>Autres options équivalentes</summary>{recommendation.alternatives?.slice(0, 2).map((alternative, index) => <p key={index}>Option {index + 2} · {alternative.sequence.length} action(s)</p>)}</details>}{recommendation.actions.length > 0 ? <p className="next-paste">Exécutez les actions, terminez le tour, puis cliquez sur Capturer ce tour au début du prochain tour.</p> : recommendation.status === 'no_safe_solution' ? <p className="next-paste"><strong>Le dragon noir a triché. Classique.</strong><br />Ce tour-ci, aucune action sûre n’est possible : restez sur place et terminez le tour. On garde le plan — la victoire reste jouable.</p> : recommendation.status === 'capacity_error' ? <p className="next-paste">Le calcul a été interrompu. Relancez la capture ; si cela se répète, jouez ce tour manuellement.</p> : <p className="next-paste">Aucune action sûre à exécuter. Reprenez une capture complète ou corrigez les éléments signalés.</p>}<button className="new-fight" onClick={newFight}>Nouveau combat</button></> : <><p className="step">ANALYSE</p><h2>Calcul en cours…</h2></>}</aside>}

        {data && debug && <aside>
          <div className="aside-heading"><div><p className="step">DIAGNOSTIC</p><h2>État détecté</h2></div></div>

          <section className="review-block">
            <h3>Joueur</h3><p>{player ? 'Le repère cyan montre la figurine contrôlée.' : 'Aucun joueur fiable n’a été trouvé.'}</p>
            <button className={correctionMode === 'player' ? 'active' : ''} onClick={() => setCorrectionMode(correctionMode === 'player' ? null : 'player')}>Corriger par un clic sur l’image</button>
          </section>

          <section className="review-block">
            <h3>Piliers · {pillars.length}</h3><div className="pillar-list" aria-label="Liste complète des piliers détectés">{pillars.map(item => <span key={item.id} className={(proposalById.get(item.id)?.confidence ?? 0) < 0.8 ? 'pill doubtful' : 'pill'}>{item.id} · {spellLabels[item.spellType]}</span>)}</div>
            <label className="review-check"><input type="checkbox" checked={pillarOverlayReviewed} onChange={event => setPillarOverlayReviewed(event.target.checked)} />J’ai vérifié toute la liste sur l’image.</label>
            <button disabled={!pillarOverlayReviewed || !pillars.length || busy} onClick={() => send('set_pillar_set_complete', { complete: true })}>{turn.flags?.pillarSetComplete ? '✓ Piliers confirmés' : 'Confirmer tous les piliers'}</button>
          </section>

          <section className="review-block">
            <h3>Motif central</h3>{glyphCount === 0 && <p className="warning">Le motif central n’a pas été détecté.</p>}
            <div className="button-row"><button className={correctionMode === 'glyph-black' ? 'active' : ''} onClick={() => setCorrectionMode('glyph-black')}>Ajouter une case sombre</button><button className={correctionMode === 'glyph-white' ? 'active' : ''} onClick={() => setCorrectionMode('glyph-white')}>Ajouter une case claire</button></div>
            <button disabled={!glyphCount || busy} onClick={() => send('set_projection_anchor_confirmation', { confirmed: true })}>{turn.flags?.anchorConfirmed ? '✓ Motif confirmé' : 'Confirmer le motif affiché'}</button>
          </section>

          <section className="review-block">
            <h3>Budget d’actions</h3><div className="choice-row" role="group" aria-label="Budget d’actions">{[0, 1, 2, 3, 4, 5, 6].map(value => <button key={value} disabled={busy} className={turn.resources?.actionBudget === value ? 'selected' : ''} onClick={() => send('set_action_budget', { value })}>{value}</button>)}</div>
          </section>

          <section className="review-block spells"><h3>État des quatre sorts</h3>{spellKeys.map(spell => <div className="spell-row" key={spell}><span>{spellLabels[spell]}</span><div role="group" aria-label={`État de ${spellLabels[spell]}`}>{(['unknown', 'available', 'unavailable'] as Availability[]).map(value => <button key={value} disabled={busy} className={spells?.[spell]?.availability === value ? 'selected' : ''} onClick={() => send('set_spell_state', { spell, availability: value, value: null, confirmed: value !== 'unknown' })}>{value === 'unknown' ? '?' : value === 'available' ? 'Disponible' : 'Indisponible'}</button>)}</div></div>)}</section>

          <button disabled={busy} className={turn.flags?.criticalFieldsConfirmed ? 'confirmed-detection' : ''} onClick={() => send('accept_detection', {})}>{turn.flags?.criticalFieldsConfirmed ? '✓ Détections vérifiées' : 'Valider les éléments détectés'}</button>

          <div className="readiness"><h3>Prêt pour le calcul ?</h3><ul>{checks.map(item => <li key={item.label} className={item.ok ? 'done' : ''}><span>{item.ok ? '✓' : '○'}</span>{item.label}</li>)}</ul>{!turn.flags?.criticalFieldsConfirmed && <p>Validez aussi les éléments détectés.</p>}</div>
          <button className="solve" onClick={runSolver} disabled={busy || !ready}>Debug · lancer le solveur</button>

          {debug && <section className="debug-panel"><h3>Informations de diagnostic</h3><dl><dt>État</dt><dd>{data.session.state}</dd><dt>Version</dt><dd>{data.session.stateVersion}</dd><dt>Analyse</dt><dd>{data.recognition?.metrics?.path ?? 'inconnue'}</dd><dt>Blocages</dt><dd>{data.session.gate.blockingReasonCodes.join(', ') || 'aucun'}</dd></dl></section>}
        </aside>}
      </div>}

      <footer className="site-credit">© 2026 Pawmi (Sinaninho)</footer>
    </main>
  );
}
