# Human Decision

Approver: Roee, on behalf of Sagiv and the project team

Created at: 2026-09-15T10:21:50Z

Scope: Resolve whether exchange-traded CME Gold futures Order Flow may be used
as a cross-market context input when the trade tree's price/economic instrument
remains `OANDA:XAUUSD`.

Decision: APPROVED.

Policy:

- The trade instrument, price bars, levels, entry, stop, target, fill and
  economic outcome remain `OANDA:XAUUSD`.
- `CME:GC` from the approved local Databento archive is an explicitly labelled
  **Order Flow context source**. It supplies no XAUUSD price, level, stop,
  target, fill or economic value.
- The source feature must retain both identities: target instrument
  `OANDA:XAUUSD`, source instrument `CME:GC`, source `DATABENTO/GLBX.MDP3`.
- A decision at T may use only a GC minute whose end is at or before T. No
  interpolation, price offset, rolling-price conversion, silent alias or
  future minute is permitted.
- The selected input is `gc/GCext_of_1m.parquet`, with minute `volume`,
  `delta` and `trades` only. The 2017 damaged aggressor window is excluded.
  Archived CVD and all cumulative carry remain forbidden under the existing
  row-mask policy.
- Missing or late GC evidence is an explicit unavailable context. Full-
  information research eligibility must record it; the original tree's existing
  optional-branch semantics are not silently changed by this decision.

Evidence: User stated in the active Codex session that if Codex judges CME GC
Order Flow appropriate for XAUUSD context, that judgment is also Sagiv's
approval: "אם מבחינתך כן אז גם מבחינת שגיב כן".

Supersedes only the prior prohibition on unapproved XAUUSD/GC proxy mapping in
`agent-exchange/decisions/2026-09-02T052003Z-human-d6-final-order-flow-source-decision.md`.
It does not approve a GC price mapping, source-faithful OANDA price substitution,
dataset build, model training, promotion, execution or live trading.

Design: `docs/superpowers/specs/2026-09-15-gc-order-flow-xauusd-context-design.md`.
