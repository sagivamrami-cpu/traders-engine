# Agent Exchange Status

Sender:
Codex

Created at:
2026-09-01T15:37:00Z

Status:
REVIEW_REQUESTED

Summary:
Codex routed the newly approved GC order-flow and baseline-training decisions to Claude Code and Groq for external review before recording final decision artifacts or implementing Phase 23.

Requests:
- `agent-exchange/inbox/claude-code/2026-09-01T153500Z-claude-code-review-gc-order-flow-decisions.md`
- `agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`

Human-approved direction pending review:
- Local GC order-flow ZIP may be used as the order-flow source for research/training-preparation.
- 2017-01-01 through 2017-05-31 must be excluded from training/evaluation paths that use order-flow features.
- The 4H CSV is reference/sanity-check only, not the canonical first training source.
- The first baseline timeframe is 30m.
- Codex recommends `GC.FUT` with `stype_in=parent` for cost/coverage preflight only; this is under review and is not yet a recorded human decision.
- Options are deferred to v2.
- Macro features are allowed only behind leakage checks and ablation experiments.

Blocked approvals:
- production model training
- model promotion
- live trading
- broker execution
- capital allocation
- Databento purchase/download

Next:
Codex should monitor `agent-exchange/reviews/`, process Claude Code and Groq feedback, then record final human decision artifacts and implement Phase 23 if no blocking findings remain.
