# TEST MATRIX & PERFORMANCE BUDGETS — Phase 5

## 1. Test layers

| Layer | Required scope | Release blocker |
|---|---|---|
| Schema/contract | every schema and example; TS/Python generated-binding parity | yes |
| Unit | transforms, commands, gates, storage deletion, copy interpolation | yes |
| Property | Phase-3 geometry, search, ranking and status invariants | yes |
| Fixture regression | all 26 solver and 20 visual fixtures | yes |
| Integration | upload→recognition→edit→solve→overlay→delete | yes |
| Browser E2E | Chromium, Firefox, WebKit desktop; upload/paste/keyboard | yes |
| Visual regression | key workspace states at 1440×900 and 1920×1080 | yes |
| Accessibility | automated WCAG checks plus keyboard-only scripted flow | yes |
| Privacy | TTL, delete, no-log payload, consent isolation | yes |
| Security | decompression bomb, MIME mismatch, path traversal, oversized file | yes |
| Performance | budgets below on reference CPU profile | yes for manual-first path |

## 2. Contract tests

- OpenAPI payloads validate against the versioned JSON Schemas;
- generated TypeScript and Pydantic adapters preserve enum values and required fields;
- unknown additional properties are rejected where schemas forbid them;
- old Phase-3/4 schema versions remain readable and are not rewritten silently;
- API error codes and UI message keys have one-to-one catalogue coverage.

## 3. Critical end-to-end scenarios

1. valid image, all automatic fields require confirmation under unvalidated model;
2. manual registration, full board correction, solver blocked by projection anchor;
3. complete confirmed fixture, solved recommendation and overlay;
4. progress unknown, movement recommendation without terminal claim;
5. correction after solve invalidates result;
6. duplicate command with idempotency key does not duplicate audit;
7. stale state version returns conflict and preserves newer state;
8. rejected arena never exposes solve action;
9. multiplayer detection rejects V1;
10. deletion during recognition prevents late persistence;
11. TTL cleanup removes every asset and record;
12. fixture mode startup is refused under production environment.

## 4. Performance budgets

Measured after warm-up on the declared reference machine in Phase 6; until then these are engineering gates, not achieved claims.

| Operation | Budget |
|---|---:|
| landing interactive on local preview | <= 2.0 s p95 |
| upload validation before recognition | <= 500 ms p95 for 10 MiB local file |
| image decode + normalisation | <= 1.5 s p95 at 4K |
| baseline registration | <= 3.0 s p95 CPU |
| complete baseline recognition | <= 8.0 s p95 CPU, <= 15 s hard timeout |
| editor command API | <= 150 ms p95 excluding image export |
| viewport edit feedback | <= 100 ms perceived latency |
| solver search | <= 500 ms p95 normal fixtures; 2 s hard timeout |
| overlay JSON generation | <= 200 ms p95 |
| annotated PNG export | <= 2.0 s p95 at 4K |
| delete endpoint | <= 500 ms p95 plus asynchronous secure filesystem cleanup <= 10 s |

Memory guards:

- API RSS <= 1.5 GiB during one 33.2 MP analysis;
- no more than three concurrent analyses per API instance in preview;
- browser workbench <= 500 MiB for a 4K screenshot;
- solver max 100,000 visited nodes unless a reviewed fixture proves a higher safe bound.

## 5. Capacity semantics

Hitting timeout, node, memory or queue limits returns a technical capacity result/error. It must not produce `no_safe_solution`, `solved` or a partial recommendation.

## 6. Accessibility acceptance

- entire correction flow executable by keyboard at desktop width;
- visible focus on every interactive overlay element;
- 200% browser zoom without lost controls;
- no meaning conveyed by colour alone;
- status announcements use polite live regions and do not repeat on every polling tick;
- reduced-motion path tested;
- French, German and English labels fit without clipping in the accepted breakpoints.

## 7. Release report

Phase 6 must output one machine-readable and one Markdown report containing test counts, failures, skipped tests with reason, performance environment, measured percentiles and known limitations. “Pass” cannot hide skipped critical scenarios.
