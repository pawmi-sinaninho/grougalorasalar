# Frontend-only spell mechanics gate patch

## Problem

The browser-local solver can currently display recommendations that look solved but violate spell mechanics or overlay assumptions.
This is worse than no recommendation.

## Fix

This patch adds a central mechanics gate for all four spells in the frontend TypeScript solver:

- Indécision: target/destination must be exactly one orthogonal adjacent free cell.
- Reflet: target must be a pillar exactly one diagonal cell away (`abs(dx)=1`, `abs(dy)=1`), and destination is the reflected cell behind that pillar if free.
- Rejet: target must be a pillar straight/diagonal at range 1-2; movement is away from the target pillar up to 3 cells, shortened at the first obstacle/border, with diagonal corner blocking.
- Attrait: target must be a pillar in a straight line at range 1-6; path to target must be clear; movement is up to 3 cells toward the pillar and stops before it.

The gate runs inside `enumerateActions`, before candidates can enter the BFS/ranking. If the local generator makes a bad action, the gate removes it.

## Intent

No invalid recommendation should reach the UI. This may temporarily reduce the number of displayed solutions, but that is safer than showing broken instructions.
