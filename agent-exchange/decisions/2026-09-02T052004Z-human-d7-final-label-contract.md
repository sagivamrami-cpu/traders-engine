# Human Decision

Approver: Human Data Owner

Created at: 2026-09-02T05:20:04Z

Scope: Approve the v1 GC baseline label contract as a future-only
outcome-contract label and reject HHLL as the primary training label.

Decision: APPROVED

Policy:
- At each 30m decision bar, evaluate a future-only long/short outcome contract.
- Positive class means target reached before stop.
- Negative class means stop reached before target or target not reached before
  expiry.
- Same-bar target-and-stop ambiguity is excluded from training.
- HHLL files remain auxiliary/reference-only and must not be the primary label.

Starter contract:
- Direction candidates: long and short scored separately, then one binary
  training target per configured direction.
- Risk unit `R`: `ATR(14)` on 30m bars, computed only from closed OHLCV bars
  available at the decision bar.
- Target distance: `1.0 * R`.
- Stop distance: `1.0 * R`.
- Max horizon: `8` bars of 30m, equal to 4 hours.
- Entry availability: next bar open after the decision bar is closed.
- Cost/fill policy: zero-cost research baseline, explicitly not executable
  production truth.

Constraints:
- This record authorizes implementation of the real GC label builder.
- This record does not approve live execution truth, broker fills, model
  promotion, live trading, broker execution, or capital allocation.

Evidence:
- Human approval in active Codex session: "כל הסעיפים מאושרים מבחינתי".
- Human condition in active Codex session: "ניתן להתקדם רק אחרי שקלוד ואתה מסכימים".
- Claude Code review: `agent-exchange/reviews/2026-09-02T051500Z-claude-code-recheck-phase-40-human-decision-packet.md`.
- Codex decision packet: `agent-exchange/inbox/human/2026-09-02T040000Z-human-phase-40-remaining-training-gate-decisions.md`.
