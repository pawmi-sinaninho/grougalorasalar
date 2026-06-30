#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../services/api"
PYTHONPATH=. exec uvicorn grougal_solver.app:app --host 0.0.0.0 --port 8000 --no-access-log
