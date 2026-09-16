# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T15:35:00Z

Status:
REVIEW_ONLY

Objective:
Review the proposed human decisions and next implementation direction for GC order-flow intake and first training dataset construction.

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
- Are these decisions sufficient to unblock Phase 23 order-flow intake without approving production model training or live trading?
- Does the 30m baseline choice fit the existing architecture better than 4H, 5m, or 1m for the first real pipeline?
- What validators, schema fields, and tests should Phase 23 add?
- Are there implementation risks in treating the 4H CSV as reference-only while using 1m Parquet as canonical input?
- Are any existing Phase 21/22 contracts likely to conflict with the proposed `GC.FUT` cost-preflight-only usage?

Non-negotiables:
- no API keys in repo or exchange
- no raw market-data payloads in repo or exchange
- no Databento data download or purchase
- no live trading, broker execution, or capital allocation
- no model promotion
- no hidden approval by implication
- no `timeseries.get_range`

Deliverables:
- Write a review file under `agent-exchange/reviews/`.
- Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.
- Include severity-ordered findings and exact commands run.
- If you recommend changing any human decision, state the concrete replacement decision and why.

Suggested verification commands:
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `python tools/validate_phase21.py`
- `python tools/validate_databento_gc_contract_stype_decision.py`

Out of scope:
- Do not call Databento APIs with a real key.
- Do not approve data purchase, production training, or trading.
- Do not mutate the working tree.

Notes:
Copy/paste prompt for Claude Code:

```text
You are Claude Code reviewing the proposed GC order-flow decisions in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/claude-code/2026-09-01T153500Z-claude-code-review-gc-order-flow-decisions.md`.

Your job is review-only. Evaluate whether the proposed decisions safely unblock Phase 23: local GC order-flow intake, metadata/profile only, no raw market data committed. Pay special attention to the 30m first baseline, excluding 2017-01-01 through 2017-05-31 for order-flow features, treating `gold_orderflow_4h.csv` as reference-only, reviewing Codex's proposed `GC.FUT` cost/coverage preflight mode without treating it as human-approved, deferring options to v2, and gating macro features behind leakage checks. Run the suggested commands if available and write your review to `agent-exchange/reviews/`.
```
