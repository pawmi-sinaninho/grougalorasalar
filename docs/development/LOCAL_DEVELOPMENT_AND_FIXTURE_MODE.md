# LOCAL DEVELOPMENT & FIXTURE MODE — Phase 5

## 1. Supported setup

Primary reproducible path on Windows, macOS and Linux:

```text
Docker Desktop / Docker Engine with current Docker Compose plugin
Git
```

Native Node/Python setup is optional for faster development but cannot replace the container acceptance path.

## 2. Required commands

Phase-6 repository must implement these exact root commands:

```bash
docker compose up --build
```

Starts web at `http://localhost:3000` and API at `http://localhost:8000`.

```bash
docker compose run --rm api python tests/validate_phase5.py
npm ci
npm run check
npm run test:e2e
npm run fixture -- VFX-001
```

`npm run check` must run formatting check, TypeScript, lint, contract generation drift, Python static checks and unit/contract tests through repository scripts. The user should not need to remember package-specific commands.

## 3. Native development contract

```bash
npm ci
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
npm run dev
```

`npm run dev` launches both processes and stops both when one fails. Runtime version checks fail with a precise message when Node/Python do not match the frozen baseline.

## 4. Fixture mode

Enable only locally/test:

```bash
GS_ENV=development GS_FIXTURE_MODE=1 npm run dev
```

Fixture mode provides:

- visual fixtures `VFX-001`–`VFX-020`;
- solver fixtures `F-001`–`F-026`;
- the reference manual editor session;
- forced lifecycle/error states;
- deterministic fake latency, optional only;
- downloadable JSON for recognition, TurnState, recommendation, trace and overlay.

Fixture mode cannot:

- silently switch the production rules profile;
- auto-confirm fields that the fixture does not mark confirmed;
- write to consented evidence storage;
- be enabled in preview/production.

## 5. Developer diagnostics

The diagnostics page shows:

- release/runtime/schema/model versions;
- manifest verification;
- current analysis lifecycle and state version;
- observation list with confidence components and reason codes;
- immutable detector proposal vs manual override;
- solver preflight, dependencies, node counts and timings;
- privacy timer and asset inventory.

It does not show secrets, local absolute paths or unrelated environment variables.

## 6. Seeded acceptance flow

A single command must load a known fixture and produce a stable result:

```bash
npm run fixture -- F-019
```

Expected outcome is read from the fixture catalogue, never hard-coded in the script. The command exits non-zero on schema, status, canonical-sequence or trace mismatch.

## 7. Reproducibility

- dependency lockfiles are mandatory;
- container images use immutable digests in release manifests;
- generated bindings include a schema-manifest checksum;
- the complete test suite records OS/architecture/runtime versions;
- no test depends on network access or current external services.
