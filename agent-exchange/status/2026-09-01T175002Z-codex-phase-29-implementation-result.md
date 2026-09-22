# Codex Status

Status:
IMPLEMENTED_NEEDS_REVIEW

Phase:
29

Subject:
GC label-contract and split/embargo policy candidate

Summary:
Codex implemented Phase 29 as a fail-closed policy candidate. It records a Codex recommendation candidate for outcome-contract labels, keeps HHLL auxiliary-only and blocked from training targets, requires chronological walk-forward split with purge/embargo, and carries the 2017 damaged-aggressor exclusion requirement. It does not approve D7/D8 and does not implement a row-level mask.

Not authorized:
- Real label building
- Real split building
- Real dataset construction
- Feature construction
- Fixture trade-contract adaptation to real GC
- HHLL auxiliary training targets
- Unembargoed chronological splits
- Binary projection with ambiguous labels as negative class
- Model training
- Edge claims
- Model promotion
- Live trading
- Broker execution
- Capital allocation

Review requests:
- Claude Code: `agent-exchange/inbox/claude-code/2026-09-01T175000Z-claude-code-review-phase-29-label-split-policy.md`
- Groq: `agent-exchange/inbox/groq/2026-09-01T175001Z-groq-review-phase-29-label-split-policy.md`

Verification:
- `python -m pytest tests\research\test_gc_label_split_policy.py -q`: PASS, 5 passed.
- `python -m pytest tests\research\test_phase29_validator.py -q`: PASS, 1 passed.
- `python tools\validate_phase29.py`: PASS, `Phase 29 artifacts validated`.

Remaining gates:
- `LABEL_CONTRACT`
- `SPLIT_AND_EMBARGO_POLICY`
- `BAR_BOUNDARY`
- `SESSION_CALENDAR`
- `TIMESTAMP_ROLE`
- `AVAILABLE_AT_POLICY`
- `ROLL_POLICY`
- `CONTRACT_IDENTITY`
- `GRAPH_TRADE_CONTRACT`
- `COST_FILL_POLICY`
- `ROW_LEVEL_2017_MASK`
- `ORDER_FLOW_ERA_MAP`
- `CUMULATIVE_FEATURE_POLICY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`

Next Codex action:
Wait for Claude Code/Groq Phase 29 review if available while continuing non-training pre-dataset work that does not require a new human decision.

Commit/push:
Not performed by user instruction.
