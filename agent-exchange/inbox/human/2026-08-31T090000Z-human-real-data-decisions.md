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
- `configs/data/real-ohlcv-source-metadata-template.yaml`
- `docs/implementation-reports/phase-12-real-data-readiness-checklist.md`
- `docs/implementation-reports/phase-13-local-csv-inspection.md`
- `docs/implementation-reports/phase-17-human-real-ohlcv-intake-packet.md`
- `docs/implementation-reports/phase-18-real-source-onboarding-preflight.md`
- `tools/prepare_real_ohlcv_intake.py`
- `tools/preflight_real_source_onboarding.py`
- `tools/real_data_readiness.py`
- `agent-exchange/templates/human-decision-record.md`
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
- A local file path can be supplied to local CLI arguments outside
  `agent-exchange/`, but it must not be written into exchange files.
- Use `agent-exchange/templates/human-decision-record.md` only as a starting
  point. The template itself is not an approval record.
- Use `configs/data/real-ohlcv-source-metadata-template.yaml` for source
  metadata, replacing every `UNSET_` sentinel before real intake.
- The intake CLI output is sanitized and redacts local paths, but it is still
  not approval for production dataset construction, production model training,
  model promotion, live trading, broker execution, or capital allocation.
- The preflight CLI output is also sanitized. Phase 18 is report-only: even
  when all records are present, it does not authorize local manifest creation,
  source-bundle validation, production dataset construction, production model
  training, model promotion, live trading, broker execution, or capital
  allocation.
- Do not paste output from lower-level inspect, onboard, bundle, or dry-run
  tools into `agent-exchange/`; those tools are not the human exchange intake
  surface.

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
- `python tools/prepare_real_ohlcv_intake.py --csv <local_csv_path> --metadata <metadata_yaml_path>`
- `python tools/preflight_real_source_onboarding.py --csv <local_csv_path> --metadata <metadata_yaml_path> --decisions <decisions_yaml_path>`
- `python tools/validate_phase17.py`
- `python tools/validate_phase18.py`

Out of scope:
- Live trading approval.
- Broker execution approval.
- Capital allocation approval.
- Model promotion approval.
- Deployment approval.

Notes:
Until these decisions exist, the system must stay blocked for production
dataset construction and production model training.
