# Historical level-map source contract

Read-only source study for the next implementation stage. This is not an
implemented historical map, an atomic registry for all 22 layers, or approval
to use market data. Authority: the approved existing-repository baseline.

## Pinned evidence

chart-desk commit: `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`.
Files inspected as text, never imported or executed:

| File | Git blob |
| --- | --- |
| chartdesk/levelmap.py | 01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e |
| chartdesk/tr.py | 8297c712d20404880d4d8949e96efbf48613909c |
| chartdesk/sessions.py | 2f44d322178feb14b0488abda51b40581db5b31f |
| chartdesk/basis.py | f3396f3a9fefd71f0f71422001a5521af0a05cd2 |
| chartdesk/replaysource.py | 39f5ddb25728a42e63ff8e59fb1fd4d911532247 |

## Calculation to consumer mapping

Prices and price distances use the exact source instrument's units; no GC/spot
substitution. Each emitted value needs its own observed/available/dependency
evidence. The complete map feeds level_reversal.find/detect_frame/build_plan;
detector-eligible anchors are a subset of pricing target candidates.

| Family | Source calculation / consumption | Temporal and coverage requirements |
| --- | --- | --- |
| ADR-HI/LO | tr.average_range length14; current low + prior mean range, current high - prior mean range | 14 completed daily periods plus current forming period; levelmap requires available and verified |
| RD-HI/LO | tr.range_hilo length15 delegates to average_range, NOT rolling maximum/minimum | 15 completed daily periods plus current; levelmap requires verified |
| AWR-HI/LO, RW-HI/LO | weekly average_range4 and range_hilo13 | tr_levels first requires >4 weekly rows; RW can then remain unavailable if insufficient history |
| AMR-HI/LO | monthly average_range6 | >6 monthly rows; source calls without broker_bars even when daily is verified |
| ADR50/AWR50/AMR50 HI/LO | corresponding from_open result high/low: current period open +/- half average range | Do not confuse with average_range's high50/low50 outputs, which are different fields |
| YDAY-HI/LO/CLOSE | daily.iloc[-2] | Last row must genuinely represent current period, not yesterday's final bar |
| D2/D3/D4 HI/LO | levelmap._back_day_levels; last offsets3..5 | Requires >=5 daily rows before emitting any back-day levels |
| LWEEK-HI/LO | tr_levels weekly.iloc[-2] | In source nested under >4 weekly rows; do not silently remove this guard |
| DAY-OPEN/WEEK-OPEN | final daily/weekly row open | A known opening observation is sufficient for open, never for final high/low/close |
| LONDON-OPEN/NY-OPEN | levelmap._session_open_levels, exact 5m opening bar | Only during that venue's active session; no nearest-bar approximation, no carry into next day |
| PSY-HI/LO | sessions.psy_levels, week's first Asian window | Prefer corrected1h then15m; broker shape7-day guard; exclude proxy portion before splice seam |
| EMA200-1h/EMA800-1h | tr.emas and levelmap._ema_levels | >=400/1600 rows, final non-null value; captured partial higher-TF bars need separate policy |
| CLOUD50-4h/EMA200-4h | tr.emas on4h, lengths50/200 | >=100/400 rows; CLOUD50 means EMA50 basis here, not cloud envelope |
| Q-WHOLE/Q-HALF/Q-QUARTER | quarters.nearest(symbol,current daily close,count=2) | Four grid locations; preserve order and duplicate display names through explicit level IDs |

Classic floor pivots and M levels are deliberately not surfaced by this source
map. tr_levels still computes pivots internally. Preserve this code variant and
record its difference from HTML; do not add excluded levels to reproduce HTML.

## Source details that must not be silently repaired

1. tr.weekly_from_daily shifts daily timestamps forward3h before W resampling;
   monthly_from_daily uses the same shift before MS resampling. This is bucket
   assignment, not the actual observation/publication timestamp. Preserve exact
   behavior, including Sunday rollover and month-boundary tests.
2. Range formulas exclude the final forming row from historical mean and use its
   current extremes or open as anchor. Completed end-of-day OHLC at a morning
   decision would leak future information. ClosedBar currently represents only
   fixed-duration5m/15m/30m/1h/4h bars, not source daily/weekly/monthly state.
3. broker_shape_ok(corr,days) accepts tv_daily/mt5_broker and exchange-native
   BINANCE:BTCUSDT. A tv_spliced frame qualifies only after enough genuine span.
   Its source use of Timestamp.now must be replaced by an explicit replay clock
   through a documented, audited specialization. No present-day clock in replay.
4. Source gating is asymmetric: ADR/RD check verified; AWR/RW/AMR and from-open
   map branches check availability/keys but do not all check verified. Record
   calculation evidence and source gating separately; do not claim verified
   broker shape for every emitted family or silently invent a blanket veto.
5. Session opens use Europe/London08:00-16:30 and America/New_York09:30-16:00,
   weekday windows from sessions.SESSIONS. UTC shifts with the venue's DST, not
   Israel's. Source windows do not by themselves certify historical holidays.
   A tv_spliced opening bar before tv_from is omitted. Source correctionNone or
   source==none also omits session opens.
6. psy_levels uses Sydney-local Saturday08:00 (crypto) or Sunday08:00 (forex)
   through next-day17:00 by its actual mask. It groups available samples at
   gaps>12h, takes the final group, and exports scheduled window_end separately
   from the last observed bar. Do not relabel the scheduled end as availability.
   Its prose convention is not a separate authoritative Tokyo-calendar formula.
   Partial coverage and DST boundaries need focused source-fidelity tests.
7. level_reversal.find first requires nonempty levels and non-unverified level
   correction. Bar correction also must exist and have source!=none. It compares
   M5/M15 confirmations, newest first and M5 on an equal time. Current pricing
   adapter does not implement these provenance gates or cross-timeframe choice.

## Implementation acceptance boundaries

The next vertical work must reconstruct period state and original map calculations
before wiring source producer selection. Required tests are independently derived
OHLC at several intraday decisions, future-extension invariance, delayed/missing
bar exclusion, complete scheduled-coverage checks, exact opening observations,
period rollover/DST, insufficient history, original feed/proxy/splice gates, all
listed level families and source order. Unknown input stays unavailable.

One exact source dependency slice may be ported independently, but cannot claim
the whole map. A supplied partial-bar record needs the extent actually observed,
its publication time and provenance; its eventual final values must not replace
earlier states. Raw-data retention and real input coverage remain human-governed.

After map construction: source find selection, remaining acceptance/arbitration,
order lifecycle, fixed initial-stop/full-TP1 economics and separate movement
outcomes. Only then can resolved candidate histories enter the new training view.

## Existing replay-hook limitations confirmed in pinned source

Additional read-only inspection on 2026-09-09; the source checkout was clean and
the replaysource.py working-file blob matched the pinned Git blob above.

- basis.fetch_corrected returns Correction(..., source="replay", confidence="high")
  whenever replaysource is active. broker_shape_ok does not recognize "replay"
  as tv_daily/mt5_broker/tv_spliced. For OANDA:XAUUSD this returns false; native
  BINANCE:BTCUSDT still receives the separate native exemption. Thus a replay
  installed successfully is not evidence of identical level-map family coverage:
  ADR/RD and PSY shape gates can omit levels. Do not fix this by falsely relabeling
  an unknown feed as broker data; historical source identity needs real evidence.
- This hook's Correction.note is a dictionary despite the class's str annotation.
  A typed research evidence object is not a drop-in loader for that legacy object.
  The new correction adapter accepts an attested string note; any later legacy
  importer must explicitly normalize and preserve its original provenance.
- ParquetSource.slice reconstructs coarser forming bars from the known fine-bar
  prefix; do not claim this version merely filters a final coarse bar by open.
  Its cursor denotes a bar open plus cursor_timeframe duration for the known
  cutoff. That convention must be translated explicitly to decision_time.
- The existing source does not independently represent publication timestamps,
  calendar-backed completeness or exact per-frame instrument identity. _read
  keeps the last duplicate timestamp and fills absent volume with zero; those
  behaviors are not adequate evidence for the stricter outcome dataset contract.
  No cursor returns the complete frame. serve(timeframe) has no symbol argument.
- Its default daily aggregation is midnight-based pandas 1D resampling, not a
  supplied broker-day/calendar contract. This is a separate source limitation
  from future-bar exclusion. Remaining live wall-clock consumers also require
  explicit replay-clock adapters rather than reliance on the feed hook alone.

These are source-code findings and engineering constraints, not a diagnosis of
which mechanism actually affected an earlier training run; that would require
the exact run inputs/configuration/logs. No existing live or replay code was
changed by this inspection.
