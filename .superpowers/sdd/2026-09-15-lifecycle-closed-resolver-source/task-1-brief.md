### Task 1: Closed-bar runtime resolver

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_closed_resolver.py`
- Create: `tests/tree_replay/test_lifecycle_closed_resolver.py`
- Create: `docs/architecture/LIFECYCLE-CLOSED-RESOLVER-SOURCE-USAGE.md`

**Interfaces:**
- Consumes: `LifecycleClosedResolver(source).resolve(state: dict, *, now: float)`, where `source.fetch_corrected(symbol, "15m", 3)` returns the caller-owned frame/correction and `now` is the single pass clock.
- Produces: `(list[tuple[str, bool]], bool)`; it mutates only supplied tracker records through accepted lifecycle components.

- [ ] **Step 1: Write focused failing tests**

```python
def test_pre_fill_high_cannot_hit_a_long_target_after_a_retest_fill():
    messages, changed = resolver.resolve(state, now=PASS_CLOCK)
    assert changed is True
    assert state["trade"]["state"] == "OPEN"
    assert state["trade"]["hit"] == []

def test_closed_open_order_is_minimum_then_ambiguity_then_continue():
    messages, changed = resolver.resolve(state, now=PASS_CLOCK)
    assert [message for message, _group in messages] == [minimum_message, ambiguity_message]
    assert state["trade"]["state"] == "STOPPED"
```

- [ ] **Step 2: Prove the tests are red**

Run: `python -B -m pytest tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider`

Expected: failure because `LifecycleClosedResolver` is not importable.

- [ ] **Step 3: Implement the smallest source-ordered resolver**

```python
for key, trade in list(state.items()):
    if trade.get("state") in TERMINAL:
        continue
    frame, correction = source.fetch_corrected(trade["symbol"], "15m", 3)
    if bad(correction):
        continue
    since = frame[utc_seconds(frame.index) > float(trade["ts"])]
    if since.empty:
        continue
    high, low = float(since.high.max()), float(since.low.min())
    hi_f, lo_f = _open_extremes(since, trade) or (float(trade["entry"]),) * 2
    pending.resolve(trade, state=state, since=since, high=high, low=low, now=now)
    if trade.get("state") == "OPEN":
        resolve_closed_open(trade, since=since, high=hi_f, low=lo_f, now=now)
```

`resolve_closed_open` must call `DeskSuccess.observe_bars(trade, since)`, preserve its raw `minimum_success` outcome/state update, call accepted protection before accepted ordinary resolution, and prevent ordinary resolution after ambiguity changed the record.

- [ ] **Step 4: Prove runtime behaviour**

Run: `python -B -m pytest tests/tree_replay/test_lifecycle_closed_pending_resolution.py tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider`

Expected: PASS; cases cover per-record skip, strict timestamp cut, correction gates, pending fall-through, fill-bar pessimism, closed minimum, ambiguity, target ordering, empty targets and ordinary protection.

