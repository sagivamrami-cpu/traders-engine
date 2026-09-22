# Daily Order Flow evidence for the TR channel

The collector retains six raw Databento files for every closed UTC day: trades
and MBP-10 for GC, NQ and CME Bitcoin. Trades are the source for footprint,
aggressor delta and tape-speed calculations; MBP-10 is the source for the ten
visible DOM levels. Raw DBN stays private under `market-data/` with SHA-256 and
request provenance in a per-day manifest.

The target instruments remain `OANDA:XAUUSD`, `OANDA:NAS100USD` and
`BINANCE:BTCUSDT`. CME futures are confirmation context only. The collector
does not map futures prices into target entries, stops, targets or P&L.

Run the previous closed UTC day:

```powershell
py -3 tools/collect_databento_orderflow.py --data-root C:\Users\roeea\sagiv-repos\traders-engine\market-data\databento-orderflow-daily
```

Backfill a closed interval:

```powershell
py -3 tools/collect_databento_orderflow.py --start 2026-08-30 --end 2026-09-19 --data-root C:\Users\roeea\sagiv-repos\traders-engine\market-data\databento-orderflow-daily
```

The command requires `DATABENTO_API_KEY` in the process or user environment.
It estimates all six request costs before downloading and refuses the entire
day above the configured cap. Missing credentials, cost refusal and network
failure are written to `status/YYYY-MM-DD.json`; they are not reported as
successful collection.

Install the daily 03:30 Israel-time task with:

```powershell
powershell -ExecutionPolicy Bypass -File tools/install_orderflow_daily_task.ps1
```
