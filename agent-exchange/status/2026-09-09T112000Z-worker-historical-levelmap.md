# Agent Exchange Result

Target:
Codex controller

Sender:
Codex scoped Task3 implementer

Created at:
2026-09-09T11:27:27Z

Request:
agent-exchange/inbox/codex/2026-09-09T112000Z-historical-levelmap.md

Status:
IMPLEMENTED_AWAITING_CODEX_REVIEW

Summary:
Implemented the public historical level-map adapter over accepted frames,
correction evidence and complete source graph. It preserves lazy source fetch
order and asymmetric gates, records causal selected dependency evidence, emits
stable-ID LevelSnapshot-compatible maps at decision time, and blocks invalid
source levels/errors. All readiness flags and tradeable remain false.

Changed files:

- trading_system/tree_replay/levelmap.py
- tests/tree_replay/test_levelmap.py
- docs/architecture/HISTORICAL-LEVELMAP-USAGE.md
- .superpowers/sdd/2026-09-09-historical-levelmap-core/task-3-report.md
- agent-exchange/status/2026-09-09T112000Z-worker-historical-levelmap.md

Verification results:

- RED: python -m pytest tests/tree_replay/test_levelmap.py -q --tb=short:
  31 failed in 1.10s, explicit missing-adapter assertion before implementation.
- First implementation: 30 passed / 1 failed; real EMA roundoff required an approx
  stop assertion. Source behavior was not changed. Then 31 passed in 4.66s.
- Final same focused command: 40 passed in 5.65s, exit 0, no uncaptured warnings.
  Nine supplementary characterization cases passed existing implementation;
  they are not claimed as a separate pre-implementation RED cycle.
- Real synthetic map -> LevelSnapshot -> reversal -> pricing, plus no-candidate
  path. Exact source families/order/prices and temporal/gating/hash/error tests.
  No calculation dependencies mocked.
- Self-reviewed actual untracked three-file diffs; no whitespace-error diagnostics.
- Controller reported all six source audit CLIs PASS; not rerun by worker.
  Integration/broad suites are controller-owned and not run by worker. Broad
  command must explicitly retain --ignore-glob='*validator*' legacy exclusion.

Decisions needed:
None for this implementation. No new domain thresholds or instrument mappings.

Blockers:
None for Task3 implementation. Controller verification/review/acceptance pending.

Recommended next action:
Review the five scoped files and detailed task-3-report.md, run controller-owned
integration/broad checks, then record acceptance and controller documentation.

Notes:
Closed-base precision and supplied calendar/correction provenance are explicit
attestations. Full producer/admission/arbitration, execution, datasets, training
and human gates remain open. No accepted dependency changes, nested agents,
commits/worktrees/cleanup, source downloads, real-data access, live changes or
deployment. ready_for_replay=false; ready_for_training=false; tradeable=false.
