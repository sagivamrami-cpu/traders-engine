# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T23:00:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Review the Phase 21 Databento access/cost preflight implementation for integration correctness, missing tests, and hidden approval risk.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-21-databento-access-cost-preflight.md`
- `configs/data/databento-gc-vendor-preflight.yaml`
- `schemas/databento_gc_vendor_preflight.schema.json`
- `trading_system/research/databento_vendor_preflight.py`
- `tools/preflight_databento_gc_vendor.py`
- `tools/validate_phase21.py`
- `tests/research/test_databento_vendor_preflight.py`
- `tests/research/test_phase21_validator.py`
- `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`

Required inputs:
- Read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md` before review.
- Treat the human-provided Databento API key as secret; do not ask Codex to write it to a file.

Contracts:
- Offline and missing-key paths must not import or require the Databento SDK.
- Online mode may use only `metadata.get_dataset`, `metadata.list_schemas`, `symbology.resolve`, and `metadata.get_cost`.
- Reports must not serialize API key values, local absolute paths, account IDs, or raw market data.
- Readiness must remain `BLOCKED`; no decision record may be marked satisfied by this review.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no Databento data download or purchase
- no `timeseries.get_range`

Deliverables:
- Write a review file under `agent-exchange/reviews/`.
- Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.
- Findings must be ordered by severity.
- Include exact commands run and pass/fail results.
- Include patch recommendations for any issue found.

Verification commands:
- `python -m pytest tests/research/test_databento_vendor_preflight.py tests/research/test_phase21_validator.py -q`
- `python tools/validate_phase21.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:
- Do not implement fixes unless Codex explicitly routes an implementation task.
- Do not call Databento APIs with a real key.
- Do not change human decision records.

Notes:
Copy/paste prompt for Claude Code:

```text
You are Claude Code reviewing Phase 21 in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/claude-code/2026-08-31T230000Z-claude-code-review-phase-21-databento-access-cost-preflight.md`.

Your job is to review, not implement. Focus on integration correctness, missing tests, secret/path leakage, and hidden approval risk. Confirm the offline and missing-key paths do not require Databento SDK; confirm online mode only uses metadata/symbology/get_cost and never `timeseries.get_range`, batch, live, or download APIs. Run the verification commands listed in the request if available. Write your result to `agent-exchange/reviews/` with verdict `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`, findings by severity, commands run, and any patch recommendations.
```
