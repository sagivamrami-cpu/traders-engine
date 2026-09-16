# Agent Exchange Review

Spec compliance: PASS for Task 1 source closure.
Task quality: APPROVED. No Critical or Important findings.

Reviewer: Codex task reviewer
Target request: agent-exchange/inbox/codex/2026-09-09T132000Z-tracker-admission-review.md
Created at: 2026-09-09
Status: REVIEW_READY_FOR_CODEX

## Scope and method

Read the request first, then the named brief, complete implementation report
including rename addendum, complete eight-file task-1-diff.md, and full
docs/architecture/TRACKER-ADMISSION-SOURCE-CONTRACT.md. Applied
superpowers/subagent-driven-development/task-reviewer-prompt.md to both verdicts.
Reviewed the diff in contiguous passes through its final fence; no omitted hunks.
BASE/HEAD in the package is c1b6071633c55376c64f0a98ece843706f420f49; these are
eight new untracked files, not a committed branch comparison.

Read-only inspection used Get-Content and rg, with bounded inherited-dependency
checks described below. No retained-source execution, suite reruns, nested
agents, runtime/test edits, git mutations or external actions. Only this review
artifact was written, via apply_patch. Parent acceptance remains separate.

## Spec compliance and strengths

All eight requested deliverables have full new-file hunks:

| Deliverable | Evidence and assessment |
| --- | --- |
| trading_system/tree_replay/_vendor/tracker_admission.py | :110 per-instance ports; :115 bias/thesis/born calculations precede lock; :163 locked reload, OPEN recheck, exact-geometry dedup/archive, full persisted fields and propagating save. :208 OPEN-only exposure; :425 post-stop order and catches; :499 same-level first-match semantics. |
| trading_system/tree_replay/_vendor/tracker_symbols.py | :155 preserves original pip resolution; whole pure module is included, without a new public instrument adapter. |
| trading_system/tree_spec/tracker_admission_source.py | :40 independently enumerates source blobs and inherited projections; :76 and :109 enumerate scoped substitutions; :150 demands exactly one matching substitution; :174 compares the complete ordered adapted module; :209 preserves Plan fields/four properties and audits inherited modules. :255 checks explicit source identities and manifest independently of runtime. |
| configs/trees/tracker-admission-source-contracts.json | :1 declares both exact commits, fixed blobs, methods, imports, substitutions and false readiness. Equality against independent authority prevents narrowing the manifest into a passing audit. |
| tools/check_tracker_admission_source_parity.py | :13 requires --source-root and returns a nonzero exit for blocked evidence. |
| tests/tree_replay/test_tracker_admission.py | :112 asserts complete stored rows and call order; :163 simulates lock-time state change; :171 asserts save propagation; :181, :191, :200 and :213 cover signed bias, age, real swing and pip boundaries. |
| tests/tree_spec/test_tracker_admission_source.py | :22 requires pinned evidence without skip; :29 checks missing-root blockers; :50, :66, :87 and :106 reject runtime/dependency/source mutations, manifest changes, pins and missing substitution preconditions. |
| docs/architecture/TRACKER-ADMISSION-SOURCE-USAGE.md | :15 documents explicit ports and caller gate responsibility; :60 identifies the additional required born_in_zone helper; :104 and :132 distinguish source closure from causal binding, lifecycle and readiness. |

The lazy reader refinement is implemented correctly: runtime :39 opens the
factory within the original try/with and preserves seek/expand/drop/fallback;
:299 passes the factory without calling it. Tests :327 independently assert
returned bytes, exact seeks, 400,000 bytes consumed and closure over a virtual
10 GB prefix. Tests :483 cover reader/context failures. The documented cap is
not incorrectly described as an absolute read limit.

Rejection tests :267, :278, :294 and :503 exercise equal-time first selection,
malformed trailing JSON, inclusive age/gap boundaries, non-rejection byte
ejection, newest selection and rounding. This tests source bytes rather than
substituting a semantic rejection list. Quote/thesis tests :240, :249 and :312
cover the asymmetric source conditions. Born-open evidence remains explicitly
unverified at runtime :186 and test :128; no economic fill is inferred.

The isolated test at :354 records forbidden access attempts even when source
catches could swallow them. The distinct runtime/audit test basenames resolve
the collection conflict without changing global pytest behavior. The 550-line
runtime is largely the prescribed complete source projection and source
documentation; its size does not introduce a separate maintainability blocker.

## Findings

Critical: none.
Important: none.
Minor: no actionable task defect found. The package includes Git LF/CRLF
conversion warnings, and the report identifies existing line-ending warnings;
these are packaging/check noise, not a demonstrated runtime or test failure.

## Bounded inherited-source checks and limits

- Risk: the audited helper list might omit a dependency actually used by
  admission or alter its binding. Read unchanged private pricing.py,
  basis_symbols.py, admission_quality.py and admission_swing.py; inspected
  retained tradeplan/basis/quality/zones import and definition declarations as
  inert text. Pricing entry_zone uses the included canonical alias map;
  anchor_names uses the included regex/constants; _last_swing uses SWING_K and
  supplied frame values. The latter retains the source low/high asymmetry for
  up=short. Runtime :76 also includes the otherwise missing source
  tradeplan.born_in_zone; inspected original tradeplan.py:309 and :316 directly.
- Risk: inherited pricing's local quarters import or package initialization
  might introduce unaudited host access. Read quarters.py and the unchanged
  tree_replay, _vendor and tree_spec package initializers. Quarters is pure and
  included in the new audit; these initializers contain documentation only.
  Inspected retained tracker.py's import/constants prefix to check the source
  bindings replaced by the explicit ports. No retained module was imported.
- Cannot independently certify unchanged source identity/parity solely from
  new-file hunks. The above reads establish dependency shape, while the parent's
  fresh source CLI supplies execution evidence for the seven complete ordered
  projections and pinned roots/blobs. This reviewer did not repeat that audit.
- Cannot verify future causal port implementations, real historical coverage,
  transactional sinks/lock behavior, source log production/spacing and intra-pass
  publication ordering, or subsequent lifecycle from this diff. They are outside
  Task 1, explicitly unfinished at usage :132, and must not inherit acceptance
  from the private closure.
- Original catches remain consequential: runtime :425 and :499 can return no
  block after malformed/unavailable state; :299 can propagate malformed numeric
  rejection timestamps; tests :299 and :517 preserve those outcomes. These are
  baseline behaviors, not evidence of complete historical decisions. Later
  ports must record unavailable/error dependencies as required at usage :104.
  Neither optional telemetry nor source advisory OPEN is a new economic gate.
- The isolated test guards new-module import and exercised execution after
  preloading selected dependencies; it is not certification of every third-party
  import or every possible caller-supplied port. Full-module AST comparisons
  and the bounded import checks complement that test.

## Verification reviewed

Read agent-exchange/status/2026-09-09T132100Z-tracker-admission-intake.md:

```powershell
python -m pytest tests/tree_replay/test_tracker_admission.py tests/tree_spec/test_tracker_admission_source.py tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py tests/tree_replay/test_pricing_source.py tests/tree_replay/test_pricing.py tests/tree_replay/test_state.py -q --tb=short
```

Parent: PASS, 428 passed in 36.09s, exit 0, default mode. Worker reports the same
command passing 428 in 35.45s. Parent also reports fresh PASS/VERIFIED, seven
checked projections, empty blockers and false readiness for:

```powershell
python tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

Parent confirms runtime/auditor/renamed-test hashes match the report snapshot,
and no runtime/test edits followed packaging. Worker RED/GREEN chronology was
reviewed as reported historical evidence, including its explicit distinction
between missing-module/collection RED and behavioral failures. It was not
independently reproduced by this reviewer. No concrete remaining doubt required
a focused execution probe or repetition of these suites.

Open questions: no Task 1 implementation blocker identified; the scoped limits
above remain for controller reconciliation and later binding.

Recommended next action: parent may proceed to the planned final component
review and record scoped acceptance. This verdict does not certify whole-loop
replay, training, economic labels or live use.
