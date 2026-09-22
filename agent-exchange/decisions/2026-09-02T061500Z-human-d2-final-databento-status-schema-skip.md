# Human Decision

Approver: Human Data Owner

Created at: 2026-09-02T06:15:00Z

Scope: Skip Databento `status` schema query for the
`cme-globex-metals-research-v1` session-calendar implementation path.

Decision: APPROVED

Constraints:
- Do not query Databento `status` schema for Phase 42.
- Do not use observed activity as schedule authority.
- Use CME Group public references as the authoritative source family for
  normal GC Globex hours.
- Treat the v1 calendar as research-only and not execution truth.
- Keep dataset construction, resampling, model training, promotion, live
  trading, broker execution, and capital allocation blocked.
- Resolve actual missing bars, holiday gaps, and special-hour gaps through the
  later missing-bar policy and dataset manifest gates.

Evidence:
- D2-final calendar implementation decision:
  `agent-exchange/decisions/2026-09-02T052000Z-human-d2-final-session-calendar-implementation.md`.
- Claude Code accepted the Phase 40 human decision packet:
  `agent-exchange/reviews/2026-09-02T051500Z-claude-code-recheck-phase-40-human-decision-packet.md`.
