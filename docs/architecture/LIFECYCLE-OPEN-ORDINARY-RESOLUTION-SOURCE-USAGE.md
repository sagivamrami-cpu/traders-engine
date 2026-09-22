# Lifecycle OPEN ordinary-resolution source usage

`LifecycleOpenOrdinaryResolution(source)` is a private, offline projection of
the source's ordinary OPEN branch over one caller-supplied post-fill window.

```python
from trading_system.tree_replay._vendor.lifecycle_open_ordinary_resolution import (
    LifecycleOpenOrdinaryResolution,
)

messages, changed = LifecycleOpenOrdinaryResolution(source).resolve(
    open_trade,
    low=supplied_post_fill_low,
    high=supplied_post_fill_high,
    minimum_message=observed_minimum_message,
)
```

The caller owns the causal evidence and must invoke `LifecycleOpenProtection`
first. If that conservative ambiguity projection changes the trade, this
ordinary resolver is not called. `low`, `high`, and `minimum_message` must be
the caller's already-observed post-fill facts; this component acquires no bars
or quotes.

When called, it preserves the retained physical order: suppresses or emits
progress, records every touched unhit target in ordinal order, then rechecks
the published protective level. Its target and protective records are raw
tracker facts, while its progress messages describe movement only. Neither is
an economic label, a fill/P&L assertion, replay input, dataset, training data,
model output, or trading authorization.

`audit_lifecycle_open_ordinary_resolution_source(source_root)` and
`tools/check_lifecycle_open_ordinary_resolution_source_parity.py` are a
read-only retained-source proof for the pinned physical fragment and this
private projection. They parse source text and ASTs only; they never import or
execute the retained source. A `VERIFIED` report means the pin, physical order,
allowed runtime projection, and accepted transition/outcome-shelf child proofs
match. It still reports `ready_for_replay=false` and
`ready_for_training=false`.

This component does not implement ambiguity, live-spot zone return,
persistence, gates, delivery, economics, replay, datasets, training, models,
or readiness.
