# Trend-reaction producer: pinned source intake

Date: 2026-09-09. Read-only source study for required remaining master area D,
while admission-dependency reviews run. This document is not an implementation.
It does not replace the pending outer-admission path or approve a new policy.

## Source identity and ownership

chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
chartdesk/trend_reaction.py blob64d191d8a9a69e6b10fd9680efcf94490ff03b20.
The complete source file was read as text (no imports/execution), along with
market_watch.py1116-1197. Identity rests on the pinned blob, not an inventory count.

This is continuation after a pullback, not level_reversal. Source callers process
classic reversal first, then trend_reaction, then tree/engine. A tradeable
same-pass opposite classic reversal blocks this producer before state mutation.
An admitted trend-reaction candidate can block opposite generic tree/engine plans.
Both active maps are assigned before episode dedupe, so a duplicate alert can
still own arbitration. Do not collapse their event identities or target entries.

## Atomic detector requirements to bind

| Source calculation | Exact rule | Temporal or interpretation constraint |
| --- | --- | --- |
| TF_MINUTES / LIVE_MAX_AGE_S |5m/15m;370seconds freshness each | Explicit actual T; only completed target bars |
| Initial warmup | raw and closed-frame length at least102 | Loop begins at index100, not102; final102-row minimum still applies |
| `_normalise` | UTC index, keep-last duplicate, ascending sort | Public adapter must separately define lawful source revisions/availability; no future revision import |
| `_trend_at` context | previous candle i-1; EMA5/13/50 order plus EMA50 slope over3bars | Reaction close cannot manufacture prior trend; fast EMA slopes are not required |
| Fan separation |abs(EMA13-EMA50)/ATR at i-1 >=0.35 and >=0.35 of prior50-bar median | Median excludes i-1; source boundary comparisons are inclusive |
| First touch | prior low strictly above prior anchor for long; prior high strictly below for short | Adjacent timestamps must differ exactly one target interval |
| Reaction candle | touches level, closes on trend side and correct half of candle | Mirrored long/short geometry; prior and current EMA anchors differ |
| Away/body | close at least0.05ATR from level; body at least0.15ATR and correct color | Uses reaction candle ATR, distinct from prior fan ATR |
| Eligible locations | EMA5/13/50 at reaction close plus `_named` using reversal eligibility | Named-level eligibility comes from the accepted reversal closure, not all map names |
| Multi-hit choice | long chooses lowest touched price; short highest | All unique hit names preserved; location_kind=confluence if >1hit |
| PVSRA | vector kind is recorded | No mandatory vector-color trigger in this detector |
| Event identity |symbol/direction/trend-reaction/confirmation.floor15min | Unlike classic reversal's vector-time episode; newest per same bucket retained |
| Ranking | newest confirmation; M5 wins equal confirmation | Distinguish detector-level dedupe from cross-TF find selection |

`detect_frame` returns immutable Reaction records with actual anchor, confluence
names, close, rejection extreme, fan measurements, vector kind and source identity.
Freshness is optional in the detector but fixed by `find`; raw supplied candidate
booleans or externally asserted MTF agreement cannot establish a replayed producer.

## MTF context and full producer order

`_context_direction` fetches15m55days,1h240days,4h240days in that order. Each must
have a correction, not unverified and source neither none nor tv_stale; then
normalization/closed-target selection and at least100bars. It consumes
`matrix.read_tr(frame).direction`, NOT full weighted matrix.net. 15m must be
directional; no higher TF may oppose it, and at least one must agree. Neutral
other higher TF is allowed. Any missing/failed required context returnsNone.

`find` obtains context BEFORE constructing the full level map. Empty map/missing
or unverified daily correction stops it. It fetches5m then15m with10-day lookback;
fetch failures skip that TF, while source none/tv_stale/unverified also skip.
It retains only reactions agreeing with computed context, selects newest/M5tie,
then calls build_plan with mtf_confirmed=True on that selection only. Current
historical map and source evidence are decision-time information, not something
that can be backdated to an older confirmation.

## Pricing differences from classic reversal

Source `build_plan` uses history index strictly before confirmation and unseeded
TR ATR; nonpositive/missing ATR fallback is max(abs(close-anchor),1e-9).
Pure named-level reactions enter at the anchor. EMA or confluence reactions
enter at the confirmation CLOSE, because a moving EMA is not a fixed future
limit price. This difference is load-bearing, not a cosmetic price label.

Raw stop is rejection extreme +/-0.15ATR; style scalp for5m and intraday for15m.
Original stop-band and target-ladder/obstacle/refusal functions are reused. If
the band-tightened stop no longer lies strictly past the rejection wick, the
source refuses even if the reward ratio otherwise qualifies. Missing MTF
confirmation replaces the refusal with observation-only. Reasons and warnings
are the original source strings, not a learned model explanation.

## Remaining operational path

Market-watch annotation is not a veto. Order after find/score: source plan
tradeable, classic reversal conflict, hunting, floor entry clock, post-stop,
has_open, same-level, active registration, episode dedupe, publication mode,
record success, then persisted episode. Recording rechecks OPEN/geometry and
sets initial advisory state as described in MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md.

Required implementation: audited complete detector/pricing/context/find closure,
causal frame/correction/map binding, explicit decision-time snapshots, outer
state/arbitration and source recording, full evidence tests. No implementation,
source-parity pass, market result, label or model is asserted by this intake.
