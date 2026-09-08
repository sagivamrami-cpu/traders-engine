# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-01T15:36:00Z

Status:
REVIEW_ONLY

Objective:
Challenge the proposed GC order-flow and baseline-training decisions from market-data, leakage, hidden-assumption, and research-validity angles.

Scope:
- `AGENTS.md`
- `agent-exchange/README.md`
- `agent-exchange/protocol.md`
- `configs/research/real-data-readiness-checklist.yaml`
- `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `configs/data/databento-gc-contract-stype-decision-template.yaml`
- `docs/implementation-reports/phase-20-databento-gc-zip-source-profile.md`
- `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`
- `docs/implementation-reports/phase-22-databento-contract-stype-decision-gate.md`
- Proposed Phase 23 direction: local GC order-flow ZIP intake, metadata/profile only, no raw market data committed.

Human decisions under review:
- Approve the newly supplied local GC order-flow ZIP as the order-flow source for research/training-preparation.
- Exclude 2017-01-01 through 2017-05-31 from any training or evaluation path that uses order-flow features because delta/aggressor-side data is damaged.
- Do not use `gold_orderflow_4h.csv` as the canonical first training source; keep it as reference/sanity-check because the first model should start from a lower timeframe.
- Use 30m as the first baseline training timeframe.
- Codex recommendation under review, not yet a human decision: use `GC.FUT` with `stype_in=parent` only for Databento cost/coverage preflight, not as training truth or execution truth.
- Defer options features to v2.
- Allow macro features only behind leakage checks and ablation experiments.

Review focus:
- Find any contradiction between these decisions and earlier project constraints.
- Challenge whether 30m is a defensible first baseline timeframe for GC futures with order-flow features.
- Challenge whether the 2017 exclusion window is sufficient or whether broader era normalization/gating is required.
- Identify leakage risks from `cvd`, macro features, derived labels, continuous/parent futures identity, and any 4H reference file.
- Identify hidden approvals that Phase 23 must avoid.
- State any additional acceptance gates Codex should require before feature building or training.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no Databento data download or purchase
- no model promotion
- no `timeseries.get_range`

Deliverables:
- Write a review file under `agent-exchange/reviews/`.
- Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.
- Include severity-ordered findings and exact commands run.
- If a decision is unsafe, propose the exact safer wording.

Suggested verification commands:
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `python tools/validate_phase21.py`
- `python tools/validate_databento_gc_contract_stype_decision.py`

Out of scope:
- Do not call Databento APIs with a real key.
- Do not approve data purchase, production training, or trading.
- Do not mutate the working tree.

Notes:
Copy/paste prompt for Groq:

```text
You are Groq reviewing the proposed GC order-flow decisions in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/groq/2026-09-01T153600Z-groq-review-gc-order-flow-decisions.md`.

Your job is review-only. Challenge the decisions from market-data, leakage, hidden-approval, and research-validity angles. Focus on approving the local GC order-flow ZIP for research/training-prep, excluding 2017-01-01 through 2017-05-31 for order-flow features, using 1m Parquet as canonical input while keeping the 4H CSV reference-only, choosing 30m as first baseline timeframe, reviewing Codex's proposed `GC.FUT` cost/coverage preflight mode without treating it as human-approved, deferring options to v2, and allowing macro features only behind leakage checks. Run the suggested commands if available and write your review to `agent-exchange/reviews/`.
```
