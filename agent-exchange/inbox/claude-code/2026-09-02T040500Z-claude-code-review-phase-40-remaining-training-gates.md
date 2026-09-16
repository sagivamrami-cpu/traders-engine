# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-02T04:05:00Z

Status:
NEEDS_REVIEW

Objective:
Review Codex's remaining-human-decision packet before the project proceeds
toward real GC dataset construction and baseline model training.

## Context

Groq is unavailable due quota, so Claude Code is the external reviewer for
this pass.

Phase 39 was sent separately for review:
`agent-exchange/inbox/claude-code/2026-09-02T034500Z-claude-code-review-phase-39-row-mask-cumulative-policy.md`

Phase 40 human packet:
`agent-exchange/inbox/human/2026-09-02T040000Z-human-phase-40-remaining-training-gate-decisions.md`

Current readiness output remains blocked with these required gates:

- `SESSION_CALENDAR`
- `MISSING_BAR_POLICY`
- `ROLL_POLICY`
- `DATASET_IDENTITY`
- `ORDER_FLOW_SOURCE_DECISION`
- `LABEL_CONTRACT`
- `SPLIT_AND_EMBARGO_POLICY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`
- `REAL_DATASET_NOT_BUILT`

## Review Focus

Please verify:

1. The Phase 40 packet does not itself approve any gate.
2. The recommendations are consistent with earlier reviews and human records.
3. The order-flow source recommendation stays bounded to `volume`, `delta`,
   and `trades`; does not permit archived `cvd` or cumulative carry.
4. The label-contract recommendation is clear enough for a first baseline and
   does not imply live execution truth.
5. The split/embargo recommendation prevents future-label leakage and applies
   the 2017 damaged-window exclusion consistently.
6. `DATASET_CONSTRUCTION_AUTHORIZATION` remains conditional and does not allow
   construction before D4-D8 approval plus Phase 39 acceptance.

## Requested Output

Write a review-only response under:
`agent-exchange/reviews/`

Use severity-ranked findings. Do not modify source/config files. Do not query
vendors. Do not read raw market rows. Do not include secrets, raw data, account
IDs, or local absolute paths.
