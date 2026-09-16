# Human Decision

Approver: Human Data Owner

Created at: 2026-09-01T17:10:00Z

Scope: Interpret the human statement "both are approved" as Phase 25 packet D4 only, paired with D5 in the sibling decision record. This record approves a policy-only no-invented-fill direction for OHLCV missing-bar handling. It does not implement row drops, does not choose drop-vs-mark behavior, does not satisfy `MISSING_BAR_POLICY`, and must not remove `MISSING_BAR_POLICY` from `required_unsatisfied_gates`.

Decision: POLICY_ONLY_NO_FILL_NOT_GATE_SATISFIED

Constraints:
- This record does not approve `ORDER_FLOW_SOURCE_DECISION`, `OPTIONS_SOURCE_DECISION`, `ORDER_FLOW_ERA_MAP`, `DATASET_CONSTRUCTION_AUTHORIZATION`, D1-D3, or D6-D9.
- This record must not be cited as evidence for any readiness-checklist `APPROVED` entry.
- OHLCV gap detection remains blocked until session calendar, bar boundary, timestamp role, and `available_at` policy are explicit.
- Future drop-or-mark behavior must be one recorded policy value per feature family, not implementer discretion.
- Future dataset manifests must count and surface excluded or marked rows per split.
- Order-flow volume/delta/trades and CVD-family missing values remain unresolved and blocked until PIT, fold-local, era-gapped recomputation policy exists.
- No `order_flow_optional` v1 training variant is approved.

Evidence: Human approval in the active Codex session on 2026-09-01; Claude Code review `agent-exchange/reviews/2026-09-01T200000Z-claude-code-review-human-clarified-gc-gate-decisions.md`; Groq review `agent-exchange/reviews/2026-09-01T201000Z-groq-review-human-clarified-gc-gate-decisions.md`.
