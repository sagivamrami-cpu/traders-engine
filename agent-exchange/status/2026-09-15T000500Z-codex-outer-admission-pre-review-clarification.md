# Codex status — outer-admission pre-review contract clarification

- Timestamp: 2026-09-15T00:05:00Z
- Status: REVIEW_REQUESTED
- Scope: wording/test-name clarification only; no runtime behavior changed.

## Finding

The source at retained
`chart-desk/scripts/market_watch.py:1068-1072` calls tracker `record` inside a
`try/except`; a raised persistence error is recorded as a source failure after
the attempt. The offline adapter faithfully maps that source branch to
`BLOCKED` / `TRACKER_RECORD_FAILED`, with no tracker identity or watch-episode
write.

The prior safety-invariant wording could be read as forbidding every
`BLOCKED` result from calling `record`, which would contradict this source
branch. It is now explicit that the no-record invariant applies to paths that
stop before the record gate. The distinct post-attempt failure remains covered
by `test_tracker_record_failure_is_a_detached_block_without_watch_mutation`.

## Changed documentation/test name

- `docs/superpowers/specs/2026-09-14-outer-admission-causal-binding-design.md`
- `docs/superpowers/plans/2026-09-14-outer-admission-causal-binding.md`
- `tests/tree_replay/test_outer_admission.py`

The requested independent reviewers must assess this clarification alongside
the full component. No acceptance is implied.

## Static-audit wording clarification

The source-audit JSON retains a legacy `unwired_outer_admission` field. It
means that the static auditor validates source order without importing or
executing a runtime adapter; it does not say that the separately implemented,
opt-in adapter is unavailable. This has been clarified in both replay usage
documents. No runtime code, source audit assertion, readiness flag, or
acceptance state changed.
