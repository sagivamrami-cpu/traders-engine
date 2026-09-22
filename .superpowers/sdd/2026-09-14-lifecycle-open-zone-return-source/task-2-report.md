# Task 2 report — lifecycle OPEN zone-return source

## Scope

Implemented Task 2 only: a read-only source auditor, explicit-root JSON CLI,
and focused source-audit tests for the pinned OPEN zone-return helper and its
live-call boundary. The auditor reads/parses retained source text and vendor
runtime text; it never imports, compiles, or executes retained `chart-desk`
source. No runtime behavior, resolver composition, persistence, delivery,
outcome/economic, replay/dataset/training/model behavior, commit, push,
subagent work, or unrelated artifact changed.

## Changed files

- `trading_system/tree_spec/lifecycle_open_zone_return_source.py`
- `tools/check_lifecycle_open_zone_return_source_parity.py`
- `tests/tree_spec/test_lifecycle_open_zone_return_source.py`
- `.superpowers/sdd/2026-09-14-lifecycle-open-zone-return-source/task-2-report.md`

## Auditor contract

The auditor pins chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and `tracker.py` blob
`b616b34022e436545d8c1daf85eced51614fd74e`. It verifies, as AST/text only:

- exact physical helper slice `tracker.py:1046–1106`, including the
  `0/0` no-excursion guard, malformed-marker fallback and `<=` target-only
  rearm, direction-specific entry-band condition, real `still_valid(t)`
  recheck/caught-error branch, ordered journey/recheck/footer assembly, and
  the only direct marker assignment `t["zone_return_at"] = gone`;
- exact live-call boundary `tracker.py:2751–2759`: helper call, truthy guard,
  append to `t["to_group"]`, then `changed = True`;
- the complete private runtime AST, including construction of
  `Revalidation(source)`, the actual `self.revalidation.still_valid(trade)`
  call, and one direct `zone_return_at` mutation; and
- accepted source-proof graphs for `lifecycle_transitions`,
  `lifecycle_primitives` (including `lifecycle_bars`/entry-band,
  `desk_success`, and `lifecycle_voice`), and `revalidation`.

Every auditor failure remains a schema-valid `BLOCKED` report with
`ready_for_replay=false` and `ready_for_training=false`. The CLI requires an
explicit `--source-root`, prints valid JSON on normal, parser, audit, malformed
report, and serialization paths, and exits `0` only for `VERIFIED`; otherwise
it exits `2`.

## Inherited revalidation boundary

The proof deliberately preserves the real `Revalidation(source)` child rather
than substituting a label port. Its accepted offline source contract may fetch
corrected evidence and its shadow path may attempt source-owned shadow writes.
The new audit records that child graph; it does not claim the composed
zone-return call is feed-free or effect-free. Zone-return itself remains the
existing label-only projection whose direct state write is `zone_return_at`.

## TDD evidence

### RED

Before adding the auditor and CLI:

```powershell
python -B -m pytest tests/tree_spec/test_lifecycle_open_zone_return_source.py -q --tb=short -p no:cacheprovider
```

Result: `20 failed in 1.17s`. Failures were the expected missing
`lifecycle_open_zone_return_source` module and missing CLI entrypoint.

### Green and correction

The first implementation run produced `18 passed, 2 failed`: both valid-source
checks were blocked by `SOURCE_BLOB_MISMATCH:tracker.py`. Root-cause inspection
showed the new auditor encoded the Git blob header separator as the two literal
characters `\\0`, unlike the accepted auditors' NUL separator. The single
audit-only correction restored `\0`; no retained or runtime source changed.

The focused suite then passed:

```text
20 passed in 19.01s
```

The tests reject mutations to helper order, no-excursion, `<=` rearm,
directional band, helper recheck; runtime `Revalidation` import/construction/
call, direct marker mutation, and live resolver call; source identity/blob/
root; malformed or re-identified children; and all CLI blocked-JSON paths.

## Final verification

Task 1, its direct helper suite, and the Task 2 audit suite:

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_revalidation.py tests/tree_spec/test_lifecycle_open_zone_return_source.py -q --tb=short -p no:cacheprovider
```

```text
189 passed in 24.69s
```

Explicit-root CLI from the repository:

```powershell
python -B tools/check_lifecycle_open_zone_return_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

Result: exit `0`, `status=VERIFIED`, all three projections checked, required
dependencies `lifecycle_transitions`, `lifecycle_primitives`, and
`revalidation`, no blockers, and both readiness flags false.
