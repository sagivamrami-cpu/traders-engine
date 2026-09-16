# Task 1 — closed-bar runtime resolver report

## Changed paths

- `trading_system/tree_replay/_vendor/lifecycle_closed_resolver.py` (created)
- `tests/tree_replay/test_lifecycle_closed_resolver.py` (created)
- `docs/architecture/LIFECYCLE-CLOSED-RESOLVER-SOURCE-USAGE.md` (created)

This report is the required Task 1 handoff artifact. No existing runtime,
tracker, plan, exchange status, or readiness artifact was altered.

## TDD evidence

### RED

Command:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider
```

Result before production code: `6 failed in 0.75s`.

Each case failed at the intended boundary:

```text
AssertionError: closed resolver runtime missing
assert None is not None
```

The missing module was
`trading_system.tree_replay._vendor.lifecycle_closed_resolver`.

An initial implementation run exposed three fixture defects, not a relaxation
of source behavior: `DeskSuccess.observe_bars` legitimately excludes the fill
bar and stops paying at the first protective touch, while arbitrary test
symbols have no desk minimum. The repaired fixtures retain their behavioral
assertions and use a known instrument, a fill bar, a clean post-fill minimum
bar, then (where required) a later protective/ambiguous bar.

### GREEN

Focused resolver command:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider
```

Result: `6 passed in 0.55s`.

Required combined command:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_closed_pending_resolution.py tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider
```

Result: `14 passed in 0.56s`.

## Coverage

The new resolver tests cover:

- retest-fill protection from a pre-fill long target-side high;
- closed OPEN ordering: bar minimum raw fact before conservative ambiguity;
- terminal skip plus independent unverified and `tv_stale` correction skips;
- strict `timestamp > plan_ts` filtering;
- ordinal closed OPEN target processing and empty-target DONE behavior; and
- ordinary protective resolution after a valid closed-bar minimum.

## Exact scope limits

The component is an offline, caller-owned mutable-state resolver only. It
fetches corrected three-day 15-minute frames per record and composes accepted
closed-PENDING, `DeskSuccess.observe_bars`, OPEN protection, and ordinary OPEN
resolution helpers. It does not load, gate, persist, save, lock, deliver,
acquire live quotes, enter the live-only zone-return branch, generate economic
outcomes, or claim replay, dataset, training, model, or live-trading readiness.
In particular, closed-bar minimum success is a source-faithful local
`DeskSuccess.observe_bars(trade, since)` adaptation and is never substituted
with the live quote minimum component.

## Fix round 1 — short closed-bar minimum progress

Review finding I1 identified a mojibake short-direction comparison in the
resolver's local pre-protection minimum-success block. Accepted children and
the retained source use the exact Unicode direction value `שורט`; the broken
comparison treated that direction as long only in this local block. A short
minimum could therefore record its raw fact while failing to record the
source's short-side progress state, because ordinary resolution correctly
suppresses duplicate progress after a minimum message.

### RED

After adding the focused real resolver regression (short OPEN XAUUSD; post-fill
low `95`, high `100`, stop `110`, unhit TP1 `90`), command:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_closed_resolver.py::test_short_closed_minimum_uses_post_fill_low_for_source_progress_before_protection -q --tb=short -p no:cacheprovider
```

Result: `1 failed in 0.83s`.

The observed failure was the intended source-fidelity divergence:

```text
KeyError: 'progress_step'
```

The existing implementation emitted the minimum-success raw fact but omitted
the required source progress step.

### GREEN

The runtime comparison was replaced with exactly `"שורט"`; no lifecycle order
or helper was otherwise changed.

Independent reviewer reproduction, using the same focused test command above:

```text
1 passed in 0.70s
```

The test asserts the trade remains `OPEN`, records `minimum_success`, and has
the retained short-side `progress_step == 55`.

Focused resolver command:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider
```

Result: `7 passed in 0.71s`.

Required combined command:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_closed_pending_resolution.py tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider
```

Result: `15 passed in 0.73s`.
