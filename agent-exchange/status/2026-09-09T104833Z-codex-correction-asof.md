# Agent Exchange Result

Target:
Roee, Sagiv and project agents

Sender:
Codex controller

Created at:
2026-09-09T10:48:33Z

Request:
agent-exchange/inbox/codex/2026-09-09T103339Z-correction-asof.md
agent-exchange/inbox/codex/2026-09-09T104507Z-correction-final-review.md

Status:
ACCEPTED_BY_CODEX

Summary:
Accepted the scoped correction-evidence component after independent task and
whole-component reviews plus controller verification. This advances historical
level-map dependencies; it does not complete the approved full A-I plan.

Implemented immutable caller-supplied correction/frame evidence, structural and
point-in-time checks, exact source unverified/native/proxy predicates, and a
narrowly audited explicit-clock specialization. Missing/future/delayed/stale
evidence is blocked with null payload and predicates. Eligible proxy/unverified
evidence stays ASSESSED with original flags, not automatic admission or failure.
No offsets are applied and no input frame is independently certified.
Both readiness flags remain false on every assessment and audit report.

Changed files:

- trading_system/tree_replay/_vendor/correction.py
- trading_system/tree_replay/corrections.py
- tools/check_correction_source_parity.py
- configs/trees/correction-source-contracts.json
- tests/tree_replay/test_correction_source.py
- tests/tree_replay/test_corrections.py
- tests/tree_replay/test_correction_range_integration.py
- docs/architecture/CORRECTION-ASOF-USAGE.md
- docs/architecture/HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md
- docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md section21
- docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md
- docs/superpowers/plans/2026-09-09-correction-asof.md
- AGENTS.md, README.md and scoped exchange request/result/review records.

Verification results:

- Baseline source ranges:65 passed1.62s, exit0.
- Worker RED:201 expected missing-module assertion failures before production
  edits; GREEN206 passed21.83s, exit0. Five later replay-hook characterization
  cases and the controller integration test do not claim an additional RED.
  Test-first chronology is worker evidence; parent observed tests before the
  production modules appeared but did not independently repeat the RED run.
- Controller: python -m pytest tests/tree_replay/test_correction_source.py
  tests/tree_replay/test_corrections.py tests/tree_replay/test_correction_range_integration.py
  -q --tb=short:207 passed20.75s, exit0.
- Controller: python tools/check_correction_source_parity.py:PASS exit0,
  no blockers, subset verified, replay/training readiness false.
- Controller: python -m pytest tests/tree_replay tests/tree_spec
  tests/data_foundation/test_sessions.py -q --tb=short:1342 passed46.09s, exit0.
- Controller: python -m pytest -q --ignore-glob='*validator*' --tb=short:
  1714 passed103.36s, exit0. Legacy validators explicitly excluded and not
  certified by this run. These totals overlap; they must not be summed.
- git diff --check:exit0, existing CRLF advisories. New eight component files
  also inspected with git diff --no-index --check from NUL:exit1 for additions,
  CRLF advisories only, no whitespace-error diagnostics. Actual complete diffs
  were packaged before independent reviews, including untracked files.
- Task review Pauli:spec PASS, quality Approved, no findings. Its source/test
  execution limits resolved through controller audit and focused run; full
  downstream replay remains explicitly outside this component's acceptance.
- Final review Volta:spec PASS, quality APPROVED, no actionable findings.
  Public report:agent-exchange/reviews/2026-09-09T104507Z-correction-final-review.md.
  Reviewer confirmed source blobs and actual packaged files; runtime execution
  results are attributed to controller, not falsely claimed reviewer reruns.
- Read both original requests and all returned reports; inspected git status,
  actual diffs and current source. HEAD unchanged:
  c1b6071633c55376c64f0a98ece843706f420f49.

Decisions needed:
The GC versus OANDA:XAUUSD real-data rule variant remains in
agent-exchange/inbox/human/2026-09-09T102100Z-gc-versus-source-gold.md.
No mapping, proxy equivalence, production data or retention approval is inferred.
There were no new domain threshold rulings in this component.

Blockers:
None for the accepted component. The full goal remains active and incomplete;
synthetic engineering can proceed. No repeated no-progress/blocking condition.

Recommended next action:
Assemble the daily/weekly/monthly historical map from causally validated period
sequence and bound correction evidence; complete PSY/session/EMA families and
source find/admission/arbitration. Then implement simulation, correct linked
dataset, model comparisons and evaluation under their respective approval gates.

Notes:
Read-only source study confirmed the existing replay hook emits source=replay,
which does not satisfy the OANDA broker-shape gate; this can omit ADR/RD/PSY
families. It is not automatically relabeled as broker data. The public source
contract also records the hook's dictionary note, cursor semantics, publication,
volume/duplicate and calendar limitations. This is not established as the cause
of earlier training results without those runs' inputs and logs.

No live-source execution, real-data access/download, market label generation,
training, alert changes, broker actions, deployment, commits, pushes, worktrees
or cleanup. Unrelated dirty work and this component's review evidence retained.
