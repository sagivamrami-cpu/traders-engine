# Agent Exchange Request

Target:
Codex final integration reviewer

Sender:
Codex controller

Created at:
2026-09-09

Status:
ACCEPTED_BY_CODEX

Objective:
Final combined review of the offline level-reversal slice against
docs/superpowers/plans/2026-09-09-level-reversal-asof.md and master section18.

Scope:
Read .superpowers/sdd/2026-09-09-level-reversal-asof/final-review.patch, the complete
ten-file source/adapter/test/contract/usage/plan package. Compare to actual files.
Read AGENTS/README additions and master section18 directly. Previous accepted
EMA/calendar/economic work is unchanged dependency context, not new work to redo.
Base/head both c1b6071633c55376c64f0a98ece843706f420f49; changes are untracked/local.

Required inputs:
AGENTS/protocol; the plan; own ledger at
.superpowers/sdd/2026-09-09-level-reversal-asof/progress.md;
agent-exchange/reviews/2026-09-09T090500Z-reversal-wrapper-review.md;
agent-exchange/reviews/2026-09-09T090800Z-reversal-source-review.md;
agent-exchange/status/2026-09-09T090000Z-worker-reversal-source.md.

Contracts:
- Preserve pinned source detector behavior, default non-auction specialization
- Closed and available bars, explicit level/source/calendar evidence and ages
- Only latest confirmation; no retrospective level lookahead
- Explicit BLOCKED / NO_CANDIDATE / DETECTED_UNPRICED separation
- No admitted trades, fills, labels, dataset or training readiness
- Identity/evaluation separation, finite snapshots and causal dependency times
- Documentation accurately states historical-level/pricing/arbitration gaps

Non-negotiables:
- Read-only code/index/branch, no nested agents, no source checkout execution
- No market data, network, secrets, commits, deployment or cleanup
- Only write the assigned review note using apply_patch

Deliverables:
agent-exchange/reviews/2026-09-09T091100Z-reversal-final-review.md using review
template. Report strengths, concrete Critical/Important/Minor issues and clear
spec/quality verdict. Triage ledger deferred/parked items (none currently).

Verification commands:
Parent fresh results on submitted code:
python -m pytest tests/tree_replay/test_reversal.py -q: 91 passed, exit0.
python -m pytest tests/tree_replay/test_reversal_source.py -q: 65 passed, exit0.
python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q --tb=short:
921 passed in 35.08s, exit0.
python -m pytest -q --ignore-glob='*validator*' --tb=short:
1293 passed in 113.10s, exit0; existing legacy validator tests explicitly excluded.
Both source parity CLIs against retained chart-desk: exit0, no blockers, readiness false.
No need to rerun these suites. Use focused read-only probes only for concrete concerns.

Out of scope:
Production or historical-profitability certification; no whole-tree completion.

Notes:
The user repeatedly asked to continue approved implementation. Final review is
for this bounded local slice; no merge/push authorized or requested here.
