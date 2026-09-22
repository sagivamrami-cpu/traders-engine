# Task 3 implementation brief

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

- [ ] Write failing end-to-end synthetic tests: known scheduled base bars and daily labels -> actual source map -> LevelSnapshot -> accepted reversal/pricing wrapper. Verify exact source families/prices/order and source omissions, higher-TF forming state, future-extension invariance, missing current/delayed frames, stale corrections, proxy/replay versus broker gates, PSY preference/unused fallback invariance, duplicate request/identity errors, no readiness/admission and no mutation. No mock calculation dependencies. A no-reversal result is valid; add a separately constructed real reversal fixture to prove actual map can be consumed without manual price-level input.
- [ ] Run focused RED/GREEN; independently review actual untracked diffs. Run all source audits and python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q --tb=short, then python -m pytest -q --ignore-glob='*validator*' --tb=short. Record legacy-validator exclusion explicitly.
- [ ] Final combined review; resolve findings with reviewed regressions. Record acceptance and exact completed precision/coverage. Keep full source find/admission/arbitration, state machine, simulator, real dataset, models/evaluation and human gates open.


Controller retains documentation acceptance edits and broad final verification. Worker owns only the three Task3 files and its two reports. Dependencies Tasks1/2 must be accepted before implementation dispatch. No parked findings or domain rulings. Actual accepted interface details are in frames.py, corrections.py, levels.py, and _vendor/levelmap_build.py. Use existing real reversal/pricing test fixtures as references, not hand-supplied map levels.
