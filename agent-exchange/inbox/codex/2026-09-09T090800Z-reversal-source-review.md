# Agent Exchange Request

Target:
Codex source task-review subagent

Sender:
Codex parent

Created at:
2026-09-09

Status:
ACCEPTED_BY_CODEX

Objective:
Independent spec and quality review of Task 1 in
docs/superpowers/plans/2026-09-09-level-reversal-asof.md.

Scope:
Read actual untracked files: trading_system/tree_replay/_vendor/level_reversal.py,
trading_system/tree_replay/_vendor/pvsra.py, tools/check_reversal_source_parity.py,
configs/trees/level-reversal-contracts.json, tests/tree_replay/test_reversal_source.py.
Base/head c1b6071633c55376c64f0a98ece843706f420f49, dirty checkout preserved.

Required inputs:
AGENTS/protocol and full plan; original request
agent-exchange/inbox/codex/2026-09-09T090000Z-reversal-source-sidecar.md and result
agent-exchange/status/2026-09-09T090000Z-worker-reversal-source.md.
Original read-only source checkout:
C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk

Contracts:
Verify exact detector subset and explicit default-non-auction PVSRA specialization;
no source execution/live imports. Fixed blob pins and coverage cannot be weakened
through manifest edits. AST validation covers full ordered vendor module,
imports/decorators/extra statements and specialization preconditions. Numerical
synthetic tests independently characterize source behavior and preserve quirks.
Readiness false; subset parity is not whole-alert parity.

Non-negotiables:
- Read-only implementation, no nested agents or source package execution
- No commits, branch/index changes, network, market feeds or cleanup
- Only write the requested review note using apply_patch

Deliverables:
agent-exchange/reviews/2026-09-09T090800Z-reversal-source-review.md using review
template, clear verdict, actual severity and reproduction for any defect.

Verification commands:
Parent independently ran scoped source tests: 65 passed in 4.47s.
Parent source parity CLI: exit0, no blockers, both readiness flags false.
Parent integration: 921 passed in 35.08s. Reproduce only targeted checks needed
to substantiate findings; do not rerun broad tests or duplicate wrapper review.

Out of scope:
Wrapper already separately reviewed, whole tree/replay/training.

Notes:
No need to reopen approved architecture. Catch concrete contract/parity defects.
