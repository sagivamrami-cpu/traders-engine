# Agent Exchange Request

Target: Groq reviewer

Sender: Codex architecture controller

Created at: 2026-09-15T09:00:00Z

Status:
REVIEW_ONLY

Objective:

Independently review the source-derived gap between the accepted raw-port
`TreeReader` / `TreeRevalidation` composition and the current closed-bar
`CausalReplay`. Identify every raw input, clock, artifact, availability rule,
or checkpoint concern that a future full-tree causal provider must cover. This
is an intake review only, not an implementation or a strategy change.

Scope:

- `docs/architecture/FULL-TREE-WALK-SOURCE-INTAKE.md`
- `docs/architecture/TREE-WALK-READER-CONTRACT.md`
- `docs/architecture/TREE-REVALIDATION-BINDING-CONTRACT.md`
- `docs/architecture/TREE-REVALIDATION-BINDING-INTAKE.md`
- `trading_system/tree_replay/_vendor/tree_walk.py`
- `trading_system/tree_replay/tree_revalidation.py`
- `trading_system/tree_replay/admission_context.py`
- `trading_system/tree_replay/causal_replay.py`
- `trading_system/tree_replay/causal_replay_contracts.py`

Required inputs:

Read the files above as text. Do not execute original source modules, access a
market-data vendor, inspect secrets, add code, or modify files.

Contracts:

The existing replay supports only `level_reversal:5m`. `TreeReader` and
`TreeRevalidation` already compose the original full tree over a supplied raw
source, but `CausalAdmissionContext` binds only frames, quotes, tracker/log
state, lock steps, and one decision time. The next component must prove
point-in-time full-tree evaluation from supplied evidence. A complete `Walk`
is neither an admission, fill, trade outcome, nor an economic label.

Non-negotiables:
- point-in-time correctness
- preserve source operation order and distinct source clock reads
- distinguish unavailable/unknown from negative evidence
- no caching or injection of provider-final Walk / Plan / boolean results
- raw payloads must not enter public replay ledger or checkpoint commitments;
  digests and identities may be recorded
- no invented thresholds, feeds, rules, or strategy corrections
- no production approval by implication
- no live trading, broker execution, capital allocation, P&L, labels, dataset,
  or model work

Deliverables:

Write one review under `agent-exchange/reviews/` using the review template.
State: (1) missing raw ports/artifacts, (2) clock/order hazards, (3) checkpoint
and commitment requirements, (4) any contradiction in the supplied contracts,
and (5) a verdict: sufficient for a design spec / insufficient, with exact
blockers. Cite file paths and line numbers where feasible. Do not propose a
new trading rule.

Verification commands:

- `rg -n "def (fetch_corrected|now_utc|calendar_text|list_reports|read_report|read_tv_csv)|_SUPPORTED_VARIANT" trading_system/tree_replay`
- `rg -n "fetch_corrected\\(|now_utc\\(|calendar_text\\(|list_reports\\(|read_report\\(|read_tv_csv\\(" trading_system/tree_replay/_vendor/tree_walk.py`

Out of scope:

Implementation, tests, source parity changes, training, simulation, economic
labels, external data acquisition, and acceptance of any existing component.

Notes:

This review does not replace the two pending independent reviews for Outer
Admission. No human approval is inferred from this request.
