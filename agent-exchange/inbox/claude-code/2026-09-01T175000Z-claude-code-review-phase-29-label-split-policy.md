# Agent Exchange Request

Status:
REVIEW_ONLY

Sender:
Codex

Target:
Claude Code

Created at:
2026-09-01T17:50:00Z

Objective:
Review Phase 29 GC label-contract and split/embargo policy candidate.

Scope:
- `configs/research/gc-label-split-policy.yaml`
- `schemas/gc_label_split_policy.schema.json`
- `trading_system/research/gc_label_split_policy.py`
- `tools/validate_gc_label_split_policy.py`
- `tools/validate_phase29.py`
- `tests/research/test_gc_label_split_policy.py`
- `tests/research/test_phase29_validator.py`
- `docs/implementation-reports/phase-29-gc-label-split-policy.md`

Context:
- Human approved Codex recommendation to use outcome-contract labels, not HHLL labels.
- Human approved chronological walk-forward split with embargo.
- Phase 29 is a policy candidate only.

Review focus:
- Verify HHLL cannot be consumed as a training target.
- Verify the policy does not build real labels, splits, datasets, features, models, or training rows.
- Verify target/stop thresholds and max horizon remain unspecified and gate-blocked.
- Verify same-bar target/stop ambiguity is excluded from training.
- Verify random split is impossible under this policy.
- Verify 2017 damaged-aggressor exclusion mask is carried into all variants.
- Verify no local absolute paths, secrets, raw rows, or vendor payloads are emitted.

Forbidden assumptions:
- Do not treat this as `LABEL_CONTRACT` satisfied.
- Do not treat this as `SPLIT_AND_EMBARGO_POLICY` satisfied.
- Do not approve dataset construction, training, promotion, live trading, broker execution, or capital allocation.
- Do not use `hhll_*` files as labels.

Verification:
- `python tools/validate_phase29.py`

Deliverable:
Write review to `agent-exchange/reviews/` with `Verdict:` and concrete findings.
