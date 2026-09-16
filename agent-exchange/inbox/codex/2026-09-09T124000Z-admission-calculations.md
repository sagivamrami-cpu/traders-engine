# Agent Exchange Request

Target:
Codex implementation worker

Sender:
Codex controller

Created at:
2026-09-09

Status:
ACTIONABLE

Objective:
Implement Task1 original admission calculation closure as a disjoint sidecar.

Scope:
Read .superpowers/sdd/2026-09-09-admission-dependencies/task-1-brief.md first.
Only files listed there and the report/result paths below are writable.

Required inputs:
docs/architecture/ADMISSION-DEPENDENCIES-CONTRACT.md (source calculations and boundaries)
AGENTS.md and exchange startup files; pinned retained source from brief.

Contracts:
Use exact source definitions and a mutation-resistant complete dependency audit.
No commits or pushes; use apply_patch; no nested agents. Work in this checkout.
Do not change any previous accepted runtime/vendor/audit files. Parent works on
state.py/test_state.py and documentation independently.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:
Full implementation report .superpowers/sdd/2026-09-09-admission-dependencies/task-1-report.md
and result agent-exchange/status/2026-09-09T124000Z-worker-admission-calculations.md.
Name changed paths, exact RED/GREEN commands/output, self-review and concerns.

Verification commands:
As brief, focused tests and explicit-root source audit. Do not run whole repo suite.

Out of scope:
Public admission orchestration, tracker lifecycle simulation, datasets/models.
