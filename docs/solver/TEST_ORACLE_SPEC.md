# SOLVER TEST ORACLE

`data/solver/verified-rules-fixtures.v1.0.0.json` is the active oracle. It replaces the hypothesis-era 26-fixture catalogue.

The oracle fixes charge transitions, all four orthogonal Indécision offsets, all four rejected diagonal offsets, exact-range cardinal/diagonal Reflet, three-cell Rejet with blocker/edge truncation, and stop-before-pillar Attrait. Executable coverage lives in `services/api/tests/test_verified_rules.py`.
