# Private operation-clock level map

Component accepted; not full-tree or historical replay certification.

`BasisOperation(source)` forwards `fetch_corrected(symbol,timeframe,lookback)`
and `now_utc()` without caching, validation or added catches. Its
`broker_shape_ok(corr,days)` is the original predicate, not a source-supplied
verdict. Only a non-native tv_spliced correction with tv_from reads the clock.

`LevelmapOperation(source).build(symbol,missing=None)` uses that facade with
the actual accepted range, back-day, session, EMA and quarter calculations.
It returns original `NamedLevel` instances and the fetched daily correction.
No pivots are added. The raw source must supply actual Correction-compatible
objects and pandas OHLC frames, not computed levels or readiness decisions.

The session helper `_session_open_levels(symbol,missing=None,now=None)` first
fetches 5m/3, then checks nonempty data and correction provenance. Only then
does it read the operation clock. Explicit now bypasses that read but not the
fetch or gates. Venue DST/weekdays, exact opening bar, first duplicate and
the splice seam are retained; exceptions outside the original fetch catch
remain visible. A raw fetch can advance time, so a session opening during
that operation is visible to the subsequent check.

Daily shape qualification (20 days), session-open eligibility and PSY shape
qualification (7 days) remain distinct. Full build order is daily/ranges,
session opens, preferred hourly PSY with original conditional fallback,
converged hourly/four-hour EMAs, then quarters. Earlier frames are not fetched
again or retroactively updated when time advances.

The existing fixed-T public map and its audit are unchanged. This private
variant is for future actual tree/caller composition, not a replacement API.
Raw ports do not prove publication cutoffs, calendar/feed coverage, full
lifecycle, execution, economic labels, a dataset or training readiness.
No acquisition, live alert, deployment or trading permissions are implied.

Source authority and exact projection: LEVELMAP-OPERATION-CLOCK-CONTRACT.md.
Source-audit CLI: `python -B tools/check_levelmap_operation_source_parity.py
--source-root <parent containing chart-desk>` (single command line).
Independent acceptance: agent-exchange/status/2026-09-10T190902Z-codex-levelmap-operation.md.
344 combined tests passed; full source/dependency audit and task/final reviews
passed. Source-body duplication across fixed/operation variants remains an
explicit maintenance obligation; the combined audit guards both projections.
