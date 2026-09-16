# Lifecycle OPEN zone-return source usage

`LifecycleOpenZoneReturn(source)` is a private, supplied-spot projection of
the pinned OPEN zone-return notification helper.

```python
from trading_system.tree_replay._vendor.lifecycle_open_zone_return import (
    LifecycleOpenZoneReturn,
)

messages, changed = LifecycleOpenZoneReturn(source).resolve(
    open_trade,
    spot=caller_supplied_live_spot,
)
```

It emits exactly one `(message, to_group)` tuple and returns `True` only when
a previously reported excursion returns to its direction-specific entry-band
edge: a short uses `spot >= zone_low`; a long uses `spot <= zone_high`.
`0/0` is silent. An existing `zone_return_at` marker suppresses further
notices until the number of hit targets increases; malformed marker target
counts are treated as zero.

The message uses accepted entry-band, lifecycle voice/journey, `DeskSuccess`,
and private `Revalidation` helpers. Revalidation is a label only: valid,
invalid, unverified, and caught-error states change advisory text but never
veto, close, resolve, or otherwise alter the lifecycle record. On emission,
the supplied trade mutates only `zone_return_at`.

The real `Revalidation(source).still_valid(trade)` child call is retained; this
is not a precomputed-label port. Its accepted offline source contract may fetch
corrected evidence and may attempt source-owned shadow writes. Those are
inherited child behavior, so this projection does not claim that composition
never acquires/revalidates or never reaches those supplied ports.

Zone-return itself does not directly persist a trade, deliver a notification,
write an outcome, or change stops, targets, protection, or terminal state. It
only writes `zone_return_at` on emission; its recheck remains advisory text. It
creates no economic/replay/dataset/training/model evidence and is not the full
OPEN resolver or a live-trading authorization.

The retained source is read/parsed only by the later static-audit task. Task 1
runtime verification is:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py -q --tb=short -p no:cacheprovider
```

The direct helper regression suite is:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider
```
