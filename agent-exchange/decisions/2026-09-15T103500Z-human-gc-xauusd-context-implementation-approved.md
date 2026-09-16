# Human decision — implement approved GC Order Flow context sidecar

Created at: 2026-09-15T10:35:00Z

Approver: Roee, acting with delegated Sagiv approval for this scope.

Decision: APPROVED

Scope: Implement the approved design at
`docs/superpowers/specs/2026-09-15-gc-order-flow-xauusd-context-design.md`.
GC from Databento is a closed-minute, explicitly labelled Order Flow context
for the `OANDA:XAUUSD` research tree. It is not an XAUUSD price, execution,
or live-trading source.

Evidence: user message “מאושר” on 2026-09-15 after review of the design.

Limits retained: no raw archive in the repository or agent exchange; no price
mapping; 2017 damage exclusion; no CVD/cumulative carry; unavailable is not
imputed; no dataset, model, promotion, live/broker, capital or deployment
approval.
