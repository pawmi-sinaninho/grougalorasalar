# Frontend-only optional result fields typefix

This patch keeps `apps/web/lib/api.ts` compatible with the current `FrontendSolveResult` type.

## Why

The frontend runtime result type does not guarantee optional diagnostic fields such as:

- `confidence`
- `warnings`
- `debug`

The API boundary must therefore read them through safe runtime helpers instead of direct property access.

## Changed

- Added typed helper accessors for optional frontend result diagnostics.
- Replaced direct `result.confidence`, `result.warnings`, and `result.debug` reads in `apps/web/lib/api.ts`.

## Expected result

`npm run build` should progress past the previous TypeScript error:

```text
Property 'confidence' does not exist on type 'FrontendSolveResult'.
```
