# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-08-31T18:25:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Review Phase 20 Databento GC ZIP source profile for source/proxy confusion,
hidden approval, raw-data leakage, path leakage, label leakage, day/session
assumption risk, and any route from source profiling into dataset construction
or model training.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-20-databento-gc-zip-source-profile.md`
- `agent-exchange/status/2026-08-31T174558Z-codex-databento-local-dataset-intake.md`
- `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `configs/data/databento-gc-source-metadata.yaml`
- `configs/data/source-inventory.yaml`
- `configs/data/symbol-map.yaml`
- `requirements.txt`
- Phase 20 implementation files if present.

Required inputs:
- Current branch: `plan/tree-to-trained-model-langgraph`
- Human clarified that the ZIP archive is purchased Databento historical data.
- Human clarified that the first source is `GC`.
- Human stated the license covers the required use.

Contracts:
- Groq reviews only. Do not implement code and do not approve production data.
- Treat GC as GC; do not let the plan or implementation silently relabel it as
  XAUUSD.
- Confirm HHLL LONG/SHORT remains an auxiliary direction label only, not a
  trade-contract outcome label or edge claim.
- Confirm day/session policy remains research-pending and measured-first.
- Look for any path where profile readiness can be mistaken for approval to run
  dry-run, build datasets, train models, promote models, deploy, trade live,
  execute broker actions, allocate capital, retain/copy/mutate/upload raw data,
  or use external accounts.
- Look for raw data rows, absolute local paths, secrets, private account data,
  or Databento redistribution risk in outputs.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, deployment, or capital allocation
- no raw market data, secrets, credentials, account identifiers, or absolute
  user paths in review output

Deliverables:
- Review file under `agent-exchange/reviews/` using
  `agent-exchange/templates/review.md`.
- Status must be `REVIEW_READY_FOR_CODEX`.
- Findings should be numbered and severity-ranked.
- For every finding include observed issue, risk, failing scenario,
  recommended fix, and whether it blocks Phase 20 acceptance.

Verification commands:
- `python tools/validate_phase19.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target groq`

Out of scope:
- Writing implementation code.
- Approving production data.
- Approving model promotion.
- Live trading, broker execution, deployment, or capital allocation.

Notes:
If Phase 20 implementation status exists by the time you start, review both
the plan and implementation. If it does not, review the plan as a
pre-implementation risk review.

Prompt to paste into Groq:
You are Groq reviewing Phase 20 in the `traders-engine` repo. Pull the latest
branch `plan/tree-to-trained-model-langgraph`. Read `AGENTS.md`,
`agent-exchange/protocol.md`, and
`agent-exchange/inbox/groq/2026-08-31T182500Z-groq-review-phase-20-databento-gc-source-profile.md`.
Review for GC-vs-XAUUSD confusion, Databento provenance/license boundaries,
HHLL label leakage, day/session assumptions, raw/path leakage, and any route
from source profiling into dry-run/dataset/training/promotion/trading/broker/
capital/deployment flows. Do not implement code. Write your review under
`agent-exchange/reviews/` with `Status: REVIEW_READY_FOR_CODEX`.
