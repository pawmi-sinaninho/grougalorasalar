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
type GlyphColour = "black" | "white";
type GlyphTemplate = {
  id: string;
  black: readonly (readonly [number, number])[];
  white: readonly (readonly [number, number])[];
};
type SpellThreshold = {
  spellType: LocalSpellKey;
  lower: Hsv;
  upper: Hsv;
  offset: Point;
  minimumFraction: number;
};

type GlyphEvidence = {
  black: number;
  white: number;
  lowSatFraction: number;
  darkFraction: number;
  brightFraction: number;
  medianValue: number;
  medianSaturation: number;
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

const GLYPH_TEMPLATES: readonly GlyphTemplate[] = [
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

function addCells(a: LocalCell, offset: readonly [number, number]): LocalCell {
  return { x: a.x + Number(offset[0]), y: a.y + Number(offset[1]) };
}

function fromTuple(tuple: readonly [number, number] | readonly number[]): LocalCell {
  return { x: Number(tuple[0]), y: Number(tuple[1]) };
}

function offsetObjects(templateOffsets: readonly (readonly [number, number])[]): Array<{ dx: number; dy: number }> {
  return templateOffsets.map(([dx, dy]) => ({ dx: Number(dx), dy: Number(dy) }));
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

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function readRgb(data: Uint8ClampedArray, width: number, x: number, y: number): [number, number, number] {
  const offset = (y * width + x) * 4;
  return [data[offset] ?? 0, data[offset + 1] ?? 0, data[offset + 2] ?? 0];
}

function median(values: number[], fallback = 0): number {
  if (!values.length) return fallback;
  const copy = [...values].sort((a, b) => a - b);
  return copy[Math.floor(copy.length / 2)] ?? fallback;
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

function sampleGlyphEvidence(imageData: ImageData, cell: LocalCell): GlyphEvidence {
  const scale = imageScale(imageData);
  const centre = projectCell(cell, imageData);
  const x0 = clampInt(centre.x - 36 * scale.sx, 0, imageData.width - 1);
  const x1 = clampInt(centre.x + 36 * scale.sx, 0, imageData.width - 1);
  const y0 = clampInt(centre.y - 31 * scale.sy, 0, imageData.height - 1);
  const y1 = clampInt(centre.y - 5 * scale.sy, 0, imageData.height - 1);

  let total = 0;
  let lowSat = 0;
  let dark = 0;
  let bright = 0;
  let veryDark = 0;
  let veryBright = 0;
  const values: number[] = [];
  const saturations: number[] = [];

  for (let y = y0; y <= y1; y += 1) {
    for (let x = x0; x <= x1; x += 1) {
      const [r, g, b] = readRgb(imageData.data, imageData.width, x, y);
      const hsv = rgbToHsv(r, g, b);
      total += 1;
      values.push(hsv.v);
      saturations.push(hsv.s);
      if (hsv.s <= 120) lowSat += 1;
      if (hsv.v <= 118 && hsv.s <= 145) dark += 1;
      if (hsv.v <= 82 && hsv.s <= 160) veryDark += 1;
      if (hsv.v >= 158 && hsv.s <= 118) bright += 1;
      if (hsv.v >= 195 && hsv.s <= 92) veryBright += 1;
    }
  }

  const medianValue = median(values, 128);
  const medianSaturation = median(saturations, 255);
  const lowSatFraction = total ? lowSat / total : 0;
  const darkFraction = total ? dark / total : 0;
  const brightFraction = total ? bright / total : 0;
  const veryDarkFraction = total ? veryDark / total : 0;
  const veryBrightFraction = total ? veryBright / total : 0;

  const backgroundPenalty = Math.max(0, medianSaturation - 135) / 255;
  const black = clamp01(darkFraction * 1.45 + veryDarkFraction * 0.90 + Math.max(0, 125 - medianValue) / 260 + lowSatFraction * 0.12 - backgroundPenalty * 0.25);
  const white = clamp01(brightFraction * 1.30 + veryBrightFraction * 0.85 + Math.max(0, medianValue - 150) / 280 + lowSatFraction * 0.10 - backgroundPenalty * 0.20);

  return { black, white, lowSatFraction, darkFraction, brightFraction, medianValue, medianSaturation };
}

function detectPlayer(imageData: ImageData, cells: LocalCell[]): { cell: LocalCell; confidence: number; count: number; ratio: number; candidates: number } | null {
  const scale = imageScale(imageData);
  const scores: Array<{ score: number; cell: LocalCell; count: number }> = [];
  for (const cell of cells) {
    const centre = projectCell(cell, imageData);
    const sample = sampleRect(
      imageData,
      { x: centre.x, y: centre.y + 7 * scale.sy },
      50 * scale.sx,
      26 * scale.sy,
      (hsv, r, g, b) => (
        (hsv.h >= 82 && hsv.h <= 120 && hsv.s >= 55 && hsv.v >= 45)
        || (b >= 92 && b > r * 1.12 && b > g * 1.02)
      ),
    );
    if (!sample.count) continue;
    scores.push({ score: sample.count + 0.01 * sample.saturationSum, cell, count: sample.count });
  }
  scores.sort((a, b) => b.score - a.score);
  const best = scores[0];
  if (!best) return null;
  const second = scores[1]?.score ?? 1;
  const ratio = best.score / Math.max(second, 1);
  const minimumCount = 65 * scale.area;
  if (best.count < minimumCount || ratio < 1.22) return null;
  return {
    cell: best.cell,
    confidence: Math.min(0.995, 0.68 + Math.min(best.count / Math.max(1, 500 * scale.area), 1) * 0.17 + Math.min((ratio - 1.22) / 4, 1) * 0.10),
    count: best.count,
    ratio,
    candidates: scores.length,
  };
}

function detectPillars(imageData: ImageData, cells: LocalCell[], playerCell: LocalCell | null): { pillars: LocalPillar[]; rawCount: number } {
  const scale = imageScale(imageData);
  const proposals = new Map<string, LocalPillar & { score: number; confidence: number }>();
  const playerKey = playerCell ? cellKey(playerCell) : null;
  for (const cell of cells) {
    if (playerKey && cellKey(cell) === playerKey) continue;
    const centre = projectCell(cell, imageData);
    for (const threshold of PILLAR_THRESHOLDS) {
      const sample = sampleRect(
        imageData,
        {
          x: centre.x + threshold.offset.x * scale.sx,
          y: centre.y + threshold.offset.y * scale.sy,
        },
        34 * scale.sx,
        28 * scale.sy,
        hsv => inRange(hsv, threshold.lower, threshold.upper),
      );
      const fraction = sample.total ? sample.count / sample.total : 0;
      const score = fraction * Math.min(1.25, Math.sqrt(sample.count / Math.max(1, 160 * scale.area)));
      if (fraction < threshold.minimumFraction || sample.count < 70 * scale.area) continue;
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
  const raw = [...proposals.values()].sort((a, b) => b.score - a.score);
  const selected = raw
    .slice(0, 32)
    .sort((a, b) => (a.cell.x + a.cell.y) - (b.cell.x + b.cell.y) || a.cell.x - b.cell.x || a.cell.y - b.cell.y);
  return {
    rawCount: raw.length,
    pillars: selected.map((item, index) => ({ id: `P${String(index + 1).padStart(2, "0")}`, cell: item.cell, spellType: item.spellType })),
  };
}

function legalCell(cell: LocalCell, cellSet: Set<string>): boolean {
  return cellSet.has(cellKey(cell));
}

function detectGlyphs(
  imageData: ImageData,
  cells: LocalCell[],
  occupiedCells: Set<string>,
  playerCell: LocalCell,
): {
  blackOffsets: Array<{ dx: number; dy: number }>;
  whiteOffsets: Array<{ dx: number; dy: number }>;
  physicalBlackCells: LocalCell[];
  physicalWhiteCells: LocalCell[];
  confidence: number;
  templateId: string;
  anchorCell: LocalCell;
  observedBlack: LocalCell[];
  observedWhite: LocalCell[];
  scores: Array<{ templateId: string; anchor: string; score: number; blackSupport: number; whiteSupport: number; conflict: number }>;
  provisional: boolean;
} | null {
  const cellSet = new Set(cells.map(cellKey));
  const anchors: LocalCell[] = [playerCell, { x: 0, y: 0 }]
    .filter((item, index, array) => array.findIndex(other => cellKey(other) === cellKey(item)) === index);

  const scored: Array<{
    template: GlyphTemplate;
    anchor: LocalCell;
    score: number;
    blackSupport: number;
    whiteSupport: number;
    conflict: number;
    physicalBlackCells: LocalCell[];
    physicalWhiteCells: LocalCell[];
    observedBlack: LocalCell[];
    observedWhite: LocalCell[];
  }> = [];

  for (const anchor of anchors) {
    for (const template of GLYPH_TEMPLATES) {
      const physicalBlackCells = template.black.map(offset => addCells(anchor, offset)).filter(cell => legalCell(cell, cellSet));
      const physicalWhiteCells = template.white.map(offset => addCells(anchor, offset)).filter(cell => legalCell(cell, cellSet));
      if (!physicalBlackCells.length || !physicalWhiteCells.length) continue;

      let blackSupport = 0;
      let whiteSupport = 0;
      let conflict = 0;
      const observedBlack: LocalCell[] = [];
      const observedWhite: LocalCell[] = [];

      for (const cell of physicalBlackCells) {
        if (occupiedCells.has(cellKey(cell))) continue;
        const evidence = sampleGlyphEvidence(imageData, cell);
        blackSupport += evidence.black;
        conflict += evidence.white * 0.70;
        if (evidence.black >= 0.22) observedBlack.push(cell);
      }
      for (const cell of physicalWhiteCells) {
        if (occupiedCells.has(cellKey(cell))) continue;
        const evidence = sampleGlyphEvidence(imageData, cell);
        whiteSupport += evidence.white;
        conflict += evidence.black * 0.55;
        if (evidence.white >= 0.22) observedWhite.push(cell);
      }

      const blackAvg = blackSupport / Math.max(1, physicalBlackCells.length);
      const whiteAvg = whiteSupport / Math.max(1, physicalWhiteCells.length);
      const conflictAvg = conflict / Math.max(1, physicalBlackCells.length + physicalWhiteCells.length);
      const observedBonus = (observedBlack.length / Math.max(1, physicalBlackCells.length)) * 0.08
        + (observedWhite.length / Math.max(1, physicalWhiteCells.length)) * 0.06;
      const anchorBonus = cellKey(anchor) === cellKey(playerCell) ? 0.045 : 0;
      const score = clamp01(blackAvg * 0.56 + whiteAvg * 0.44 + observedBonus + anchorBonus - conflictAvg * 0.24);

      scored.push({ template, anchor, score, blackSupport, whiteSupport, conflict, physicalBlackCells, physicalWhiteCells, observedBlack, observedWhite });
    }
  }

  scored.sort((a, b) => b.score - a.score);
  const best = scored[0];
  if (!best) return null;
  const second = scored[1]?.score ?? 0;
  const margin = Math.max(0, best.score - second);
  const confidence = Math.max(0.18, Math.min(0.90, 0.26 + best.score * 0.52 + Math.min(margin / 0.18, 1) * 0.12));

  // During the frontend migration a low-confidence phase is still usable as a provisional hypothesis.
  // The old backend rejected here, which surfaced as "Capture incomplète" even though grid/player/pillars were available.
  if (best.score < 0.015 && best.observedBlack.length + best.observedWhite.length === 0) return null;

  return {
    blackOffsets: offsetObjects(best.template.black),
    whiteOffsets: offsetObjects(best.template.white),
    physicalBlackCells: best.physicalBlackCells,
    physicalWhiteCells: best.physicalWhiteCells,
    confidence,
    templateId: best.template.id,
    anchorCell: best.anchor,
    observedBlack: best.observedBlack,
    observedWhite: best.observedWhite,
    provisional: confidence < 0.58,
    scores: scored.slice(0, 4).map(item => ({
      templateId: item.template.id,
      anchor: cellKey(item.anchor),
      score: Math.round(item.score * 1000) / 1000,
      blackSupport: Math.round(item.blackSupport * 1000) / 1000,
      whiteSupport: Math.round(item.whiteSupport * 1000) / 1000,
      conflict: Math.round(item.conflict * 1000) / 1000,
    })),
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
      ctx.fillRect(point.x - 8, point.y - 27 * imageScale(canvasImage).sy, 16, 16);
    }
    for (const cell of glyphWhite) {
      const point = projectCell(cell, canvasImage);
      ctx.fillStyle = "rgba(255,255,255,0.95)";
      ctx.strokeStyle = "rgba(0,0,0,0.8)";
      ctx.strokeRect(point.x - 8, point.y - 27 * imageScale(canvasImage).sy, 16, 16);
      ctx.fillRect(point.x - 6, point.y - 25 * imageScale(canvasImage).sy, 12, 12);
    }
    if (player) {
      const point = projectCell(player, canvasImage);
      ctx.fillStyle = "rgba(0,120,255,0.95)";
      ctx.beginPath();
      ctx.arc(point.x, point.y, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillText("PLAYER", point.x + 12, point.y + 4);
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
    "Browser vision executed locally; no backend call was used.",
    "Glyph Patch C anchors the phase detector on the detected player cell first, then falls back to arena centre.",
  ];

  const playerRaw = detectPlayer(imageData, cells);
  const playerCell = playerRaw?.cell ?? null;
  const pillarDetection = detectPillars(imageData, cells, playerCell);
  const pillars = pillarDetection.pillars;
  const occupied = new Set<string>(pillars.map(item => cellKey(item.cell)));
  if (playerCell) occupied.add(cellKey(playerCell));
  const glyphs = playerCell ? detectGlyphs(imageData, cells, occupied, playerCell) : null;

  if (pillars.length < 8) {
    warnings.push({ code: "pillar_uncertain", message: `Only ${pillars.length} pillars detected locally.`, confidence: Math.min(0.5, pillars.length / 24) });
  }
  if (pillars.length > 26) {
    warnings.push({ code: "pillar_uncertain", message: `Local pillar detector found ${pillars.length} candidates; result is provisional.`, confidence: Math.min(0.8, 24 / Math.max(1, pillars.length)) });
  }
  if (!playerRaw) {
    warnings.push({ code: "player_uncertain", message: "Player cell was not detected by local blue-base sampling.", confidence: 0 });
  }
  if (!glyphs) {
    warnings.push({ code: "glyph_uncertain", message: "Glyph phase was not detected by local player-anchored sampling.", confidence: 0 });
  } else if (glyphs.provisional) {
    warnings.push({ code: "glyph_uncertain", message: `Glyph phase is provisional: ${glyphs.templateId} anchored at ${glyphs.anchorCell.x},${glyphs.anchorCell.y}.`, confidence: glyphs.confidence });
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
    pillars_raw_detected: pillarDetection.rawCount,
    player_detected: Boolean(playerRaw),
    player_candidate_cells: playerRaw?.candidates ?? 0,
    black_glyphs_detected: glyphs?.blackOffsets.length ?? 0,
    white_glyphs_detected: glyphs?.whiteOffsets.length ?? 0,
    glyph_template: glyphs?.templateId ?? "none",
    glyph_anchor_cell: glyphs ? `${glyphs.anchorCell.x},${glyphs.anchorCell.y}` : "none",
    glyph_scores: glyphs?.scores ?? [],
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
        `Pillars: ${pillars.length} (raw ${pillarDetection.rawCount})`,
        `Glyph template: ${glyphs.templateId}`,
        `Glyph anchor: ${glyphs.anchorCell.x},${glyphs.anchorCell.y}`,
      ],
    },
    metrics: {
      cells: cells.length,
      pillars: pillars.length,
      pillarsRaw: pillarDetection.rawCount,
      playerConfidence: playerRaw.confidence,
      playerBluePixelCount: playerRaw.count,
      playerSeparationRatio: playerRaw.ratio,
      glyphTemplate: glyphs.templateId,
      glyphConfidence: glyphs.confidence,
      glyphProvisional: glyphs.provisional,
    },
  };
}

