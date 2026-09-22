# SDD ledger — plan: docs/superpowers/plans/2026-09-09-reversal-pricing.md

Full objective remains active. Baseline HEAD c1b6071633c55376c64f0a98ece843706f420f49.
Normal checkout, existing plan/tree-to-trained-model-langgraph; no commits/cleanup.
Existing reversal baseline freshly verified: 156 passed in5.88s.

| Tasks | Interface/self consistency | Finding |
| --- | --- | --- |
| 1 / 2 | source build_plan(Reversal, levels, DataFrame) -> pricing wrapper | Pure dependencies; same source ATR, not indicators ATR |
| 1 / 3 | fixed manifest/audit -> parity evidence | Explicit class projection, existing detector audit also required |
| 2 / 3 | priced but unadmitted -> docs/evaluation | Source tradeable separate from whole-pipeline admission |
| 1 | tests vs copies | Zone-edge stop and obstacles are original behavior, no new formulas |
| 2 | instruments vs existing bars | Full identity retained; unsupported GC not remapped to spot |
| 3 | acceptance vs full goal | Component acceptance not dataset/model completion |

Task1: pending sidecar dispatch. Task2: parent starts TDD. Task3: pending.
No domain rulings; observed source constraints are documented in the plan.

Task1: Carver (01a08594-7504-7a63-b1ce-aae5962b8d27) implementing source dependencies.
Task2: initial RED24 missing pricing module; then GREEN24 with actual source modules.
Source-levelmap inspection found duplicate Q-QUARTER names at distinct prices;
previous name-only identity rejects legitimate target maps.
Ruling: allow repeated display names only with distinct explicit level_id and prices, retaining rejection of ambiguous duplicates — source quarters require multiple same-named locations; detector calculations are unchanged — if identity policy is wrong, historical level adapters and stored evidence keys need migration, not invented trade prices.
Amendment RED8 failed/24 passed (new identity unsupported). Preserve before-images
of levels.py/reversal.py for task review; bump adapter version for changed hashing.

Task 1: complete (HEAD unchanged c1b6071, spec and quality approved by Newton).
Task 1: minor (deferred): source tests depend on a retained user-specific checkout;
final reviewer must triage portability before future CI reuse.
Task 2: complete (HEAD unchanged c1b6071, spec and quality approved by Leibniz).
Cross-task items resolved: original numerical pricing audit independently passed;
wrapper positive/finite/closed/available/exact identity guards verified by parent
197-test run and Task2 review. Detector diff changes version only. No persisted
new dataset exists to migrate; v2 evidence incompatibility documented explicitly.
Full-tree/live behavior claims remain outside scope; no imports into live paths.
Fresh integration:1027 passed in60.82s. Broad suite running (legacy validators
excluded). Both previous source CLIs passed, blockers empty/readiness false.
Task3: docs and final combined review in progress. All three task agents closed.

Broad run completed:1399 passed in177.77s, exit0, legacy validators excluded.
Final reviewer Chandrasekhar:01a085a2-e59b-75c0-9161-23d711b9ec9a.
Source symbol inventory cross-check: basis.TV_ONLY line108, patterns.SYMBOLS
line63 and tradeplan.build_all defaults line2101 name the three exact identities.
Next source intake documented in HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md; no
historical-map implementation or partial-period correctness claim yet.

Task 3: complete (HEAD unchanged c1b6071, final review spec/quality approved;
one nonblocking deferred Minor portability item). Final parent scoped197 passed
in12.30s; pricing sourceCLI passed. Acceptance recorded in
agent-exchange/status/2026-09-09T101048Z-codex-reversal-pricing.md.
Final reviewer closed. No code changed after verification; no commit/cleanup.
Full master-plan scope remains open; next source map documented, not implemented.
