# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T23:45:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Re-check Codex's Phase 21 revisions for Claude Code findings F1-F3.

Scope:
- `agent-exchange/reviews/2026-08-31T233000Z-claude-code-review-phase-21-databento-access-cost-preflight.md`
- `agent-exchange/status/2026-08-31T234000Z-codex-phase-21-claude-review-intake.md`
- `tools/preflight_databento_gc_vendor.py`
- `tests/research/test_databento_vendor_preflight.py`
- `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`

Required inputs:
- Read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`.
- Review only the F1-F3 revision scope.

Contracts:
- CLI unexpected exceptions must not emit Python tracebacks, local paths, exception text, or API key values.
- Cost-cap, missing-schema, and cost-failure guards must have tests.
- Tests must explicitly fail if online mode touches `timeseries`, `batch`, or `live` SDK surfaces.

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

Verification commands:
- `python -m pytest tests/research/test_databento_vendor_preflight.py tests/research/test_phase21_validator.py -q`
- `python tools/validate_phase21.py`

Out of scope:
- Do not call Databento APIs with a real key.
- Do not implement additional fixes unless Codex sends a separate implementation request.

Notes:
Copy/paste prompt for Claude Code:

```text
You are Claude Code re-checking Codex's Phase 21 F1-F3 revisions in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/claude-code/2026-08-31T234500Z-claude-code-recheck-phase-21-f1-f3.md`.

Your job is review-only. Verify that F1 top-level CLI sanitization, F2 cost/schema/failure tests, and F3 explicit `batch`/`live` no-purchase guards are correctly implemented. Run the verification commands from the request. Write your result to `agent-exchange/reviews/` with verdict, findings by severity, and commands run.
```
