# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-01T00:00:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Re-check Codex's Phase 21 hardening after Groq's blocking review.

Scope:
- `agent-exchange/reviews/2026-08-31T233500Z-groq-review-phase-21-databento-access-cost-preflight.md`
- `agent-exchange/status/2026-08-31T235800Z-codex-phase-21-groq-review-intake.md`
- `configs/data/databento-gc-vendor-preflight.yaml`
- `schemas/databento_gc_vendor_preflight.schema.json`
- `trading_system/research/databento_vendor_preflight.py`
- `tools/preflight_databento_gc_vendor.py`
- `tools/validate_phase21.py`
- `tests/research/test_databento_vendor_preflight.py`
- `configs/data/databento-gc-contract-stype-decision-template.yaml`
- `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`

Required inputs:
- Read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`.
- Review only the Phase 21 hardening relative to the prior Groq findings.

Contracts:
- `GC` remains only a canonical research token, not a proven Databento dated/parent/continuous contract identity.
- Statuses must not use `READY` or positive `AVAILABLE` wording for Phase 21 success paths.
- MBO must remain reference-only and not a purchase candidate.
- One-day estimates must be labeled sample-only, not interval coverage or budget.
- XAUUSD/GLD aliases must remain rejected.
- Options parent query must remain blocked.
- The CLI must block real online cost-estimate calls until a separate contract/stype decision exists.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no Databento data download or purchase
- no `timeseries.get_range`

Deliverables:
- Write a re-check review under `agent-exchange/reviews/`.
- Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.
- Include commands run and pass/fail results.
- State whether Phase 21 may be accepted as a blocked metadata/cost planner before a contract/stype decision and real-key online run.

Verification commands:
- `python -m pytest tests/research/test_databento_vendor_preflight.py tests/research/test_phase21_validator.py -q`
- `python tools/validate_phase21.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:
- Do not approve order-flow or options source decisions.
- Do not call Databento APIs with a real key.
- Do not change repo files.

Notes:
Copy/paste prompt for Groq:

```text
You are Groq re-checking Phase 21 hardening in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/groq/2026-09-01T000000Z-groq-recheck-phase-21-databento-hardening.md`.

Your job is review-only. Check whether Codex resolved your prior blocking findings: GC/stype identity must stay pending, status values must not imply READY/AVAILABLE approval, MBO must be reference-only and not a purchase candidate, the one-day window must be sample-only, XAUUSD/GLD aliases must be rejected, options parent query must remain blocked, and the CLI must block real online calls until a contract/stype decision exists. Run the listed verification commands if available. Write your result to `agent-exchange/reviews/` with verdict, findings by severity, and commands run.
```
