# Agent Exchange Review

Spec compliance: PASS. Task quality: APPROVED with one Minor test-coverage concern.

Reviewer: Codex independent task reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T153900Z-admission-frame-review.md

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

## Spec compliance

- The complete supplied three-new-file diff matches Task 1 and the named `docs/architecture/ADMISSION-FRAME-BINDING-CONTRACT.md`. Frozen keyword-only requests, six exact key pairs, native request types, correction association, constructor revalidation, unique keys/frame IDs and supported instrument validation are implemented at `trading_system/tree_replay/admission_frames.py:18`, `:22`, `:30` and `:50`.
- Actual decision time and closed-base-prefix construction delegate to the existing source at `trading_system/tree_replay/admission_frames.py:55`, `:66` and `:83`. The adapter introduces no minimum-day gate, row trim, target-row filter, correction-quality veto or duplicated matrix formulas. Ordered fetch/render/read_frame and abort-on-error behavior are explicit at `trading_system/tree_replay/admission_frames.py:85` and `:88`.
- Invalid direct bindings retain fetch evidence at `trading_system/tree_replay/admission_frames.py:69`; matrix attempts record starting fetch index, failure and exception type before rethrowing at `:88`. The caught numerical-error integration asserts the retained evidence after tracker returns None at `tests/tree_replay/test_admission_frames.py:285`.
- All three promised files are present. Usage documents supplied-history limits, mutable local context, independent synthetic seeds and unfinished state/quote/log/lifecycle/economic work at `docs/architecture/ADMISSION-FRAME-BINDING-USAGE.md:42` and `:69`. No full readiness claim is introduced.

## Strengths

- Thin source binding preserves the original calculation implementation instead of introducing score inputs. Literal ATR/net/tool readings and a nonconstant fixture exercise actual calculations at `tests/tree_replay/test_admission_frames.py:63` and `:90`.
- Real causal frame fixtures cover missing early requests, unavailable versus assessed-unverified corrections, mutation isolation, incomplete supplied sessions, forming target rows and future input exclusion at `tests/tree_replay/test_admission_frames.py:100`, `:112`, `:134`, `:143`, `:157`, `:174` and `:193`.
- Actual tracker bias/thesis/post-stop and selected-Plan record integrations use this provider at `tests/tree_replay/test_admission_frames.py:269` and `:297`. The documentation accurately limits what independently supplied producer and matrix fixtures prove at `docs/architecture/ADMISSION-FRAME-BINDING-USAGE.md:75`.

## Findings

Critical: None.

Important: None.

Minor M1 — The no-trimming test does not supply history exceeding the requested lookback. `tests/tree_replay/test_admission_frames.py:82` uses the default 120 bars from `:31` for every pair. Even 15m/5 contains only 1.25 days; each other fixture is also shorter than its requested days. These assertions detect a new minimum-day gate, but an erroneous trim to the requested days would still pass. Add a 15m/5 fixture exceeding five days (for example, 600 bars) and assert both the earliest supplied source index and the complete row count survive. Current runtime is correct by inspection: `trading_system/tree_replay/admission_frames.py:83` delegates to `trading_system/tree_replay/levelmap.py:120`, which constructs the DataFrame from all returned rows. This is a regression-coverage improvement, not a blocking behavioral defect.

## Focused integration checks

- Risk: accidental source-order or row-set changes. Read the named intake depth/ordering section at `docs/architecture/MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md:257`, inert retained `chart-desk/chartdesk/matrix.py:173` and `:188`, and `trading_system/tree_replay/_vendor/admission_matrix.py:146`. Fetch with LOOKBACK, conditional Correction.render, TFView calculations and ordered comprehension match the new binding. Retained source parent: `C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
- Risk: the new request type bypassing causal assessment or returning shared outputs. Inspected `_OfflineSource` at `trading_system/tree_replay/levelmap.py:68`: it consumes the shared request fields, builds on each call, requires ASSESSED correction, records failures and creates fresh Correction/DataFrame outputs (`:93`, `:108`, `:117`, `:121`, `:131`). No new shape veto is called by this adapter.
- Risk: inherited time normalization losing finer precision or frame identity validation being absent. Inspected `trading_system/tree_replay/bars.py:35`, `trading_system/tree_replay/frames.py:52` and `:222`. UTC normalization explicitly rejects submicrosecond values; FrameSpec validates its supplied associations and the builder retains actual decision-time availability checks.

## Verification reviewed

- Reviewed the supplied Task 1 brief, report, named contract and all 521 added lines (102 runtime, 329 tests, 90 usage) in the packaged diff, in two contiguous reading segments. No changed file was separately reread. No nested agents or other plan scratch were used.
- Implementer-reported verification: `python -m pytest tests/tree_replay/test_admission_frames.py -q --tb=short` — RED 39 failures, then GREEN 39, then 40 passed after the additional record integration.
- Implementer-reported verification: `python -m pytest tests/tree_replay/test_admission_frames.py tests/tree_replay/test_admission_calculations.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_reversal_handoff.py tests/tree_replay/test_frames.py tests/tree_replay/test_corrections.py -q --tb=short` — 435 passed.
- Implementer-reported verification: `python tools/check_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149` — VERIFIED, 10 inherited projections, no blockers. Counts overlap; they are not additive.
- Those execution results and original RED chronology were not independently reproduced. Per the review request, no suite was rerun: static inspection raised no concrete unresolved runtime doubt requiring a focused probe. The package carries LF/CRLF conversion advisories; these are packaging noise, not evidence of test failures or source-parity defects.

Open questions: None blocking this task. Full historical feed/seed certification and complete caller readiness remain outside this component.

Recommended next action: Proceed to the separate full component review; retain M1 as a Minor coverage improvement. This artifact is the task review, not final component acceptance or production authorization.
