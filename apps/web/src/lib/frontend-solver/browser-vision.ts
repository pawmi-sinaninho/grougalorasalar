
import type { CanvasImage } from "./image";
import { getImageData } from "./image";
import type { LocalCell, LocalGivenState, LocalPillar, LocalSpellKey } from "./local-solver";
import type { CaptureDebug, CaptureRejectReason, CaptureWarning } from "./types";

const REF_WIDTH = 1951;
const REF_HEIGHT = 1267;
const REF_ORIGIN = { x: 964.895, y: 441.7425 };
const REF_BASIS_X = { x: 66.75, y: 33.375 };
const REF_BASIS_Y = { x: -66.75, y: 33.375 };
const EXPECTED_CELL_COUNT = 338;

type Hsv = { h: number; s: number; v: number };
type Point = { x: number; y: number };
type SpellThreshold = {
  spellType: LocalSpellKey;
  lower: Hsv;
  upper: Hsv;
  offset: Point;
  minimumFraction: number;
};

export interface BrowserVisionResult {
  ok: boolean;
  state?: LocalGivenState;
  confidence: number;
  warnings: CaptureWarning[];
  debug: CaptureDebug;
  reason?: CaptureRejectReason | string;
  metrics: Record<string, number | boolean | string>;
}

const PILLAR_THRESHOLDS: SpellThreshold[] = [
  { spellType: "indecision", lower: { h: 60, s: 70, v: 70 }, upper: { h: 95, s: 255, v: 255 }, offset: { x: 0.48, y: -43.43 }, minimumFraction: 0.10 },
  { spellType: "reflection", lower: { h: 35, s: 150, v: 60 }, upper: { h: 65, s: 255, v: 255 }, offset: { x: -0.42, y: -42.66 }, minimumFraction: 0.08 },
  { spellType: "repulsion", lower: { h: 23, s: 180, v: 100 }, upper: { h: 35, s: 255, v: 255 }, offset: { x: 1.89, y: -43.02 }, minimumFraction: 0.08 },
  { spellType: "attraction", lower: { h: 0, s: 160, v: 70 }, upper: { h: 14, s: 255, v: 255 }, offset: { x: -0.76, y: -41.06 }, minimumFraction: 0.08 },
];

const GLYPH_TEMPLATES = [
  {
    id: "inner-cardinal",
    black: [[-1, 0], [0, -1], [0, 1], [1, 0]],
    white: [[-1, -1], [-1, 1], [1, -1], [1, 1]],
  },
  {
    id: "inner-diagonal",
    black: [[-1, -1], [-1, 1], [1, -1], [1, 1]],
    white: [[-3, 0], [-2, 0], [0, -3], [0, -2], [0, 2], [0, 3], [2, 0], [3, 0]],
  },
  {
    id: "outer-cardinal",
    black: [[-3, 0], [-2, 0], [0, -3], [0, -2], [0, 2], [0, 3], [2, 0], [3, 0]],
    white: [[-3, -3], [-3, 3], [-2, -2], [-2, 2], [2, -2], [2, 2], [3, -3], [3, 3]],
  },
  {
    id: "outer-diagonal",
    black: [[-3, -3], [-3, 3], [-2, -2], [-2, 2], [2, -2], [2, 2], [3, -3], [3, 3]],
    white: [[-1, 0], [0, -1], [0, 1], [1, 0]],
  },
] as const;

function canonicalArenaCells(): LocalCell[] {
  const cells: LocalCell[] = [];
  for (let x = -12; x <= 13; x += 1) {
    for (let y = -12; y <= 13; y += 1) {
      if (-11 <= x + y && x + y <= 13 && -13 <= x - y && x - y <= 13) {
        cells.push({ x, y });
      }
    }
  }
  return cells.sort((a, b) => a.y - b.y || a.x - b.x);
}

function cellKey(cell: LocalCell): string {
  return `${cell.x},${cell.y}`;
}

function fromTuple(tuple: readonly [number, number] | readonly number[]): LocalCell {
  return { x: Number(tuple[0]), y: Number(tuple[1]) };
}

function imageScale(image: { width: number; height: number }): { sx: number; sy: number; area: number } {
  const sx = image.width / REF_WIDTH;
  const sy = image.height / REF_HEIGHT;
  return { sx, sy, area: Math.max(0.18, sx * sy) };
}

function projectCell(cell: LocalCell, image: { width: number; height: number }): Point {
  const { sx, sy } = imageScale(image);
  return {
    x: (REF_ORIGIN.x + cell.x * REF_BASIS_X.x + cell.y * REF_BASIS_Y.x) * sx,
    y: (REF_ORIGIN.y + cell.x * REF_BASIS_X.y + cell.y * REF_BASIS_Y.y) * sy,
  };
}

function rgbToHsv(r: number, g: number, b: number): Hsv {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const delta = max - min;
  let hDeg = 0;
  if (delta !== 0) {
    if (max === rn) hDeg = 60 * (((gn - bn) / delta) % 6);
    else if (max === gn) hDeg = 60 * ((bn - rn) / delta + 2);
    else hDeg = 60 * ((rn - gn) / delta + 4);
  }
  if (hDeg < 0) hDeg += 360;
  return { h: hDeg / 2, s: max === 0 ? 0 : (delta / max) * 255, v: max * 255 };
}

function inRange(hsv: Hsv, lower: Hsv, upper: Hsv): boolean {
  return hsv.h >= lower.h && hsv.h <= upper.h && hsv.s >= lower.s && hsv.s <= upper.s && hsv.v >= lower.v && hsv.v <= upper.v;
}

function clampInt(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, Math.round(value)));
}

function readRgb(data: Uint8ClampedArray, width: number, x: number, y: number): [number, number, number] {
  const offset = (y * width + x) * 4;
  return [data[offset] ?? 0, data[offset + 1] ?? 0, data[offset + 2] ?? 0];
}

function sampleRect(
  imageData: ImageData,
  center: Point,
  radiusX: number,
  radiusY: number,
  predicate: (hsv: Hsv, r: number, g: number, b: number) => boolean,
): { count: number; total: number; saturationSum: number; valueValues: number[]; saturationValues: number[] } {
  const x0 = clampInt(center.x - radiusX, 0, imageData.width - 1);
  const x1 = clampInt(center.x + radiusX, 0, imageData.width - 1);
  const y0 = clampInt(center.y - radiusY, 0, imageData.height - 1);
  const y1 = clampInt(center.y + radiusY, 0, imageData.height - 1);
  let count = 0;
  let total = 0;
  let saturationSum = 0;
  const valueValues: number[] = [];
  const saturationValues: number[] = [];
  for (let y = y0; y <= y1; y += 1) {
    for (let x = x0; x <= x1; x += 1) {
      const [r, g, b] = readRgb(imageData.data, imageData.width, x, y);
      const hsv = rgbToHsv(r, g, b);
      total += 1;
      if (predicate(hsv, r, g, b)) {
        count += 1;
        saturationSum += hsv.s;
        valueValues.push(hsv.v);
        saturationValues.push(hsv.s);
      }
    }
  }
  return { count, total, saturationSum, valueValues, saturationValues };
}

function median(values: number[], fallback = 0): number {
  if (!values.length) return fallback;
  const copy = [...values].sort((a, b) => a - b);
  return copy[Math.floor(copy.length / 2)] ?? fallback;
}

function detectPlayer(imageData: ImageData, cells: LocalCell[], pillars: LocalPillar[]): { cell: LocalCell; confidence: number; count: number; ratio: number } | null {
  const pillarCells = new Set(pillars.map(item => cellKey(item.cell)));
  const scale = imageScale(imageData);
  const scores: Array<{ score: number; cell: LocalCell; count: number }> = [];
  for (const cell of cells) {
    if (pillarCells.has(cellKey(cell))) continue;
    const centre = projectCell(cell, imageData);
    const sample = sampleRect(
      imageData,
      { x: centre.x, y: centre.y + 7 * scale.sy },
      48 * scale.sx,
      24 * scale.sy,
      hsv => hsv.h >= 85 && hsv.h <= 115 && hsv.s >= 75 && hsv.v >= 55,
    );
    if (!sample.count) continue;
    scores.push({ score: sample.count + 0.01 * sample.saturationSum, cell, count: sample.count });
  }
  scores.sort((a, b) => b.score - a.score);
  const best = scores[0];
  if (!best) return null;
  const second = scores[1]?.score ?? 1;
  const ratio = best.score / Math.max(second, 1);
  const minimumCount = 80 * scale.area;
  if (best.count < minimumCount || ratio < 1.45) return null;
  return {
    cell: best.cell,
    confidence: Math.min(0.995, 0.72 + Math.min(best.count / Math.max(1, 500 * scale.area), 1) * 0.16 + Math.min((ratio - 1.45) / 4, 1) * 0.10),
    count: best.count,
    ratio,
  };
}

function detectPillars(imageData: ImageData, cells: LocalCell[]): LocalPillar[] {
  const scale = imageScale(imageData);
  const proposals = new Map<string, LocalPillar & { score: number; confidence: number }>();
  for (const cell of cells) {
    const centre = projectCell(cell, imageData);
    for (const threshold of PILLAR_THRESHOLDS) {
      const sample = sampleRect(
        imageData,
        {
          x: centre.x + threshold.offset.x * scale.sx,
          y: centre.y + threshold.offset.y * scale.sy,
        },
        36 * scale.sx,
        30 * scale.sy,
        hsv => inRange(hsv, threshold.lower, threshold.upper),
      );
      const fraction = sample.total ? sample.count / sample.total : 0;
      const score = fraction * Math.min(1.25, Math.sqrt(sample.count / Math.max(1, 160 * scale.area)));
      if (fraction < threshold.minimumFraction || sample.count < 65 * scale.area) continue;
      const confidence = Math.min(0.995, 0.56 + score * 0.75);
      const key = cellKey(cell);
      const previous = proposals.get(key);
      if (!previous || score > previous.score) {
        proposals.set(key, {
          id: "pending",
          cell: { ...cell },
          spellType: threshold.spellType,
          score,
          confidence,
        });
      }
    }
  }
  const selected = [...proposals.values()].sort((a, b) => (a.cell.x + a.cell.y) - (b.cell.x + b.cell.y) || a.cell.x - b.cell.x || a.cell.y - b.cell.y);
  return selected.map((item, index) => ({ id: `P${String(index + 1).padStart(2, "0")}`, cell: item.cell, spellType: item.spellType }));
}

function detectGlyphs(imageData: ImageData, occupiedCells: Set<string>): {
  blackOffsets: Array<{ dx: number; dy: number }>;
  whiteOffsets: Array<{ dx: number; dy: number }>;
  physicalBlackCells: LocalCell[];
  physicalWhiteCells: LocalCell[];
  confidence: number;
  templateId: string;
  observedBlack: LocalCell[];
  observedWhite: LocalCell[];
} | null {
  const scale = imageScale(imageData);
  const observed: Array<{ cell: LocalCell; colour: "black" | "white"; strength: number }> = [];
  for (let x = -3; x <= 3; x += 1) {
    for (let y = -3; y <= 3; y += 1) {
      const cell = { x, y };
      if (occupiedCells.has(cellKey(cell))) continue;
      const centre = projectCell(cell, imageData);
      const sample = sampleRect(
        imageData,
        { x: centre.x, y: centre.y - 17 * scale.sy },
        30 * scale.sx,
        13 * scale.sy,
        hsv => hsv.s < 82,
      );
      const lowFraction = sample.total ? sample.count / sample.total : 0;
      if (lowFraction < 0.20) continue;
      const value = median(sample.valueValues, 255);
      const saturation = median(sample.saturationValues, 255);
      const darkness = Math.max(0, (145 - value) / 145);
      const lightness = Math.max(0, (value - 145) / 110);
      const strength = Math.min(1, 0.35 + lowFraction * 0.65 + Math.max(darkness, lightness) * 0.25 - Math.max(0, saturation - 70) / 400);
      observed.push({ cell, colour: darkness >= lightness ? "black" : "white", strength });
    }
  }

  const observedBlack = observed.filter(item => item.colour === "black");
  if (!observedBlack.length) return null;

  const templateScores = GLYPH_TEMPLATES.map(template => {
    const blackKeys = new Set(template.black.map(item => `${item[0]},${item[1]}`));
    const support = observedBlack.filter(item => blackKeys.has(cellKey(item.cell))).reduce((sum, item) => sum + item.strength, 0);
    const conflict = observedBlack.filter(item => !blackKeys.has(cellKey(item.cell))).reduce((sum, item) => sum + item.strength, 0);
    const expectedHits = observedBlack.filter(item => blackKeys.has(cellKey(item.cell))).length;
    const precision = support / Math.max(0.001, support + conflict);
    const coverage = expectedHits / template.black.length;
    return { template, score: precision * (0.8 + 0.2 * coverage), precision, coverage, support };
  }).filter(item => item.support > 0).sort((a, b) => b.score - a.score);

  const best = templateScores[0];
  if (!best) return null;
  const second = templateScores[1]?.score ?? 0;
  const margin = best.score - second;
  const confidence = Math.min(0.92, 0.58 + best.precision * 0.24 + Math.min(margin / 0.20, 1) * 0.10);
  return {
    blackOffsets: best.template.black.map(([dx, dy]) => ({ dx, dy })),
    whiteOffsets: best.template.white.map(([dx, dy]) => ({ dx, dy })),
    physicalBlackCells: best.template.black.map(fromTuple),
    physicalWhiteCells: best.template.white.map(fromTuple),
    confidence,
    templateId: best.template.id,
    observedBlack: observedBlack.map(item => item.cell),
    observedWhite: observed.filter(item => item.colour === "white").map(item => item.cell),
  };
}

function maybeOverlay(canvasImage: CanvasImage, cells: LocalCell[], pillars: LocalPillar[], player: LocalCell | null, glyphBlack: LocalCell[], glyphWhite: LocalCell[]): string | undefined {
  if (typeof document === "undefined") return undefined;
  try {
    const canvas = document.createElement("canvas");
    canvas.width = canvasImage.width;
    canvas.height = canvasImage.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return undefined;
    ctx.drawImage(canvasImage.canvas as CanvasImageSource, 0, 0);
    ctx.lineWidth = Math.max(1, Math.round(canvasImage.width / 900));
    ctx.font = `${Math.max(10, Math.round(canvasImage.width / 140))}px sans-serif`;
    ctx.fillStyle = "rgba(255,255,255,0.80)";
    for (const cell of cells) {
      const point = projectCell(cell, canvasImage);
      ctx.fillRect(point.x - 1, point.y - 1, 2, 2);
    }
    ctx.fillStyle = "rgba(255,180,0,0.95)";
    for (const pillar of pillars) {
      const point = projectCell(pillar.cell, canvasImage);
      ctx.beginPath();
      ctx.arc(point.x, point.y - 32 * imageScale(canvasImage).sy, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillText(pillar.spellType[0].toUpperCase(), point.x + 6, point.y - 26 * imageScale(canvasImage).sy);
    }
    ctx.fillStyle = "rgba(0,0,0,0.90)";
    for (const cell of glyphBlack) {
      const point = projectCell(cell, canvasImage);
      ctx.fillRect(point.x - 7, point.y - 24, 14, 14);
    }
    ctx.fillStyle = "rgba(255,255,255,0.95)";
    for (const cell of glyphWhite) {
      const point = projectCell(cell, canvasImage);
      ctx.strokeStyle = "rgba(0,0,0,0.8)";
      ctx.strokeRect(point.x - 7, point.y - 24, 14, 14);
      ctx.fillRect(point.x - 5, point.y - 22, 10, 10);
    }
    if (player) {
      const point = projectCell(player, canvasImage);
      ctx.fillStyle = "rgba(0,120,255,0.95)";
      ctx.beginPath();
      ctx.arc(point.x, point.y, 9, 0, Math.PI * 2);
      ctx.fill();
    }
    return canvas.toDataURL("image/png");
  } catch {
    return undefined;
  }
}

export function recogniseScreenshotToLocalState(canvasImage: CanvasImage): BrowserVisionResult {
  const imageData = getImageData(canvasImage);
  const cells = canonicalArenaCells();
  const warnings: CaptureWarning[] = [];
  const debugNotes: string[] = [
    "Browser vision Patch B executed locally; no backend call was used.",
    "Registration is a fixed-reference projection scaled to the current screenshot size. This is fast, but less tolerant than the old ORB backend path.",
  ];

  const pillarsRaw = detectPillars(imageData, cells);
  const playerRaw = detectPlayer(imageData, cells, pillarsRaw);
  const playerCell = playerRaw?.cell ?? null;
  const pillars = playerCell ? pillarsRaw.filter(item => cellKey(item.cell) !== cellKey(playerCell)) : pillarsRaw;
  const occupied = new Set<string>(pillars.map(item => cellKey(item.cell)));
  if (playerCell) occupied.add(cellKey(playerCell));
  const glyphs = detectGlyphs(imageData, occupied);

  if (pillars.length < 8) {
    warnings.push({ code: "pillar_uncertain", message: `Only ${pillars.length} pillars detected locally.`, confidence: Math.min(0.5, pillars.length / 24) });
  }
  if (!playerRaw) {
    warnings.push({ code: "player_uncertain", message: "Player cell was not detected by local blue-base sampling.", confidence: 0 });
  }
  if (!glyphs) {
    warnings.push({ code: "glyph_uncertain", message: "Glyph phase was not detected by local cell sampling.", confidence: 0 });
  }

  const confidenceParts = [
    playerRaw?.confidence ?? 0,
    Math.min(1, pillars.length / 24),
    glyphs?.confidence ?? 0,
  ];
  const confidence = Math.round((Math.min(...confidenceParts) || 0) * 1000) / 1000;
  const overlay = maybeOverlay(canvasImage, cells, pillars, playerCell, glyphs?.physicalBlackCells ?? [], glyphs?.physicalWhiteCells ?? []);
  const baseDebug: CaptureDebug = {
    image_size: { width: canvasImage.width, height: canvasImage.height },
    cells_expected: EXPECTED_CELL_COUNT,
    cells_detected: cells.length,
    pillars_detected: pillars.length,
    player_detected: Boolean(playerRaw),
    black_glyphs_detected: glyphs?.blackOffsets.length ?? 0,
    white_glyphs_detected: glyphs?.whiteOffsets.length ?? 0,
    confidence,
    overlay_data_url: overlay,
    notes: debugNotes,
  };

  if (!playerRaw) {
    const reason: CaptureRejectReason = "player_not_found";
    return {
      ok: false,
      confidence,
      warnings,
      reason,
      debug: { ...baseDebug, reason },
      metrics: {
        cells: cells.length,
        pillars: pillars.length,
        player: false,
        glyphTemplate: glyphs?.templateId ?? "none",
      },
    };
  }

  if (!glyphs) {
    const reason: CaptureRejectReason = "glyph_detection_low_confidence";
    return {
      ok: false,
      confidence,
      warnings,
      reason,
      debug: { ...baseDebug, reason },
      metrics: {
        cells: cells.length,
        pillars: pillars.length,
        player: true,
        glyphTemplate: "none",
      },
    };
  }

  if (pillars.length < 8) {
    const reason: CaptureRejectReason = "pillar_detection_low_confidence";
    return {
      ok: false,
      confidence,
      warnings,
      reason,
      debug: { ...baseDebug, reason },
      metrics: {
        cells: cells.length,
        pillars: pillars.length,
        player: true,
        glyphTemplate: glyphs.templateId,
      },
    };
  }

  const state: LocalGivenState = {
    arena: { walkable: cells, boundaryUnverified: [], occludedUnknown: [], permanentBlocked: [] },
    player: { current: playerRaw.cell },
    pillars,
    glyphs: {
      blackOffsets: glyphs.blackOffsets,
      whiteOffsets: glyphs.whiteOffsets,
      physicalBlackCells: glyphs.physicalBlackCells,
      physicalWhiteCells: glyphs.physicalWhiteCells,
    },
    resources: {
      actionBudget: 12,
      spells: {
        indecision: { availability: "available", value: 2, confirmed: false },
        reflection: { availability: "available", value: 2, confirmed: false },
        repulsion: { availability: "available", value: 2, confirmed: false },
        attraction: { availability: "available", value: 2, confirmed: false },
      },
    },
    flags: {
      solverInputComplete: true,
      recognitionValidated: confidence >= 0.85,
      glyphHypothesisUsable: true,
      pillarHypothesisUsable: true,
      pillarSetComplete: pillars.length >= 20,
      anchorConfirmed: true,
    },
  };

  if (confidence < 0.85) {
    warnings.push({ code: "glyph_uncertain", message: "Local recognition is provisional; verify the recommendation against the board.", confidence });
  }

  return {
    ok: true,
    state,
    confidence,
    warnings,
    debug: {
      ...baseDebug,
      notes: [
        ...debugNotes,
        `Player: ${playerRaw.cell.x},${playerRaw.cell.y}`,
        `Pillars: ${pillars.length}`,
        `Glyph template: ${glyphs.templateId}`,
      ],
    },
    metrics: {
      cells: cells.length,
      pillars: pillars.length,
      playerConfidence: playerRaw.confidence,
      playerBluePixelCount: playerRaw.count,
      playerSeparationRatio: playerRaw.ratio,
      glyphTemplate: glyphs.templateId,
      glyphConfidence: glyphs.confidence,
    },
  };
}
