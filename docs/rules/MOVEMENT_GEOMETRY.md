# MOVEMENT GEOMETRY

This document is the verified DofusPourLesNoobs/observed movement contract.

- **Indécision:** destination is exactly one orthogonal neighbour. Diagonals, off-arena cells, pillars, obstacles and occupied destinations are illegal.
- **Reflet:** target any-colour pillar at exactly two aligned logical steps, cardinal or diagonal. Destination is `2*T-P`. Another pillar or obstacle may not be crossed; destination must be free and in the arena.
- **Rejet:** target cardinally or diagonally; move up to three cells away. Stop at the last free cell before a pillar, obstacle or arena edge. The destination must be free.
- **Attrait:** target cardinally or diagonally; move up to three cells toward the pillar and stop immediately before it when closer. Pillars/obstacles may not be crossed and the destination must be free.

Internal spell IDs remain `indecision`, `reflection`, `repulsion`, `attraction`; player-facing names are Indécision, Reflet, Rejet and Attrait.
