repo: C:\Users\sinan\Documents\Grouga Dofus
wrote: services\api\grougal_solver\perf_runtime.py
wrote: services\api\grougal_solver\solver_perf.py
patched FastAPI perf middleware: services\api\grougal_solver\app.py
decorated services\api\grougal_solver\solver.py: _apply_movement_constraints
decorated services\api\grougal_solver\fast_recognition.py: import only
wrote: apps\web\lib\perfFetch.ts
patched frontend API fetch cache: apps\web\lib\api.ts
frontend-solver directory not found; local solver perf helpers skipped.
wrote: tools\benchmark_recommendation_perf.py
wrote: docs\PERF_RECOMMENDATION_ACTIONS.md

git status --short:
M apps/web/lib/api.ts
 M apps/web/next-env.d.ts
 M services/api/grougal_solver/app.py
 M services/api/grougal_solver/fast_recognition.py
 M services/api/grougal_solver/solver.py
?? .perf_patch_backup/
?? apply_recommendation_perf_patch_v2.py
?? apps/web/lib/perfFetch.ts
?? docs/PERF_RECOMMENDATION_ACTIONS.md
?? services/api/grougal_solver/perf_runtime.py
?? services/api/grougal_solver/solver_perf.py
?? tools/

git diff --stat:
warning: in the working copy of 'apps/web/lib/api.ts', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'services/api/grougal_solver/app.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'services/api/grougal_solver/fast_recognition.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'services/api/grougal_solver/solver.py', LF will be replaced by CRLF the next time Git touches it
 apps/web/lib/api.ts                             | 13 +++++++------
 apps/web/next-env.d.ts                          |  2 +-
 services/api/grougal_solver/app.py              |  2 ++
 services/api/grougal_solver/fast_recognition.py |  1 +
 services/api/grougal_solver/solver.py           |  2 ++
 5 files changed, 13 insertions(+), 7 deletions(-)
