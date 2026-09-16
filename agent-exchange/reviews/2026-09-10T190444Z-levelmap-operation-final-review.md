# Final independent operation-clock component review

Reviewer: Codex independent final-review sidecar

Request: `agent-exchange/inbox/codex/2026-09-10T190444Z-levelmap-operation-final-review.md`

Created at: 2026-09-10 19:06:26 UTC

Status: REVIEW_READY_FOR_CODEX

Spec compliance: PASS.

Quality verdict: APPROVED for seven-file component acceptance.

## Scope and requirements

Reviewed the complete seven-file `final-diff.md`, both task briefs, binding
`LEVELMAP-OPERATION-CLOCK-CONTRACT.md`, implementation plan, source intake,
Task2 report, progress ledger, and Task1/Task2 reviews including the I1 addendum.
Applied the requested `requesting-code-review/code-reviewer.md` rubric.
Base and HEAD are both `c1b6071633c55376c64f0a98ece843706f420f49`; this is a
review of untracked additions, not a committed range or branch merge.

## Strengths and spec compliance

- `basis_operation.py:9` forwards raw fetch/time calls without caching or added
  catches. The actual predicate at `:15` preserves the pure-broker and native
  early returns; only the non-native splice with `tv_from` reads operation time.
  The original 20/7-day comparisons are retained, with no provider verdict seam.
- `levelmap_operation.py:13` retains fetch, empty/provenance checks and index
  conversion before the clock at `:31`. Explicit `now` skips only that read.
  Venue time, exact first opening row, source-none rejection, per-bar splice
  cutoff, and the original exception boundaries remain intact. Compared these
  complete selected bodies with retained original source text, without execution.
- `levelmap_operation.py:72` retains the full original build sequence and unequal
  family gates: daily/ranges/back-days, session opens, conditional hourly/15m PSY,
  EMA, then quarters. It reuses the accepted `NamedLevel`, `_ema_levels`, ranges,
  sessions and other calculation dependencies. The seven additions do not
  modify the fixed-T public implementation or introduce pivots or live behavior.
- `levelmap_operation_source.py:67` independently specifies source imports,
  signatures, constructors, forwarders and exact replacement counts, then
  compares complete ordered candidate modules. Source commit/blob and baseline
  checks at `:92` are independent of candidate declarations. Original docstring
  values remain part of method-body comparison.
- The real inherited audit call at `levelmap_operation_source.py:134` checks the
  fixed-T projection and its graph. Inspection of `check_levelmap_source_parity.py`
  confirmed ordered map/session/composition checks, strict EMA checks and actual
  range/pricing/correction dependency audits. Their declarations include back-days,
  quarters and `EXCHANGE_NATIVE`. Dependency blockers and false-with-empty results
  prevent operation verification. Both readiness flags remain false.
- Runtime tests use raw OHLC/Correction fixtures and literal outputs, including
  advancing fetch time (`test_levelmap_operation.py:59`), early-return clock
  exclusion, explicit time, venue boundaries, splice equality, full level/type
  identity (`:195`), different family times (`:230`), and original PSY catch/fallback
  behavior (`:250`). Audit tests cover candidate/source drift, missing files,
  signatures, duplicate nodes/clocks, ordering, dependency failures, actual inherited
  EMA drift, unrelated-directory CLI execution and source/runtime import guards.

## Issues and finding disposition

### Critical

None.

### Important

No open findings. **I1 — deliberate duplicated source bodies: ADDRESSED.**
The controller ruling in `progress.md` and contract explicitly retains separate
operation-time and fixed-T projections. The required mitigation is implemented:
operation certification invokes the complete fixed-T graph audit as well as its
own whole-module comparison. A one-sided body change cannot retain that combined
certification. This resolves the reported current acceptance concern; maintaining
both projections at a future source upgrade remains a disclosed obligation.
No current behavioral divergence was found, and no refactor is requested.

### Minor

None. New finding IDs: none.

## Verification reviewed

- Independently checked `git status --short`, `git diff --stat`, targeted `git diff`
  and `git rev-parse HEAD`. Existing unrelated changes were left untouched.
- `Get-FileHash` confirmed all seven current SHA256 values exactly match
  `task-2-report.md`. A separate read-only PowerShell comparison reconstructed
  all seven addition bodies from `final-diff.md` and matched each current file,
  normalizing line endings. All seven comparisons passed.
- Reviewed reported combined verification:
  `python -B -m pytest tests/tree_replay/test_levelmap_operation.py tests/tree_spec/test_levelmap_operation_source.py tests/tree_replay/test_levelmap.py tests/tree_replay/test_levelmap_source.py tests/tree_replay/test_correction_source.py -q --tb=short -p no:cacheprovider`
  — terminal 54448: **339 passed, 201.38s, exit 0**, after the docstring correction.
- Reviewed reported verification after five audit-test additions:
  `python -B -m pytest tests/tree_replay/test_levelmap_operation.py tests/tree_spec/test_levelmap_operation_source.py -q --tb=short -p no:cacheprovider`
  — terminal 46454: **101 passed, 17.89s, exit 0** (48 runtime/53 audit).
  These overlap; they are not a current 344-case combined execution.
- Reviewed the reported standalone command
  `python -B tools/check_levelmap_operation_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`
  — **VERIFIED, exit 0**, both projections and inherited graph, no blockers,
  false readiness. Also reviewed the reported two candidate-only mutation probes
  and normal missing-feature RED summaries. These are report evidence, not
  independently reproduced execution or independently observed RED history.
- No suites, audit CLI or executable mutation probes were rerun, as requested.
  Original source was read only. No nested agents, runtime edits, commits, branch
  changes or cleanup. Only this assigned review was written through `apply_patch`.

## Recommendations and assessment

Ready for component acceptance: **Yes**. Ready to merge: **not assessed; outside
this assignment**. The combined implementation meets its specified source and
clock contracts, and current-file hashes bind the reviewed verification evidence.

Open questions: none blocking this component.

Recommended next action: controller may record component acceptance and complete
the planned status/usage/tracker updates. The usage document's pending Task2/final
sentence should be advanced during that already-planned acceptance bookkeeping.
Another runner must supply the pinned checkout through `TR_TREE_SOURCE_ROOT`.
Future source upgrades must re-prove both projections. Causal feed/publication
evidence, full tree/caller/lifecycle composition, economics, datasets and models
remain outside this acceptance; no full-master completion or readiness is implied.
