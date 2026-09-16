# Human Decision

Approver: Human Data Owner

Created at: 2026-09-02T05:20:06Z

Scope: Approve the dataset-construction authorization rule for the first real
GC 30m research dataset. This is a conditional rule, not immediate permission
to build a dataset.

Decision: APPROVED

Policy:
- Dataset construction may proceed only after a future readiness run shows
  every pretraining gate satisfied, including `SESSION_CALENDAR`,
  `MISSING_BAR_POLICY`, `ROLL_POLICY`, `DATASET_IDENTITY`,
  `ORDER_FLOW_SOURCE_DECISION`, `LABEL_CONTRACT`, and
  `SPLIT_AND_EMBARGO_POLICY`.
- The construction decision record must bind to the assembled dataset-identity
  manifest and its deterministic hash.
- Authorization is for one identified dataset build, not a broad category of
  future datasets.
- Dataset construction must use the tested order-flow exclusion function:
  `trading_system.research.gc_order_flow_row_mask_cumulative_policy.apply_gc_order_flow_training_mask`.

Constraints:
- This record does not itself satisfy `DATASET_CONSTRUCTION_AUTHORIZATION`.
- This record does not authorize training until the real dataset is built and
  the training-readiness gate passes.
- This record does not approve production model promotion, live trading,
  broker execution, or capital allocation.

Evidence:
- Human approval in active Codex session: "כל הסעיפים מאושרים מבחינתי".
- Human condition in active Codex session: "ניתן להתקדם רק אחרי שקלוד ואתה מסכימים".
- Claude Code review: `agent-exchange/reviews/2026-09-02T051500Z-claude-code-recheck-phase-40-human-decision-packet.md`.
- Codex decision packet: `agent-exchange/inbox/human/2026-09-02T040000Z-human-phase-40-remaining-training-gate-decisions.md`.
