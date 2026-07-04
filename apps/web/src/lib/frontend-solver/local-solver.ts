import type { FrontendSolveResult, PipelineTimingsMs, SolverActionStep } from "./types";

export const LOCAL_SPELLS = ["indecision", "reflection", "repulsion", "attraction"] as const;
export type LocalSpellKey = (typeof LOCAL_SPELLS)[number];
export type LocalAvailability = "unknown" | "available" | "unavailable";

export interface LocalCell {
  x: number;
  y: number;
}

export interface LocalPillar {
  id: string;
  cell: LocalCell;
  spellType: LocalSpellKey;
}

export interface LocalSpellState {
  availability?: LocalAvailability;
  value?: number | null;
  confirmed?: boolean;
}

export interface LocalGivenState {
  arena?: {
    walkable?: LocalCell[];
    boundaryUnverified?: LocalCell[];
    occludedUnknown?: LocalCell[];
    permanentBlocked?: LocalCell[];
  };
  player?: { current?: LocalCell | null };
  pillars?: LocalPillar[];
  glyphs?: {
    blackOffsets?: Array<{ dx: number; dy: number }>;
    whiteOffsets?: Array<{ dx: number; dy: number }>;
    physicalBlackCells?: LocalCell[];
    physicalWhiteCells?: LocalCell[];
  };
  resources?: {
    actionBudget?: number | null;
    spells?: Partial<Record<LocalSpellKey, LocalSpellState>>;
  };
  flags?: Record<string, boolean | undefined>;
}

export interface LocalSolverAction {
  actionId: string;
  spell: LocalSpellKey;
  sourceCell: LocalCell;
  destinationCell: LocalCell;
  targetKind: "cell" | "pillar";
  targetCell: LocalCell;
  targetPillarId: string | null;
  canonicalSignature: string;
  instruction: string;
  pathCells: LocalCell[];
}

export interface LocalTerminalCandidate {
  sequence: string[];
  actions: LocalSolverAction[];
  finalCell: LocalCell;
  raceOutcome: "crocoburio_advance" | "dragon_advance" | "neutral" | "unknown";
  blackPillarIds: string[];
  whitePillarIds: string[];
  rechargedSpells: LocalSpellKey[];
  nextSpellState: Record<LocalSpellKey, number>;
  directCenterEffect: "black_adverse" | "white_recharge" | "none";
  remainingBudget: number;
  castCount: number;
}

export interface LocalSolverResult {
  status: "solved" | "no_safe_solution" | "invalid_state" | "capacity_error";
  statusReasonCodes: string[];
  actions: LocalSolverAction[];
  expected: {
    finalCell: LocalCell | null;
    raceOutcome: string;
    blackPillarIds: string[];
    whitePillarIds: string[];
    rechargedSpells: LocalSpellKey[];
    directCenterEffect: string;
    nextSpellState: Record<LocalSpellKey, number> | null;
  };
  diagnostics: {
    terminalCandidates: LocalTerminalCandidate[];
    nodeCount: number;
  };
}

type CellTuple = [number, number];
type CellClass = "walkable" | "boundary" | "occluded" | "blocked" | "outside";

type InternalAction = Omit<LocalSolverAction, "instruction" | "pathCells">;

type SearchNode = {
  cell: CellTuple;
  budget: number;
  actions: InternalAction[];
  castCounts: Record<LocalSpellKey, number>;
  charges: Record<LocalSpellKey, number>;
};

const SPELL_ORDER: Record<LocalSpellKey, number> = {
  indecision: 0,
  reflection: 1,
  repulsion: 2,
  attraction: 3,
};

const DEFAULT_CHARGES: Record<LocalSpellKey, number> = {
  indecision: 2,
  reflection: 2,
  repulsion: 2,
  attraction: 2,
};

function cloneCell(cell: LocalCell): LocalCell {
  return { x: Number(cell.x), y: Number(cell.y) };
}

function cellTuple(cell: LocalCell | CellTuple): CellTuple {
  return Array.isArray(cell) ? [Number(cell[0]), Number(cell[1])] : [Number(cell.x), Number(cell.y)];
}

function cellDict(cell: CellTuple): LocalCell {
  return { x: cell[0], y: cell[1] };
}

function cellKey(cell: LocalCell | CellTuple): string {
  const [x, y] = cellTuple(cell);
  return `${x},${y}`;
}

function sameCell(a: LocalCell | CellTuple, b: LocalCell | CellTuple): boolean {
  const [ax, ay] = cellTuple(a);
  const [bx, by] = cellTuple(b);
  return ax === bx && ay === by;
}

function sign(value: number): number {
  return value === 0 ? 0 : value > 0 ? 1 : -1;
}

function alignment(dx: number, dy: number): "cardinal" | "diagonal" | null {
  if ((dx === 0 && dy !== 0) || (dy === 0 && dx !== 0)) return "cardinal";
  if (dx !== 0 && Math.abs(dx) === Math.abs(dy)) return "diagonal";
  return null;
}

function alignedSteps(dx: number, dy: number): number | null {
  if (dx === 0) return Math.abs(dy);
  if (dy === 0) return Math.abs(dx);
  if (Math.abs(dx) === Math.abs(dy)) return Math.abs(dx);
  return null;
}

function normalisedDirection(dx: number, dy: number): CellTuple | null {
  return alignment(dx, dy) ? [sign(dx), sign(dy)] : null;
}

function unique<T>(items: T[]): T[] {
  return Array.from(new Set(items));
}

function compareCells(a: LocalCell, b: LocalCell): number {
  return (a.x + a.y) - (b.x + b.y) || a.x - b.x || a.y - b.y;
}

class ArenaSets {
  private walkable: Set<string>;
  private boundary: Set<string>;
  private occluded: Set<string>;
  private blocked: Set<string>;

  constructor(given: LocalGivenState) {
    const arena = given.arena ?? {};
    const suppliedWalkable = arena.walkable ?? [];
    this.walkable = new Set(suppliedWalkable.map(cellKey));
    this.boundary = new Set((arena.boundaryUnverified ?? []).map(cellKey));
    this.occluded = new Set((arena.occludedUnknown ?? []).map(cellKey));
    this.blocked = new Set((arena.permanentBlocked ?? []).map(cellKey));

    if (!this.walkable.size && !this.boundary.size) {
      for (let x = -12; x <= 12; x += 1) {
        for (let y = -12; y <= 12; y += 1) {
          this.walkable.add(`${x},${y}`);
        }
      }
    }
  }

  classification(cell: LocalCell | CellTuple): CellClass {
    const key = cellKey(cell);
    if (this.walkable.has(key)) return "walkable";
    if (this.boundary.has(key)) return "boundary";
    if (this.occluded.has(key)) return "occluded";
    if (this.blocked.has(key)) return "blocked";
    return "outside";
  }

  mobility(cell: LocalCell | CellTuple): number {
    const [x, y] = cellTuple(cell);
    return [[-1, 0], [0, -1], [0, 1], [1, 0]].filter(([dx, dy]) => (
      this.classification([x + dx, y + dy]) === "walkable"
    )).length;
  }
}

function makePillarMap(pillars: LocalPillar[]): Map<string, LocalPillar> {
  const result = new Map<string, LocalPillar>();
  for (const pillar of pillars) result.set(cellKey(pillar.cell), pillar);
  return result;
}

function makePillarById(pillars: LocalPillar[]): Map<string, LocalPillar> {
  const result = new Map<string, LocalPillar>();
  for (const pillar of pillars) result.set(pillar.id, pillar);
  return result;
}

function canonicalActionSignature(spell: LocalSpellKey, targetKind: "cell" | "pillar", targetCell: CellTuple, pillarId: string | null): string {
  return `${spell}@${targetKind}:${targetCell[0]},${targetCell[1]}:${pillarId ?? "-"}`;
}

function makeAction(
  spell: LocalSpellKey,
  source: CellTuple,
  target: CellTuple,
  targetKind: "cell" | "pillar",
  destination: CellTuple,
  targetPillarId: string | null,
): InternalAction {
  const signature = canonicalActionSignature(spell, targetKind, target, targetPillarId);
  return {
    actionId: `local-${signature}`,
    spell,
    sourceCell: cellDict(source),
    destinationCell: cellDict(destination),
    targetKind,
    targetCell: cellDict(target),
    targetPillarId,
    canonicalSignature: signature,
  };
}

function actionSortKey(action: InternalAction): string {
  const target = action.targetCell;
  return [
    SPELL_ORDER[action.spell],
    action.targetKind === "cell" ? 0 : 1,
    String(target.x).padStart(4, "0"),
    String(target.y).padStart(4, "0"),
    action.targetPillarId ?? "",
  ].join("|");
}

function pathCells(source: CellTuple, destination: CellTuple): LocalCell[] {
  const dx = destination[0] - source[0];
  const dy = destination[1] - source[1];
  const steps = Math.max(Math.abs(dx), Math.abs(dy));
  if (steps === 0) return [cellDict(source)];
  if (dx !== 0 && dy !== 0 && Math.abs(dx) !== Math.abs(dy)) return [cellDict(source), cellDict(destination)];
  const ux = sign(dx);
  const uy = sign(dy);
  const result: LocalCell[] = [];
  for (let index = 0; index <= steps; index += 1) {
    result.push(cellDict([source[0] + index * ux, source[1] + index * uy]));
  }
  return result;
}

function withDisplayFields(action: InternalAction, order?: number): LocalSolverAction {
  const source = cellTuple(action.sourceCell);
  const destination = cellTuple(action.destinationCell);
  const target = action.targetPillarId ? action.targetPillarId : `case ${action.targetCell.x},${action.targetCell.y}`;
  return {
    ...action,
    instruction: `${action.spell} → ${target}`,
    pathCells: pathCells(source, destination),
  };
}

export function resolveNextCharges(chargesAtTurnStart: number, castsThisTurn: number, matchingWhiteHits: number, maximum = 4): number {
  const remaining = chargesAtTurnStart - castsThisTurn;
  if (remaining < 0) throw new Error("charges may never fall below zero during a turn");
  return Math.min(maximum, remaining + matchingWhiteHits);
}

function invalidReasons(given: LocalGivenState, arena: ArenaSets, pillars: LocalPillar[]): string[] {
  const reasons: string[] = [];
  const cells = pillars.map(pillar => cellKey(pillar.cell));
  if (cells.length !== new Set(cells).size) reasons.push("S-INVALID-DUPLICATE-PILLAR");
  const player = given.player?.current;
  if (!player || ["outside", "blocked"].includes(arena.classification(player))) {
    reasons.push("S-INVALID-PLAYER-CELL");
  }
  return reasons;
}

function normaliseSpells(given: LocalGivenState): Record<LocalSpellKey, LocalSpellState> {
  const spells = given.resources?.spells ?? {};
  return {
    indecision: { availability: "available", value: DEFAULT_CHARGES.indecision, confirmed: true, ...spells.indecision },
    reflection: { availability: "available", value: DEFAULT_CHARGES.reflection, confirmed: true, ...spells.reflection },
    repulsion: { availability: "available", value: DEFAULT_CHARGES.repulsion, confirmed: true, ...spells.repulsion },
    attraction: { availability: "available", value: DEFAULT_CHARGES.attraction, confirmed: true, ...spells.attraction },
  };
}

function spellUsable(spell: LocalSpellKey, spells: Record<LocalSpellKey, LocalSpellState>, charges: Record<LocalSpellKey, number>): boolean {
  const state = spells[spell];
  if (state.availability === "unavailable") return false;
  if (typeof state.value === "number") return charges[spell] >= 1;
  return state.availability === "available" && charges[spell] >= 1;
}

function pillarAction(spell: LocalSpellKey, source: CellTuple, pillar: LocalPillar): InternalAction | null {
  const target = cellTuple(pillar.cell);
  const dx = target[0] - source[0];
  const dy = target[1] - source[1];
  const align = alignment(dx, dy);
  const steps = alignedSteps(dx, dy);
  if (!align || steps === null) return null;

  if (spell === "reflection") {
    if (Math.abs(dx) !== 1 || Math.abs(dy) !== 1) return null;
    return makeAction(spell, source, target, "pillar", [target[0] + dx, target[1] + dy], pillar.id);
  }

  if (spell === "repulsion") {
    if (steps < 1 || steps > 2) return null;
    const targetUnit = normalisedDirection(dx, dy);
    if (!targetUnit) return null;
    const awayUnit: CellTuple = [-targetUnit[0], -targetUnit[1]];
    return makeAction(spell, source, target, "pillar", [source[0] + 3 * awayUnit[0], source[1] + 3 * awayUnit[1]], pillar.id);
  }

  if (spell === "attraction") {
    if (align !== "cardinal" || steps < 1 || steps > 6) return null;
    const unit = normalisedDirection(dx, dy);
    if (!unit) return null;
    const move = Math.min(3, steps - 1);
    if (move < 1) return null;
    return makeAction(spell, source, target, "pillar", [source[0] + move * unit[0], source[1] + move * unit[1]], pillar.id);
  }

  return null;
}

function applyMovementConstraints(action: InternalAction, source: CellTuple, arena: ArenaSets, pillarByCell: Map<string, LocalPillar>): InternalAction | null {
  const destination = cellTuple(action.destinationCell);
  const target = cellTuple(action.targetCell);

  const isFree = (cell: CellTuple): boolean => arena.classification(cell) === "walkable" && !pillarByCell.has(cellKey(cell));

  if (action.spell === "indecision") {
    if (action.targetKind !== "cell") return null;
    const dx = target[0] - source[0];
    const dy = target[1] - source[1];
    if (Math.abs(dx) + Math.abs(dy) !== 1) return null;
    if (!sameCell(destination, target)) return null;
    if (!isFree(destination)) return null;
    return { ...action, destinationCell: cellDict(destination), targetCell: cellDict(target) };
  }

  if (action.spell === "reflection") {
    if (action.targetKind !== "pillar") return null;
    if (!pillarByCell.has(cellKey(target))) return null;

    const dx = target[0] - source[0];
    const dy = target[1] - source[1];
    if (Math.abs(dx) !== 1 || Math.abs(dy) !== 1) return null;

    const reflected: CellTuple = [target[0] + dx, target[1] + dy];
    if (!isFree(reflected)) return null;

    return { ...action, targetCell: cellDict(target), destinationCell: cellDict(reflected) };
  }

  if (action.spell === "repulsion") {
    if (action.targetKind !== "pillar") return null;
    if (!pillarByCell.has(cellKey(target))) return null;

    const targetDx = target[0] - source[0];
    const targetDy = target[1] - source[1];
    const targetSteps = alignedSteps(targetDx, targetDy);
    const targetUnit = normalisedDirection(targetDx, targetDy);

    if (targetSteps === null || targetSteps < 1 || targetSteps > 2 || !targetUnit) return null;

    const awayUnit: CellTuple = [-targetUnit[0], -targetUnit[1]];
    let lastFree: CellTuple = [source[0], source[1]];

    for (let distance = 1; distance <= 3; distance += 1) {
      const previous: CellTuple = [source[0] + (distance - 1) * awayUnit[0], source[1] + (distance - 1) * awayUnit[1]];
      const candidate: CellTuple = [source[0] + distance * awayUnit[0], source[1] + distance * awayUnit[1]];

      if (awayUnit[0] !== 0 && awayUnit[1] !== 0) {
        const sideA: CellTuple = [previous[0] + awayUnit[0], previous[1]];
        const sideB: CellTuple = [previous[0], previous[1] + awayUnit[1]];
        if (!isFree(sideA) || !isFree(sideB)) break;
      }

      if (!isFree(candidate)) break;
      lastFree = candidate;
    }

    if (sameCell(lastFree, source)) return null;
    return { ...action, targetCell: cellDict(target), destinationCell: cellDict(lastFree) };
  }

  if (action.spell === "attraction") {
    if (action.targetKind !== "pillar") return null;
    if (!pillarByCell.has(cellKey(target))) return null;

    const targetDx = target[0] - source[0];
    const targetDy = target[1] - source[1];
    const targetSteps = alignedSteps(targetDx, targetDy);
    const targetUnit = normalisedDirection(targetDx, targetDy);

    if (targetSteps === null || targetSteps < 1 || targetSteps > 6 || !targetUnit) return null;
    if (targetUnit[0] !== 0 && targetUnit[1] !== 0) return null;

    for (let distance = 1; distance < targetSteps; distance += 1) {
      const between: CellTuple = [source[0] + distance * targetUnit[0], source[1] + distance * targetUnit[1]];
      if (pillarByCell.has(cellKey(between))) return null;
      if (arena.classification(between) !== "walkable") return null;
    }

    let lastFree: CellTuple = [source[0], source[1]];
    const maxPull = Math.min(3, targetSteps - 1);
    for (let distance = 1; distance <= maxPull; distance += 1) {
      const candidate: CellTuple = [source[0] + distance * targetUnit[0], source[1] + distance * targetUnit[1]];
      if (!isFree(candidate)) break;
      lastFree = candidate;
    }

    if (sameCell(lastFree, source)) return null;
    return { ...action, targetCell: cellDict(target), destinationCell: cellDict(lastFree) };
  }

  return null;
}

function enumerateActions(
  source: CellTuple,
  given: LocalGivenState,
  arena: ArenaSets,
  pillarByCell: Map<string, LocalPillar>,
  spells: Record<LocalSpellKey, LocalSpellState>,
  charges: Record<LocalSpellKey, number>,
  budget: number,
): InternalAction[] {
  if (budget < 1) return [];
  const pillars = [...(given.pillars ?? [])].sort((a, b) => compareCells(a.cell, b.cell) || a.id.localeCompare(b.id));
  const actions: InternalAction[] = [];

  for (const spell of LOCAL_SPELLS) {
    if (!spellUsable(spell, spells, charges)) continue;
    const candidates: InternalAction[] = [];

    if (spell === "indecision") {
      for (const [dx, dy] of [[-1, 0], [0, -1], [0, 1], [1, 0]] as const) {
        const target: CellTuple = [source[0] + dx, source[1] + dy];
        candidates.push(makeAction(spell, source, target, "cell", target, null));
      }
    } else {
      for (const pillar of pillars) {
        const candidate = pillarAction(spell, source, pillar);
        if (candidate) candidates.push(candidate);
      }
    }

    for (const candidate of candidates) {
      const constrained = applyMovementConstraints(candidate, source, arena, pillarByCell);
      if (constrained) actions.push(constrained);
    }
  }

  return actions.sort((a, b) => actionSortKey(a).localeCompare(actionSortKey(b)));
}

function resolveTerminal(node: SearchNode, given: LocalGivenState, pillars: LocalPillar[]): LocalTerminalCandidate {
  const final = node.cell;
  const pillarByCell = makePillarMap(pillars);
  const pillarById = makePillarById(pillars);
  const glyphs = given.glyphs ?? {};
  const physicalBlack = new Set((glyphs.physicalBlackCells ?? []).map(cellKey));
  const physicalWhite = new Set((glyphs.physicalWhiteCells ?? []).map(cellKey));
  const finalKey = cellKey(final);
  const directBlack = physicalBlack.has(finalKey);
  const directWhite = physicalWhite.has(finalKey);
  const blackPillarIds: string[] = [];
  const whitePillarIds: string[] = [];

  for (const offset of glyphs.blackOffsets ?? []) {
    const projected: CellTuple = [final[0] + Number(offset.dx), final[1] + Number(offset.dy)];
    const pillar = pillarByCell.get(cellKey(projected));
    if (pillar) blackPillarIds.push(pillar.id);
  }

  for (const offset of glyphs.whiteOffsets ?? []) {
    const projected: CellTuple = [final[0] + Number(offset.dx), final[1] + Number(offset.dy)];
    const pillar = pillarByCell.get(cellKey(projected));
    if (pillar) whitePillarIds.push(pillar.id);
  }

  let raceOutcome: LocalTerminalCandidate["raceOutcome"] = "neutral";
  if (directBlack || blackPillarIds.length) raceOutcome = "dragon_advance";
  else if (directWhite || whitePillarIds.length) raceOutcome = "crocoburio_advance";

  const whiteCounts: Record<LocalSpellKey, number> = { indecision: 0, reflection: 0, repulsion: 0, attraction: 0 };
  for (const id of whitePillarIds) {
    const pillar = pillarById.get(id);
    if (pillar) whiteCounts[pillar.spellType] += 1;
  }

  const nextSpellState = {} as Record<LocalSpellKey, number>;
  for (const spell of LOCAL_SPELLS) {
    const casts = node.castCounts[spell];
    const startValue = node.charges[spell] + casts;
    nextSpellState[spell] = resolveNextCharges(startValue, casts, whiteCounts[spell], 4);
  }

  const displayActions = node.actions.map((action, index) => withDisplayFields(action, index + 1));

  return {
    sequence: node.actions.map(action => action.canonicalSignature),
    actions: displayActions,
    finalCell: cellDict(final),
    raceOutcome,
    blackPillarIds: unique(blackPillarIds).sort(),
    whitePillarIds: unique(whitePillarIds).sort(),
    rechargedSpells: LOCAL_SPELLS.filter(spell => whiteCounts[spell] > 0),
    nextSpellState,
    directCenterEffect: directBlack ? "black_adverse" : directWhite ? "white_recharge" : "none",
    remainingBudget: node.budget,
    castCount: node.actions.length,
  };
}

function isBlackSafe(candidate: LocalTerminalCandidate): boolean {
  return candidate.blackPillarIds.length === 0 && candidate.directCenterEffect !== "black_adverse";
}

function rankingKey(candidate: LocalTerminalCandidate, arena: ArenaSets): Array<string | number | boolean> {
  const raceRank: Record<string, number> = {
    crocoburio_advance: 0,
    neutral: 1,
    unknown: 2,
    dragon_advance: 3,
  };
  const charges = LOCAL_SPELLS.map(spell => candidate.nextSpellState[spell]);
  return [
    candidate.castCount,
    false,
    -Math.min(...charges),
    -charges.reduce((sum, value) => sum + value, 0),
    raceRank[candidate.raceOutcome] ?? 4,
    -arena.mobility(candidate.finalCell),
    candidate.sequence.join("->"),
  ];
}

function compareRanking(a: LocalTerminalCandidate, b: LocalTerminalCandidate, arena: ArenaSets): number {
  const ak = rankingKey(a, arena);
  const bk = rankingKey(b, arena);
  for (let index = 0; index < ak.length; index += 1) {
    const av = ak[index];
    const bv = bk[index];
    if (av < bv) return -1;
    if (av > bv) return 1;
  }
  return 0;
}

function emptyResult(status: LocalSolverResult["status"], reasons: string[]): LocalSolverResult {
  return {
    status,
    statusReasonCodes: reasons,
    actions: [],
    expected: {
      finalCell: null,
      raceOutcome: "unknown",
      blackPillarIds: [],
      whitePillarIds: [],
      rechargedSpells: [],
      directCenterEffect: "unknown",
      nextSpellState: null,
    },
    diagnostics: { terminalCandidates: [], nodeCount: 0 },
  };
}

export function solveLocalGiven(given: LocalGivenState, options: { maxNodes?: number; timeoutMs?: number } = {}): LocalSolverResult {
  const arena = new ArenaSets(given);
  const pillars = given.pillars ?? [];
  const invalid = invalidReasons(given, arena, pillars);
  if (invalid.length) return emptyResult("invalid_state", invalid);

  const player = given.player?.current;
  if (!player) return emptyResult("invalid_state", ["S-INVALID-PLAYER-CELL"]);

  const budget = Number(given.resources?.actionBudget ?? 12);
  if (!Number.isFinite(budget) || budget < 1) return emptyResult("invalid_state", ["S-INVALID-ACTION-BUDGET"]);

  const spells = normaliseSpells(given);
  const initialCharges = {} as Record<LocalSpellKey, number>;
  for (const spell of LOCAL_SPELLS) {
    const value = spells[spell].value;
    initialCharges[spell] = typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.min(4, Math.floor(value))) : DEFAULT_CHARGES[spell];
  }

  const pillarByCell = makePillarMap(pillars);
  const startedAt = Date.now();
  const maxNodes = options.maxNodes ?? 100_000;
  const timeoutMs = options.timeoutMs ?? 1_500;
  const startCell = cellTuple(player);
  const queue: SearchNode[] = [{
    cell: startCell,
    budget,
    actions: [],
    castCounts: { indecision: 0, reflection: 0, repulsion: 0, attraction: 0 },
    charges: { ...initialCharges },
  }];
  const visited = new Map<string, string>();
  const terminalCandidates: LocalTerminalCandidate[] = [];
  let nodeCount = 0;

  while (queue.length) {
    if (Date.now() - startedAt > timeoutMs || nodeCount > maxNodes) {
      return emptyResult("capacity_error", ["S-CAPACITY-LIMIT"]);
    }

    const node = queue.shift();
    if (!node) break;
    nodeCount += 1;

    if (node.actions.some(action => !sameCell(action.sourceCell, action.destinationCell))) {
      terminalCandidates.push(resolveTerminal(node, given, pillars));
    }

    if (node.budget < 1) continue;
    const actions = enumerateActions(node.cell, given, arena, pillarByCell, spells, node.charges, node.budget);

    for (const action of actions) {
      const spell = action.spell;
      if (node.charges[spell] <= 0) continue;
      const nextCharges = { ...node.charges, [spell]: node.charges[spell] - 1 };
      const nextCastCounts = { ...node.castCounts, [spell]: node.castCounts[spell] + 1 };
      const nextActions = [...node.actions, action];
      const nextCell = cellTuple(action.destinationCell);
      const stateKey = [
        cellKey(nextCell),
        node.budget - 1,
        ...LOCAL_SPELLS.map(item => nextCharges[item]),
        ...LOCAL_SPELLS.map(item => nextCastCounts[item]),
      ].join("|");
      const sequence = nextActions.map(item => item.canonicalSignature).join("->");
      const previous = visited.get(stateKey);
      if (previous !== undefined && previous <= sequence) continue;
      visited.set(stateKey, sequence);
      queue.push({
        cell: nextCell,
        budget: node.budget - 1,
        actions: nextActions,
        castCounts: nextCastCounts,
        charges: nextCharges,
      });
    }
  }

  const safe = terminalCandidates.filter(isBlackSafe).sort((a, b) => compareRanking(a, b, arena));
  const best = safe[0];
  if (!best) {
    return {
      ...emptyResult("no_safe_solution", terminalCandidates.length ? ["S-NO-SAFE-SOLUTION"] : ["S-NO-LEGAL-MOVEMENT"]),
      diagnostics: { terminalCandidates, nodeCount },
    };
  }

  return {
    status: "solved",
    statusReasonCodes: ["S-SOLVED-CONTRACT"],
    actions: best.actions,
    expected: {
      finalCell: best.finalCell,
      raceOutcome: best.raceOutcome,
      blackPillarIds: best.blackPillarIds,
      whitePillarIds: best.whitePillarIds,
      rechargedSpells: best.rechargedSpells,
      directCenterEffect: best.directCenterEffect,
      nextSpellState: best.nextSpellState,
    },
    diagnostics: { terminalCandidates, nodeCount },
  };
}

export function localSolverResultToFrontendResult(
  local: LocalSolverResult,
  timings: PipelineTimingsMs,
  imageSize?: { width: number; height: number },
): FrontendSolveResult {
  const ok = local.status === "solved";

  const actions: SolverActionStep[] = local.actions.map((action, index) => ({
    label: action.instruction,
    instruction: action.instruction,
    spell: action.spell,
    from: `${action.sourceCell.x},${action.sourceCell.y}`,
    to: `${action.destinationCell.x},${action.destinationCell.y}`,
    apCost: 1,
    note: action.canonicalSignature,
    order: index + 1,
    sourceCell: { ...action.sourceCell },
    destinationCell: { ...action.destinationCell },
    targetKind: action.targetKind,
    targetCell: { ...action.targetCell },
    targetPillarId: action.targetPillarId,
    canonicalSignature: action.canonicalSignature,
    pathCells: action.pathCells.map(cell => ({ ...cell })),
  }));

  return {
    ok,
    source: "frontend",
    status: ok ? "solved" : "rejected",
    message: ok
      ? "Local TypeScript solver returned a recommendation."
      : "Local TypeScript solver did not find a safe recommendation.",
    reason: ok ? undefined : local.status,
    confidence: ok ? 1 : 0.3,
    actions,
    expected: {
      finalCell: local.expected.finalCell,
      raceOutcome: local.expected.raceOutcome,
      blackPillarIds: local.expected.blackPillarIds,
      whitePillarIds: local.expected.whitePillarIds,
      rechargedSpells: local.expected.rechargedSpells,
      directCenterEffect: local.expected.directCenterEffect,
      nextSpellState: local.expected.nextSpellState,
    },
    warnings: [],
    debug: {
      reason: ok ? undefined : "solver_failed",
      image_size: imageSize,
      confidence: ok ? 1 : 0.3,
      solver_status: local.status,
      solver_reason_codes: local.statusReasonCodes,
      solver_node_count: local.diagnostics.nodeCount,
      notes: [
        "TypeScript local tactical solver executed in the browser.",
        `Solver status: ${local.status}`,
        `Reason codes: ${local.statusReasonCodes.join(", ") || "none"}`,
        `Node count: ${local.diagnostics.nodeCount}`,
      ],
    },
    timings_ms: timings,
    raw: local,
  };
}
