# SDD ledger — plan: docs/superpowers/plans/2026-09-09-historical-levelmap-core.md

Spec: approved master + HISTORICAL-LEVELMAP-SOURCE-CONTRACT.md.
BASE=HEAD c1b6071633c55376c64f0a98ece843706f420f49; dirty in-place branch preserved.
No commits/worktrees/cleanup. Previous goal turn: progress, correction accepted.

| Preflight check | Producer / consumer | Result |
| --- | --- | --- |
| Task1 internal | pure graph + explicit source/clock + exact AST audit | No live imports; complete graph includes all map families |
| Task2 internal | calendar/base/period inputs -> causal frame rows | Known base precision; no future OHLC, supplied label != availability |
| Task3 internal | request bindings -> lazy source -> graph -> level snapshot | ASSESSED != shape verified != admission; no generic blanket veto |
| Task1 -> Task3 | build_at(source,decision_time) + source.fetch/broker_shape methods | Signatures explicit; original fetch ordering and exceptions retained |
| Task2 -> Task3 | FrameSpec/build_frame_asof rows/status/hash | Only AVAILABLE rows become fresh DataFrame; no supplied ready flags trusted |
| Task1 vs Task2 | disjoint source closure vs frame builder files | One worker plus parent critical path, no shared implementation files |

Task1: in progress, Dirac01a085d2-1788-7293-963e-65b3a8757710; owns source closure only.
Task2: controller implementation. Baseline periods/session tests69 passed0.77s.
RED55 failures (missing assigned module assertions) before frames.py existed.
Initial GREEN attempt45passed/10failed: existing select_closed_bars requires a
strictly positive age integer, while new explicit frame policy supports zero.
Root cause traced to bars.py:133 through session_bars; preserve existing selector
contract and enforce the exact frame policy after compatible selection.
Task2 GREEN59 passed0.71s. Additional RED2cases proved a missing string guard
for unhashable timeframe inputs; fixed with ValueError contract. Two later
characterization cases are not claimed as new RED behavior.
Task2 independent reviewer Aquinas01a085d9-6438-7973-97f0-23731cbb4fc4 pending;
actual three-file diff packaged with brief/report and public review request.
Task1 dependency preflight: older EMA audit trusts manifest blob values/module
order. Bound new graph audit to independent indicators blob and ordered existing
EMA projections, with coordinated drift/reorder regressions; worker notified and
both plan/brief clarified. No old tool mutation or trading policy change.
Task3: pending accepted dependencies.
No open/parked/deferred findings or rulings.
Task2 review returned spec FAIL/quality Needs fixes: required cross-day/month,
calendar coverage and final1h/4h regressions absent; upsampling case masks its
guard with an earlier identity error. No demonstrated production defect.
Task2 fix round1 planned: narrowly complete test evidence, then scoped re-review.
Fix implementer Bohr01a085dc-46e4-7a71-9c5f-949d91c83d38 active, test-only scope.
Task3 snapshot clock semantics clarified in plan: map state depends on T itself,
so snapshot observed/available=T; actual price timestamps remain in dependencies.
Task 2: fix round 1/5 (2 addressed, 0 open; no commits). Kant scoped re-review
task-2-fix-1-review.md clean. Parent fresh69passed0.57s; acceptance recorded in
agent-exchange/status/2026-09-09T111800Z-codex-historical-frames.md.
Task 2: complete (uncommitted additions, review clean). Fixer/re-reviewer closed.
Task1 worker returned146passed96.96s, sourceauditPASS. Parent sourceauditPASS;
independent combined tests in progress. Lorentz01a085e2-a81d-7c31-96f4-af1e3faa48d2
reviewing actual seven-file diff under request2026-09-09T111600Z.
Parent combined verification finished: python -m pytest tests/tree_replay/test_frames.py
tests/tree_replay/test_levelmap_source.py -q --tb=short ->215passed96.46s, exit0.
Task1 independent review pending, not accepted from tests alone.
Task 1: complete (uncommitted additions, review clean). Lorentz specPASS and
qualityApproved; parent215passed96.46s +auditPASS; durable acceptance
agent-exchange/status/2026-09-09T112000Z-codex-levelmap-source.md.
Task3 prerequisites accepted. No parked/deferred findings or rulings.
Task3: in progress, Huygens01a085e5-4880-73b1-9ac7-55ab5aab5850; owns public
adapter/tests/usage only. Controller owns final integration and memory updates.
All six source CLIs verified by parent while Task3 develops. range/correction/
levelmap used default retained root; ema/reversal/pricing used explicit
--source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk.
All final calls exit0 with blockers=[] and readiness false. Initial calls to the
older three CLIs omitted required --source-root and exited1 with usage errors;
corrected arguments, no code fix or audit failure claimed.
Task3 handoff received: worker40passed5.65s, parent40passed5.59s. Read detailed
report/result/request, gitstatus/diff and adapter. Actual three-file diff packaged.
Euclid01a085ed-66cf-76e1-bdb3-b5aecea9662b task review active under112900Z request.
Parent integration session20115 and broad session82313 running; legacy validators
explicitly excluded only in broad command. Do not start duplicate runs while active.
Task3 scoped implementation review Euclid: specPASS, qualityAPPROVED, no findings.
Parent resolved prerequisite audit/acceptance obligations via Task1/2 records and
six successful audit CLIs. Integration/broad/final combined review still pending;
do not mark whole Task3 complete until those gates close. Memory scope documented.
Parent integration complete:1597passed182.72s exit0; session20115 terminal.
Broad session82313 still running. Final reviewer Noether01a085f0-5d14-7c01-ab99-3b09540f4206
active with actual combined diff under113200Z final-review request.
Parent broad complete: python -m pytest -q --ignore-glob='*validator*' --tb=short
->1969passed247.11s exit0. Legacy validators not certified. Session82313 terminal.
No active test processes remain; final combined review still pending.
Final combined review Noether specPASS/qualityAPPROVED, no findings. Controller
read review and resolved remaining bookkeeping obligations. Runtime code unchanged.
Task 3: complete (uncommitted additions, review clean). All255component tests,
1597integration and1969broad passed, sourceauditsPASS; legacy validators excluded.
Durable combined acceptance:agent-exchange/status/2026-09-09T113512Z-codex-historical-levelmap.md.
All three component tasks complete. No parked/deferred findings or Ruling entries.
Full master objective active/incomplete; next original producer admission/M5-M15
selection and timestamp compatibility. No dataset/model or market-performance claim.
Preserve scratch/no commits/cleanup; no active test sessions. Final reviewer closed
after intake. Acceptance patch initially failed context verification atomically;
confirmed no partial writes, corrected the doc anchor and reapplied successfully.
