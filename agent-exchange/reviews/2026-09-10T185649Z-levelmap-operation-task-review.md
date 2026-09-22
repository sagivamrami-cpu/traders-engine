## Spec Compliance

Spec compliance: PASS for the Task1 requirements visible in the supplied diff.

- All four required additions are present. Raw forwarding and the actual lazy shape predicate are implemented in `trading_system/tree_replay/_vendor/basis_operation.py:8` and `:14`. The required reader construction, optional session clock, and build composition appear in `trading_system/tree_replay/_vendor/levelmap_operation.py:10`, `:44`, and `:86`.
- Literal tests cover advancing fetch time, early returns, explicit time, venue boundaries, duplicate/exact opens, splice thresholds, actual full-family output/type identity, read ordering, and conditional PSY fallback: `tests/tree_replay/test_levelmap_operation.py:57`, `:65`, `:85`, `:116`, `:176`, `:198`, `:231`, and `:248`.
- Limits and unchanged public API intent are documented in `docs/architecture/LEVELMAP-OPERATION-CLOCK-USAGE.md:15` and `:29`; the supplied diff contains only the four requested additions.
- Cannot verify from this diff: exact original blob/import/signature/AST parity and the complete inherited dependency closure. These are explicitly pending Task2 in `docs/architecture/LEVELMAP-OPERATION-CLOCK-USAGE.md:37`. The controller must obtain that audit before component acceptance; this is not a missing Task1 deliverable.

## Strengths

- Clock reads remain at the relevant operation: session time follows fetch, correction gates, and index conversion (`trading_system/tree_replay/_vendor/levelmap_operation.py:31`); only the non-native splice branch reads time in the predicate (`trading_system/tree_replay/_vendor/basis_operation.py:40`). No added forwarding catches or cached time obscure failures.
- The reader reuses actual `NamedLevel`, EMA, range, session, back-day, and quarter dependencies (`trading_system/tree_replay/_vendor/levelmap_operation.py:3`). The full-build test asserts the ordered literal prices, kinds, correction identity, and raw calls (`tests/tree_replay/test_levelmap_operation.py:198`), rather than supplying final levels or broker verdicts.

## Issues

### Critical

None.

### Important

- **I1 — Plan-mandated duplication.** `trading_system/tree_replay/_vendor/levelmap_operation.py:109` copies the family-selection/output block from `trading_system/tree_replay/_vendor/levelmap_build.py:149`; the session eligibility/output block at `levelmap_operation.py:45` likewise overlaps `levelmap_build.py:54`. This creates two maintained copies of the same gates and missing-output behavior, so a future source update can change one variant while leaving the other behind. The contract explicitly mandates these separate full bodies (`docs/architecture/LEVELMAP-OPERATION-CLOCK-CONTRACT.md:26` and `:30`). The requested task-reviewer template explicitly classifies plan-mandated verbatim logic duplication as Important, so this finding is retained despite the source-projection rationale. No current behavioral divergence was found. Resolution requires a controller ruling on the mandated duplication and its independent parity-audit mitigation, or an authorized design revision; do not unilaterally refactor the fixed-T API or alter original branches.

### Minor

None.

## Assessment

Task quality: NEEDS FIXES / explicit disposition of I1 under the requested rubric.

The visible implementation preserves the required operation clocks, source gates, dependency identities, and exception boundaries. The quality objection is the rubric's mandatory treatment of duplicated source bodies, not an observed incorrect output; pinned-source certification remains a separate Task2 gate.

## Verification reviewed

- Read the complete supplied Task1 diff once; base and head both `c1b6071633c55376c64f0a98ece843706f420f49`, with full untracked additions included.
- Reported GREEN command: `python -B -m pytest tests/tree_replay/test_levelmap_operation.py tests/tree_replay/test_levelmap.py tests/tree_replay/test_levelmap_source.py tests/tree_replay/test_correction_source.py -q --tb=short -p no:cacheprovider`. Implementer reports **291 passed, 162.30s, exit 0, no warnings** in `task-1-report.md:7`. This result was reviewed, not independently rerun.
- Reported RED: 48 normal missing-reader cases, 6.92s (`task-1-report.md:3`); the report supplies a summary, not a raw RED transcript. No independent TDD-history claim is made.
- Focused unchanged-code check for duplication and dependency compatibility: read `levelmap_build.py`, confirming the duplicated blocks and the reused `_ema_levels(..., source=...)` interface at `:95`.
- Focused reference-fixture check: inspected `tests/tree_replay/test_levelmap_source.py:119`; the operation test retains its hand-specified family values and kinds while adding real predicate/clock inputs.
- No tests or executable probes were run; no preserved original source was imported, executed, or inspected. No git commands, subagents, commits, or production edits were performed. Only this assigned review was written using `apply_patch`.

Reviewer: Codex independent Task1 sidecar

Request: `agent-exchange/inbox/codex/2026-09-10T185649Z-levelmap-operation-task-review.md`

Created at: 2026-09-10 18:58:05 UTC

Status: REVIEW_READY_FOR_CODEX

Open questions: Controller disposition of I1; subsequent Task2 source-audit evidence.

Recommended next action: Resolve the explicitly plan-mandated quality finding without changing source semantics; complete the separately planned source audit and final review before component acceptance.

## Scoped addendum — 2026-09-10 18:59:44 UTC

Spec compliance of the docstring fix: PASS on static review. Task quality for this supplement and the I1 disposition: APPROVED; amended-file verification and gate acceptance remain pending.

- **I1 disposition: ADDRESSED by explicit controller ruling, retained as a disclosed maintenance obligation.** `.superpowers/sdd/2026-09-10-levelmap-operation-clock/progress.md:34` records the decision, mitigation, and cost at future source upgrades. `docs/architecture/LEVELMAP-OPERATION-CLOCK-CONTRACT.md:36` makes invocation of the existing full fixed-T graph audit mandatory for operation-reader certification. Requiring both exact source projections to pass that combined certification directly addresses the one-sided drift risk while preserving the two clock contracts. This accepts the disposition; it does not independently certify the new auditor's implementation, which is outside this supplement.
- **Docstring correction: ADDRESSED; no new breakage found.** The two hunks in `.superpowers/sdd/2026-09-10-levelmap-operation-clock/task-1-fix-diff.md:5` and `:19` replace only the first string-literal statements in `BasisOperation.broker_shape_ok` and `LevelmapOperation._session_open_levels`. Explicit `\n` escapes preserve line breaks and four-space source indentation inside the values, including their trailing newline/indentation. Both remain valid Python docstrings; parameters, comments outside the literals, calculations, catches, calls, and clock placement are untouched. The correction matches the exact-literal requirement now stated at `docs/architecture/LEVELMAP-OPERATION-CLOCK-CONTRACT.md:40`.
- **New findings:** none; no new Critical, Important, or Minor issues in the supplement. The earlier quality verdict is superseded for I1 by the accepted disposition above.
- **Verification boundary:** reviewed only the supplied narrow fix and disposition paragraphs. No original-review repetition, runtime/source-audit execution, source inspection, subagents, or suite rerun. Session **54448 remains pending according to the supplied status**; the earlier 291-pass result predates these literal corrections and is not amended-file evidence. Terminal combined-test evidence and Task2 audit acceptance are still required before gate acceptance.

Recommended next action: Supply terminal evidence for the amended files and complete the separately scoped Task2 audit review. No additional Task1 implementation change is requested by this addendum.
