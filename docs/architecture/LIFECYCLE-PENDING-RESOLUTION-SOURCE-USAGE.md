# Lifecycle PENDING-resolution source usage

`LifecyclePendingResolution(source)` is an offline projection of the pinned
tracker PENDING fill/cancel branch. It resolves one caller-supplied record:

```python
messages, changed = LifecyclePendingResolution(source).resolve(
    trade,
    state=state_image,
    price=price,
    bar_extremes={"OANDA:XAUUSD": (low, high)},
)
```

It derives the accepted entry band, applies the source one-sided forming-bar
touch comparison, then either keeps the record unchanged, cancels it for an
existing OPEN slot or failed revalidation, or changes it from `PENDING` to
`OPEN`. Cancellation writes only the corresponding raw tracker fact through
the accepted outcome shelf. A successful fill has no outcome row.

The component consumes only the supplied state image, price and extremes.
It does not load or save state, lock, acquire quotes or bars, gate or deliver
messages, progress an OPEN trade, calculate economics, create labels/dataset
rows, fit a model, or establish replay or training readiness.

The supplied source must provide the existing raw outcome-shelf ports and
`now_epoch()`. The fill timestamp is one `now_epoch()` value assigned to both
`filled_ts` and `progress_ts`; terminal cancellation retains the accepted
transition helper's own timestamp behavior.
