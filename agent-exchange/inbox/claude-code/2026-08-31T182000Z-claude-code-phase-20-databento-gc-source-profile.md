# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-08-31T18:20:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Implement Phase 20: Databento GC ZIP source profile. The goal is to safely
inspect the purchased Databento GC one-second ZIP archive and emit a sanitized
source-profile payload before any real dataset construction or model training.

Scope:
- `docs/superpowers/plans/2026-08-31-phase-20-databento-gc-zip-source-profile.md`
- `agent-exchange/status/2026-08-31T174558Z-codex-databento-local-dataset-intake.md`
- `agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `configs/data/databento-gc-source-metadata.yaml`
- `configs/data/symbol-map.yaml`
- `configs/data/source-inventory.yaml`
- `requirements.txt`
- `trading_system/research/`
- `schemas/`
- `tools/`
- `tests/research/`

Required inputs:
- Current branch: `plan/tree-to-trained-model-langgraph`
- Local ZIP path supplied by human outside committed files and outside
  `agent-exchange/`.
- Phase 20 plan:
  `docs/superpowers/plans/2026-08-31-phase-20-databento-gc-zip-source-profile.md`

Contracts:
- Start with tests from the Phase 20 plan.
- Use `pyarrow`/`pandas` to read parquet files inside the ZIP.
- Treat the source as Databento `GC`, not `XAUUSD`.
- Do not approve or implement GC-to-XAUUSD proxy use.
- Emit sanitized profile JSON only; do not write raw extracts or copied source data.
- Do not commit absolute local paths, raw data rows, secrets, broker/account identifiers, or private credentials.
- Keep `production_allowed=false`.
- Keep `dataset_construction_allowed=false`.
- Keep `training_allowed=false`.
- Keep `allowed_next_actions=[]`.
- Do not run dry-run, build real datasets, train models, promote models, deploy, live trade, execute broker actions, or allocate capital.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, deployment, or capital allocation
- no approval from agent-authored files
- no committed real raw data or absolute user paths

Deliverables:
- Implement every task in
  `docs/superpowers/plans/2026-08-31-phase-20-databento-gc-zip-source-profile.md`.
- Completion result under `agent-exchange/status/` using
  `agent-exchange/templates/result.md` with status
  `IMPLEMENTED_AWAITING_CODEX_REVIEW`.
- List every changed file and exact verification output.

Verification commands:
- `python -m pytest tests/research/test_databento_gc_source_profile.py tests/research/test_phase20_validator.py -v`
- `python tools/validate_phase20.py`
- `python tools/real_data_readiness.py --decisions agent-exchange/decisions/databento-gc-real-data-decisions.yaml`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q`
- `foreach ($p in 0..20) { python "tools/validate_phase$p.py"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }`
- `git diff --check`

Out of scope:
- Resampling the archive into a persistent 4H dataset.
- Building candidate training rows.
- Training models.
- Model promotion.
- GC-to-XAUUSD proxy approval.
- Live trading, broker execution, deployment, or capital allocation.

Notes:
If Codex is already implementing the same task in this working tree, do not
duplicate edits. Leave a verification/status result instead.

Prompt to paste into Claude Code:
You are Claude Code implementing Phase 20 in the `traders-engine` repo. Pull
the latest branch `plan/tree-to-trained-model-langgraph`. Read `AGENTS.md`,
`agent-exchange/protocol.md`, and
`agent-exchange/inbox/claude-code/2026-08-31T182000Z-claude-code-phase-20-databento-gc-source-profile.md`.
Implement the Phase 20 plan exactly, tests first. The source is Databento GC,
not XAUUSD. Keep output sanitized and read-only: no raw extracts, no absolute
paths, no dry-run, no dataset construction, no training, no broker/trading/
capital/deployment actions. Write your result under `agent-exchange/status/`
with status `IMPLEMENTED_AWAITING_CODEX_REVIEW`.
