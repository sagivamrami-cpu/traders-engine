# Full tree.walk and builder source intake

Read-only source evidence, 2026-09-10; continuation of master C/D. The source
was read completely as text, never executed. This is not an implemented tree.
Authority chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9, tree.py blob
fdb439a39bbd35230e421c0319c6be0e2fbfbc1d. Entire1496lines reviewed, including
walk528-1224, helpers and trade_from_walk1353-1496.

## Original ordering and observable meanings

STAGES has12 entries: DATA, CONTEXT, LEVELS, SESSION, PATTERN, LOCATION, VECTOR,
MTF, TRAP, MEMORY, TRIGGER, TARGET. FINAL_STAGE assigned from STAGES[-1].
Walk.complete is no stopped_because AND reached FINAL_STAGE, not proof of risk
acceptance/fill. passed means visited, not positive evidence. Do not enforce
the HTML target order over this selected source variant. Walk carries missing,
assumptions, facts, zones, decided_close/bar and a refused Plan separately.

DATA fetches15m10 then4h60; captured errors return a DATA stop. Both correction
unverified flags checked, then length>=5 for both, then source.endswith('_stale').
CorrectionNone does not itself veto. ATR and close use delivered final row;
vector evidence/trigger use[-2]/[-3]. Private raw-reader parity must retain this
mixed convention; a causal producer must supply/reconstruct correct forming and
closed rows, not silently replace every[-2] by[-1].

CONTEXT real matrix.read_tr4h; on failure placeholder neutral only for that read
plus missing text. Then1h/30m/15m/5m lookback30 each, skip unverified/errors.
Higher pair agreement wins, then shorter group, then all; selected actual TF
ToolRead replaces r4, while structure and EMA slopes still use actual4h frame.
Agreement ignores neutral readings and can exist with some frames absent.
Optionswall.load is optional; stretch missing gives UNKNOWN (dev0 but NOT
CONSOLIDATING). Present max_dev>=3 givesDEVIATED. Structure errors separately
marked; EMA50/200/800 fivebar slope uses source raw comparisons/NaNs.

LEVELS _variant_levels uses actual levelmap.build first. Failure returnsNone;
empty successful map is separate. strict adds tr.daily_pivots(1d30); a pivot
failure invalidates entire universe, cannot replace base map with pivots.

SESSION news cached rawJSON is mandatory: _news_stop requires a future event
and uses inclusive +/-15minutes. No future coverage, unreadable JSON or missing
inside-window impact stops the walk. This differs from revalidation's30minute
observational shadow. Then current_session clock, Brinks box, and PSY forming
window (another UTC clock) are evaluated. Outside session is not a global veto.

PATTERN calls wm.detect1h OR15m (short-circuit), FirstVector5m, RVC/GVC15m.
WM's None can mean source-caught failure; outer formation_read only proves call
returned. RVC recovered+wick_ok supplies pattern context if WM absent. Missing
patterns do not stop. LOCATION within0.35ATR and exhaustion names reported.

VECTOR real PVSRA last-row available flag but[-2]kind; stoppingvolume uses[-2]
shape and previous10volumes[-12:-2], >=1.5baseline, body<=.35, wick>=.5. Failed
PVSRA marked unread; absent vector/SV and missing context are not vetoes.
Context = nearby EMA50/200/800 within1ATR, unstretched, or WM/RVC pattern.
MTF is six completed1h vector-kind counts, not true4h-to15m decomposition.
1h30 fetched again; unavailable source differs from successfully observed0.

TRAP Brinks checklist is optional. Percentile window excludes forming row;
evidence close[-2], upper85%/lower15%, up to40bars. Buy at high/sell at low
inverts vector side; opposite edge keeps vector side; midrange uses selected
trend. SV-only inversion requires matching trend. Stamp decision from[-1]
for every branch, including traps. Do not confuse evidence and decision rows.

MEMORY liquidity pools/run and TR vector zones are different objects. Pool
nearest unswept on either side within5ATR is context. Vector zones contribute
actual(mid,kind,touches), including every open zone, to later geometry. Unknown
zone computation is not empty. DirectionNone stops only after MEMORY; otherwise
TRIGGER signed[-3]->[-2] movement classified at.15ATR, negative result is fact
not missing and no veto. TARGET requires at least one distinct level ahead;
no stop/RR ladder exists until builder.

## Builder and source dependencies

trade_from_walk requires complete+direction, re-fetches15m10, checks drift>.33ATR
against current ATR and recorded price (not recorded bar equality), re-builds
variant map. Closed/open VZ50 midpoints within5ATR augment both targets and
invalidation anchors. Nearestbehind +/- .35ATR cushion, actualintraday stopband,
then original resolve_ladder. Stop clamp must stay beyond invalidation. Rejected
Plan carried in w.refused; accepted sourcePlan still UNADMITTED, not filled.
Missing/facts/assumptions and causal anchor text preserved; trap text can change
Plan.kind to reversal. levels_to_trade is another original consumer and retains
its own geometry/order/refusal behavior.

Dependencies already present: actual admission_matrix, tr.emas/ema_cloud,
defaultpvsra, stretch, pricing Plan/distinct_targets/stopband/resolve_ladder,
map_sessions and original levelmap.build_at graph. Source operation-clock map
binding remains: original _session_open_levels reads its clock AFTER5m3fetch;
passing a clock read before whole map build is not identical event ordering.
Existing fixed-T public map contract must remain unchanged.

New consumed source readers, all main-read completely:

| File | Git blob | Needed behavior |
| --- | --- | --- |
| brinks.py | 5c69c3367221e818a2b82f3ca559e1c5a36af675 | Box/today_box;14-15UTC, relevance15<=hour<20 weekdays;5m2 min8rows; actual defaultPVSRA+zones |
| wm.py | d04a462eb0692ed991f25ea2633d8c81783db877 | Formation/swings/plateau dedup/detect; TF10, min30, freshestW/M |
| checklists.py | 5c78955a6bb58d88c8117274606409fced65e22c | RVC/GVC, block quality/blocks and BrinksRead; same raw catches/order |
| liquidity.py | d73f06f323d39142932cb218935c15455244ce8b | Pools grouping/sweep and run speed+pool; own repeatedfetch |
| optionswall.py | c7d27ca396c162f6997b2a72bbd035ed6477e05b | Complete reportJSON/CSV/clock/expiry/frozenanchor mapping; optional context |
| tr.py | 8297c712d20404880d4d8949e96efbf48613909c | vector_zones defaultnonauction and daily_pivots; existingEMA/PVSRA reused |

Important raw behavior: WM vec_near passes only5rows to PVSRA whose baseline
needs10 priorrows; preserve observed source output, do not fabricate vectors.
Liquidity swings prioritize highs, WM lows; WM deduplicates plateaus, liquidity
does not. Liquidity run re-fetches pools; no frozen invented result. Brinks
formed_at is formatted range text, but checklist attempts pd.Timestamp(...)
then tz_convert; caught parsing failure can leave swept_asia=None. Do not fix
this source quirk silently while claiming parity.

Options chooses lexically last report path then first matching undegradedETF;
permission exact realtime_permission, age[-2,45]minutes, anchor<=marketasof
andgap<=75, optional src filter. First unexpired entry in inputorder, not sort.
Mapping ratio from historical anchor and ETFspot, NOT current_spot argument.
Logical artifact path/bytes/time ports must replace IO, not final Walls values.

## Remaining implementation sequence

1. TR vector-zone/defaultPVSRA closure and daily pivots with literal fixtures.
2. Actual pattern/liquidity/Brinks/checklist readers and options artifacts reader.
3. Full original walk+builder with complete dependency composition, operation-
   clock map adaptation and full ordered source audits; connect revalidation.
4. Causal provider/frame convention, main resolver/gates/park/receipts/outbox,
   branch-specific caller ordering and generated lifecycle; other producers.
5. Simulator/data/model/evaluation remain fullmaster requirements and human
   economic/instrument decisions remain separate. No new live or data authority.
