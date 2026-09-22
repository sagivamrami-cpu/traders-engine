# Agent Exchange Request

Target:
Codex source-sidecar subagent

Sender:
Codex parent

Created at:
2026-09-09

Status:
ACCEPTED_BY_CODEX

Objective:
Implement Task 1 of docs/superpowers/plans/2026-09-09-level-reversal-asof.md.

Scope:
Only trading_system/tree_replay/_vendor/level_reversal.py,
trading_system/tree_replay/_vendor/pvsra.py,
tools/check_reversal_source_parity.py,
configs/trees/level-reversal-contracts.json,
tests/tree_replay/test_reversal_source.py and your result note.

Required inputs:
Read AGENTS/protocol/startup inbox and the plan. Read original source at
C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk.
Commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
Read chartdesk/level_reversal.py, chartdesk/tr.py pvsra and auction.resolve_slots
to confirm default auction=False path. Existing tools/check_ema_source_parity.py
is a reference, not in your write scope.

Contracts:
Vendor exact detector constants ELIGIBLE_LEVELS/ELIGIBLE_MA_PREFIXES,
SELL_VECTORS/BUY_VECTORS/TF_MINUTES/LIVE_MAX_AGE_S, Reversal dataclass,
_utc/_normalise/is_eligible_level/_eligible/_episode/two_bar_signal/
single_bar_signal/detect_frame. No build_plan/find/conflicts or live imports.
Use `from . import pvsra as tr` so the exact source detect_frame calls tr.pvsra.
Vendor pvsra(df, lookback=10) specialization of ONLY default non-auction branch;
preserve exact source statement ASTs, drop auction/seasonal-only setup/branches
and unused parameters, document specialization. Imports numpy/pandas only.
Source check verifies fixed file hashes and exact AST symbol coverage, approved
imports, default PVSRA statement subset, and expected source defaults/branch
preconditions. Never execute/import the source checkout. Fail closed on omitted
manifest coverage or extra executable vendor statements. CLI --source-root path.
Return subset_verified and ready_for_replay/ready_for_training false.
Preserve source semantics, including >= spread-volume climax, prior-10 rolling,
M5 climax-only, M15 rising allowed, level order ties, event vs dedup bucket bases.
Tests use synthetic OHLCV, both directions/timeframes and tamper cases.

Non-negotiables:
- point-in-time correctness; no invented thresholds or feeds
- no source package execution, installs, network/data downloads, live effects
- no production approval, commits, cleanup, or edits outside write scope
- use apply_patch, TDD; work directly in shared checkout, preserve others' work

Deliverables:
Code/tests/contracts and agent-exchange/status/2026-09-09T090000Z-worker-reversal-source.md
using result template, Request pointing here, exact verification results.

Verification commands:
python -m pytest tests/tree_replay/test_reversal_source.py -q
python tools/check_reversal_source_parity.py --source-root <retained-chart-desk>

Out of scope:
Wrapper/level snapshots, pricing, full producer arbitration, datasets/training.

Notes:
Parent concurrently owns wrapper/tests. Source detector API is detect_frame as
above and pvsra(df, lookback=10). Notify parent if a source detail conflicts.
