# VISUAL & INTERACTION SYSTEM — Phase 5

## 1. Direction

The interface is a tactical workbench, not a generic analytics dashboard. The screenshot is the main surface. Panels exist to verify evidence and execute one next action.

Use original UI geometry and symbols. Do not copy decorative DOFUS panels, fonts or game assets into the product chrome. Game imagery appears only inside the user-provided screenshot and consented diagnostic derivatives.

## 2. Tokens

### Neutral surfaces

- background: near-black neutral;
- workbench: slightly lighter matte surface;
- panel: opaque, high-contrast surface;
- borders: one-pixel neutral plus focus outline;
- text: primary, secondary and disabled tiers meeting WCAG AA.

### Semantic signals

- confirmed: check symbol plus solid outline;
- review: question symbol plus dashed outline;
- conflict: split diamond plus cross-hatch;
- missing: hollow marker plus label;
- manual override: small audit notch plus “modifié”.

Spell semantics retain their established colours, always paired with icon/letter:

- Indécision: cyan + `I`;
- Reflet: green + `R`;
- Rejet: yellow + `J`;
- Attrait: red + `A`.

Black/white glyphs use fill plus contrasting border and pattern, so white cells remain visible on pale tiles.

## 3. Overlay grammar

- player: double-ring diamond centred on logical cell;
- pillar: numbered circle anchored at pillar base, with spell letter;
- black glyph: filled square with diagonal hatch;
- white glyph: hollow square with dot pattern;
- uncertainty: small attached badge, never a global fog;
- action target: numbered pin matching the instruction number;
- movement: segmented arrow from source to destination;
- final cell: thick octagonal ring;
- unsafe projected hit: cross marker on the exact pillar;
- recharge hit: plus marker on the exact pillar.

Overlay z-order:

1. screenshot;
2. grid/boundary hints;
3. detected objects;
4. uncertainty/conflicts;
5. active edit preview;
6. recommendation actions;
7. focus/keyboard indicator.

## 4. Rendering rules

- use SVG for crisp logical overlays and accessible element grouping;
- image and SVG share one transform matrix;
- logical coordinates are the source of truth; no per-resolution hand-tuning;
- zoom may not change stroke widths below readable minimums;
- hit targets are at least 32 CSS px on desktop;
- overlays remain aligned under browser zoom and high-DPI displays;
- annotated export uses the same overlay document, rendered server-side or deterministically in browser.

## 5. Motion

Only informational motion is permitted:

- 150–200 ms marker transition after a confirmed move;
- progressive reveal of numbered action arrows;
- brief invalidation fade when a result becomes stale;
- no looping glows, bouncing CTAs or fake AI scanning animations.

Respect `prefers-reduced-motion` by replacing transitions with immediate state changes.

## 6. Correction interaction

- selection previews the logical cell before commit;
- destructive edits require undo, not modal confirmation, except deleting the whole analysis;
- alternatives are shown side by side or toggled on the same screenshot region;
- the active tool and affected field are always visible;
- every command returns validation feedback adjacent to the edited object;
- manual confirmation never changes the displayed detector score.

## 7. Result visual hierarchy

1. numbered executable actions;
2. exact target markers on screenshot;
3. final position;
4. race outcome and recharge;
5. assumptions/claim limits;
6. alternatives and full trace.

Do not lead with a percentage. Confidence is supporting evidence after the action sequence and gate status.
