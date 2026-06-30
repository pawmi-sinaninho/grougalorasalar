# UNKNOWN RULES AND SAFE DEFAULTS

## Principle

A safe default is not a guessed game mechanic. It is a product behaviour used when a mechanic is unknown.

| Unknown | Unsafe behaviour | Safe product behaviour |
|---|---|---|
| AP/cast budget | Assume a number and recommend too many casts | Ask the user to confirm visible AP or restrict to manually entered budget |
| Numeric charges | Infer exact values from gauge artwork | Use available/unavailable/unknown until calibrated |
| Path blocking | Apply generic DOFUS displacement logic | Mark affected actions as mechanically ambiguous |
| Short-range Attrait | Assume truncation or overshoot | Exclude those targets unless confirmed |
| Track length | Hard-code 13 or 14 | Detect progress visually and treat threshold as profile data |
| Multiplayer | Solve only the selected avatar | Reject screenshot with multiple controllable characters |
| Central white glyph | Assume all spells +1 | Show assumption and require confirmation |
| No black/no white outcome | Assume Crocoburio +1 | Use only under a named single-source assumption |

## Pre-live permissive mode

A developer-only permissive mode may simulate hypotheses for testing. Its output must contain:

- `status = confirmation_required` or `blocked_unverified_rule`;
- every assumption ID;
- the alternative outcomes under other supported profiles.

It must never be presented as a normal player recommendation.
