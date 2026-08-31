# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-08-31T09:00:00Z

Status:
REVIEW_ONLY

Objective:
Review Phases 8-13 and the new `agent-exchange/` workflow for contradictions,
unsafe assumptions, missing edge cases, and unclear handoffs before real-data
decision intake continues.

Scope:
- `AGENTS.md`
- `agent-exchange/README.md`
- `agent-exchange/protocol.md`
- `docs/implementation-reports/phase-8-local-csv-onboarding.md`
- `docs/implementation-reports/phase-9-local-csv-research-dry-run.md`
- `docs/implementation-reports/phase-10-raw-data-retention-policy.md`
- `docs/implementation-reports/phase-11-local-source-bundle-validation.md`
- `docs/implementation-reports/phase-12-real-data-readiness-checklist.md`
- `docs/implementation-reports/phase-13-local-csv-inspection.md`
- `configs/data/local-csv-onboarding-template.yaml`
- `configs/research/real-data-readiness-checklist.yaml`
- `schemas/local_csv_inspection_report.schema.json`
- `schemas/real_data_readiness_report.schema.json`
- `schemas/source_bundle_validation.schema.json`
- `tools/inspect_local_ohlcv_csv.py`
- `tools/onboard_ohlcv_csv.py`
- `tools/validate_local_source_bundle.py`
- `tools/run_local_csv_dry_run.py`
- `tools/real_data_readiness.py`
- `tests/data_foundation/`
- `tests/research/`

Required inputs:
- Current branch `plan/tree-to-trained-model-langgraph`.
- Phase 8-13 implementation reports.
- Agent-exchange protocol and role boundaries.

Contracts:
- This is a review/scenario-generation task only.
- Groq should not edit files, approve data, approve promotion, or decide
  architecture.
- Findings should be written as a markdown review file under
  `agent-exchange/reviews/`.
- Each finding should include severity, source file/path, observed issue, risk,
  and suggested follow-up.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no secrets or raw market data in the review

Deliverables:
- Review of whether Phases 8-13 preserve the human-approval boundary.
- Edge cases for local CSV inspection, onboarding, source bundle validation,
  and dry-run execution.
- Contradictions or gaps in `agent-exchange/` workflow.
- Recommendations for Phase 14 acceptance tests.
- Explicit statement if no blocking issues are found.

Verification commands:
- `python tools/real_data_readiness.py`
- `python tools/inspect_local_ohlcv_csv.py --help`
- `python tools/onboard_ohlcv_csv.py --help`
- `python tools/validate_local_source_bundle.py --help`
- `python tools/run_local_csv_dry_run.py --help`
- `python -m pytest tests/data_foundation tests/research -v`

Out of scope:
- Code changes.
- Merging.
- Commit/push.
- Human approval.
- Production model training.

Notes:
Prioritize fast contradiction-finding and adversarial scenarios. Codex will
make acceptance and routing decisions after reviewing the output.
