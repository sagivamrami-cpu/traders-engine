# Task 2 independent review: source-pinned outer-pass intake

Status: CHANGES_REQUESTED

## Scope reviewed

Read-only review of Task 2 in the closed-bar causal replay plan and design,
the implementation report, all five current Task 2 deliverables, and retained
`chart-desk/scripts/market_watch.py` as text only. The retained checkout was
not imported, compiled, or executed.

## Critical

None.

## Important

1. **Outer-gate proof can return `VERIFIED` after a gate is disabled.**
   `causal_replay_source._project_required_order()` verifies each outer-gate
   call's name and fixed line number, and `_validate_projection()` verifies
   only that those lines precede `_trk.record`. It does not prove the result is
   tested or that the rejecting branch reaches `continue` before record.

   Exact reproduction (no file writes; retained source read/AST-parsed only):

   ```python
   changed = original.replace("            if outside:\\n", "            if False:\\n", 1)
   audit.BLOB = git_blob_sha1(changed.encode("utf-8"))
   # supply changed text only through an in-memory Path.read_text substitute
   report = audit.check_source_parity(RETAINED_ROOT)
   ```

   Result: `status == "VERIFIED"` and `blockers == []`.

   The `_outside()` call remains at line 1034, all projected line numbers are
   unchanged, and the fixed source pin would normally block a changed checkout.
   However, the Task 2 requirement is mutation-resistant proof that every
   designated outer gate occurs before record; the proof must remain sound when
   a future approved pin is deliberately updated. Add AST/control-flow checks
   for the gate predicates and their rejection `continue` paths (including the
   producer-arbitration/dedup path), and regression mutations that force each
   gate false/remove its `continue` while preserving the call and line.

## Minor

1. The suite mutates a tree walk before reversal but has no direct
   engine-before-reversal mutation. The implementation's line comparison would
   block that change, but Task 2 explicitly calls for tree/engine placement
   mutation coverage. Add the engine counterpart to make the evidence match
   the contract.

## Exact checks completed

- Confirmed the manifest and code pin chart-desk commit
  `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and
  `scripts/market_watch.py` blob
  `f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b`. The auditor limits retained
  checkout interaction to read-only Git identity queries, text reading, and
  `ast.parse`; no retained-source import/compile/execute path was found.
- Confirmed the current source projection checks load, pre-producer save,
  locked `closeout_check() + check()`, lifecycle gate, reversal before tree
  and engine, alert-only record guard, and final state save at the pinned
  locations.
- Confirmed normal reports label the six outer gates as
  `UNWIRED_OUTER_ADMISSION`, and all normal and blocked report constructors
  retain `ready_for_replay == False` and `ready_for_training == False`.
- Confirmed the CLI catches parser/auditor/report-shape failures, emits JSON
  only, and maps verified/blocked results to exit 0/2.
- Ran:

  ```text
  python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
  25 passed in 4.12s

  python -B tools/check_causal_replay_source_parity.py --source-root C:\\Users\\roeea\\AppData\\Local\\Temp\\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
  ```

  The CLI returned JSON `VERIFIED`, exit 0, with both readiness flags false.

## Required revision evidence

Add the failing gate-control-flow and engine-order mutations, make the AST
projection reject them with a schema-valid `BLOCKED` report and both readiness
flags false, then rerun the focused suite and pinned CLI command.
