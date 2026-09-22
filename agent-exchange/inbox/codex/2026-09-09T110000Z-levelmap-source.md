# Agent Exchange Request

Target:
Codex scoped source implementer

Sender:
Codex controller

Created at:
2026-09-09

Status:
ACCEPTED_BY_CODEX

Objective:
Port and audit the complete original level-map calculation graph, including its
session/PSY dependencies, with explicit offline source and replay-clock injection.

Scope:
Task1 of docs/superpowers/plans/2026-09-09-historical-levelmap-core.md;
extracted task brief in that plan's own scratch directory is the exact contract.

Required inputs:
Pinned chartdesk/levelmap.py and sessions.py, accepted range/EMA/quarter/correction
dependencies. Source text only, not source module execution.

Contracts:
Original complete family order/guards/formulas; narrow listed AST adaptations;
false readiness; no mutation to existing dependencies.

Non-negotiables:
- point-in-time correctness
- no invented thresholds, feeds, aliases or features
- no production approval by implication
- no live trading, broker execution, capital allocation, data access or training
- preserve dirty checkout; no commits, worktrees, cleanup or nested agents

Deliverables:
Task1 files, tests and report at
agent-exchange/status/2026-09-09T110000Z-worker-levelmap-source.md,
plus detailed task-1-report.md in this plan's scratch.

Verification commands:
python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short
python tools/check_levelmap_source_parity.py

Out of scope:
Frame builder, public map adapter, live source, real data and full-goal acceptance.
