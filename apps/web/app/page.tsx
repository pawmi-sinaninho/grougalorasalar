'use client';

import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { command, createAnalysis, solve, uploadImage, type AnalysisEnvelope } from '../lib/api';

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
  session_created: 'Session privée créée', upload_running: 'Analyse de l’arène',
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
  const startedAt = useRef<number | null>(null);
  const lastAutoSolvedVersion = useRef<number | null>(null);

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
    if (!busy || startedAt.current === null) return;
    const timer = window.setInterval(() => setElapsedMs(performance.now() - (startedAt.current ?? performance.now())), 100);
    return () => window.clearInterval(timer);
  }, [busy]);

  useEffect(() => () => { if (imageUrl.startsWith('blob:')) URL.revokeObjectURL(imageUrl); }, [imageUrl]);

  useEffect(() => {
    const paste = (event: ClipboardEvent) => {
      const image = Array.from(event.clipboardData?.items ?? []).find(item => item.type.startsWith('image/'))?.getAsFile();
      if (!image) return;
      event.preventDefault();
      void begin(new File([image], image.name || 'capture-collee.png', { type: image.type }));
    };
    window.addEventListener('paste', paste);
    return () => window.removeEventListener('paste', paste);
  });

  useEffect(() => {
    if (!data || !ready || busy || data.recommendation || lastAutoSolvedVersion.current === data.session.stateVersion) return;
    lastAutoSolvedVersion.current = data.session.stateVersion;
    void runSolver();
  }, [busy, data, ready]);

  function startLocalWorker(file: File) {
    if (typeof Worker === 'undefined') return;
    const worker = new Worker('/workers/analysis-worker.js');
    worker.onmessage = (event: MessageEvent<WorkerStage & { type: string }>) => {
      if (event.data.type === 'stage') setProgress(event.data);
      if (event.data.type === 'complete' || event.data.type === 'error') worker.terminate();
    };
    worker.postMessage({ file });
  }

  async function begin(file: File) {
    startedAt.current = performance.now();
    const continuingFight = Boolean(data && token && data.recommendation);
    setElapsedMs(0); setBusy(true); setError(''); setCorrectionMode(null); setPillarOverlayReviewed(false);
    if (!continuingFight) setData(null);
    if (imageUrl.startsWith('blob:')) URL.revokeObjectURL(imageUrl);
    setImageUrl(URL.createObjectURL(file));
    setProgress({ stage: 'preview_ready', elapsedMs: 0 });
    startLocalWorker(file);
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
      setData(uploaded);
      if (uploaded.fight?.syncStatus === 'player_mismatch') {
        setError('La position du joueur ne correspond pas à la fin calculée du tour précédent. Le combat n’a pas été avancé.');
      }
      setProgress({ stage: 'recognition_complete', elapsedMs: performance.now() - (startedAt.current ?? performance.now()) });
    } catch {
      setError('La capture n’a pas pu être analysée. Réessayez avec une capture complète du combat.');
    } finally {
      setBusy(false); setElapsedMs(performance.now() - (startedAt.current ?? performance.now()));
    }
  }

  async function send(type: string, payload: object) {
    if (!data) return null;
    setBusy(true); setError('');
    try {
      const updated = await command(data.session.analysisId, token, data.session.stateVersion, type, payload);
      setData(updated);
      return updated;
    } catch {
      setError('La modification n’a pas pu être enregistrée. Réessayez.');
      return null;
    } finally { setBusy(false); }
  }

  async function runSolver() {
    if (!data || !ready) return;
    setBusy(true); setError('');
    try { setData(await solve(data.session.analysisId, token, data.session.stateVersion)); }
    catch { setError('Le calcul n’a pas abouti. Vérifiez les éléments signalés puis réessayez.'); }
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

  const recommendation = data?.recommendation;

  return (
    <main>
      <header>
        <p className="eyebrow">ASSISTANT DE TOUR · VERSION 0.9.0</p>
        <h1>Grougalorasalar Solver</h1>
        <p>Copiez votre capture de combat puis collez-la ici avec Ctrl+V. La détection et le calcul démarrent automatiquement.</p>
        {fight && <p>Tour {fight.round} · Charges suivies automatiquement : bleu {fight.charges.indecision}, vert {fight.charges.reflection}, jaune {fight.charges.repulsion}, rouge {fight.charges.attraction}.</p>}
      </header>

      {!imageUrl && <section className="upload"><h2>Collez la capture avec Ctrl+V</h2><p>Aucune saisie manuelle n’est nécessaire.</p><button className="debug-toggle" aria-pressed={debug} onClick={() => setDebug(value => !value)}>Debug</button>{debug && <label>Fixture locale<input aria-label="Capture du combat (debug)" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={event => event.target.files?.[0] && begin(event.target.files[0])} /></label>}</section>}

      {imageUrl && <div className={data ? 'workspace' : 'workspace preview-only'}>
        <section className="board-card">
          <div className={`board-image ${correctionMode ? 'is-correcting' : ''}`}>
            <img src={imageUrl} alt="Capture du combat à vérifier" onLoad={event => setImageSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })} />
            {data && registration?.originImage && <svg data-testid="detection-overlay" className="overlay" viewBox={`0 0 ${imageSize.width} ${imageSize.height}`} onClick={handleBoardClick} role="img" aria-label="Repères détectés sur la capture">
              {pillars.map(item => {
                const centre = project(item.cell, registration); const points = polygon(item.cell, registration);
                const doubtful = doubtfulPillars.some(candidate => candidate.id === item.id);
                if (!centre || !points) return null;
                return <g key={item.id} data-testid="pillar-overlay">
                  <polygon points={points} className={doubtful ? 'pillar-cell doubtful' : 'pillar-cell'} />
                  <text x={centre.x} y={centre.y - 2} className="overlay-label">{item.id}</text>
                  <text x={centre.x} y={centre.y + 14} className="overlay-sub">{spellLabels[item.spellType].slice(0, 3).toUpperCase()}</text>
                </g>;
              })}
              {blackCells.map((cell, index) => { const centre = project(cell, registration); return centre && <circle key={`b-${index}`} data-testid="glyph-overlay" cx={centre.x} cy={centre.y} r="15" className="glyph black" />; })}
              {whiteCells.map((cell, index) => { const centre = project(cell, registration); return centre && <circle key={`w-${index}`} data-testid="glyph-overlay" cx={centre.x} cy={centre.y} r="15" className="glyph white" />; })}
              {player && (() => { const centre = project(player, registration); const points = polygon(player, registration); return centre && points && <g data-testid="player-overlay"><polygon points={points} className="player-cell" /><circle cx={centre.x} cy={centre.y} r="9" className="player-dot" /><text x={centre.x} y={centre.y - 18} className="player-label">JOUEUR</text></g>; })()}
            </svg>}
          </div>
          <div className="analysis-strip" aria-live="polite"><strong>{stageLabels[progress.stage] ?? 'Analyse en cours'}</strong><span>{Math.round(elapsedMs || progress.elapsedMs)} ms</span></div>
          {data && <div className="summary-grid">
            <div className={player ? 'summary ok' : 'summary warn'}><strong>{player ? 'Joueur détecté' : 'Joueur à corriger'}</strong><span>Repère cyan sur la capture</span></div>
            <div className={pillars.length ? 'summary ok' : 'summary warn'}><strong>{pillars.length} piliers proposés</strong><span>{doubtfulPillars.length ? `${doubtfulPillars.length} à vérifier en orange` : 'Tous clairement positionnés'}</span></div>
            <div className={glyphCount ? 'summary ok' : 'summary warn'}><strong>{glyphCount ? `${glyphCount} cases du motif` : 'Motif à corriger'}</strong><span>{glyphCount ? 'Noires et blanches sur la capture' : 'Le motif central n’a pas été détecté.'}</span></div>
          </div>}
          {correctionMode && <p className="click-hint">Cliquez directement sur la bonne case de la capture.</p>}
        </section>

        {data && !debug && <aside><div className="aside-heading"><div><p className="step">AUTOMATIQUE · TOUR {fight?.round ?? 1}</p><h2>{ready ? 'Calcul du tour en cours' : 'Analyse de la capture'}</h2></div><button className="debug-toggle" aria-pressed={debug} onClick={() => setDebug(true)}>Debug</button></div><p>Collez uniquement une capture au début de chaque tour. Les charges sont reprises du résultat calculé au tour précédent.</p></aside>}

        {data && debug && <aside>
          <div className="aside-heading"><div><p className="step">VÉRIFICATION</p><h2>Ce qu’il reste à faire</h2></div><button className="debug-toggle" aria-pressed={debug} onClick={() => setDebug(value => !value)}>Debug</button></div>

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

      {recommendation && <section className="result" aria-live="polite"><p className="step">RECOMMANDATION</p><h2>{recommendation.status === 'solved' ? 'Votre tour est prêt' : recommendation.status === 'no_safe_solution' ? 'Aucun déplacement sûr trouvé' : 'Une vérification reste nécessaire'}</h2>{recommendation.actions.length ? <ol>{recommendation.actions.map(action => <li key={action.canonicalSignature}>{action.spell && action.targetPillarId ? `Lancez ${spellLabels[action.spell as SpellKey]} sur le pilier ${action.targetPillarId}.` : action.instruction}</li>)}</ol> : recommendation.status === 'solved' && <p>Terminez ce tour sans lancer de sort.</p>}</section>}
      {error && <p className="error" role="alert">{error}</p>}
    </main>
  );
}
