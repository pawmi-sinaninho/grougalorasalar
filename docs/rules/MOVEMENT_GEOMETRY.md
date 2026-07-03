# MOVEMENT GEOMETRY

This document is the verified DofusPourLesNoobs/observed movement contract.

- **Indécision:** destination is exactly one orthogonal neighbour. Diagonals, off-arena cells, pillars, obstacles and occupied destinations are illegal.
- **Reflet:** target an any-colour pillar on exactly one of the eight cells at Manhattan distance 2: `(±2,0)`, `(0,±2)`, `(±1,±1)`. Destination is `2*T-P`. Another pillar or obstacle may not be crossed; destination must be free and in the arena.
- **Rejet:** target an any-colour pillar on one of the eight cardinal/diagonal rays at one or two aligned logical steps. A cardinal cast moves exactly three cells away; a diagonal cast moves exactly two diagonal cells away. Every traversed cell and the destination must be free and inside the arena. A pillar, obstacle or arena edge anywhere on that movement path makes the cast illegal; movement is never truncated.
- **Attrait:** target an any-colour pillar only on one of the four cardinal lines at range 1 through 6; diagonal targets are illegal. The complete ray from player to target must be clear of every other pillar and obstacle, including blockers beyond the three-cell movement destination. Move up to three cells toward the pillar and stop immediately before it when closer.

Internal spell IDs remain `indecision`, `reflection`, `repulsion`, `attraction`; player-facing names are Indécision, Reflet, Rejet and Attrait.
