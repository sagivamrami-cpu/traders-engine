# Agent Exchange Request

Target:
Codex

Sender:
Codex

Created at:
2026-08-31T09:00:00Z

Status:
ACTIONABLE

Objective:
Re-check the current tree-to-trained-model project state after Phases 0-13,
keep architecture ownership, and route the next work to the right tool before
any implementation starts.

Scope:
- `AGENTS.md`
- `agent-exchange/README.md`
- `agent-exchange/protocol.md`
- `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`
- `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`
- `docs/implementation-reports/phase-0-specification-freeze.md`
- `docs/implementation-reports/phase-1-data-foundation.md`
- `docs/implementation-reports/phase-2-deterministic-feature-engines.md`
- `docs/implementation-reports/phase-3-candidate-label-factory.md`
- `docs/implementation-reports/phase-4-fixture-dataset-factory.md`
- `docs/implementation-reports/phase-5-baseline-training-readiness.md`
- `docs/implementation-reports/phase-6-walk-forward-evaluation.md`
- `docs/implementation-reports/phase-7-model-card-governance.md`
- `docs/implementation-reports/phase-8-local-csv-onboarding.md`
- `docs/implementation-reports/phase-9-local-csv-research-dry-run.md`
- `docs/implementation-reports/phase-10-raw-data-retention-policy.md`
- `docs/implementation-reports/phase-11-local-source-bundle-validation.md`
- `docs/implementation-reports/phase-12-real-data-readiness-checklist.md`
- `docs/implementation-reports/phase-13-local-csv-inspection.md`
- `configs/`
- `schemas/`
- `tools/`
- `trading_system/`
- `tests/`

Required inputs:
- GitHub PR #1 on branch `plan/tree-to-trained-model-langgraph`.
- Current head at or after `f18d85e chore: add shared agent exchange workflow`.
- Current agent-exchange inbox items for Codex, Claude Code, Groq, and human.

Contracts:
- Codex owns architecture, phase sequencing, task routing, acceptance decisions,
  commits, pushes, and PR updates.
- Claude Code implements scoped implementation tasks only after Codex defines
  the task contract.
- Groq reviews, finds contradictions, and generates scenarios; it does not make
  approval or merge decisions.
- Humans approve production data, raw-data retention, model promotion, live
  trading, broker execution, capital allocation, and deployment.
- Phase 0-13 validators are the current baseline.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation
- no secrets, credentials, account data, raw market-data payloads, or large
  artifacts in `agent-exchange/`
- no phase may unblock production training unless a matching human decision
  record exists under `agent-exchange/decisions/`

Deliverables:
- A Codex architecture/status note under `agent-exchange/status/` or
  `agent-exchange/reviews/`.
- A decision on whether Phase 14 should proceed as real-data decision intake or
  wait for human inputs.
- Updated task routing files if the next phase changes.
- Acceptance criteria for any Claude Code implementation output.

Verification commands:
- `git status --short`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target codex`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target claude-code`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target groq`
- `python C:/Users/roeea/.codex/skills/agent-inbox-checker/scripts/check_inbox.py --target human`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`
- `python tools/validate_phase4.py`
- `python tools/validate_phase5.py`
- `python tools/validate_phase6.py`
- `python tools/validate_phase7.py`
- `python tools/validate_phase8.py`
- `python tools/validate_phase9.py`
- `python tools/validate_phase10.py`
- `python tools/validate_phase11.py`
- `python tools/validate_phase12.py`
- `python tools/validate_phase13.py`

Out of scope:
- Broker integration.
- Live execution.
- Model promotion.
- Production data approval.
- Implementing Claude Code's assigned code changes directly unless Codex
  explicitly decides to take back that implementation work.

Notes:
The current recommended next implementation task is Phase 14: real-data
decision intake. Codex should keep that phase blocked from production effects
unless explicit human decision records exist.
