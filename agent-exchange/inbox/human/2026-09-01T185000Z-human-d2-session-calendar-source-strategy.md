# Agent Exchange Request

Target:
Human

Sender:
Codex

Created at:
2026-09-01T18:50:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Approve or reject the D2 source strategy for the GC CME Globex metals session calendar.

Decision Needed:
Should v1 use the following D2 strategy?

1. Build an observed-activity calendar from the already-licensed historical GC 1s archive as the first zero-cost evidence leg.
2. Use official CME GC/Globex documents as the authoritative public reference for product scope, current hours, holidays, and maintenance/session definitions.
3. Use Databento `status` schema only after a separate cost/source approval confirms schema availability, historical era coverage, and query cost.
4. Do not use TradingView as authoritative evidence for session-calendar membership; it may be used only as an informal visual sanity check.
5. Require an era-versioned calendar: every historical era must carry evidence. Eras without evidence remain `UNVERIFIED_HISTORICAL` and cannot receive guessed session membership.
6. Distinguish scheduled closures from observed venue/data gaps. Any disagreement between observed activity, Databento status, and CME documentation must become an explicit overlay/review item, not a silent choice.

What This Approval Would Allow:
- Design and implement a D2 session-calendar policy artifact.
- Profile observed historical activity gaps from already-licensed local data in sanitized aggregate form.
- Prepare, but not execute, any Databento `status` schema request unless separately approved.

What This Approval Would Not Allow:
- No Databento API query by itself.
- No new data purchase.
- No real bar resampling.
- No missing-bar fill/drop/mark implementation.
- No dataset construction.
- No feature build.
- No label build.
- No model training.
- No model promotion, live trading, broker execution, or capital allocation.

Recommended Decision:
Approve the strategy above.

Evidence:
- `agent-exchange/reviews/2026-09-01T224500Z-claude-code-review-d1-d3-intake-and-d2-calendar-recommendation.md`
- `agent-exchange/reviews/2026-09-01T231500Z-claude-code-groq-takeover-d1-d3-d2-challenge-review.md`
- `agent-exchange/status/2026-09-01T184500Z-codex-claude-d1-d3-d2-review-intake.md`

Notes:
This is a decision request only. It contains no secrets, raw market rows, local absolute paths, or vendor credentials.
