# REJECTION & FAILURE-COPY CONTRACT — Phase 4

## 1. Rules

Each message must contain:

1. what could not be established;
2. why this matters;
3. the single next action the user can perform.

Do not use “AI error”, “something went wrong” or confidence percentages without a remedy.

The machine-readable multilingual catalogue is `data/vision/failure-message-catalog.v0.5.0.json`.

## 2. Severity

- `blocker`: no solver call;
- `warning`: solver may continue with a precisely limited claim;
- `info`: no safety effect.

## 3. Stable reason codes

Reason codes are stored in recognition results and audit logs. UI translations can change without changing the semantic code.

Principal codes:

- `IMG-*` — file, arena presence or crop;
- `REG-*` — registration;
- `MULTI-*` — solo-scope failure;
- `PLAYER-*` — player extraction;
- `PILLAR-*` — pillar set/cell/type;
- `GLYPH-*` — black/white pattern;
- `ANCHOR-*` — projection anchor;
- `BUDGET-*` — action budget;
- `SPELL-*` — spell resources;
- `PROGRESS-*` — race tracks;
- `MODEL-*` — validation-policy gate.

## 4. Claim limitation

Warnings must change the actual output. Example: `PROGRESS-001` removes any “wins this turn” or “loses this turn” claim; it is not merely a banner above an unchanged result.
