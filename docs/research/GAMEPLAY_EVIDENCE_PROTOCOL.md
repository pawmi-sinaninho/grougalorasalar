# GAMEPLAY EVIDENCE CAPTURE PROTOCOL

## Goal

Turn live gameplay into reproducible evidence that can close a specific rule ID.

## Minimum recording settings

- original resolution;
- full game window visible;
- lower gauges and both progress tracks visible;
- no crop or social-media recompression;
- language and UI scale recorded;
- game version/build recorded when visible.

## Per-turn capture

For every turn save:

1. screenshot before the first action;
2. exact spell name;
3. exact target cell or pillar;
4. screenshot immediately after each cast when practical;
5. screenshot immediately before ending the turn;
6. screenshot after progress and recharge resolution;
7. whether any spell became unavailable.

## Observation naming

```text
run-<date>-turn-<nn>-obs-<nn>
```

Example:

```text
run-2026-07-04-turn-03-obs-02
```

## High-value edge cases

- Attrait with pillar 1 or 2 cells away;
- Rejet toward map edge;
- Reflet destination occupied by a pillar;
- black and white projected hits in one turn;
- direct central white cell;
- direct central black cell;
- no pillar touched by either colour;
- same start and final cell after multiple casts;
- spell cursor exactly reaching the black endpoint;
- two white hits on same spell colour;
- multiplayer entry and shared spell use.

## Review rule

A gameplay observation closes a critical mechanic only when the before-state, action and after-state are all visible or independently reconstructable.
