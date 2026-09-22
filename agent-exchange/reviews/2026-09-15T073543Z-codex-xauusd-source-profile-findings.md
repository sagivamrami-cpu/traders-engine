# XAUUSD source profile — evidence and recommendations

Reviewer: Codex

Target request: `agent-exchange/inbox/human/2026-09-15T065418Z-human-xauusd-source-profile-required.md`

Created at: 2026-09-15T07:35:43Z

Status: REVIEW_READY_FOR_CODEX

Verdict: Some XAUUSD data already exists locally. Full historical input coverage,
price-source equivalence and executed order-flow semantics are not established.
The previous assertion that progress requires humans to supply every technical
profile field was too broad: Codex can investigate those fields now.

## Local evidence (read-only)

Inspected sibling repositories and existing dataset manifests. The source-file
names below are evidence of local content, not certification of provenance.
TV timestamps are as stored, without an explicit offset in these files.

| Local source | Observed extent | Limitation |
| --- | --- | --- |
| chart-desk/data/tv/XAUUSD_M5.csv | 3,355 rows; 2026-08-11 13:20 to 2026-08-27 17:10 | Short history |
| chart-desk/data/tv/XAUUSD_M15.csv | 1,323 rows; 2026-08-07 08:45 to 2026-08-27 17:15 | Short history |
| chart-desk/data/tv/XAUUSD_M30.csv | 359 rows; 2026-08-17 23:00 to 2026-08-27 17:00 | Short history |
| chart-desk/data/tv/XAUUSD_H1.csv | 536 rows; 2026-07-27 10:00 to 2026-08-27 16:00 | Short history |
| chart-desk/data/tv/XAUUSD_H4.csv | 367 rows; 2026-06-03 05:00 to 2026-08-27 13:00 | Short history |
| chart-desk/data/tv/XAUUSD_D1.csv | 311 rows; 2025-06-15 21:00 to 2026-08-26 21:00 | About a year, not ten years |
| chart-desk/data/duka/candles/XAUUSD | 139 monthly filenames; BID_hour_201501 through BID_hour_202607 | Filenames only; contents/completeness not audited; different provider |
| chart-desk/data/orderflow/XAUUSD_1min.parquet | 259,395 rows; ts min 2025-08-25 17:00Z, max 2026-08-23 23:59Z | Dukascopy-derived; execution-volume semantics not validated |
| news-desk/data/ff_calendar.json | 96 events, 2026-08-16 through 2026-08-21 as stored | One calendar interval; no historical revision archive demonstrated |

The TV files expose `time,open,high,low,close,volume` and no `src` column.
First/last CSV rows and Parquet timestamp extrema do not prove continuity,
correct source labels, point-in-time publication or full historical coverage.
Options history/live files exist, but a decade of synchronized historical GLD
chains/OI/quotes has not been demonstrated by this inspection.

The older GC build manifest reports 104,212,803 source 1s rows and GC order-flow
inputs. It remains GC evidence, not proof of XAUUSD coverage.

## Source identity and provider recommendation

Prefer the chart's actual OANDA source for price fidelity. Investigate OANDA's
historical API first, comparing overlapping bars with the existing TV captures
before treating it as equivalent. `chartdesk/basis.py` prefers TV CSVs, then MT5,
and also contains proxy/splice routes; the instrument label alone does not prove
which physical feed supplied a historical calculation.

OANDA documents that historical candles can differ from account-specific live
pricing because historical candles use a base pricing group:
https://help.oanda.com/us/en/faqs/rest-v20-api-troubleshooting-guide.htm

OANDA candle definitions expose opening time, bid/ask/mid OHLC, completion and a
`volume` count of prices. That volume is not an executed-trade tape:
https://developer.oanda.com/rest-live-v20/instrument-df/

Exact historical reach, XAU instrument entitlement, price basis and candle
alignment still need evidence. No purchase, authenticated request or download
was performed during this investigation.

## Material semantic issue: Dukascopy order flow

The sibling `chartdesk/orderflow.py` describes `ask_vol - bid_vol` as executed
aggressor delta. Its `ticks_to_minutes` consumes fields decoded by `duka.py`.
Dukascopy's ITick documentation defines ask/bid volume as available size at the
best quoted prices:
https://www.dukascopy.com/client/javadoc/com/dukascopy/api/ITick.html

Therefore the existing name/comment does not establish an executed-buy-minus-
executed-sell measurement. Validate the exact BI5 feed fields and ingestion
lineage before approving Delta/CVD training features. This is a source-semantic
finding, not a runtime fix or a complete audit of that module.

## All branches and source-faithful behavior

`trading_system/tree_replay/_vendor/optionswall.py` explicitly maps XAUUSD to GLD
options context, uses a synchronized TV anchor and rejects stale/unsuitable
evidence. The age limit is 45 minutes. `tree_walk.py` treats this context as
optional, whereas failure to read the news calendar stops the walk.

Consequences of the new full-information target:
- A documented GLD context mapping is distinct from replacing XAUUSD prices with
  GC prices. Avoid the earlier blanket statement that all proxies are forbidden.
- Joint usable history is the intersection of each branch's valid coverage and
  freshness windows. Market hours differ; the longest price archive alone cannot
  determine the training interval.
- A verified empty event list/no vector is a valid answer, unlike a missing feed.
- Keep original replay decisions and coverage eligibility separately observable.
  Excluding incomplete samples changes the research population; report excluded
  periods/reasons and measure resulting selection bias.
- Requiring every source to veto every live entry would be a versioned strategy
  change. That behavior has not been implemented.

## Engineering choices Codex can own

- Internal UTC; Israel display via Asia/Jerusalem, not fixed UTC+3.
- Explicit bar start/end, observed interval, and availability evidence. A 10:00
  5m candle's final close/high/low cannot be consumed at 10:02. A forming higher
  bar can use the available closed-base prefix, as in the existing replay design.
- Preserve source timestamps and distinguish actual publication from a declared
  historical availability assumption. A download timestamp is not historical
  publication evidence.
- Store versioned source metadata, instrument, timeframe, price basis, timezone,
  acquisition time, coverage, transformation version and SHA-256 per artifact.
  SHA-256 detects byte changes; it does not prove the vendor's data was correct.
- Determine revision policy from provider documentation/evidence; user should
  not be expected to invent it.

## Next actions and remaining human input

Codex can continue offline coverage/provenance audits and public provider
research. Exact adapters and labels require the resulting source contracts;
full-tree provider/capture independent reviews also remain pending.

Needed from the team when access is necessary: whether an OANDA/API account or
historical export is already available (no credentials in chat). Needed from
Sagiv: the actual market/feed used for the intended executed Order Flow signal,
especially if it differs from the current Dukascopy quote-size calculation.

Verification reviewed: PowerShell CSV row/column/extents inspection, JSON
calendar count/dates, Parquet ts-only scan with PyArrow min/max, local source
reading and official provider documentation. No runtime files modified or tests
claimed. Earlier exploratory schema/PowerShell aggregation errors were corrected
before the tabulated findings were recorded.
