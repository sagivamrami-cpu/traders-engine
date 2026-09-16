### Task 5: Usage documentation, full acceptance and independent review

**Files:**
- Create: `docs/architecture/CAUSAL-REPLAY-USAGE.md`
- Modify: `AGENTS.md`
- Modify: `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md`
- Modify: `docs/superpowers/plans/2026-09-15-closed-bar-causal-replay.md`
- Create: `agent-exchange/status/<UTC>-codex-closed-bar-causal-replay.md`

**Interfaces:**
- Usage documentation exposes only supplied-evidence construction, run/resume,
  ledger inspection, source-audit command and the complete excluded-scope list.
- Acceptance status reports exact test/CLI evidence and says training readiness
  is false.

- [ ] **Step 1: Write the user-facing usage contract before acceptance**

```python
ledger = ClosedBarCausalReplay(
    bundle, clock=ReplayClock(bundle.start_at), watch=watch,
    admission=admission, reversal_inputs=inputs,
).run()
assert all(row.outcome != "SUCCESS" for row in ledger.records)
assert all("net_pnl" not in row.as_dict() for row in ledger.records)
```

Document that the run uses synthetic/supplied evidence only; historical vendor
data, raw-data retention, outer admission, new tracker registration, economics,
dataset construction and model fitting remain separate work and permissions.

- [ ] **Step 2: Run all acceptance evidence**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_replay/test_causal_replay.py tests/tree_spec/test_causal_replay_source.py tests/tree_replay/test_admission_context.py tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider`

Run: `python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Expected: every test passes; CLI reports `VERIFIED`; both readiness flags are false.

- [ ] **Step 3: Obtain independent final review**

The reviewer must inspect the source-order audit, contracts, checkpoint restore,
runner order and test mutations. The review must reject any new tracker record,
delivery, economic label, raw-data write, source execution or readiness claim.

- [ ] **Step 4: Record bounded acceptance**

Mark completed checkboxes only after the evidence and final review pass. Update
the tracker to state precisely: closed-bar causal replay now records raw
internal-reversal observations and supplied tracker lifecycle, while full outer
admission, remaining producers, economics, dataset, training, evaluation and
all production permissions remain open.

## Self-Review

- Spec coverage: Tasks 1 and 3 implement evidence/ledger/checkpoint contracts; Task 2 pins source order; Task 4 connects the accepted components without creating new trades; Task 5 documents and independently accepts every boundary.
- Placeholder scan: every task declares files, exported interfaces, failing tests, commands and expected results; no task infers trading, cost, data or source policy.
- Type consistency: Task 1 bundle/anchor/ledger types feed Task 3 checkpoints and Task 4 runner; Task 3 shared `ReplayClock` is consumed by the Task 4 watch/admission pair; Task 2 remains static and is never imported by the runtime.
