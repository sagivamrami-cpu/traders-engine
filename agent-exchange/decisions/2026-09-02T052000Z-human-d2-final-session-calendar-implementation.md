# Human Decision

Approver: Human Data Owner

Created at: 2026-09-02T05:20:00Z

Scope: Approve implementation of `cme-globex-metals-research-v1` as the v1
GC research session calendar. This authorizes Codex to implement and test the
calendar using CME Group public references as the authoritative source family,
with historical GC observations used only as reconciliation evidence.

Decision: APPROVED

Constraints:
- Encode normal Globex metals hours, daily maintenance break, holidays,
  special hours, DST behavior, and required overlays.
- Create a dated overlay/reconciliation table with source attribution.
- Do not use observed activity as schedule authority.
- Do not query Databento `status` schema unless a separate human scope/cost
  approval exists.
- Record a v1 skip decision for Databento `status` schema for this
  implementation path.
- This record does not itself satisfy `SESSION_CALENDAR`; implementation,
  validation, and contract wiring are still required.

Evidence:
- Human approval in active Codex session: "כל הסעיפים מאושרים מבחינתי".
- Human condition in active Codex session: "ניתן להתקדם רק אחרי שקלוד ואתה מסכימים".
- Claude Code review: `agent-exchange/reviews/2026-09-02T051500Z-claude-code-recheck-phase-40-human-decision-packet.md`.
- Codex decision packet: `agent-exchange/inbox/human/2026-09-02T040000Z-human-phase-40-remaining-training-gate-decisions.md`.
