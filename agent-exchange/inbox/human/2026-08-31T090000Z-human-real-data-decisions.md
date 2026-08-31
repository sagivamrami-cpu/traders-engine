# Agent Exchange Request

Target:
Human

Sender:
Codex

Created at:
2026-08-31T09:00:00Z

Status:
NEEDS_HUMAN_APPROVAL

Objective:
Provide the real-data inputs and explicit human decisions required before the
project can move from fixture/synthetic readiness into real research data
preparation.

Scope:
- `configs/research/real-data-readiness-checklist.yaml`
- `docs/implementation-reports/phase-12-real-data-readiness-checklist.md`
- `docs/implementation-reports/phase-13-local-csv-inspection.md`
- `tools/inspect_local_ohlcv_csv.py`
- `tools/onboard_ohlcv_csv.py`
- `tools/validate_local_source_bundle.py`
- `tools/run_local_csv_dry_run.py`
- `tools/real_data_readiness.py`
- `agent-exchange/decisions/`

Required inputs:
- A local path to the first real historical OHLCV CSV or approved vendor export.
- The first canonical instrument/symbol to research.
- The first historical date interval to research.
- A production OHLCV vendor approval or an explicit local-only decision.
- A raw-data storage root, retention duration, and license decision.
- An order-flow source approval or explicit defer decision.
- An options source approval or explicit defer decision.

Contracts:
- Human decisions must be recorded under `agent-exchange/decisions/`.
- Each decision record must include approver, timestamp, scope, decision, and
  evidence.
- Do not place secrets, broker credentials, account data, private identifiers,
  raw market-data payloads, or large generated artifacts in `agent-exchange/`.
- A local file path can be referenced, but raw CSV contents should remain
  outside `agent-exchange/`.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no broker credentials or secrets in the repository

Deliverables:
- One or more decision records under `agent-exchange/decisions/` covering:
  - `REAL_HISTORICAL_OHLCV_CSV`
  - `PRODUCTION_OHLCV_VENDOR_DECISION`
  - `FIRST_REAL_SYMBOL`
  - `FIRST_HISTORICAL_INTERVAL`
  - `RAW_DATA_STORAGE_LICENSE_APPROVAL`
  - `ORDER_FLOW_SOURCE_DECISION`
  - `OPTIONS_SOURCE_DECISION`
- Local CSV location supplied outside this inbox file.
- Evidence references for each approval or defer decision.

Verification commands:
- `python tools/real_data_readiness.py`
- `python tools/inspect_local_ohlcv_csv.py --input <local_csv_path>`
- `python tools/onboard_ohlcv_csv.py --help`
- `python tools/validate_local_source_bundle.py --help`
- `python tools/run_local_csv_dry_run.py --help`

Out of scope:
- Live trading approval.
- Broker execution approval.
- Capital allocation approval.
- Model promotion approval.
- Deployment approval.

Notes:
Until these decisions exist, the system must stay blocked for production
dataset construction and production model training.
