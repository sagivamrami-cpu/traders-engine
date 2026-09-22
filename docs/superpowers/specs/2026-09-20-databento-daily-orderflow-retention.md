# Databento daily Order Flow retention

## Goal

Retain causal raw Order Flow evidence every UTC day for the three instruments
traded by the TR channel: gold, Nasdaq and Bitcoin. The feed is confirmation
evidence. It never replaces the target instrument's price, entry, stop, target
or fill source.

## Identity map

| TR target | Databento context | request symbol |
|---|---|---|
| `OANDA:XAUUSD` | `CME:GC` | `GC.v.0` |
| `OANDA:NAS100USD` | `CME:NQ` | `NQ.v.0` |
| `BINANCE:BTCUSDT` | `CME:BTC` | `BTC.v.0` |

All requests use `DATABENTO/GLBX.MDP3`, `stype_in=continuous`. Continuous
symbols map to the actual volume-leading contract without back-adjusting its
prices. Every manifest retains the requested context and target identities.

## Retained evidence

For every asset and closed UTC day, retain:

- `trades` DBN: every trade print required to reconstruct volume, aggressor
  delta, footprint and tape speed;
- `mbp-10` DBN: every top-ten market-by-price update required to reconstruct
  historical DOM state;
- a manifest containing request parameters, UTC coverage, byte length,
  SHA-256, record count, API/client version and acquisition time;
- a day status ledger covering successes, skips and explicit blockers.

Raw DBN is authoritative. Derived summaries may be added later and must be
reproducible from the pinned raw bytes. MBO/L3 is excluded from this first daily
collector because footprint plus DOM requires trades plus MBP-10; an MBO stream
would multiply storage and cost and is not needed to satisfy this evidence
contract.

## Safety and operation

- Default collection date is the previous UTC date. An incomplete current day
  is refused unless an explicit research override is supplied.
- Estimate cost before any download. Refuse the whole requested day when the
  total exceeds the configured daily USD cap; do not create a partial set.
- Write to a temporary file, validate DBN metadata (zero records are legitimate
  on a closed market day), hash it, then
  atomically publish it. A valid existing artifact is idempotently skipped.
- The API key is read only from `DATABENTO_API_KEY`; it is never logged or
  written to a file.
- Raw data lives under ignored `market-data/`; only code, policy and tests may
  enter Git.
- A Windows scheduled task runs daily at 03:30 Asia/Jerusalem and requests the
  previous UTC day. Missed-start execution is enabled.

## Acceptance

Tests prove symbol/schema requests, cost-first refusal, missing-key behavior,
current-day refusal, atomic writes, hash verification, idempotency and complete
six-artifact daily membership. A live attempt must produce either a complete
verified day or an explicit blocked status; it must never silently pass.
