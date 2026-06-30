# TEST ORACLE SPECIFICATION

## Purpose

The Phase-3 oracle catalogue specifies expected behaviour without claiming that synthetic profiles match live DOFUS. It separates:

- formula and enumeration contracts;
- authority/status gates;
- gameplay evidence fixtures.

## Catalogue

`data/solver/fixture-catalog.v0.5.0.json` contains 26 fixtures:

- 25 synthetic contract/gating cases;
- one compact gate projection of the Phase-2 manual reference screenshot.

Each fixture declares:

- exact input summary;
- arena authority classes;
- player, pillars and glyphs;
- resources and flags;
- definite and conditional root actions;
- terminal outcomes where relevant;
- status and reason codes;
- expected recommendation ordering.

## Interpretation

Every fixture names `profileId = review-explicit-hypothesis-0.5.0` and then applies only its declared `profileOverrides`.

`profileMode = explicit_test_profile` means the named concrete values are tested as a formal contract while live evidence authority is intentionally ignored. It is not gameplay evidence and may not be loaded in production.

`profileMode = real_authority_profile` means the expected status applies the actual rule-catalog authority. These cases expose where the current product must confirm or block.

## Oracle equality

Two implementations are compliant when, for every fixture, they produce the same:

1. status;
2. set of definite root action signatures;
3. set of conditional action signatures and dependency rule IDs;
4. listed terminal outcomes;
5. ordered recommendation sequence list.

Messages, internal node IDs and trace prose may differ. Canonical signatures, reason codes and rule IDs may not.

## Gameplay-fixture gate

Synthetic fixtures prove implementation consistency only. A fixture becomes gameplay-authoritative only after it references a reviewed `VerificationObservation` with original evidence and all used critical rules are promoted appropriately.
