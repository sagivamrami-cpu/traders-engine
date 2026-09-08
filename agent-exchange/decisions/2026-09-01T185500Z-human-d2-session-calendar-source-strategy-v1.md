# Human Decision

Decision ID: D2_SESSION_CALENDAR_SOURCE_STRATEGY_V1

Approver: Human Data Owner

Recorded by: Codex

Created at: 2026-09-01T18:55:00Z

Scope: GC CME Globex metals session-calendar source strategy for v1 research.

Decision: APPROVED_SOURCE_STRATEGY_V1_NOT_CALENDAR_AUTHORIZATION

Approved Strategy:
- Build an observed-activity calendar profile from the already-licensed historical GC 1s archive as the first zero-cost evidence leg.
- Use official CME GC/Globex documents as the authoritative public reference for product scope, current hours, holidays, and maintenance/session definitions.
- Use Databento `status` schema only after a separate cost/source approval confirms schema availability, historical era coverage, and query cost.
- Do not use TradingView as authoritative evidence for session-calendar membership; it may be used only as an informal visual sanity check.
- Require an era-versioned calendar. Every historical era must carry evidence. Eras without evidence remain `UNVERIFIED_HISTORICAL` and cannot receive guessed session membership.
- Distinguish scheduled closures from observed venue/data gaps. Any disagreement between observed activity, Databento status, and CME documentation must become an explicit overlay/review item.

Allows:
- D2 source-strategy policy artifacts.
- Sanitized aggregate observed-activity profiling from already-licensed local GC 1s data.
- Preparation of a future Databento `status` request for separate human approval.

Does Not Approve:
- No Databento API query.
- No new data purchase.
- No session-calendar registration for production use.
- No real bar resampling.
- No missing-bar fill/drop/mark implementation.
- No dataset construction.
- No feature build.
- No label build.
- No model training.
- No model promotion.
- No live trading.
- No broker execution.
- No capital allocation.

Evidence:
- `agent-exchange/inbox/human/2026-09-01T185000Z-human-d2-session-calendar-source-strategy.md`
- Human response: `מאשר`
- `agent-exchange/reviews/2026-09-01T224500Z-claude-code-review-d1-d3-intake-and-d2-calendar-recommendation.md`
- `agent-exchange/reviews/2026-09-01T231500Z-claude-code-groq-takeover-d1-d3-d2-challenge-review.md`
- `agent-exchange/status/2026-09-01T184500Z-codex-claude-d1-d3-d2-review-intake.md`
