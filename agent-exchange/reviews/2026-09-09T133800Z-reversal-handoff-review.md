# Agent Exchange Review

Reviewer: Codex

Target request: agent-exchange/inbox/codex/2026-09-09T133800Z-reversal-handoff-review.md

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

## Spec compliance

Verdict: PASS. The three-file task delta satisfies Task 1 and
`docs/architecture/REVERSAL-HANDOFF-CONTRACT.md`; no missing, extra, or
misunderstood implementation requirements found.

- `trading_system/tree_replay/reversal_producer.py:161` defines the private frozen
  result with the original source types. At line 179 the unchanged public
  signature delegates to the extracted evaluator and returns only its report.
- `trading_system/tree_replay/reversal_producer.py:238` calls the original source
  selection once. Lines 248 and 262 preserve that event/Plan pair by identity,
  only after source-plan serialization, pricing snapshot, and selected-evidence
  deepcopy complete. There is no reconstruction, repricing, or tradeability gate
  replacing a selected refusal.
- `trading_system/tree_replay/reversal_producer.py:208` initializes both retained
  objects to None; line 270 clears them on caught failure. The existing report
  hashes precede the private return at line 276. Validation and report/hash
  construction remain the original implementation.
- `docs/architecture/REVERSAL-HANDOFF-USAGE.md:45` documents mutable ownership and
  detached reports; line 67 explicitly limits the tracker integration to test
  ports and distinguishes advisory OPEN from economic execution. The delta adds
  no tracking, saving, notification, public exports, or inferred admission.

## Strengths

- `tests/tree_replay/test_reversal_handoff.py:95` verifies a call-through spy's
  actual returned objects and independently specified geometry, close, kind,
  direction, reasons, and event times. The golden compatibility cases beginning
  at line 119 use literal pre-refactor hashes, with dependency versions recorded.
- The supplied test diff also covers refused-newest selection, nonselection and
  source failure, both named late serializers, validation exceptions, real
  tracker recording, nested mutation isolation, and independent evaluations.
  Runtime changes are a small extraction rather than duplicated selection logic.

## Findings

Critical: None.

Important: None.

Minor: None.

## Focused integration check

Named risk: retaining a mutable Plan must preserve the original fields used by
the real tracker without allowing tracker mutation to alter the evidence report.
Inspected only `trading_system/tree_replay/_vendor/pricing.py:147` and
`trading_system/tree_replay/_vendor/tracker_admission.py:110` through the record
implementation. Plan defines close/kind and independent list defaults; tracker
stamps born_open at line 129, reads close at line 153, copies geometry/list fields
at lines 178-184, and marks born OPEN unverified at lines 188-193. This agrees with
the new integration assertions. No integration defect found.

The packaged runtime hunks cut off the evaluator's middle, including the source
call and pre-selection error gates. Read only runtime lines 211-250 to close
that specific gap; no other changed file was read separately.

## Verification reviewed

Reviewed repository startup instructions and Codex inbox listing, original review
request, supplied brief/report/full diff, named contract, and SDD task-reviewer
prompt. Review basis: supplied saved pre-task runtime delta plus two new files;
BASE == HEAD `c1b6071633c55376c64f0a98ece843706f420f49`, not a commit-range diff.

Reported commands and outcomes, not independently rerun:

- `python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short`
  — baseline PASS, 78 tests.
- `python -m pytest tests/tree_replay/test_reversal_handoff.py -q --tb=short`
  — intended RED, 24 collected failures at missing helper lookup; subsequent
  GREEN, 24 passed.
- `python -m pytest tests/tree_replay/test_reversal_handoff.py tests/tree_replay/test_reversal_producer.py tests/tree_replay/test_tracker_admission.py -q --tb=short`
  — reported PASS, 208 tests, default pytest mode, no pytest warnings.

No uncovered doubt justified a focused execution or suite rerun. Pre-edit hash
capture chronology is supported by the supplied report, not independently
recreated. Package LF/CRLF advisories are Git output, not test warnings.

## Assessment

Task quality: Approved. The extraction preserves the public evidence path while
retaining original mutable source objects under the required success boundary;
the added tests exercise actual selection and consumer behavior.

Open questions: None blocking this task review. Full causal binding and final
component acceptance remain outside this task verdict.

Recommended next action: Proceed to controller/final component review. This
review does not confer causal-admission, replay, economic-label, or model readiness.
