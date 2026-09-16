# Agent Exchange Request

Target:
Codex task-review subagent

Sender:
Codex parent

Created at:
2026-09-09

Status:
ACCEPTED_BY_CODEX

Objective:
Review Task 2 against docs/superpowers/plans/2026-09-09-level-reversal-asof.md.

Scope:
Read-only on trading_system/tree_replay/levels.py, reversal.py, and
tests/tree_replay/test_reversal.py. Review relevant existing bars/session/snapshot
contracts and vendored detect_frame/pvsra dependencies as necessary. Source parity
tool is being implemented separately; do not review that tool in this task.

Required inputs:
AGENTS/protocol, full plan, named source files. Parent test run: 91 passed.
Base/head c1b6071633c55376c64f0a98ece843706f420f49; changes are untracked new files
in a dirty shared checkout, so inspect actual files rather than empty HEAD diff.

Contracts:
Only current latest-selected confirmation, no retrospective level snapshot use;
immutable explicit level metadata; strict source pattern semantics; all dependency
availability <= T; volume/history failures distinct from negative detection;
finite values/JSON; separate event identity and evaluation fingerprint; no labels,
pricing, full-tree readiness or production authority. Test calendar boundary cases.

Non-negotiables:
- No source package execution, network, commits or mutation of implementation
- No nested reviewers/subagents
- Only write your review note using apply_patch

Deliverables:
agent-exchange/reviews/2026-09-09T090500Z-reversal-wrapper-review.md using review
template. Return clear pass/fail, concrete severity/file:line and reproductions.
Assess plan alignment and code quality together; do not reopen approved scope.

Verification commands:
python -m pytest tests/tree_replay/test_reversal.py -q

Out of scope:
Full historical levels, tradeplan, dataset/training and other preexisting changes.

Notes:
Report any non-blocking provenance or identity limitations accurately. Metadata
cannot prove genuine feed lineage; that limitation is explicit and in scope.
