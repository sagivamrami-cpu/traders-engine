# Lifecycle OPEN ordinary-resolution source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faithfully project the ordinary, non-ambiguous OPEN progress, target
and protective resolution order over caller-supplied post-fill evidence.

**Architecture:** A private offline resolver composes accepted transition and
outcome-shelf helpers. It runs only after `LifecycleOpenProtection` has found
no ambiguous touch, accepts `(trade, low, high, minimum_message)`, and returns
source-ordered messages plus a changed flag. A retained-source AST audit pins
only lines 2721–2750 and fail-closes on source, projection or child-proof drift.

**Tech Stack:** Python 3, pytest, `ast`, existing private tree-replay source
ports and explicit-root verification CLI.

**Spec:** `docs/architecture/LIFECYCLE-OPEN-ORDINARY-RESOLUTION-SOURCE-INTAKE.md`

## Global Constraints

- Parse and read the retained source; never import or execute it.
- Preserve the source's order: progress gate, ordinal target loop, recomputed
  protection, terminal state/outcome writes.
- Use accepted `LifecycleTransitions` and `LifecycleOutcomeShelf`; do not copy
  their helper policy.
- All wall-clock writes use the supplied offline source clock.
- Preserve `ready_for_replay=false` and `ready_for_training=false` in every
  audit/CLI report path.
- Do not acquire bars/quotes, persist, deliver, infer economics or construct a
  replay/dataset/model artifact.

---

### Task 1: Ordinary OPEN runtime projection

**Files:**
- Create: `trading_system/tree_replay/_vendor/lifecycle_open_ordinary_resolution.py`
- Create: `tests/tree_replay/test_lifecycle_open_ordinary_resolution.py`
- Create: `docs/architecture/LIFECYCLE-OPEN-ORDINARY-RESOLUTION-SOURCE-USAGE.md`

**Interfaces:**
- Consumes: `LifecycleTransitions._protective`, `_progress_messages`,
  `_target_line`, `_resolve_protective`, `_mark_terminal`; and
  `LifecycleOutcomeShelf._outcome`.
- Produces: `LifecycleOpenOrdinaryResolution(source).resolve(trade, *, low,
  high, minimum_message) -> tuple[list[tuple[str, bool]], bool]`.

- [x] **Step 1: Write failing directional-order tests.**

```python
def test_long_target_is_recorded_before_recomputed_protection(source, trade):
    messages, changed = LifecycleOpenOrdinaryResolution(source).resolve(
        trade, low=99.0, high=120.0, minimum_message=None,
    )
    assert changed is True
    assert trade["hit"] == ["TP1"]
    assert trade["state"] == "DONE"
    assert outcome_results(source) == ["tp1", "be_after_tp"]

def test_short_progress_uses_low_and_stays_silent_when_tp1_is_now_touched(source, trade):
    messages, changed = LifecycleOpenOrdinaryResolution(source).resolve(
        trade, low=target_one, high=adverse_but_not_protective, minimum_message=None,
    )
    assert changed is True
    assert not any("התקדמות מאז הכניסה" in message for message, _ in messages)
    assert trade["hit"] == ["TP1"]
```

Include a no-touch/no-mutation case, minimum-message progress suppression,
multiple ordinal target hits, no-target source behavior, and a physical
low/high mutation that prevents the directional target/protective effects.

- [x] **Step 2: Run the focused tests and confirm failure.**

Run: `python -m pytest -q tests/tree_replay/test_lifecycle_open_ordinary_resolution.py`

Expected: failure because `LifecycleOpenOrdinaryResolution` does not exist.

- [x] **Step 3: Implement the smallest source-ordered resolver.**

```python
class LifecycleOpenOrdinaryResolution:
    def resolve(self, trade, *, low, high, minimum_message):
        short = trade["direction"] == "שורט"
        protective = self.transitions._protective(trade, short)
        hit_protect = high >= protective if short else low <= protective
        tp1_now = bool(trade["targets"]) and (
            low <= float(trade["targets"][0][1]) if short
            else high >= float(trade["targets"][0][1])
        )
        # Preserve source progress gate, target loop, protective recomputation
        # and raw outcome order exactly; return (messages, changed).
```

Do not implement the ambiguity or zone-return branches in this file.

- [x] **Step 4: Run focused runtime tests.**

Run: `python -m pytest -q tests/tree_replay/test_lifecycle_open_ordinary_resolution.py`

Expected: PASS.

- [x] **Step 5: Write the usage boundary.**

Document that callers invoke `LifecycleOpenProtection` first, pass only
caller-owned causal evidence, and do not treat emitted raw facts or movement
messages as economic labels or training data.

### Task 2: Retained-source proof and fail-closed CLI

**Files:**
- Create: `trading_system/tree_spec/lifecycle_open_ordinary_resolution_source.py`
- Create: `tools/check_lifecycle_open_ordinary_resolution_source_parity.py`
- Create: `tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py`
- Modify: `docs/architecture/LIFECYCLE-OPEN-ORDINARY-RESOLUTION-SOURCE-USAGE.md`

**Interfaces:**
- Consumes: pinned source root, baseline source-pin manifest, Task 1 runtime,
  accepted transition/outcome-shelf auditors.
- Produces: `audit_lifecycle_open_ordinary_resolution_source(source_root) -> dict`
  and a JSON CLI whose only success status is `VERIFIED` with both readiness
  flags false.

- [x] **Step 1: Write failing audit tests.**

```python
def test_audit_rejects_low_high_projection_mutation(source_root, monkeypatch):
    monkeypatch.setattr(module, "VENDOR", str(mutated_vendor))
    report = audit_lifecycle_open_ordinary_resolution_source(source_root)
    assert report["status"] == "BLOCKED"
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
```

Also test source commit/blob mismatch, modified physical source order, malformed
child report, missing root and CLI JSON-error behavior.

- [x] **Step 2: Run audit tests and confirm failure.**

Run: `python -m pytest -q tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py`

Expected: failure because the auditor and CLI do not exist.

- [x] **Step 3: Implement the fail-closed physical-slice auditor.**

Pin `tracker.py` lines 2721–2750, parse them in a synthetic loop wrapper only
to make source `continue` syntax valid, compare their ordered AST to the
expected physical branch, and compare the runtime AST to the allowed
projection. Require exactly the accepted transition and outcome-shelf child
reports; reject missing/extra projections, non-serializable reports, changed
commit/blob, parse failure and CLI exceptions.

- [x] **Step 4: Run the combined tests and CLI.**

Run:

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_ordinary_resolution.py tests/tree_spec/test_lifecycle_open_ordinary_resolution_source.py
python -B tools/check_lifecycle_open_ordinary_resolution_source_parity.py --source-root 'C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
```

Expected: tests PASS; CLI JSON has `status="VERIFIED"`, an empty `blockers`
array, `source_subset_verified=true`, and both readiness flags `false`.

- [x] **Step 5: Request independent task and final reviews, then record Codex acceptance.**

Acceptance must independently rerun the exact combined command, inspect the
runtime and audit diff, and explicitly state that zone return, full resolver,
persistence/delivery, economics, replay, datasets, training and models remain
unaccepted.
