# Agent Exchange Request

Target:
Codex scoped Task3 implementer

Sender:
Codex controller

Created at:
2026-09-09T11:20:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Bind causal historical frames and correction evidence to the original complete
map graph and demonstrate real reversal/pricing consumption of its output.

Scope:
Task3 exact brief .superpowers/sdd/2026-09-09-historical-levelmap-core/task-3-brief.md.
Start only on controller dispatch after dependency acceptance.

Required inputs:
Accepted frames.py, corrections.py, levels.py, _vendor/levelmap_build.py and
existing real reversal/pricing fixtures; supplied synthetic inputs only.

Contracts:
Lazy original fetch order, common explicit decision time, source gates retained,
actual dependency traces, stable IDs, false readiness and no admission.

Non-negotiables:
- point-in-time correctness, no invented thresholds, feeds or instrument aliases
- no production approval, data access, downloads, fitting or live operations
- preserve dirty files, no commits/worktrees/cleanup or nested agents

Deliverables:
Only levelmap.py, test_levelmap.py, HISTORICAL-LEVELMAP-USAGE.md; detailed report
in this plan's task-3-report.md; exchange result
agent-exchange/status/2026-09-09T112000Z-worker-historical-levelmap.md.

Verification commands:
python -m pytest tests/tree_replay/test_levelmap.py -q --tb=short
Controller owns all-audit, integration, broad tests and final acceptance.

Out of scope:
Existing dependency modifications, master/README/AGENTS updates (controller),
producer admission/arbitration, simulator, dataset, model and full-goal acceptance.
