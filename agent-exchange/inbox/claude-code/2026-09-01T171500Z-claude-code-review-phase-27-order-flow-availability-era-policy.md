# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T17:15:00Z

Status:
REVIEW_REQUESTED

Priority:
HIGH

Objective:
Review Phase 27 GC order-flow availability-era policy candidate implementation.

Scope:
- `docs/superpowers/plans/2026-09-01-phase-27-gc-order-flow-availability-era-policy.md`
- `schemas/gc_order_flow_availability_era_policy.schema.json`
- `trading_system/research/gc_order_flow_availability_era_policy.py`
- `tools/inspect_gc_order_flow_availability_era_policy.py`
- `tools/validate_phase27.py`
- `tests/research/test_gc_order_flow_availability_era_policy.py`
- `tests/research/test_phase27_validator.py`
- `docs/implementation-reports/phase-27-gc-order-flow-availability-era-policy.md`

Review focus:
- Verify the policy cannot be consumed as source approval, feature approval, dataset construction authorization, or training readiness.
- Verify `ORDER_FLOW_ERA_MAP` remains unsatisfied via `UNSATISFIED_POLICY_CANDIDATE_ONLY`.
- Verify the file-range regime split around the known 2017 damaged window is correct enough for a policy candidate and does not imply row-level masking is implemented.
- Verify archived `cvd` remains forbidden and cumulative carry requires reset boundaries.
- Check that CLI output is sanitized and cannot leak local paths or raw market rows.

Forbidden assumptions:
- Do not approve order-flow source readiness.
- Do not approve canonical input selection.
- Do not approve row-level masks.
- Do not build features, labels, datasets, or models.
- Do not query vendors or external APIs.
- Do not write secrets, raw rows, local absolute paths, or large artifacts.

Verification command:
- `python tools/validate_phase27.py`

Expected output:
Write review to `agent-exchange/reviews/` with verdict, findings by severity, commands run, and whether Codex may accept Phase 27 as a blocked policy candidate.
