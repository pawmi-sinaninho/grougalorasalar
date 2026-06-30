.PHONY: dev api web test validate fixture clean

dev:
	docker compose up --build

api:
	cd services/api && PYTHONPATH=. uvicorn grougal_solver.app:app --reload --host 0.0.0.0 --port 8000

web:
	cd apps/web && npm run dev

test:
	cd services/api && PYTHONPATH=. pytest -q

validate:
	python scripts/validate_phase7a.py

fixture:
	GS_FIXTURE_MODE=1 GS_ENV=development $(MAKE) api

clean:
	rm -rf runtime/sessions/ana_* services/api/.pytest_cache apps/web/.next


arena-build:
	python scripts/build_canonical_arena.py

arena-check:
	python scripts/build_canonical_arena.py --check
	python scripts/validate_phase7b.py

arena-benchmark:
	PYTHONPATH=. python scripts/benchmark_canonical_arena.py
