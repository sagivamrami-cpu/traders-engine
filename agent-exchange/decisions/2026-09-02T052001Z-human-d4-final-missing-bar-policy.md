# Human Decision

Approver: Human Data Owner

Created at: 2026-09-02T05:20:01Z

Scope: Approve v1 fail-closed missing-bar handling for the first real GC 30m
research dataset.

Decision: APPROVED

Policy:
- OHLCV gaps exclude affected 30m rows from all training variants.
- Order-flow `volume`, `delta`, and `trades` gaps exclude affected rows from
  the order-flow training variant.
- No v1 `order_flow_optional` fallback variant is approved.
- No forward-fill or invented values are allowed for price, volume, delta,
  trades, labels, or execution truth.
- Dataset manifests must emit row-exclusion counts by reason and split.

Constraints:
- This record authorizes implementation of deterministic missing-bar exclusion
  after the session calendar exists.
- This record does not itself satisfy `MISSING_BAR_POLICY`; implementation,
  validation, and contract wiring are still required.

Evidence:
- Human approval in active Codex session: "כל הסעיפים מאושרים מבחינתי".
- Human condition in active Codex session: "ניתן להתקדם רק אחרי שקלוד ואתה מסכימים".
- Claude Code review: `agent-exchange/reviews/2026-09-02T051500Z-claude-code-recheck-phase-40-human-decision-packet.md`.
- Codex decision packet: `agent-exchange/inbox/human/2026-09-02T040000Z-human-phase-40-remaining-training-gate-decisions.md`.
