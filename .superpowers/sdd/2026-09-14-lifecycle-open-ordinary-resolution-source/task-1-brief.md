# Task 1: Ordinary OPEN runtime projection

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

## Requirements

- Parse/read retained source only; never import or execute it.
- Preserve the source's physical order: progress gate, ordinal target loop,
  recomputed protection, terminal state/outcome writes.
- Run only after the ambiguity component has reported no change. Do not
  implement ambiguity or zone return here.
- All time writes use the supplied offline source clock via accepted helpers.
- No bars/quotes acquisition, persistence, delivery, economics, replay,
  dataset, training or model behavior.

## TDD behavior

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

Cover no-touch/no-mutation, minimum-message progress suppression, multiple
ordinal target hits, no-target source behavior, and a physical low/high
mutation that prevents directional target/protective effects.

Implement the smallest resolver. Core shape:

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

Write a usage document: callers invoke `LifecycleOpenProtection` first, pass
only caller-owned causal evidence, and raw facts/movement messages are not
economic labels or training data.

Run:

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_ordinary_resolution.py
```

Write report to:
`.superpowers/sdd/2026-09-14-lifecycle-open-ordinary-resolution-source/task-1-report.md`.

Report status `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`;
list changed files and exact test command/result. Do not commit, push, change
unrelated files, or spawn subagents.
