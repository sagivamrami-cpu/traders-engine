# Agent Exchange Request

Target: Claude Code

Sender: Codex

Created at: 2026-09-14T23:59:00Z

Status:
REVIEW_ONLY

Objective:

Perform an independent, read-only final review of the offline outer-admission
causal binding. This is a secondary review because the worktree contains
user-owned untracked project files; do not rely on a Git range to decide which
files exist or which code is in scope.

Scope:

- `trading_system/tree_replay/outer_admission_contracts.py`
- `trading_system/tree_replay/outer_admission_ports.py`
- `trading_system/tree_replay/outer_admission.py`
- `trading_system/tree_replay/causal_replay.py`
- `trading_system/tree_replay/causal_replay_contracts.py`
- `trading_system/tree_replay/causal_replay_checkpoint.py`
- `tests/tree_replay/test_outer_admission_contracts.py`
- `tests/tree_replay/test_outer_admission_ports.py`
- `tests/tree_replay/test_outer_admission.py`
- `tests/tree_replay/test_causal_replay.py`
- `tests/tree_replay/test_causal_replay_checkpoint.py`
- `tests/tree_spec/test_outer_admission_source.py`
- `docs/superpowers/specs/2026-09-14-outer-admission-causal-binding-design.md`
- `docs/superpowers/plans/2026-09-14-outer-admission-causal-binding.md`
- `docs/architecture/OUTER-ADMISSION-CAUSAL-REPLAY-USAGE.md`

Authority and requirements:

The implementation must reproduce only the source-faithful bounded
`level_reversal:5m` outer-admission path. It must bind one supplied input
through one current `OUTER_ADMISSION_INPUT` event and a canonical commitment to
the actual private selected `Plan`; block before provider mutation on missing,
future, duplicate, or substituted evidence; preserve default `OBSERVE_ONLY`
when outer inputs are absent; and serialize detached facts only.

`ADMITTED_TRACKER` means advisory tracker registration only. It must never
become a fill, economic result, label, dataset row, model prediction, readiness
claim, broker action, delivery, or live behavior.

Non-negotiables:

- Read-only review: do not edit source, tests, docs, Git state, or inbox files.
- No hidden threshold, feed, source import, raw market/log payload, live action,
  broker execution, capital allocation, economics, dataset, model, or approval.
- Check causal ordering, plan-commitment order, checkpoint/resume behavior,
  error/mutation boundaries, safe diagnostics, and documentation consistency.
- Treat the retained source root as static audit authority, never runtime code:
  `C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.

Deliverable:

Write one review using `agent-exchange/templates/review.md` to
`agent-exchange/reviews/` with status `REVIEW_READY_FOR_CODEX`. Give exact
file/line references for findings, severity, verification reviewed, and a
clear verdict. If no issue is found, list concrete inspected invariants and
remaining out-of-scope areas.

Verification commands:

```powershell
python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
python -B -m pytest tests/tree_replay/test_outer_admission_contracts.py tests/tree_replay/test_outer_admission_ports.py tests/tree_replay/test_outer_admission.py tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_spec/test_outer_admission_source.py tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
```

Clarification to assess:

The source calls tracker `record` inside `try/except` at
`chart-desk/scripts/market_watch.py:1068-1072`. The no-record invariant covers
only candidates stopped before that gate. A post-attempt persistence failure is
expected to be `BLOCKED` / `TRACKER_RECORD_FAILED` without tracker identity or
watch-state write; see
`agent-exchange/status/2026-09-15T000500Z-codex-outer-admission-pre-review-clarification.md`.
