# Agent Exchange Request

Target:
Codex scoped implementer

Sender:
Codex controller

Created at:
2026-09-09T10:33:39Z

Status:
ACCEPTED_BY_CODEX

Objective:
Implement source-faithful, explicit-clock correction evidence for historical level maps.

Scope:
Task 1 in docs/superpowers/plans/2026-09-09-correction-asof.md, extracted into its own task brief.

Required inputs:
Pinned chartdesk/basis.py; existing bars/levels validators and source audit patterns.

Contracts:
Exact source Correction and native set; narrowly audited replay-clock specialization; immutable as-of evidence. Explicit caller freshness and lookback. ASSESSED is not admission.

Non-negotiables:
- point-in-time correctness
- no invented thresholds, feeds, aliases or features
- no production approval by implication
- no live trading, broker execution, capital allocation, downloads or training
- preserve dirty checkout; no commits, cleanup, nested agents or worktrees

Deliverables:
Task 1 files, test-first evidence and result at agent-exchange/status/2026-09-09T103339Z-worker-correction-asof.md.

Verification commands:
python -m pytest tests/tree_replay/test_correction_source.py tests/tree_replay/test_corrections.py -q --tb=short
python tools/check_correction_source_parity.py

Out of scope:
Full level map, applying price offsets, producer admission, market labels, model training.

Notes:
Only Codex controller updates inbox status after independent intake.
