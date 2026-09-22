# Task 1 implementation report

Status: DONE / IMPLEMENTED_AWAITING_CODEX_REVIEW
Request: agent-exchange/inbox/codex/2026-09-09T133400Z-reversal-handoff.md
Brief: .superpowers/sdd/2026-09-09-reversal-handoff/task-1-brief.md
Contract: docs/architecture/REVERSAL-HANDOFF-CONTRACT.md
Branch preserved: plan/tree-to-trained-model-langgraph

## Implemented

Extracted the existing evaluator body into private `_evaluate_reversal_asof`
with the same keyword-only inputs. Public `find_reversal_asof` retains its
signature/docstring and returns the private evaluation's report. Added frozen
`_ReversalEvaluation(report, selected_event, selected_plan)` with the contracted
types. Source objects start as None, are retained by identity only after the
existing selected serialization/deepcopy succeeds, and are cleared on caught
failure. Report hashes are computed before constructing the private result.

The actual event and mutable Plan come from the existing single `find_at` call.
No reconstruction, repricing, new admission, source policy, public export,
manifest, or VERSION change. Source-refused plans remain refused selections.
The existing validation, lazy calls, source gates, dictionary construction,
serialization, and hash inputs are unchanged.

Added 24 behavioral test cases in the sole new test file and private-interface
usage documentation. The real producer-to-tracker test uses the selected Plan,
not a manually constructed Plan, and a test-only detached in-memory port set.

## Task checklist

- [x] Read brief first, named contract, repository startup files, own inbox list
  and original request; inspected latest tracker acceptance and result template.
- [x] Read and applied TDD plus writing-good-tests, implementer-prompt,
  executing-plans, and verification-before-completion instructions. Explicit
  user restrictions override skill suggestions for worktrees/agents/commits.
- [x] Compared runtime with supplied baseline before editing: exact SHA256 match.
- [x] Captured four real public hash pairs before refactor and recorded dependency
  versions; ran existing producer baseline once.
- [x] Wrote tests with private lookup inside each test; observed 24 RED failures
  before touching runtime.
- [x] Extracted evaluator, preserved original pair, public contract, and refusals.
- [x] Verified source errors/nonselection/unsupported/unavailable None pairs,
  concrete late serialization faults, raised validation, and golden compatibility.
- [x] Verified original geometry/reasons through real TrackerAdmission.record;
  separate nested mutation and repeat-evaluation tests.
- [x] Ran the exact required three-file suite in default pytest mode.
- [x] Self-reviewed runtime baseline diff, complete new test, and usage document;
  wrote full report and exchange result.
- [ ] Parent independent verification, complete task review, final component
  review and acceptance before actual causal binding: intentionally parent-owned.

## TDD and verification evidence

Environment: Python 3.13.5, pandas 2.3.3, NumPy 2.2.6, pytest 8.3.3.
Dependencies were unchanged throughout capture and verification.

1. Baseline command, before any edit:

   `python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short`

   Exit 0: `78 passed in 5.02s`. Baseline was not rerun separately; these tests
   later ran within the required compatibility suite.

2. RED command, new tests present and runtime still untouched:

   `python -m pytest tests/tree_replay/test_reversal_handoff.py -q --tb=short`

   Exit 1: `24 failed in 1.37s`. All 24 collected normally and failed at the
   in-test helper lookup. Representative exact output:

   ```text
   _____ test_handoff_retains_single_actual_selection_and_original_geometry ______
   tests\tree_replay\test_reversal_handoff.py:96: in test_handoff_retains_single_actual_selection_and_original_geometry
       evaluate = adapter._evaluate_reversal_asof
   E   AttributeError: module 'trading_system.tree_replay.reversal_producer' has no attribute '_evaluate_reversal_asof'
   ```

   This was the intended missing-feature failure, with no collection error.
   Runtime implementation was added only afterward.

3. Focused GREEN command after extraction:

   `python -m pytest tests/tree_replay/test_reversal_handoff.py -q --tb=short`

   Exit 0: `24 passed in 2.07s`. No intermediate test fixes or runtime iterations
   were needed after initial extraction.

4. Required final compatibility command:

   `python -m pytest tests/tree_replay/test_reversal_handoff.py tests/tree_replay/test_reversal_producer.py tests/tree_replay/test_tracker_admission.py -q --tb=short`

   Exit 0: `208 passed in 7.42s`. Session 2175 was polled to confirmed completion.
   This is 24 new handoff + 78 unchanged producer + 106 unchanged tracker cases.
   All pytest runs used default configuration/import mode; no warnings reported.

5. Self-review commands:

   - `git diff --no-index -- .superpowers/sdd/2026-09-09-reversal-handoff/baseline-reversal_producer.py.txt trading_system/tree_replay/reversal_producer.py`
   - `git diff --check`
   - `git diff --no-index --check -- .superpowers/sdd/2026-09-09-reversal-handoff/baseline-reversal_producer.py.txt trading_system/tree_replay/reversal_producer.py`
   - `git diff --no-index --check -- NUL tests/tree_replay/test_reversal_handoff.py`
   - `git diff --no-index --check -- NUL docs/architecture/REVERSAL-HANDOFF-USAGE.md`

   Reviewed the complete runtime diff and new files. No whitespace defects were
   reported; Git emitted LF/CRLF conversion advisories. Ordinary tracked diff
   alone is insufficient because this runtime/test package was already untracked.

## Before/after public hash evidence

Before-runtime-edit capture used an inline Python invocation with
`sys.path.insert(0, 'tests/tree_replay')`, unchanged `find/maps/reversal/history`
fixtures from `test_reversal_producer`, and actual source `find_at` wrapped by a
call-through spy. No selection was supplied or fabricated. The capture printed
each report's status, decision_id and evaluation_sha256 and the original pairs.

Inputs below correspond to `inputs(case)` in the new test file. All use
snapshot_id `test`, instrument `OANDA:XAUUSD`, decision T `2026-09-09T14:00:00Z`.
The literal pairs below were captured before runtime editing and matched after
editing in both focused GREEN and the final suite. They are not dynamically
computed expected values.

| Case | Before decision_id = after decision_id | Before evaluation_sha256 = after evaluation_sha256 |
| --- | --- | --- |
| accepted | reversal-decision:ee71d09cd6f493c3b3337a1c3361339b2f92616e6b85348cf46ebe32f4acfac2 | 2bcb79936f6b7c697b0419b43807bb42262be89ea8ded8e13c88baf966aa03dd |
| refused | reversal-decision:f4108f2ac91b7702835503dacff83d03fa6c9e764f38bf5703fb74f74413ab80 | 80dc43f9309b7530fb473951e1c8fcb42c62513835ae0fdd66ed28cc1a16084c |
| quiet | reversal-decision:f65b52bd4a10b7682db738a912178e9b1cdf9df9abf479116d98c297fc076b02 | 063c2e66fe5492d391ec797e9103828ee991aedb75b97f6ea3858b7e5f86c208 |
| unavailable_daily | reversal-decision:210e7c0472032da134d4013685b21b25a6deca4bf210f349f3f2a26015db1413 | f2b37afdfd76254b0402b2c2509dc11b4940665bc1ea0753d78393eebdbc2ee7 |

- Accepted: default real map rails 112/88 with equal-confirmation M5 long/M15
  short; M5 wins and pricing is accepted but unadmitted.
- Refused: real daily rails 110/90, M5 confirmed T-5 minutes, newest M15 short
  at T. M15 stays selected and refused; the M5 alone pays.
- Quiet: both histories set to [103,108,98,102,100], producing NO_CANDIDATE.
- Unavailable daily: map_requests=(), producing BLOCKED.

## Consumer and ownership evidence

The accepted event is M5 DAY-OPEN two_bar_reclaim, long, vector at 13:50,
confirmation opening 13:55 and closing at T. The hand-checked confirmation bar
is [99,102,99,101,100]. Plan.close=101, kind=reversal, style=scalp, entry=100,
stop=93, targets in source order 112/125/150. The four literal Hebrew reasons
were checked against the source builder and synthetic event, not generated by
the tested code as expected values. The spy proves retained event/Plan identity
and one real source invocation for the evaluated handoff.

The real tracker stores those literal entry/stop/target/kind/reason fields.
Controlled ports provide T explicitly, known empty detached state and quote,
and matrix nets {4h:10,1h:20,30m:5,15m:5,5m:5}. With close 101 inside [98,102],
empty quotes defer to build close. Actual record sets Plan.born_open=True and
advisory OPEN with revalidation_verified=False and
fill_verification_reason=born_open_not_broker_verified. It does not establish
economic execution. Full report equality before/after record includes both
hashes and all false readiness flags.

Separate tests mutate retained Plan lists, nested selected-report target and
obstacle dictionaries, reasons/warnings, and detached stored tracker lists.
They verify no alias into the report, Plan, or candidate evidence. Repeated
evaluations return distinct Plans/events; downstream list changes and dynamic
attributes remain local. Frozen result bindings do not freeze the Plan.

Concrete `_source_plan` and `_pricing_snapshot` fault tests call their original
serializers after actual find returns the Plan, then raise RuntimeError through
pytest monkeypatch. Both yield pricing_serialization BLOCKED with no retained
objects. Real numerical source failure and seven input-validation cases are
also covered.

## Changed files and checksums

Only these authored files were changed/created:

- trading_system/tree_replay/reversal_producer.py
- tests/tree_replay/test_reversal_handoff.py
- docs/architecture/REVERSAL-HANDOFF-USAGE.md
- .superpowers/sdd/2026-09-09-reversal-handoff/task-1-report.md
- agent-exchange/status/2026-09-09T133400Z-worker-reversal-handoff.md

Runtime before edit and supplied baseline SHA256:
`3E53F915E4076C6302709D3C3C671A993E8A49690D4C60B6FE3E1E32C72CAF63`.
Runtime after edit:
`CF22D15655B7B87F2E2B7F03D54D3C5CA780D8DFE205FD3F781792C4EA255F33`.
New test:
`ECA23471D8799E3649450107FC7B1C07871BCDBD63A271E658F2ACF156CD7263`.
New usage:
`734E2A8864C5803A935BB3BF36B8C995F27FC3DCD0B31AA333E5E259FB6C68F2`.

## Self-review and concerns

No implementation blocker or unresolved interface. Runtime changes are limited
to the contracted extraction, dataclass, retained locals and return wrapper.
The source call remains single and the report dictionaries/hash inputs match
the baseline. No vendor files, existing tests, exports, manifests, pytest mode,
source behavior, or unrelated dirty files were edited. No commits, pushes,
cleanup, agents, source reconstruction, network, or external actions.

Golden values intentionally describe the stated dependency environment; report
hashes include dependency versions. Future dependency changes require explicit
review of those compatibility expectations. Shared fixture imports use the
existing default pytest layout; no alternative runner portability is claimed.

The user's nonblocking source finding is reflected in usage documentation:
LOOKBACK is requested depth, not proof of delivered days; original TV/MT5 paths
return the full file, and matrix read_tf has no producer unverified veto or
closed-target filter. Test matrix/quote/state ports are controlled inputs, not
certified causal providers. Actual provider binding and all seven tracker
final-review constraints remain follow-on work.

This handoff does not complete outer admission, lifecycle, caller ordering,
publication, raw-log/watch-memory coverage, other producers, full replay,
economic labels, datasets or models. Public readiness remains false. Parent
independent verification and task/final acceptance are still required.
