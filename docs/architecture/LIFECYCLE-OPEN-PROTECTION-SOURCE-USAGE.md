# Lifecycle OPEN protection source usage

`LifecycleOpenProtection(source)` is a private, offline projection of the
source's conservative ambiguity branch for one supplied OPEN trade.

```python
from trading_system.tree_replay._vendor.lifecycle_open_protection import LifecycleOpenProtection

messages, changed = LifecycleOpenProtection(source).resolve(
    open_trade,
    low=supplied_post_fill_low,
    high=supplied_post_fill_high,
)
```

The caller owns the causal post-fill window. This component neither acquires
bars nor quotes, and it does not inspect a state image. If the supplied window
touches the current protective level and at least one unhit target, its order
is unknowable. The component records the source-conservative terminal result:
`STOPPED` when no target was hit, otherwise `DONE`. It composes accepted
`LifecycleTransitions` for the terminal message/result and accepted
`LifecycleOutcomeShelf` for exactly one raw tracker fact.

When the supplied window is not ambiguous, it returns `([], False)` and does
not mutate the trade or write a fact. It does not resolve ordinary protection
hits, targets, progress, minimum success, persistence, gates, delivery,
economic P&L, replay, datasets, training, models, or readiness. The source
audit, CLI, review, and acceptance remain outside this Task 1 implementation.
