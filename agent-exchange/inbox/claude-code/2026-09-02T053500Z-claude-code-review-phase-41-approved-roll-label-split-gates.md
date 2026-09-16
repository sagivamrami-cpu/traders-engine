# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-02T05:35:00Z

Status:
NEEDS_REVIEW

Objective:
Review Phase 41, where Codex converted the human-approved Phase 40 D5/D7/D8
decisions into enforceable v1 research metadata.

## Changed Areas

- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `tests/research/test_gc_real_dataset_contract.py`
- `configs/research/gc-label-split-policy.yaml`
- `schemas/gc_label_split_policy.schema.json`
- `tests/research/test_gc_label_split_policy.py`
- `schemas/gc_pretraining_readiness_report.schema.json`
- `tests/research/test_gc_pretraining_readiness.py`
- Phase 41 report/status files

## Review Focus

Please verify:

1. `ROLL_POLICY`, `LABEL_CONTRACT`, and `SPLIT_AND_EMBARGO_POLICY` are the only
   gates newly removed from readiness.
2. The roll policy preserves the research-only caveat:
   `UNDECLARED_PENDING_RESEARCH`.
3. The label policy exactly matches D7-final: outcome contract, ATR(14) closed
   bars, 1R target/stop, 8-bar horizon, next-bar-open entry, same-bar ambiguity
   excluded, HHLL not primary.
4. The split policy exactly matches D8-final: chronological only, no random
   split, purge, 8-bar embargo, fold-local transforms, shared 2017 mask function.
5. Dataset construction and training remain blocked.
6. No raw data, local absolute paths, secrets, model artifacts, or training
   outputs were added.

## Verification To Run

- `python -m pytest tests\research\test_gc_label_split_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`
- `python tools\validate_gc_label_split_policy.py --policy configs\research\gc-label-split-policy.yaml`
- `python tools\gc_pretraining_readiness.py --contract configs\datasets\gc-30m-real-dataset-contract.yaml --decisions agent-exchange\decisions\databento-gc-real-data-decisions.yaml --checklist configs\research\real-data-readiness-checklist.yaml --training-policy configs\models\baseline-training-policy.yaml --groq-phase24-review agent-exchange\reviews\2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md --groq-phase24-intake agent-exchange\status\2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md`

Write a review-only response under `agent-exchange/reviews/`.

Do not modify source/config files. Do not query vendors. Do not read raw market
rows. Do not include secrets, raw data, account IDs, or local absolute paths.
