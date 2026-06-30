# DEFECT BACKLOG — v0.9.0

| ID | Status | Severity | Area | Defect / gap | Acceptance evidence |
|---|---|---|---|---|---|
| P7-001 | Open | Blocker | Gameplay | Resolve V-001–V-010 with current-version recordings | Adjudicated observations and promoted rule authorities |
| P7-002 | Partially resolved | Blocker | Vision | Fast baseline exists; locked-corpus generalisation remains absent | 150 screenshots, 15 sessions, field metrics, zero critical false-safe results |
| P7-003 | Partially resolved v0.9.0 | High | UX | Player and glyph correction are direct-click; full pillar add/move/delete correction remains incomplete | Browser E2E for remaining pillar correction operations |
| P7-004 | Open | High | Oracle | Phase-3 fixtures contain focus-scoped and malformed expectations | Versioned erratum or assertion-scope field |
| P7-005 | Resolved v0.9.0 | High | Runtime | Docker Compose clean-start path failed | No-cache build, health checks, browser E2E, down, and restart log |
| P7-006 | Partially resolved v0.9.0 | High | Testing | Real-fixture Playwright E2E exists; visual regression and accessibility remain open | Desktop/tablet/mobile, keyboard, and accessibility CI reports |
| P7-007 | Open | High | Privacy | Expiry cleanup lacks supervised periodic execution/race tests | Kill/restart/expiry/deletion integration tests |
| P7-008 | Resolved v0.8.0 | Medium | UI | Fixed action-budget button value 3 | Explicit unknown/numeric selection with no default |
| P7-009 | Open | Medium | UI | German/English copy is not selectable at runtime | Locale routing and key-parity browser tests |
| P7-010 | Partially resolved v0.9.0 | Medium | Resources | Three-state spell availability is explicit; numeric charges remain open | Numeric-value UI tests |
| P7-011 | Open | Medium | Operations | Rate limiting and production telemetry exporters absent | Load test, bounded metrics, payload-redaction test |
| P7-012 | Open | Medium | Security | No content/malware scanner integration | Threat-model decision and upload-fuzz evidence |
| P7-013 | Open | Medium | Deployment | Filesystem session store prohibits scaling | Single-replica contract or durable-store ADR |
| P7-014 | Open | Low | API | Starlette TestClient deprecation warning | Dependency/API update with clean test output |
| P7-015 | Open | High | Vision | Browser-local registration/classification equivalence is unproven | Same-corpus logical equality and cold-start measurements |
| P7-016 | Open | High | Vision | Glyph completeness is not proven across the full corpus | Double annotation, adjudication, detector metric |
| P7-017 | Partially resolved v0.9.0 | High | UI extraction | Action/spell manual fallback exists; automatic extraction and progress indices remain open | Current-version UI evidence and field-specific extraction tests |
| P7-018 | Open | Medium | Performance | Full supported-hardware percentiles are not measured | Playwright User Timing report |
| P7-019 | Open | Medium | Runtime | Five-second cancellation is not isolated from late persistence | Timeout integration test |
| P7-020 | Partially resolved v0.9.0 | Blocker | Arena | 338-cell structure exists; seven boundary cells remain unresolved | Empty edge-review list and position verification |
| P7-021 | Open | Low | Evidence | Original green boundary annotation bytes are absent | Re-upload or equivalent signed evidence |
| P7-022 | Resolved v0.9.0 | Blocker | Packaging | Fresh Web build failed in `npm install --ignore-scripts` | Pinned Node/npm, `npm ci`, no-cache Compose build, restart |
| P7-023 | Resolved v0.9.0 | Blocker | Player UX | Standard flow exposed coordinates/internal blockers and no usable recommendation | Real-fixture Playwright upload-to-recommendation flow |
