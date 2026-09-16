# Task 1 re-review: lifecycle OPEN zone-return source

Reviewer: Codex

Target request: Direct user request for a read-only re-review of the prior
Task 1 M1--M4 findings.

Created at: 2026-09-14T22:00:00Z

Status: REVIEW_READY_FOR_CODEX

## Verdict

- Spec compliance: **ADDRESSED**
- Task quality: **ADDRESSED**

## Scope re-reviewed

- `agent-exchange/reviews/2026-09-14T210000Z-lifecycle-open-zone-return-task1-review.md`
- `.superpowers/sdd/2026-09-14-lifecycle-open-zone-return-source/task-1-report.md`
- `docs/architecture/LIFECYCLE-OPEN-ZONE-RETURN-SOURCE-INTAKE.md`
- `docs/architecture/LIFECYCLE-OPEN-ZONE-RETURN-SOURCE-USAGE.md`
- `docs/superpowers/plans/2026-09-14-lifecycle-open-zone-return-source.md`
- `trading_system/tree_replay/_vendor/lifecycle_open_zone_return.py`
- `tests/tree_replay/test_lifecycle_open_zone_return.py`
- Accepted child implementation/tests: `revalidation.py` and
  `tests/tree_replay/test_revalidation.py`; `desk_success.py`.

## M1 -- ADDRESSED: composed child boundary versus zone-return direct effects

The revised intake, usage, and plan no longer claim that the composition has no
acquisition/effects. They explicitly retain `Revalidation(source).still_valid`,
and state that the accepted child may call `source.fetch_corrected(...)` and
attempt source-owned shadow writes through its offline ports. The runtime
constructs that real child at initialization and calls `still_valid(trade)` in
the advisory label path. The revalidation helper and its direct suite confirm
the corresponding supplied-port fetch/shadow behavior.

The narrower claim is accurate: zone-return itself only writes
`trade["zone_return_at"]` after an emission. It has no direct terminal,
outcome, persistence, or delivery call. The controlled label/effect isolation
test preserves every other trade field and the source effect ports remain
unused by zone-return's own body. The real-child spy test also rejects replacing
the retained child call with a static label tuple.

## M2 -- ADDRESSED: malformed marker with zero targets

`test_malformed_marker_with_zero_targets_suppresses_the_same_excursion` sets a
malformed prior marker, positive `progress_step`, and an empty `hit` list. It
requires `([], False)` and no marker mutation, directly exercising the retained
`len(hit) <= said_targets` boundary at `0 <= 0`. The fix-round report records
the exact `<` mutant and its targeted RED result (a duplicate message emitted).

## M3 -- ADDRESSED: DeskSuccess-reached excursion

`test_valid_desk_success_arms_a_zero_progress_step_excursion` supplies a
complete identity-bound minimum-success proof with `progress_step=0`. It emits
and records `zone_return_at == "1/0"`, proving `DeskSuccess.reached(trade)`
participates in the numerator while the existing zero-proof case remains
silent. The report records the exact `DeskSuccess.reached(trade) -> 0` mutant
and its targeted RED result.

## M4 -- ADDRESSED: full message order and recheck distinction

The literal-message regression asserts the retained header, supplied spot then
zone, original-stop distance, journey, recheck, and unchanged-stop/targets
footer in source order. A separate regression proves a direct valid-but-
unverified result retains its reason, whereas the caught-error fallback has no
such reason. The fix-round report records targeted RED evidence for both exact
mutants: journey/recheck order swapped, and the caught-error reason replaced
with the direct-unverified reason.

## Verification

Freshly run:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py -q --tb=short -p no:cacheprovider
```

PASS: `19 passed in 0.50s`.

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider
```

PASS: `169 passed in 5.26s`.

The exact mutation RED runs are recorded in the Task 1 fix-round report and
their named tests/assertions match the current artifacts. They were not
re-applied in this re-review because the requested scope forbids edits.

## Remaining scope limits

Task 2 static source audit/CLI and any full resolver, persistence, delivery,
outcome/economic, replay, dataset, training/model, or live-trading readiness
claim remain outside Task 1.
