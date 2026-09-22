# As-of EMA Adapter Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development with TDD and independent review. The user approved the existing architecture and explicitly requested continuation; do not reopen that approval.

**Goal:** Produce typed historical EMA observations from only completed, available bars, faithfully reusing a small audited subset of chart-desk calculations.

**Architecture:** A strict bar selector establishes a contiguous, explicitly anchored as-of window. A vendored pure calculation subset preserves existing numerical behavior; a separate adapter exports numeric observations and provenance into the existing snapshot contract. This is a calculation slice of B/C, not a complete candidate producer or simulator.

**Tech Stack:** Existing Python, pandas/numpy and pytest; no installation or feeds.

**Spec:** `docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md` sections 3, 5, 10, 15; approved decision `agent-exchange/decisions/2026-09-08T180046Z-user-economic-target-and-baseline.md`.

## Global Constraints

- Existing local research branch; preserve prior changes. No commits, pushes, new worktree or scratch deletion in this slice.
- No external feeds, raw market inputs, notifications, broker actions, labels or training.
- Reuse pinned chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`; no imports of its live entrypoints.
- Explicit source, venue:symbol, timeframe, history start, decision time and freshness budget. Never infer instrument conversion, missing bars or a trading calendar.
- Closed-bar research slice only; unfinished live-bar parity is not claimed. Gaps, delayed bars and unsupported histories must not be silently compressed into a valid EMA history.
- This slice supports microsecond-exact timestamps. Normalize aligned datetime subclasses (including pandas Timestamp) into native UTC datetime; reject sub-microsecond input explicitly, never round it into the freshness boundary. Nanosecond feed integration requires a separate exact-time contract.
- SMA-seeded EMA and population stdev are source behavior, not a new trading rule. Observation warmup uses features.draw_trend's 2*length requirement.
- No order/above/cloud result is an entry gate. All snapshot definitions are optional observations; snapshot eligible is not replay readiness.

## Task 1: Closed-bar as-of boundary (delegated sidecar)

Files: create only `trading_system/tree_replay/bars.py`, `tests/tree_replay/test_bars.py`, and assigned worker report. Parent owns package initializer.

Interfaces (frozen keyword-only dataclasses):

```python
class ClosedBar:
    instrument: str
    timeframe: str                  # 5m, 15m, 30m, 1h, 4h only
    opened_at: datetime
    closed_at: datetime
    available_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None             # explicit None allowed, never replaced by 0
    source: str

class BarWindow:
    instrument: str
    timeframe: str
    decision_time: datetime
    history_start: datetime
    max_age_seconds: int
    bars: tuple[ClosedBar, ...]
    blocker: str | None

def select_closed_bars(bars, *, instrument, timeframe, decision_time,
                       history_start, max_age_seconds) -> BarWindow:
    ...
```

- [x] Write behavior tests first and run RED: future-close and future-availability exclusions; equality at T included; metadata validation and timezone/DST normalization; exact fixed duration; finite positive OHLC with low<=open/close<=high; finite nonnegative volume or None; bool/non-numeric rejection; explicit positive integer freshness; exact instrument/frame matching; duplicate opens rejected, out-of-order input deterministically sorted.
- [x] Implement UTC-normalized ClosedBar validation; require nonempty trimmed source and exact non-whitespace venue:symbol. Accept native int/float prices and normalize to float; reject other numeric types/nonfinite overflow. All fields required.
- [x] Selector consumes only ClosedBar inputs; validate request fields and history_start<=T. Reject mixed instrument/frame and duplicate opens, including unsupported revisions. Filter opened_at>=history_start, closed_at<=T and available_at<=T before calculation. No market calendar/resampling or latest-revision selection.
- [x] Assign blockers in precedence: NO_HISTORY if empty; HISTORY_INCOMPLETE if first open != history_start; HISTORY_GAP if adjacent close != next open; STALE if T-last close exceeds max_age_seconds; otherwise None. Equality at freshness bound is permitted. Missing planned opening bars and delayed interior observations therefore cannot silently produce a compressed history. This strict contiguous-segment policy is intentionally not weekend-aware.
- [x] Run `python -m pytest tests/tree_replay/test_bars.py -q`, self-review, report RED/GREEN. No subagents, outside files or commits.

Literal scenario: 5m bars 12:00-12:05 and 12:05-12:10, second available at12:11. At12:10 only first is available; freshness300 permits it. At12:11 both are available. At12:10:00.000001 with freshness300 the first is stale. Removing an interior bar from a longer window yields HISTORY_GAP, never a valid shorter rolling history.

## Task 2: Pinned numerical subset and typed adapter (parent critical path)

Files: `trading_system/tree_replay/__init__.py`, `_vendor/__init__.py`, `_vendor/indicators.py`, `_vendor/tr.py`, `ema.py`; `configs/trees/ema-feature-contracts.json`; `tests/tree_replay/test_ema.py`; `tools/check_ema_source_parity.py`.

Interface:

```python
def ema_snapshot(bars, *, snapshot_id, instrument, timeframe, decision_time,
                 history_start, max_age_seconds) -> dict:
    ...
```

- [x] Before production code, write RED fixtures demonstrating SMA seed, cloud population stdev, warmup, as-of selection and numeric snapshot output. The expected EMA5 for closes1..10 is8; cloud size for closes1..100 is sqrt(833.25)/4.
- [x] Vendor exact function bodies `_seeded_recursive`, `ema`, `stdev` from indicators.py and `emas`, `ema_cloud` plus TR_EMAS from tr.py. Only audited numpy/pandas and relative pure subset imports. Preserve attribution and describe behavior as pinned chart-desk, not an independent claim about TradingView. Record original blob hashes, commit, selected symbols and mapped consumer lines.
- [x] Adapter consumes Task1 selector. On blocked history export all observations null: STALE for stale window, UNAVAILABLE otherwise. For usable history, emit per-period EMA price, close-above boolean, and signed EMA change over five bars with 2*n warmup; UNKNOWN during warmup. The unnormalized delta is source T3 numerator, not an ATR-normalized slope or momentum score.
- [x] Emit available EMA descending order as a categorical period list (stable tie order as source), full-fan stacked boolean only after all EMAs meet warmup, cloud50 basis/upper/lower/size and close location ABOVE/BELOW/INSIDE after100bars. Partial order remains usable when only some averages exist. Record partial/full coverage separately; no invented equality direction.
- [x] Use namespaced feature IDs `chartdesk.<timeframe>.ema<n>`, `.above_ema<n>`, `.ema<n>_delta5`, `.ema_order`, `.ema_stacked`, `.cloud50_<basis|upper|lower|size|location>`. All raw numbers unrounded; no outcome features. Known timestamps last closed bar and max availability of ALL selected dependencies. Missing/warmup timestamps record evaluation atT. Use existing build_snapshot; all feature definitions PRE_ENTRY/required=False.
- [x] Add canonical selected-input SHA256 and metadata including exact instrument, timeframe, history_start, freshness, source commit, adapter version and pandas/numpy versions. Excluded future rows cannot change payload/identity at the same T. Reports always ready_for_replay=false/ready_for_training=false.
- [x] Add standalone read-only parity CLI taking explicit --source-root (chart-desk checkout). Compare selected function ASTs and source Git blob identities against pinned manifest, before executing ONLY the reviewed vendored functions. No dynamic exec or import from source checkout. Functional golden tests establish numerical behavior; source AST identity demonstrates reuse. Mutated source must fail (nonzero exit), no skip if source missing.
- [x] Tests: 5/15/30/60/240m aligned closed inputs, short/full warmup, known False/zero retained, equality in cloud, rising/falling/mixed/tied order, stale/gap/allmissing, late earlier dependency availability propagated, future suffix extreme changes excluded, caller input/output nonmutation and deterministic identity, all-finite output. Reject numerical overflow rather than turn it into warmup.

## Task 3: Integration, reviews and durable handoff

- [x] Independent task reviews plus final combined review; controller reads original task/result and actual diff, independently verifies delivered tests.
- [x] Run `python -m pytest tests/tree_replay tests/tree_spec -q`, source-parity CLI on retained pinned checkout, and `python -m pytest -q --ignore-glob='*validator*'`. Legacy validator exclusions remain explicit.
- [x] Update master progress, AGENTS/README links and usage. Record exact commands, scope and review outcomes in agent-exchange/status. Do not call this full replay, complete feature coverage or training.

## Preflight / progress

| Task/pair | Scope and interface check |
|---|---|
| 1 | Explicit metadata and contiguous-window policy; no calendar inference |
| 2 | Five EMAs/cloud only; T3 numerator not normalized T3; observation not decision |
| 1/2 | BarWindow.bars/blocker and normalized timestamps are the join; disjoint writes |
| 2/3 | Vendored AST identity plus independent arithmetic fixtures, not self-comparison |
| 1/3 | Controller verifies time/gap behavior before accepting adapter integration |

Continuation of approved architecture, not a new trading-design decision. Process
adaptations: existing workspace/no commits; parent handles critical path while one
sidecar worker handles bar validation. Review packages use explicit untracked-file
diffs. No market policies are inferred. Full candidate/walk parity remains next.
