# Lifecycle OPEN protection — final read-only review

Reviewer: Codex

Target request: Direct user request — final read-only review of lifecycle OPEN
protection; no implementation, commit, push, or subagent work.

Created at: 2026-09-14T14:00:00Z

Status: REVIEW_READY_FOR_CODEX

Verdict: PASS

## Scope reviewed

- `docs/superpowers/plans/2026-09-14-lifecycle-open-protection-source.md`
- `docs/architecture/LIFECYCLE-OPEN-PROTECTION-SOURCE-INTAKE.md`
- `trading_system/tree_replay/_vendor/lifecycle_open_protection.py`
- `trading_system/tree_spec/lifecycle_open_protection_source.py`
- `tools/check_lifecycle_open_protection_source_parity.py`
- both runtime and source-auditor test modules
- both task reports under `.superpowers/sdd/2026-09-14-lifecycle-open-protection-source/`
- pinned `chart-desk/chartdesk/tracker.py` lines 2690–2715 at commit
  `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, blob
  `b616b34022e436545d8c1daf85eced51614fd74e`

## Findings

- The runtime projects only the source's conservative ambiguity branch.  It
  invokes the accepted directional predicate with `(low, high)`, marks an
  unhit-target ambiguity `STOPPED` and a post-hit ambiguity `DONE`, resolves
  the source message/result, and appends the raw outcome fact.
- The asymmetric long/short tests prove the physical adverse/favourable
  extrema.  Their executable mutation swaps the predicate inputs to
  `(high, low)` and then proves no resolution, no trade mutation, no clock
  call, and no raw fact.  This closes the earlier low/high coverage defect.
- The auditor pins and parses only the physical source slice, checks its full
  ordered AST including the ambiguity branch, compares the runtime AST to its
  allowed projection, and fail-closes on source identity, blob, projection, or
  child-report drift.
- The CLI validates its report shape and serializability and returns blocked
  JSON on audit, parse, or serialization failure.  Child proofs for
  `lifecycle_outcome_shelf` and `lifecycle_transitions` were verified by the
  live CLI report.
- Replay and training readiness are explicitly `false` in the top-level and
  verified child reports.  This slice contains no ordinary OPEN progression,
  economic P&L, dataset construction, model training, delivery, or live-trade
  claim.

## Verification reviewed

Passed:

```powershell
python -m pytest -q tests/tree_replay/test_lifecycle_open_protection.py tests/tree_spec/test_lifecycle_open_protection_source.py
# 27 passed in 26.26s

python -B tools/check_lifecycle_open_protection_source_parity.py --source-root 'C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'
# VERIFIED; blockers=[]; source_subset_verified=true;
# ready_for_replay=false; ready_for_training=false
```

The scoped worktree files are untracked pre-existing implementation artifacts;
this review changed only this review record.  No commit, push, or subagent was
used.

Open questions: None within this narrow source-projection scope.

Recommended next action: Record Codex acceptance for this conservative OPEN
protection prerequisite, then continue with the separately scoped ordinary
OPEN progression/target/protection ordering work.  Do not infer replay,
economic, dataset, training, model, or live-trading readiness.
