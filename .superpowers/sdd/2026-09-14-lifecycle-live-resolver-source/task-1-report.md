# Task 1 report: lifecycle live resolver source

## Scope completed

Implemented only the Task 1 runtime kernel described by
`.superpowers/sdd/2026-09-14-lifecycle-live-resolver-source/task-1-brief.md`:
the private two-observation snapshot and the ordered PENDING/OPEN composition.
No source-audit/CLI work, accepted-child changes, caller binding, persistence,
delivery, replay, economic, dataset, training, model, broker, or live-trading
work was performed.

## Changed files

- `trading_system/tree_replay/_vendor/lifecycle_live_resolver.py` — new private
  `LifecycleLiveResolver` and source-ordered observation helper.
- `tests/tree_replay/test_lifecycle_live_resolver.py` — new focused TDD suite.
- `docs/architecture/LIFECYCLE-LIVE-RESOLVER-SOURCE-USAGE.md` — Task 1 usage
  boundary and inherited-child-effects note.
- `.superpowers/sdd/2026-09-14-lifecycle-live-resolver-source/task-1-report.md`
  — this report.

## TDD evidence

### RED

Tests were written before the vendor module existed, then run with:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py -q --tb=short -p no:cacheprovider
```

Result: `9 failed in 0.72s`.

Every test failed at the intended missing-module/import boundary:

```text
AssertionError: live resolver module missing
assert None is not None
```

No production resolver module existed during this run.

### GREEN

After adding only the resolver and its private snapshot, the same focused
command was rerun:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py -q --tb=short -p no:cacheprovider
```

Result: `9 passed in 0.49s`.

The focused tests cover exactly two quote reads, raw-quote forwarding,
corrected range carry, no-price/terminal/missing-price skips, PENDING no-touch,
cancellation and same-pass fill behavior, minimum-before-protection ordering,
ambiguity continuation, ordinary terminal zone suppression, and unchanged OPEN
zone return.

## Direct-child regression evidence

The focused suite and every direct accepted-child runtime suite were run with:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py tests/tree_replay/test_lifecycle_live_evidence.py tests/tree_replay/test_lifecycle_live_resolution_evidence.py tests/tree_replay/test_lifecycle_pending_resolution.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_lifecycle_open_protection.py tests/tree_replay/test_lifecycle_open_ordinary_resolution.py tests/tree_replay/test_lifecycle_open_zone_return.py -q --tb=short -p no:cacheprovider
```

Result: `111 passed in 1.20s`.

## Scope caveats

- The retained tracker source was not imported or executed.
- The accepted `LifecycleLiveResolutionEvidence.collect` and every accepted
  child module remain unchanged.
- This runtime component receives explicit offline ports and mutable supplied
  state; it is not a full caller loop or a causal feed.
- Child-owned raw outcome writes and zone-return revalidation behavior remain
  inherited effects. This Task 1 composition does not make them persistence,
  delivery, economic, replay, dataset, training, model, or live-readiness
  evidence.
- Static source parity/audit/CLI work is Task 2 and was not modified.

---

# Task 1 fix round 1/5: M1–M2 fallback and raw-snapshot evidence closure

## Scope completed

Read review `agent-exchange/reviews/2026-09-15T000000Z-lifecycle-live-resolver-task1-review.md`
verbatim. This fix round closes only its M1–M2 runtime-test/evidence gaps.
The pre-existing runtime already conformed to the reviewed fallback and
error-to-empty behavior, so it has no lasting production-code change.

## Changed paths for this fix round

- `tests/tree_replay/test_lifecycle_live_resolver.py` — added eight focused
  regressions for carried fallback extrema, rejected corrections, exact force
  age, strict bar freshness, sibling continuation, and a failed second raw
  quote read.
- `.superpowers/sdd/2026-09-14-lifecycle-live-resolver-source/task-1-report.md`
  — appended this fix-round evidence.

`trading_system/tree_replay/_vendor/lifecycle_live_resolver.py` was changed
only temporarily for the two mutation checks below and restored exactly to its
prior runtime behavior.

## Test and mutation evidence

New test coverage was added before changing production behavior. Against the
unchanged runtime, the expanded focused suite passed:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py -q --tb=short -p no:cacheprovider
```

Result: `17 passed in 0.49s`.

Two temporary runtime mutations then established that the new regressions are
not tautological:

1. Swapped the fallback-carried low/high tuple, then ran:

   ```powershell
   python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py::test_fallback_wick_reaches_pending_as_the_real_low_high_pair -q --tb=short -p no:cacheprovider
   ```

   Result: `1 failed in 0.63s`; the assertion observed
   `(31.75, 28.25)` instead of the required `(28.25, 31.75)`. The tuple order
   was restored immediately.

2. Replaced second raw-quote error-to-empty handling with a re-raise, then ran:

   ```powershell
   python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py::test_second_raw_quote_failure_uses_empty_quote_and_continues_with_fallback_price -q --tb=short -p no:cacheprovider
   ```

   Result: `1 failed in 0.61s` with the intentional `OSError: raw snapshot
   unavailable`. The original `{}` fallback was restored immediately.

The restored focused and direct-child verification commands were:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py -q --tb=short -p no:cacheprovider
python -B -m pytest tests/tree_replay/test_lifecycle_live_resolver.py tests/tree_replay/test_lifecycle_live_evidence.py tests/tree_replay/test_lifecycle_live_resolution_evidence.py tests/tree_replay/test_lifecycle_pending_resolution.py tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_lifecycle_open_protection.py tests/tree_replay/test_lifecycle_open_ordinary_resolution.py tests/tree_replay/test_lifecycle_open_zone_return.py -q --tb=short -p no:cacheprovider
```

Results: `17 passed in 0.48s`; `119 passed in 1.16s`.

## Coverage added

- A corrected fallback close and its exact low/high wick reach PENDING through
  `bar_extremes`.
- Unverified and `tv_stale` corrections cannot create a price.
- Quote age exactly `120.0` seconds skips corrected fallback.
- A correction replaces the quote only when its bar timestamp is strictly
  newer; equality remains the raw quote with no carried extrema.
- A failed fallback for one active symbol does not suppress a valid sibling.
- When the second/raw quote read fails, exactly two reads occur, `{}` reaches
  minimum-success, and a corrected fallback price still reaches the OPEN path.

## Scope caveats

This remains Task 1 runtime coverage only. No retained-source auditor/CLI,
accepted child module, caller binding, persistence/delivery behavior, economic
label, replay, dataset, training, model, or live-trading readiness claim was
added or changed.
