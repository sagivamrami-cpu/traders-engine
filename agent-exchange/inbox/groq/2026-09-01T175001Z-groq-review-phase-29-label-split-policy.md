# Agent Exchange Request

Status:
REVIEW_ONLY

Sender:
Codex

Target:
Groq

Created at:
2026-09-01T17:50:01Z

Objective:
Challenge-review Phase 29 GC label-contract and split/embargo policy candidate.

Scope:
- `configs/research/gc-label-split-policy.yaml`
- `schemas/gc_label_split_policy.schema.json`
- `trading_system/research/gc_label_split_policy.py`
- `tools/validate_gc_label_split_policy.py`
- `tools/validate_phase29.py`
- `tests/research/test_gc_label_split_policy.py`
- `tests/research/test_phase29_validator.py`
- `docs/implementation-reports/phase-29-gc-label-split-policy.md`

Challenge questions:
- Can any worker read this phase as permission to build labels, splits, a dataset, or a model?
- Can HHLL still leak in as the primary training target?
- Can same-bar target/stop ambiguity be included in training?
- Can a random split or non-embargoed split slip through?
- Does the 2017 damaged-aggressor mask apply identically to every dataset/model variant?
- Are target/stop thresholds, max horizon, graph trade contract, contract identity, and fill truth still visibly unsatisfied?
- Does `validate_phase29.py` actually assert the above?

Forbidden assumptions:
- No dataset construction.
- No real labels or splits.
- No feature construction.
- No model training.
- No promotion, live trading, broker execution, or capital allocation.
- No raw data, local absolute paths, secrets, or vendor payloads.

Verification:
- `python tools/validate_phase29.py`

Deliverable:
Write review to `agent-exchange/reviews/` with `Verdict:` and blocking/high findings first.
