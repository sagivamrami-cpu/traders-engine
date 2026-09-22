# Lifecycle OPEN minimum-success source usage

`LifecycleOpenMinimumSuccess(source)` is a private, offline projection of the
pinned tracker OPEN minimum-success branch. It consumes only caller-supplied
OPEN trade state, post-fill `low`/`high`, spot, the raw quote record for that
symbol, forming-bar-extremes membership, and the provisional bar
`minimum_message`.

```python
from trading_system.tree_replay._vendor.lifecycle_open_minimum_success import (
    LifecycleOpenMinimumSuccess,
)

messages, changed, minimum_message = LifecycleOpenMinimumSuccess(source).resolve(
    open_trade,
    low=supplied_post_fill_low,
    high=supplied_post_fill_high,
    spot=supplied_spot,
    quote=supplied_symbol_quote,
    has_bar_extremes=supplied_forming_bar_membership,
    minimum_message=provisional_bar_minimum_message,
)
```

The projection first derives the published protective touch from the supplied
window. Without a bar minimum message and only while protection is untouched,
it accepts a quote minimum when the supplied quote's `lp` exactly equals spot,
its timestamp is fresh under the source's 120-second gate, it is not before
the fill time, and the caller reports no forming-bar extremes for the symbol.
It then preserves source ordering: a minimum message records its raw
`minimum_success` tracker fact, source minimum points, and the last reached
progress rung only when protection was untouched.

The caller owns all evidence and subsequent control flow. This component does
not acquire quotes or bars, decide ambiguity/protection/targets/terminal state,
persist a tracker, gate or deliver messages. `minimum_success` is a raw tracker
fact, not a fill, P&L/economic label, replay row, dataset row, training target,
model signal, or trading authorization. The retained-source audit and CLI are
separate Task 2 work; no readiness claim is made here.
