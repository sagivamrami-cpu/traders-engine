# Agent Exchange Review

Reviewer: Codex independent final component reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T134100Z-reversal-handoff-final-review.md

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec PASS. Whole-component quality/integration APPROVED for the private
selected-Plan handoff. No actionable Critical, Important or Minor findings.
Ready for controller component acceptance; full causal admission and replay
remain unfinished.

## Review basis

Read the target request first, repository startup files and Codex inbox listing,
the current task's complete brief/report/progress and three-file delta, the
handoff contract, task review133800Z, parent intake133900Z and task
acceptance134100Z, including their original requests. Applied
superpowers:requesting-code-review and its code-reviewer.md checklist directly,
without nested agents. The prior clean verdict was supporting context, not the
basis for this independent assessment.

Reviewed the actual runtime against its saved pre-task baseline, all new tests
and usage documentation, and relevant unchanged selector, pricing serializer,
Plan builder, synthetic fixtures and tracker consumer. Read the preceding
tracker acceptance and all seven final-review132300Z boundary requirements.
Inspected git status and tracked diff. BASE == HEAD is
`c1b6071633c55376c64f0a98ece843706f420f49`; the review covers the uncommitted
three-file component, not the unrelated prior untracked implementation or an
empty commit-range diff.

## Strengths and spec assessment

- `trading_system/tree_replay/reversal_producer.py:238` makes the single original
  `find_at` call. The source selects the newest confirmation with the M5 tie
  preference and prices only that winner at
  `trading_system/tree_replay/_vendor/reversal_producer.py:30`. The adapter keeps
  that exact event/Plan at `reversal_producer.py:262`, after serialization and
  selected-evidence deepcopy. No JSON reconstruction, second selection or
  repricing was introduced. The retained pair preserves source event clocks,
  close, kind, direction, style, ordered targets and refusal.
- `tests/tree_replay/test_reversal_handoff.py:95` proves object identity using a
  call-through spy, one source invocation and literal geometry/event assertions.
  The confirmation close101 agrees with the actual synthetic bar at
  `tests/tree_replay/test_reversal_producer_source.py:54`; source reasons and
  close/kind assignment agree with `_vendor/reversal_pricing.py:31`. The newer
  refused M15 remains selected over a separately demonstrated paying M5 in
  `test_reversal_handoff.py:133`.
- `trading_system/tree_replay/reversal_producer.py:169` preserves the public
  keyword-only signature and docstring, returning only the extracted report.
  Comparison with the saved baseline shows unchanged validation, source gates,
  lazy evaluation, report construction, VERSION and hash inputs. Validation
  remains outside the calculation catch at `:189`; neither retained object
  enters the report or hashes at `:274`. Four literal pre-refactor hash pairs
  and public/private equality are exercised at
  `tests/tree_replay/test_reversal_handoff.py:119`.
- `trading_system/tree_replay/reversal_producer.py:208` initializes both retained
  objects to None. Source/map errors take precedence over selection at `:241`;
  serialization and deepcopy must finish before assignment at `:262`. The
  catch clears both objects and public selection at `:270`. Nonselection,
  unavailable/unsupported inputs and source failure are covered at
  `tests/tree_replay/test_reversal_handoff.py:155`; real selection followed by
  each named late serializer failure is covered at `:170`. Hash failures still
  propagate as before and cannot return a private selection result.
- `trading_system/tree_replay/reversal_producer.py:160` freezes result bindings,
  while preserving the mutable source Plan required by consumers. The unchanged
  serializer builds independent target/obstacle dictionaries and reason/warning
  lists at `trading_system/tree_replay/pricing.py:31`; selected evidence is then
  deep-copied. Mutation and repeated-evaluation cases at
  `tests/tree_replay/test_reversal_handoff.py:281` and `:303` check report/Plan
  separation, independent source objects and consumer dynamic attributes.
- `tests/tree_replay/test_reversal_handoff.py:247` passes the actual selected
  Plan to real TrackerAdmission.record. The consumer reads close at
  `trading_system/tree_replay/_vendor/tracker_admission.py:153`, stamps born_open
  at `:129`, and materializes geometry, targets, reasons and kind at `:178`.
  Assertions cover literal entry100/stop93/targets112,125,150, original reasons,
  advisory OPEN, broker-unverified status and unchanged complete report/hashes.
  The detached test ports are explicitly controlled inputs, not evidence of
  historical provider coverage or outer-gate acceptance.
- `docs/architecture/REVERSAL-HANDOFF-USAGE.md:47` accurately documents mutable
  ownership and the pre-mutation meaning of report hashes. Its consumer and
  remaining-scope sections at `:67` and `:77` agree with the code. The extraction
  adds no tracker call, persistence, notification, public export, source policy,
  threshold or instrument alias. Public readiness remains false.

## Findings

Critical: none.

Important: none.

Minor: none actionable in this component.

## Full-scope boundaries retained

All seven requirements in
`agent-exchange/reviews/2026-09-09T132300Z-tracker-admission-final-review.md`
remain binding. This component closes only retention of the actual selected
event/Plan, not the remainder of that review's first requirement.

1. Actual causal matrix/swing frames and correction providers still require
   exact symbols, request identities, supplied history/calendars, publication
   and price cutoffs, error traces and original lazy ordering. LOOKBACK is
   requested depth, not delivered-day proof; matrix must not inherit the
   reversal producer's correction veto or closed-target filter.
2. Detached coverage-checked state/quotes, real offline lock/save behavior,
   transactional failure and resume remain open. Missing evidence cannot
   become empty state or a certified successful source fallback.
3. Full causal raw-log prefixes must preserve bytes, non-rejection events and
   intra-pass appends at each reader call. Scoring and post-stop readers observe
   different points in the pass; a frozen or reserialized rejection-only tail
   is insufficient.
4. Heterogeneous watch state includes scalar cooldowns, object episodes,
   deletions and ordering. Its original write boundaries remain separate from
   tracker persistence; there is no atomic full-pass claim.
5. Actual caller admission, arbitration, dedupe, publication and record ordering
   remain branch-specific. Reversal/trend, tree and engine cannot share an
   invented universal publication gate. Observational log/state effects remain
   part of faithful replay.
6. Source-generated lifecycle, other producers, full-loop replay and economic
   simulation remain open. PENDING is not OPEN exposure; advisory OPEN or record
   success is not an economic fill. Quality annotations remain advisory.
   Original-entry/stop, full-TP1 economics require explicit costs/time exits;
   coverage, datasets and models are still unfinished.
7. Exact feed/instrument boundaries and false public tradeable/replay/training
   readiness remain. This review supplies no production-data, retention,
   promotion, deployment, broker or live-trading approval.

## Verification reviewed

Parent intake133900Z reports the exact command:

```text
python -m pytest tests/tree_replay/test_reversal_handoff.py tests/tree_replay/test_reversal_producer.py tests/tree_replay/test_tracker_admission.py -q --tb=short
```

PASS: 208 tests in8.57s, exit0, session85048 observed to completion. This comprises
24 new handoff, 78 unchanged producer and 106 unchanged tracker cases. Worker
baseline78, intended RED24, focused GREEN24 and combined208 are overlapping
reported evidence, not additional coverage. Pre-edit capture chronology remains
worker-reported; the parent independently passed the four literal hash fixtures
after extraction. Dependency versions are recorded in the tests/report.

This review independently ran read-only `Get-FileHash -Algorithm SHA256` checks:

- Saved runtime baseline: `3E53F915E4076C6302709D3C3C671A993E8A49690D4C60B6FE3E1E32C72CAF63`.
- Current runtime: `CF22D15655B7B87F2E2B7F03D54D3C5CA780D8DFE205FD3F781792C4EA255F33`.
- Current new test: `ECA23471D8799E3649450107FC7B1C07871BCDBD63A271E658F2ACF156CD7263`.
- Current usage: `734E2A8864C5803A935BB3BF36B8C995F27FC3DCD0B31AA333E5E259FB6C68F2`.

PASS: all match the saved baseline/worker/parent snapshots as applicable.
`git diff --no-index -- .superpowers/sdd/2026-09-09-reversal-handoff/baseline-reversal_producer.py.txt trading_system/tree_replay/reversal_producer.py`
confirmed the packaged extraction; exit1 denotes the expected differences,
not a failed verification. No unanswered concrete runtime doubt justified a
suite rerun or new probe. No source audit was rerun or newly claimed here.

Only this requested review artifact was written, using apply_patch. No nested
agents, other-plan scratch, runtime/test/status edits, commits or git mutations.

## Assessment

Open questions: none blocking this component.

Ready to merge? Yes for this component's scoped spec and code quality; no merge
action or controller acceptance record is made by this review.

Recommended next action: controller may record final component acceptance and
proceed with separately scoped causal binding while retaining every boundary
above. This approval does not complete the master plan or authorize labels,
dataset generation or model fitting.
