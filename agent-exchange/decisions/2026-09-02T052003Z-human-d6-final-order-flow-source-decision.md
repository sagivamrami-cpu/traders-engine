# Human Decision

Approver: Human Data Owner

Created at: 2026-09-02T05:20:03Z

Scope: Approve the local licensed Databento GC order-flow archive as the v1
research order-flow feature source, bounded to the selected non-CVD 1m member
and non-cumulative feature columns.

Decision: APPROVED

Policy:
- Selected member: `gc/GCext_of_1m.parquet`.
- Allowed columns: `volume`, `delta`, `trades`, `minute`.
- Forbidden columns/features: `cvd`, cumulative delta, precomputed cumulative
  state, and cross-fold cumulative carry.
- Required exclusion: drop the 2017 damaged aggressor-side window from all
  order-flow training rows.

Constraints:
- Dataset construction remains blocked until all remaining readiness gates are
  satisfied.
- CVD and cumulative-delta features remain blocked for v1.
- This record does not approve options, macro, XAUUSD/GLD proxy mapping,
  production promotion, live trading, broker execution, or capital allocation.

Evidence:
- Human approval in active Codex session: "כל הסעיפים מאושרים מבחינתי".
- Human condition in active Codex session: "ניתן להתקדם רק אחרי שקלוד ואתה מסכימים".
- Claude Code review: `agent-exchange/reviews/2026-09-02T051500Z-claude-code-recheck-phase-40-human-decision-packet.md`.
- Codex decision packet: `agent-exchange/inbox/human/2026-09-02T040000Z-human-phase-40-remaining-training-gate-decisions.md`.
- Canonical order-flow input manifest: `configs/data/gc-canonical-order-flow-input-manifest.yaml`.
- Row-mask/cumulative policy: `configs/data/gc-order-flow-row-mask-cumulative-policy.yaml`.
