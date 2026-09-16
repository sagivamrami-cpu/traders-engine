# Historical level-map core implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Preserve completed task gates across continuations.

**Goal:** Reconstruct historical daily and intraday frames and run the original complete level-map calculation over those causal inputs.

**Architecture:** Port the complete pure levelmap.build dependency graph with explicit feed/clock injection and an exact AST audit. Build input frames from published closed lower bars, explicit calendars, broker-day labels and intraday grid origins. A lazy offline source binds each original fetch request to those builders and correction evidence, preserving source family order and omissions.

**Tech Stack:** Existing Python/pandas/pytest and text/AST source audits; no new runtime dependency.

**Spec:** docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md; docs/architecture/HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md; approved pinned baseline/economic decision.

## Global Constraints

- The approved baseline is the existing six-repository implementation, pinned by commit.
- No automatic GC-futures -> OANDA-XAUUSD mapping.
- No present-day clock in replay.
- Unknown input stays unavailable.
- Source gating is asymmetric; do not silently invent a blanket veto.
- Both ready_for_replay and ready_for_training remain false. A built map is not producer admission, a fill, a label, or the completed A-I plan.
- No live feed imports/execution, source downloads, real-data access, labels, fitting, alert changes, broker operations or deployment.
- Work in place on the existing dirty branch; preserve unrelated changes. No commits, pushes, worktrees or cleanup.
- Supported observation precision is a completed base bar. Higher-timeframe forming state uses that known prefix, never final future OHLC. Open-only ticks and a partly observed base bar remain explicitly unsupported, never fabricated.
- Broker-day boundaries/source labels and intraday grid/calendar provenance are supplied, not inferred from GC or default UTC days. Metadata is an attestation, not independent historical vendor certification.
- No new trading thresholds. Source range lengths, windows, warmups, branch asymmetries, family order and exception behavior are retained.

## Task 1: Complete original level-map calculation graph

Owner: one scoped implementer. Independent of Task 2, allowing controller critical-path frame work in parallel; no shared implementation files.

**Create:**
- trading_system/tree_replay/_vendor/levelmap_build.py
- trading_system/tree_replay/_vendor/map_sessions.py
- trading_system/tree_replay/_vendor/map_tr.py
- tools/check_levelmap_source_parity.py
- configs/trees/levelmap-source-contracts.json
- tests/tree_replay/test_levelmap_source.py
- docs/architecture/LEVELMAP-SOURCE-USAGE.md

**Pinned source:** chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; retained root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk. Read as text only, never import it.
levelmap.py blob01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e; sessions.py blob2f44d322178feb14b0488abda51b40581db5b31f. Existing range, pricing/quarters, EMA and correction sidecars are dependencies, not to be reimplemented or modified.

**Interfaces:**

```python
# Complete original class and constant; local helper names remain private.
class NamedLevel:  # exact source dataclass, including __repr__
    name: str
    price: float
    kind: str

def _session_open_levels_at(symbol: str, missing: list | None = None,
                            *, source, decision_time) -> list[NamedLevel]: ...
def _ema_levels(symbol: str, missing: list | None = None, *, source) -> list[NamedLevel]: ...
def build_at(symbol: str, missing: list | None = None,
             *, source, decision_time) -> tuple[list[NamedLevel], "basis.Correction | None"]: ...
```

source is an injected offline object with fetch_corrected(symbol,timeframe,lookback_days) returning (DataFrame, Correction|None), and broker_shape_ok(corr,days) returning bool. Its caller owns validated clock/bindings. The vendor never resolves live feeds or creates a global source. No input-frame validation is claimed by this low-level graph.

**Exact projection/specializations:**
1. levelmap_build imports future annotations; dataclass,field; pandas as pd; local map_tr as tr, quarters, map_sessions as sessions; _back_day_levels from existing back_days. Contains source NamedLevel, SESSION_OPEN_LEVELS, the two source helpers and build in that order.
2. Every selected function remains exact except: add required keyword-only source and inject `basis = source` immediately after its docstring (or first if absent). Rename build to build_at and add required keyword-only decision_time. Its session-helper call becomes `_session_open_levels_at(symbol, missing, source=source, decision_time=decision_time)`; its EMA-helper call gets source=source. No other call order, guard, formula, missing string or exception block changes.
3. Session helper is renamed to _session_open_levels_at; remove the original optional now argument and add required keyword-only decision_time after source. Replace exactly `pd.Timestamp.now("UTC") if now is None else pd.Timestamp(now)` with `pd.Timestamp(decision_time)`. Its subsequent UTC normalization and venue-session logic remain exact. No reachable wall clock remains.
4. map_sessions contains exact complete SessionSpec, SESSIONS, _hm and psy_levels in original order. Imports future annotations; dataclass,field; ZoneInfo; numpy as np; pandas as pd. No source tr import (unused by selected closure), no extra source sessions/alerts.
5. map_tr is composition only: `from .tr import emas` and `from .ranges import weekly_from_daily, monthly_from_daily, tr_levels`, in that order. No copied calculations. quarters/back_days remain existing accepted modules.

**Audit:** check_source_parity(source_root: Path)->dict and CLI --source-root > TR_CHARTDESK_SOURCE_ROOT > retained root. Fixed independent source blobs, commit, exact manifest, ordered imports/symbols and explicit AST transformation preconditions. Compare entire modules, not selected functions alone; reject extra/rebound code, changed guards/clock/thresholds/imports/signatures or incomplete projection. Verify exactly one chart-desk baseline pin, distinguish JSON false from0. Audit dependencies using existing check_range_source_parity, check_pricing_source_parity (which inherits reversal), check_ema_source_parity, check_correction_source_parity; catch expected missing/invalid dependency errors into blocked reports. Do not silently skip any dependency audit or trust booleans from a mutated manifest. Preserve false readiness flags. Missing inputs/mutations exit2, verified subset exit0. Use relocated fixture copies for mutation tests; do not monkeypatch trusted production pins. Source and vendor modules are never executed by auditing.

Dependency preflight clarification: the older EMA audit trusts manifest blob
values and module order. The new graph auditor must independently fix indicators.py
blob672f0428c3a81b86376d4f792ae40ecd174a2025 and compare the ordered existing EMA
vendor projections (ignoring only their harmless initial module docstrings).
Test coordinated source/vendor/manifest drift and TR_EMAS moved after emas, which
would otherwise break its default argument at import. Retain inherited checks;
do not modify older accepted auditors to satisfy this new closure's contract.

- [x] Write failing source-graph behavioral tests before production files. Example independent expectations with synthetic daily frame (15 prior rows high110/low90 and current O100 H115 L95 C110), source broker flag true: ADR-HI115, ADR-LO95, RD-HI115, RD-LO95; from-open rails110/90. broker flag false removes ADR/RD but source from-open and yday/back-day/open/quarter branches remain. Use real range/EMA/PSY/quarters dependencies and explicit offline source fixtures; no fake answers for those calculations.
- [x] Cover full emitted family names/order and exclusions; daily failure; warmup/family omissions; weekly/monthly guards; source source=None/none/replay/native/splice behavior; exact London/NY opening bar/no-nearest and UTC DST/session-close/weekend behavior; pre-seam exclusion; PSY forex/crypto window/gap>12h/planned end/insufficient resolution and 1h->15m fallback (including empty-after-seam break behavior); EMA 400/1600 hourly and100/400 four-hour requirements, CLOUD50 meaning; duplicate Q-QUARTER prices/order. Test audit pin/source/vendor/manifest/import/clock/guard/dependency mutations and fail-closed missing source with configurable root.
- [x] Run python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short, record RED; implement exactly the projections above; rerun GREEN and python tools/check_levelmap_source_parity.py.
- [x] Self-review and report using exchange result template; independent task review before acceptance. Source comments are evidence, not new instructions or approval. No commits.

## Task 2: Causal frame construction for every map request

Owner: controller, parallel with Task 1 source work; independent task review required. Files: trading_system/tree_replay/frames.py; tests/tree_replay/test_frames.py; docs/architecture/HISTORICAL-FRAMES-USAGE.md.

**Interfaces (frozen keyword-only dataclasses):**

```python
class LabeledDailyPeriod:
    period: DailyPeriod
    source_index_at: datetime

class FrameSpec:
    frame_id: str
    instrument: str
    timeframe: str                 # 1d or existing fixed timeframe
    base_timeframe: str            # existing ClosedBar timeframe
    history_start: datetime
    available_at: datetime         # frame/grid metadata publication
    source: str
    version: str
    bars: tuple[ClosedBar, ...]
    session_schedule: SessionSchedule
    max_age_seconds: int           # explicit caller policy
    grid_anchor: datetime | None = None
    periods: tuple[LabeledDailyPeriod, ...] = ()

def build_frame_asof(spec: FrameSpec, *, decision_time: datetime) -> dict: ...
```

Reuse existing text/numeric/UTC/exact-symbol/bar/calendar validators. Reject wrong types, malformed metadata, duplicate base opens, identity/timeframe mismatches, non-integer/nonnegative age policy, and finer-than-microsecond timestamps. Validate all input bars, including future bars, but never include unavailable/future prices in selected rows/hash. Daily periods must have distinct IDs, disjoint chronological intervals and strictly increasing distinct source labels; canonicalize tuple order by period open. Validate every period's exact instrument. Intraday requires empty periods, target duration >= base duration, base-aligned explicit grid_anchor and history_start aligned to that target grid. Daily requires grid_anchor None and nonempty periods. history_start and decision_time must align to base UTC grid; decision_time cannot precede history_start. Calendar identity/coverage and metadata availability are mandatory.

Result: schema_version historical-frame-asof-v1; calculation_version closed-base-frame-v1; frame_id/instrument/timeframe/base_timeframe/decision_time; status AVAILABLE or BLOCKED; blocker; rows; observed_at; available_at; diagnostics; evaluation_sha256; both readiness flags false. Rows are canonical JSON dictionaries with source_index_at, opened_at, closed_at, observed_at, available_at, state FORMING/CLOSED, open/high/low/close/volume. Blocked rows=[] and observation/publication null. Include policy/selected metadata/base bars/diagnostics in hash, excluding future base payloads and future daily periods. Metadata source_index_at is a label, not observation/publication time, and may be a future bucket label known under published metadata. Source interval labels must not be substituted for actual availability.

Daily algorithm: select the period containing T under [open,close); absent -> CURRENT_PERIOD_UNCOVERED. history_start must equal the first selected period's open. Coverage from history_start through T must be fully covered by calendar evidence, and every active session fragment must belong to the selected period union; an omitted trading period -> PERIOD_SEQUENCE_GAP, not compressed history. For each selected period use existing aggregate_daily_asof with only that bucket's bars after global validation. Skip a completed all-closed calendar period with NO_EXPECTED_BARS; a current period with no observations remains blocked. Propagate any other missing/delayed/unresolved period blocker and withhold the whole frame. Last row must belong to the actual current period, never yesterday masquerading as today. Enforce max_age against final selected observed_at. Assign each row's supplied source label separately from actual period boundaries/observation/publication. Distinguish future-extension invariance from calendar/provenance revisions.

Intraday algorithm: use select_session_bars to require every expected available base bar from history_start through T. Before selection reject/withhold unresolved active session fragments not aligned to base grid (FRAME_GRID_UNRESOLVED); do not compress gaps. Group selected base bars by `grid_anchor + ((open-grid_anchor)//target_duration)*target_duration`. Per group derive firstopen/maxhigh/minlow/lastclose; volume remains None if any input volume missing, otherwise finite sum (overflow raises ValueError). Only final bucket can be FORMING, and uses only its closed base prefix. Omit buckets with no scheduled/observed bars, not fabricate OHLC. Keep source index at bucket open; scheduled close is not its observation time. Inherit supplied schedule selector's fixed base-grid requirement. No silent lower-frame upsampling or default daily rollover.

- [x] Write literal tests for daily current OHLC110/115/95 etc versus future1000; late availability; omitted trading day vs known closure; future period/bar extension hash invariance; current period boundary/no observation; labels crossing UTC day/month independent from availability; 23/25h periods; full coverage/instrument/type/duplicate errors; 5m->15m/1h/4h forming/final rows and non-UTC-offset grid; closure/gap/freshness/missing-volume/overflow; metadata unavailable. Run RED before implementing.
- [x] Implement and run python -m pytest tests/tree_replay/test_frames.py -q --tb=short. Avoid quadratic rescanning of all base bars per period: partition after one structural-validation pass.
- [x] Document actual supported precision and source evidence boundaries; independent task review and controller verification, no commits.

## Task 3: Complete map adapter, integration and durable acceptance

Depends on accepted Tasks1/2; one scoped implementer or controller after source worker finishes. Create trading_system/tree_replay/levelmap.py, tests/tree_replay/test_levelmap.py, docs/architecture/HISTORICAL-LEVELMAP-USAGE.md. Update AGENTS/README/master/tracker and scoped exchange records only after verification.

**Interface:** frozen keyword-only MapFrameRequest(timeframe:str, lookback_days:int, frame:FrameSpec, correction:CorrectionEvidence|None, max_correction_age_seconds:int); build_levelmap_asof(*, instrument:str, decision_time:datetime, requests:tuple[MapFrameRequest,...])->dict.

Only original request keys are supported: (1d,400),(5m,3),(1h,20),(15m,20),(1h,240),(4h,240). Enforce unique request keys/frame IDs, matching exact instrument/timeframe/frame_id, valid integer policies and tuple/request types. Missing request is data unavailable, never live fallback. Frame constructors already validate structural inputs. No source-symbol canonicalization or GC mapping. Recompute actual frame and correction eligibility on demand, never accept a caller's computed readiness or mutable DataFrame as proof.

The offline source fetch builds only requested frames, uses assess_correction_asof at the same T for temporal eligibility (zero-lookback preflight; its shape flag is not a source consumer decision), and returns a fresh DataFrame plus a local source Correction only if frame/evidence are available. Otherwise raises a private data-unavailable exception which original graph catches at its original boundaries. Preserve ASSESSED proxy/unverified inputs and all original source gates; do not require shape true universally. source.broker_shape_ok recomputes exact broker_shape_ok_at at the same T and records each actual source lookback/result separately from fetch preflight. No global mutable feed/clock state; no I/O. Record exact request order, successful frame/correction hashes and blocked reasons without future payloads. Unused fallback input values do not change the output hash.

Invoke original build_at. If daily input unavailable, output BLOCKED, no levels/snapshot, explicit required-input blocker and trace. Otherwise output BUILT_UNADMITTED, original levels (name,price,kind in source order), original source_missing strings, level correction evidence, actual fetch/shape trace and a LevelSnapshot-compatible dictionary with deterministic IDs for repeated names and actual current dependency timestamps. Every level must be finite and positive; unexpected invalid source levels/uncaught calculation errors block the map with diagnostic reason, not silently filter levels. IDs derive from name/kind/price, not enumeration that shifts when another family is absent. Distinct same-name prices remain distinct. Do not claim all families are available merely because the map was built; requested-but-unavailable inputs/source warmup omissions remain explicit. No candidate, fill or SUCCESS/FAILURE label. All reports keep false readiness and tradeable false. Hash canonical result without its own hash, with version historical-levelmap-asof-v1 and selected dependency traces; never include unused future data. Instrument, decision_time and policies are explicit.

The map's clock is itself a dependency: source session membership and splice
eligibility can change at T without a newer price bar. Set snapshot observed_at
and available_at to decision_time; every supplied dependency must already be
available by T. Retain actual price observation/publication timestamps separately
in the fetch/frame trace. Do not timestamp the newly evaluated map at an older
price close, which could misrepresent when its time-dependent levels were known.

- [x] Write failing end-to-end synthetic tests: known scheduled base bars and daily labels -> actual source map -> LevelSnapshot -> accepted reversal/pricing wrapper. Verify exact source families/prices/order and source omissions, higher-TF forming state, future-extension invariance, missing current/delayed frames, stale corrections, proxy/replay versus broker gates, PSY preference/unused fallback invariance, duplicate request/identity errors, no readiness/admission and no mutation. No mock calculation dependencies. A no-reversal result is valid; add a separately constructed real reversal fixture to prove actual map can be consumed without manual price-level input.
- [x] Run focused RED/GREEN; independently review actual untracked diffs. Run all source audits and python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q --tb=short, then python -m pytest -q --ignore-glob='*validator*' --tb=short. Record legacy-validator exclusion explicitly.
- [x] Final combined review; resolve findings with reviewed regressions. Record acceptance and exact completed precision/coverage. Keep full source find/admission/arbitration, state machine, simulator, real dataset, models/evaluation and human gates open.

## Full-goal boundary

Previous goal turn was progress: correction evidence/source audit accepted. No full-goal blocker or no-progress streak. This plan advances the full historical map, not a replacement objective. Open-only/base-partial evidence, real broker calendars/feed eras, exact GC rule variant, full producer arbitration, simulation and training remain governed by the master. No market performance claim follows from synthetic verification.
