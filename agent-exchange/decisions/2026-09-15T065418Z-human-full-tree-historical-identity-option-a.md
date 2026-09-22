# Human Decision

Approver: Roee, human project owner

Created at: 2026-09-15T06:54:18Z

Scope: Select the identity strategy for the first actual historical full-tree
replay and its later research dataset.  This decision applies only to
source-faithful XAUUSD research and does not select a vendor or authorize data
access, raw-data retention, model promotion, execution, capital allocation or
live trading.

Decision: APPROVED — Option A, source-faithful XAUUSD path.

Policy:
- The first full-tree historical replay must use a historical source genuinely
  compatible with the existing tree's `OANDA:XAUUSD` identity, or a formally
  defined supported XAUUSD source variant.
- GC futures data must not be silently normalized, offset or otherwise
  represented as that XAUUSD source.
- A data adapter may only be implemented after the provider, exact symbol,
  history, calendar, availability/revision and provenance details are supplied
  and separately authorized where required.
- Outputs may be called source-faithful only after those adapter contracts and
  point-in-time evidence checks pass.

Evidence: Roee replied `A` in the active Codex session in direct response to
`agent-exchange/inbox/human/2026-09-15T093000Z-human-full-tree-historical-identity-decision.md`.

Follow-up required: `agent-exchange/inbox/human/2026-09-15T065418Z-human-xauusd-source-profile-required.md`.
