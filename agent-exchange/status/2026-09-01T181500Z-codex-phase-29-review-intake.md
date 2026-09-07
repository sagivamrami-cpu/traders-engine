# Codex Status

Status:
ACCEPTED_BY_CODEX

Phase:
29

Subject:
Claude Code and Groq review intake for GC label/split policy candidate

Reviews:
- Claude Code: `agent-exchange/reviews/2026-09-01T215000Z-claude-code-review-phase-29-label-split-policy.md`
- Groq: `agent-exchange/reviews/2026-09-01T220500Z-groq-review-phase-29-label-split-policy.md`

Codex decision:
Accepted both reviews. Claude Code verdict was `ACCEPT`. Groq verdict was `ACCEPT_WITH_CHANGES`; Codex accepted the technical findings and implemented the hardening.

Implemented hardening:
- Reworded Phase 29 as a Codex recommendation candidate, not a human-approved D7/D8 decision.
- Added `d7_decision_status=NEEDS_HUMAN_DECISION_RECORD`.
- Added `d8_decision_status=NEEDS_HUMAN_DECISION_RECORD`.
- Added blockers for HHLL derived ingestion, HHLL auxiliary training targets, fixture trade-contract adaptation, unembargoed splits, fixture walk-forward policy, binary projection with ambiguous labels, and continuous/stitched GC label truth.
- Added remaining gates for graph trade contract, cost/fill policy, contract identity, row-level 2017 mask, source/canonical input gates, and dataset identity.
- Changed fold fit scope to train-window only.
- Kept numeric embargo/purge windows pending max label horizon.
- Kept row-level 2017 mask required but unimplemented.

Verification:
- `python -m pytest tests\research\test_gc_label_split_policy.py -q`: PASS, 5 passed.

Commit/push:
Not performed by user instruction.
