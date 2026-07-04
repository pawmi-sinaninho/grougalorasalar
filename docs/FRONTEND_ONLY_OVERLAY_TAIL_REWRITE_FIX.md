# Frontend-only overlay tail rewrite fix

This patch repairs the broken `localSolverResultToFrontendResult` tail after the overlay wiring patch.

It deliberately does not apply another line-level fix. It truncates the corrupted function tail and appends one clean implementation, then reinforces the frontend solver result types used by the overlay UI.

Fixed failure classes:

- `export export function ...`
- dangling fragments such as `},
): FrontendSolveResult {`
- duplicate `localSolverResultToFrontendResult` bodies
- missing action geometry fields in `SolverActionStep`
- missing `expected` field in `FrontendSolveResult`
