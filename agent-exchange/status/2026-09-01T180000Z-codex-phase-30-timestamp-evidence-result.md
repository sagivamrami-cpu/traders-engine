# Codex Status

Status:
ACCEPTED_BY_CODEX

Phase:
30

Subject:
GC timestamp evidence collected; D3 decision required

Summary:
Codex implemented and validated a sanitized timestamp-evidence report. The report inspected Parquet schemas and README flags only. It did not emit raw market rows, prices, volumes, local absolute paths, secrets, or vendor payloads.

Evidence:
- OHLCV 1s `ts_event` is `timestamp[ns, tz=UTC]`.
- Order-flow long 1m `minute` is `timestamp[ns]`.
- Order-flow README says the naive timestamps are UTC wall-clock.
- The same README warns that Jan-May 2017 aggressor-side data is damaged/missing.

Resolved human decision:
- `agent-exchange/decisions/2026-09-01T181000Z-human-d3-timestamp-policy-v1.md`
- OHLCV `ts_event` is treated as interval start for the 1s OHLCV archive.
- Order-flow `minute` is treated as minute start.
- Naive long-series order-flow timestamps are localized as UTC wall-clock.

Still blocked:
- `AVAILABLE_AT_POLICY`
- Real resampling
- Order-flow/OHLCV joins
- Dataset construction
- Label building
- Training

Verification:
- `python -m pytest tests\research\test_gc_timestamp_evidence.py -q`: PASS, 3 passed.
- `python -m pytest tests\research\test_phase30_validator.py -q`: PASS, 1 passed.
- `python tools\validate_phase30.py`: PASS, `Phase 30 artifacts validated`.

Commit/push:
Not performed by user instruction.
