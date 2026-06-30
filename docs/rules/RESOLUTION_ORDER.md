# END-OF-TURN RESOLUTION ORDER

1. Validate the state and the verified rules profile.
2. Apply each cast immediately: subtract 1 AP and 1 charge; neither may become negative.
3. Determine the final player cell.
4. Resolve a physical central black/white cell according to the guide.
5. Project all black and white offsets relative to the final player cell.
6. Collect projected pillar collisions.
7. A black collision has priority for race progress; without projected black, Crocoburio advances.
8. Apply every matching white hit, including stacked hits, after progress resolution.
9. Produce next-turn charges with `min(4, chargesAtTurnStart - castsThisTurn + matchingWhiteHits)`.

White recharge can restore a spell brought to zero during the same turn and is not suppressed merely because black determined race progress.
