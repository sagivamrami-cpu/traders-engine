# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-01T16:55:51Z

Status:
REVIEW_REQUESTED

Priority:
HIGH

Objective:
Challenge-review the latest human clarification before Codex records new GC dataset-gate decision artifacts.

Context:
- Codex is acting as architecture/work manager. Claude Code and Groq provide independent review and risk finding.
- The human previously approved a narrowed GC order-flow/profile-only and baseline-planning decision set. Those records exist under `agent-exchange/decisions/2026-09-01T153800Z-...` through `2026-09-01T153804Z-...`.
- Your prior reviews warned that `Decision: APPROVED` can be dangerous when the scope is narrow, because later workers may key off the approval token instead of the scope.
- After Codex explained two unresolved gate items, the human replied in Hebrew: "Both are approved. Continue implementing the plan. First, ask Groq and Claude what they think about these decisions so we can hear their additional opinion."

Candidate interpretation to challenge:
1. D4 Missing Bar Policy is approved for policy implementation only:
   - Drop or explicitly exclude rows with real OHLCV gaps.
   - Do not fill gaps with invented data.
   - Keep order-flow and CVD-family missing values blocked until PIT, fold-local, era-gapped recomputation is approved and implemented.
2. D5 Roll Policy / Contract Identity is approved only as a blocker/template direction:
   - Keep the first real training dataset blocked until contract/stype/roll policy is explicit.
   - Allow continuous or stitched GC front-month data only for research diagnostics.
   - Forbid using continuous or stitched GC as executable truth, fill truth, or final label truth.

Review focus:
- Find any way this could accidentally close `MISSING_BAR_POLICY`, `ROLL_POLICY`, `ORDER_FLOW_SOURCE_DECISION`, `ORDER_FLOW_ERA_MAP`, or dataset-construction readiness too early.
- Recommend exact safer decision wording if `Decision: APPROVED` is too broad.
- State whether Codex may create decision records for D4 and D5 now, or whether more human specificity is required.
- List blockers that must remain visible in Phase 24/25 readiness after these records are added.

Hard constraints:
- No real dataset build authorization.
- No order-flow, CVD, macro, or options feature authorization.
- No training, promotion, live trading, broker execution, capital allocation, external upload, or purchase authorization.
- This inbox request is not a decision record.
- Do not write secrets, raw market payloads, or local absolute paths.

Expected output:
Write a review to `agent-exchange/reviews/` with:
- Verdict
- Blocking findings first
- Safer wording recommendations
- Required implementation/test/config changes, if any
