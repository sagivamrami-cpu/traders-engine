# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-01T16:36:00Z

Status:
REVIEW_ONLY

Objective:
Review Phase 23 GC order-flow profile implementation for market-data identity, leakage, era-policy, and hidden-approval risks.

Scope:
- `docs/superpowers/plans/2026-09-01-phase-23-gc-order-flow-profile.md`
- `configs/data/databento-gc-order-flow-source-metadata.yaml`
- `configs/data/gc-order-flow-quality-gates.yaml`
- `schemas/databento_gc_order_flow_profile.schema.json`
- `trading_system/research/databento_gc_order_flow_profile.py`
- `tools/inspect_databento_gc_order_flow_zip.py`
- `tools/validate_phase23.py`
- `tests/research/test_databento_gc_order_flow_profile.py`
- `docs/implementation-reports/phase-23-gc-order-flow-profile.md`
- `agent-exchange/status/2026-09-01T163000Z-codex-phase-23-implementation-result.md`

Required inputs:
- Read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`.

Review focus:
- Does Phase 23 avoid turning profile-only archive inspection into order-flow source approval?
- Does it keep contract identity, roll policy, session policy, and 30m resample policy open?
- Does it handle the 2017 damaged-aggressor window as known damage without pretending the era policy is complete?
- Does it prevent CVD/cumulative-feature leakage across folds and eras by blocking those features?
- Does it prevent 4H CSV, HHLL labels, macro columns, options, XAUUSD/GLD mapping, and Databento downloads from entering the v1 dataset path?
- Are there hidden approvals or misleading names/statuses that a later worker might misuse?

Non-negotiables:
- no raw market-data payloads
- no local absolute data paths
- no Databento API calls
- no `timeseries.get_range`
- no feature construction
- no dataset construction
- no training or model promotion
- no live trading, broker execution, or capital allocation

Deliverables:
- Write a review file under `agent-exchange/reviews/`.
- Verdict must be `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `BLOCKED`.
- Include severity-ordered findings and exact commands run.
- If unsafe, propose exact safer wording or gates.

Verification commands:
- `python tools/validate_phase23.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`

Out of scope:
- Do not call Databento APIs.
- Do not read or print raw market-data rows.
- Do not mutate the working tree.

Notes:
Copy/paste prompt for Groq:

```text
You are Groq reviewing Phase 23 in the `traders-engine` repo. First read `AGENTS.md`, `agent-exchange/README.md`, and `agent-exchange/protocol.md`. Then review `agent-exchange/inbox/groq/2026-09-01T163600Z-groq-review-phase-23-order-flow-profile.md`.

Your job is review-only. Challenge Phase 23 from market-data identity, leakage, era-policy, and hidden-approval angles. Verify it is profile-only, keeps order-flow source approval open, keeps options deferred/open, blocks CVD/cumulative leakage, blocks 4H CSV/HHLL/macro/options/XAUUSD/GLD paths, and does not approve feature/dataset/training/trading work. Run the listed commands if available and write your review to `agent-exchange/reviews/`.
```
