# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T09:00:00Z

Status:
ACTIONABLE

Objective:
Implement Phase 14: real-data decision intake. The goal is to let the project
read a human-maintained decision/evidence file and reflect satisfied readiness
items in a report without implying production approval by default.

Scope:
- `configs/research/real-data-readiness-checklist.yaml`
- new `configs/research/real-data-decisions-template.yaml`
- `schemas/real_data_readiness_report.schema.json`
- new `schemas/real_data_decisions.schema.json`
- `trading_system/research/readiness.py`
- `tools/real_data_readiness.py`
- new `tools/validate_phase14.py`
- `tests/research/test_real_data_readiness.py`
- new `tests/research/test_phase14_validator.py`
- new `docs/superpowers/plans/2026-08-31-phase-14-real-data-decision-intake.md`
- new `docs/implementation-reports/phase-14-real-data-decision-intake.md`

Required inputs:
- Existing Phase 12 readiness checklist.
- Existing Phase 13 local CSV inspection output contract.
- Existing agent-exchange approval boundary in `AGENTS.md` and
  `agent-exchange/protocol.md`.

Contracts:
- A decision file may satisfy only known checklist `item_id` values.
- Each satisfied item must include approver, timestamp, decision, scope, and
  evidence.
- Unknown item ids must fail validation.
- Missing approval evidence must fail validation.
- Open checklist items remain blocked.
- The default repository state must remain blocked because no human decisions
  are committed by default.
- Fixture and synthetic data must not satisfy real-data readiness.
- No raw CSV data or secrets may be written to the repo.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no automatic vendor approval
- no mutation of the Phase 12 checklist to mark items satisfied by default
- no committed production credentials, raw data, broker identifiers, or account
  information

Deliverables:
- Tests first for valid decisions, missing evidence, unknown item ids, default
  blocked behavior, and schema validation.
- Decision schema and template.
- Readiness loader/report update that can optionally merge a decision file.
- CLI support in `tools/real_data_readiness.py` for an optional decisions file.
- Phase 14 validator.
- Phase 14 implementation report.
- Any design notes needed by Codex for acceptance.
- Completion result under `agent-exchange/status/` using
  `agent-exchange/templates/result.md` with status
  `IMPLEMENTED_AWAITING_CODEX_REVIEW`.

Verification commands:
- `python -m pytest tests/research/test_real_data_readiness.py -v`
- `python -m pytest tests/research/test_phase14_validator.py -v`
- `python tools/validate_phase12.py`
- `python tools/validate_phase13.py`
- `python tools/validate_phase14.py`
- `python tools/real_data_readiness.py`
- `python tools/real_data_readiness.py --decisions configs/research/real-data-decisions-template.yaml`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research -v`

Out of scope:
- Fetching market data from a vendor.
- Storing raw market data.
- Training a production model.
- Backtesting, shadow trading, paper trading, live trading, broker execution,
  or capital allocation.
- Deciding that any data source is production-approved.

Notes:
Use the repo's existing dataclass, schema-validation, CLI, and validator
patterns. Keep the default `real-data-decisions-template.yaml` explicitly
non-approving; it should demonstrate required fields without satisfying real
readiness unless a human creates a separate decision record.

Codex watches `agent-exchange/status/`, `agent-exchange/reviews/`, and
`agent-exchange/decisions/` with `python tools/watch_agent_exchange.py` while
waiting for tool outputs.
