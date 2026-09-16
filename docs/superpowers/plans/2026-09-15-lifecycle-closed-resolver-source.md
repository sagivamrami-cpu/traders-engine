# Lifecycle Closed-Bar Resolver Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faithfully compose the pinned closed-15-minute-bar PENDING and OPEN lifecycle resolver over supplied offline ports.

**Architecture:** A private resolver loops the supplied tracker mapping, obtains exactly one corrected three-day frame per eligible record, and keeps post-send fill geometry separate from post-fill position geometry.  It reuses the accepted PENDING, protection and ordinary-resolution primitives, while adding the closed-bar `DeskSuccess.observe_bars` sequence that cannot be substituted with a live quote observation.  A read-only AST proof pins the source branch, child graph and fail-closed readiness.

**Tech Stack:** Python 3, pandas, pytest, AST, JSON CLI.

**Spec:** `docs/architecture/LIFECYCLE-CLOSED-RESOLVER-SOURCE-INTAKE.md`

## Global Constraints

- Read/parse retained source only; never import or execute it.
- Pin chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob `b616b34022e436545d8c1daf85eced51614fd74e`.
- Read exactly one corrected `15m`, three-day frame per nonterminal record; skip its record for failed, unverified or `tv_stale` evidence.
- Use source `>` plan-time slicing and `_open_extremes` separately from `hi`/`lo`; never turn pre-fill motion into position progress or target success.
- Preserve PENDING same-pass OPEN fall-through and the source OPEN order: minimum, ambiguity, ordinary resolution.  Do not call the live-only zone-return helper.
- No persistence, gate, save, delivery, broker, economic result, replay, dataset, training, model or live-trading behaviour; all readiness fields remain false.

### Task 1: Closed-bar runtime resolver

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_closed_resolver.py`
- Create: `tests/tree_replay/test_lifecycle_closed_resolver.py`
- Create: `docs/architecture/LIFECYCLE-CLOSED-RESOLVER-SOURCE-USAGE.md`

**Interfaces:**
- Consumes: `LifecycleClosedResolver(source).resolve(state: dict, *, now: float)`, where `source.fetch_corrected(symbol, "15m", 3)` returns the caller-owned frame/correction and `now` is the single pass clock.
- Produces: `(list[tuple[str, bool]], bool)`; it mutates only supplied tracker records through accepted lifecycle components.

- [x] **Step 1: Write focused failing tests**

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

- [x] **Step 2: Prove the tests are red**

Run: `python -B -m pytest tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider`

Expected: failure because `LifecycleClosedResolver` is not importable.

- [x] **Step 3: Implement the smallest source-ordered resolver**

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

- [x] **Step 4: Prove runtime behaviour**

Run: `python -B -m pytest tests/tree_replay/test_lifecycle_closed_pending_resolution.py tests/tree_replay/test_lifecycle_closed_resolver.py -q --tb=short -p no:cacheprovider`

Expected: PASS; cases cover per-record skip, strict timestamp cut, correction gates, pending fall-through, fill-bar pessimism, closed minimum, ambiguity, target ordering, empty targets and ordinary protection.

### Task 2: Static proof and fail-closed command

**Files:**
- Create: `trading_system/tree_spec/lifecycle_closed_resolver_source.py`
- Create: `tools/check_lifecycle_closed_resolver_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_closed_resolver_source.py`

**Interfaces:**
- Consumes: an explicit retained-source root and vendor text.
- Produces: JSON `VERIFIED` only on exact source/runtime projection and verified child reports; any error prints schema-valid `BLOCKED` with both readiness flags false.

- [x] **Step 1: Write failing audit/mutation tests**

```python
def test_audit_rejects_pre_fill_extreme_leak(tmp_path, monkeypatch):
    mutate_vendor("_open_extremes(since, trade)", "(high, low)")
    report = audit(RETAINED)
    assert "VENDOR_AST_MISMATCH:lifecycle_closed_resolver" in report["blockers"]
    assert report["ready_for_replay"] is False
```

Also mutate the three-day fetch, correction gates, strict `>`, PENDING fall-through, minimum/ambiguity/ordinary ordering, `continue`, and child-report identity.

- [x] **Step 2: Prove the audit tests are red**

Run: `python -B -m pytest tests/tree_spec/test_lifecycle_closed_resolver_source.py -q --tb=short -p no:cacheprovider`

Expected: failure because the audit module and CLI do not exist.

- [x] **Step 3: Parse and project only `tracker.py::check`**

The auditor must locate the unique closed-bar loop, require its correction/slicing/extrema statements and the PENDING/OPEN physical branch sequence, then compare the normalized vendor AST to the precise adaptation.  It must require the closed-PENDING, lifecycle primitives, outcome shelf, transitions, revalidation, protection and ordinary-resolution audit reports.

- [x] **Step 4: Prove audit and command behaviour**

Run: `python -B -m pytest tests/tree_spec/test_lifecycle_closed_resolver_source.py -q --tb=short -p no:cacheprovider`

Run: `python -B tools/check_lifecycle_closed_resolver_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Expected: all tests pass; command exits 0 and reports `VERIFIED`, `ready_for_replay=false`, `ready_for_training=false`.

### Task 3: Bounded acceptance

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md`
- Modify: `docs/superpowers/plans/2026-09-15-lifecycle-closed-resolver-source.md`
- Create: `agent-exchange/status/<UTC>-codex-lifecycle-closed-resolver.md`

**Interfaces:**
- Consumes: clean runtime and audit results plus independent task and final reviews.
- Produces: an explicit acceptance record or a revision request; never a readiness promotion.

- [x] **Step 1: Rerun combined evidence**

Run: `python -B -m pytest tests/tree_replay/test_lifecycle_closed_pending_resolution.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_spec/test_lifecycle_closed_resolver_source.py -q --tb=short -p no:cacheprovider`

Expected: PASS.

- [x] **Step 2: Obtain independent final review**

The review must compare source ordering and source clock/effect adaptation, inspect the AST report and confirm that no persistence, replay, dataset or training claim entered the change.

- [x] **Step 3: Record acceptance only on evidence**

Record the exact passing commands and source pin.  State explicitly that causal full replay, economic labelling, dataset construction, training and all production permissions remain outside this component.

## Self-Review

- Spec coverage: Task 1 covers every record-local `check()` branch through ordinary OPEN closure; Task 2 proves the source sequence and dependencies; Task 3 prevents a local component from becoming an unsupported readiness claim.
- Placeholder scan: no implementation step delegates an unspecified policy; each source-owned decision and exact test command is named.
- Type consistency: Task 1 defines `resolve(state, *, now) -> (messages, changed)`, which Tasks 2 and 3 inspect without changing.
