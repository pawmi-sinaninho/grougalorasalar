# Local Runbook — v0.8.0

## 1. Supported acceptance path

Prerequisite: Docker with Compose v2.

```bash
docker compose up --build
```

Then open:

- web workbench: `http://localhost:3000`
- API readiness: `http://localhost:8000/api/v1/health/ready`
- API documentation: `http://localhost:8000/docs`

Stop and delete containers/ephemeral volume:

```bash
docker compose down -v
```

## 2. Native development path

Required baseline:

- Node.js 24 LTS;
- CPython 3.13;
- isolated Python virtual environment.

Backend:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r services/api/requirements.txt
make api
```

Frontend in a second shell:

```bash
cd apps/web
npm ci
npm run dev
```

## 3. Validation commands

```bash
make test
python tests/validate_phase5.py
python scripts/validate_phase7a.py
python scripts/benchmark_fast_path.py
cd apps/web && npm run typecheck && npm run build && npm audit --audit-level=moderate
```

Contract/runtime files are reproducible with:

```bash
python scripts/generate_contracts.py
python scripts/generate_runtime_manifest.py
python scripts/generate_sbom.py
```

## 4. Fixture mode

Development only:

```bash
GS_FIXTURE_MODE=1 GS_ENV=development make api
```

Fixture mode must fail startup in `preview` and `production`. Never expose it through an internet-facing development server.

## 5. Manual smoke test

1. Open the web page.
2. Upload `assets/reference/user_reference.png`.
3. Verify that 27 pillar proposals appear in the API state and the gate remains `review_required`.
4. Confirm proposals, anchor and pillar completeness.
5. Enter the actual action budget; the minimal web UI currently exposes the value 3 directly.
6. Confirm each spell state.
7. Correct player, pillars and glyphs as needed.
8. Run the solver.
9. Inspect the ordered actions and annotated PNG.
10. Delete the analysis through the API before treating the smoke test as complete.

## 6. Operational invariants

- `automaticCriticalConfirmation` must remain `false`.
- readiness must fail on runtime-manifest mismatch;
- fixture mode must be false outside development/test;
- only one API replica may write the local session volume;
- protected analysis responses must remain `Cache-Control: no-store`;
- capacity errors must never be translated into `no_safe_solution`.

## 7. Recovery

The default data is ephemeral. Recovery means restoring service, not restoring analyses.

- restart the single API and web containers;
- remove corrupt/expired session directories;
- rerun readiness and the vertical-slice test;
- do not copy screenshots into logs or support tickets without explicit consent.
