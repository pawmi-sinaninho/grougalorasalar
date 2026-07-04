# Frontend-only reason typefix

Fixed unsafe access to `result.reason` on `FrontendSolveResult`.

`FrontendSolveResult` does not expose a guaranteed `reason` property on every union member, so `api.ts` now reads the failure reason through a narrow helper that checks the property at runtime.

Patched file: `C:/Users/sinan/Documents/Grouga Dofus/apps/web/lib/api.ts`

Unsafe access replacements: 1
