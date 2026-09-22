# Pinned daily/weekly/monthly range dependency subset

`trading_system.tree_replay._vendor.ranges` contains the original pure
daily_pivots, average_range, range_hilo, weekly_from_daily, monthly_from_daily and
tr_levels functions. `_vendor.back_days` contains BACK_DAYS/_back_day_levels.
They are exact source subsets, not a historical data loader or complete level map.
chart-desk commit:68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.

## Calculation contract

For source period frames, the final row represents the current period and is
excluded from the historical average. average_range projects mean prior H-L from
the current low/high, or symmetrically around current open in from_open mode.
range_hilo delegates to the same formula: RD/RW are not rolling extrema.
The defaults are ADR14 daily periods, RD15, AWR4 weekly periods, RW13, AMR6 monthly
periods. Insufficient history remains unavailable; zero range gives null used_pct.

weekly_from_daily and monthly_from_daily shift daily timestamps forward3h for
bucket assignment before resampling with W/MS. This preserves the original
Sunday-evening and month-boundary behavior; these bucket labels are not new
observation/publication timestamps. Retain causal times separately.

tr_levels preserves its actual source warmup gates and verification asymmetries,
including lweek inside the available AWR branch and monthly calls without the
broker_bars argument. A caller-supplied broker_bars flag is not independent proof
of feed shape or instrument identity. Actual source broker/proxy/splice evidence
and source map consumption rules must be connected before emitting usable levels.

daily_pivots is retained only because tr_levels calls it. Its presence does not
add floor/M pivots to the live map: the source levelmap deliberately excludes
that family. _back_day_levels preserves the five-row minimum, D2..D4 ordering
and offsets relative to the final current-period row.

## Causal inputs and limitations

Daily OHLC inputs can be reconstructed from supplied DailyPeriod/calendar/bar
evidence as described in DAILY-PERIOD-ASOF-USAGE.md. Every contributing period
must be usable at the same decision time; final daily high/low cannot replace the
current period's running values. The dependency integration test hand-checks
prior ranges10/20 with running current O100/H115/L95/C110: mean15, moving rails
110/100 and open-anchored rails107.5/92.5; a future high1000 has no effect.

These pure functions themselves do NOT validate arbitrary DataFrames, enforce
point-in-time coverage, check numerical overflow, construct period sequences,
apply real broker corrections or guarantee JSON-safe features. Consumers still
need those checks. No producer admission, simulation, label or training view is
created. Both auditor readiness flags stay false, including after parity passes.

## Verification and portability

Run `python -m pytest tests/tree_replay/test_range_source.py -q`,
`python -m pytest tests/tree_replay/test_period_range_integration.py -q`, and
`python tools/check_range_source_parity.py --source-root <pinned-chart-desk>`.

The CLI accepts explicit --source-root; otherwise it uses TR_CHARTDESK_SOURCE_ROOT
and then the retained local default. The range tests honor the same environment
override. On another machine configure a retained copy of the pinned source.
Missing source is a failure, not a skipped audit. No network clone is automatic.

The auditor pins full Git blob identities, exact selected functions/constants,
imports and ordered vendor ASTs independently of the manifest. It checks the
baseline commit and rejects source/vendor/contract mutations. Only source text
and ASTs are read; the original live source package is never executed.
