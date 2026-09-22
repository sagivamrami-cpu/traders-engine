# Agent Exchange Request

Target:
Roee, Sagiv and Yuval

Sender:
Codex architecture controller

Created at:
2026-09-15T09:30:00Z

Status:
ACTIONABLE

Objective:

Approve the architectural direction for replaying the complete existing tree
historically, before any new implementation is started.

Scope:

The decision concerns only the boundary between the accepted full-tree readers
(`TreeReader` / `TreeRevalidation`) and the current supplied-evidence
closed-bar replay. It does not choose a trading rule, model, label, broker,
dataset, or production feed.

Required inputs:

Read:

- `docs/architecture/FULL-TREE-WALK-SOURCE-INTAKE.md`
- `docs/architecture/TREE-WALK-READER-CONTRACT.md`
- `docs/architecture/TREE-REVALIDATION-BINDING-INTAKE.md`
- `agent-exchange/status/2026-09-15T091000Z-codex-full-tree-provider-readonly-intake.md`

Contracts:

The full tree consumes multiple raw evidence types: corrected bars, independent
clock calls, news calendar content, options report artifacts, TradingView CSV,
and revalidation deep/shadow artifacts. A complete `Walk` is not an admitted
trade, filled order, success/failure label, or economic outcome. The current
replay supports only `level_reversal:5m` and does not cover these full-tree
dependencies.

Non-negotiables:
- point-in-time correctness
- preserve source call ordering and separate clocks
- preserve unavailable/unknown rather than manufacturing a negative signal
- no injected provider-final Walk, Plan, pass/fail outcome or future data
- raw data stays outside public ledger/checkpoint artifacts; only identities
  and digests may be committed there
- no production approval by implication
- no live trading, broker execution, capital allocation, dataset building,
  model training, or model promotion in this decision

Decision alternatives:

1. **Recommended — separate full-tree causal provider.** Create a dedicated,
   immutable supplied-evidence provider for the full tree and expose it through
   a new explicit replay variant. It has its own operation/availability schedule
   and checkpoint baseline. It leaves `CausalAdmissionContext` and the existing
   `level_reversal:5m` path intact.

   Why: this preserves the source tree's real data and time dependencies,
   prevents accidental coupling to tracker/watch state, and lets the new path be
   tested and accepted independently.

2. **Not recommended — extend `CausalAdmissionContext`.** Put all raw tree
   artifacts into the existing admission/watch provider.

   Risk: it combines unrelated responsibilities, obscures repeated source reads
   and operation clocks, and raises regression risk for an already accepted
   closed-bar path.

3. **Rejected — feed final tree outputs into replay.** Precompute a `Walk` or
   `Plan` and store only that result.

   Risk: it cannot prove historical causality, permits hidden future leakage,
   and does not demonstrate that the tree itself was run from available evidence.

Deliverables:

Reply with one of:

- `APPROVE_OPTION_1` — authorize a detailed design spec only; implementation
  still requires review of that spec.
- `CHOOSE_OPTION_2` — request the coupled-context approach and explain why.
- `REVISE` — identify the required change to the decision scope.

Verification commands:

No commands required from the human team. The future implementation will have
separate ordered-call, availability, source-parity and checkpoint/resume tests.

Out of scope:

Any model choice, profitability target, transaction cost decision, economic
label, external data acquisition, raw-data retention, live deployment or broker
execution.

Notes:

This request is a design gate only. It does not approve the pending Outer
Admission implementation; that component still awaits independent reviews.
