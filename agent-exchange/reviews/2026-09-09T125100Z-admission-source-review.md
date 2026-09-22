# Agent Exchange Review

Reviewer:
Codex independent Task1 reviewer; no nested agents.

Target request:
agent-exchange/inbox/codex/2026-09-09T125100Z-admission-source-review.md

Created at:
2026-09-09

Status:
REVIEW_READY_FOR_CODEX

Verdict:
Spec compliance: PASS for the implemented Task1 scope; original RED/test-before-code history cannot be verified.
Task quality: APPROVED, with one non-blocking portability finding. No Critical or Important findings.
This is a task review recommendation, not controller acceptance or replay/training readiness.

Findings:

### Strengths and spec checks

- All twelve requested deliverable files have complete new-file hunks in the supplied package. The six private modules separate matrix, toolkit, indicators, quality, clocks and swing calculations; the remaining hunks provide the auditor, manifest, CLI, two test modules and usage documentation. No previous runtime module or manifest is modified by this diff.
- Source closure is independently fixed in `trading_system/tree_spec/admission_source.py:18`, checked against the manifest/baseline at `:333`, and compared as complete ordered vendor modules at `:380`. Shared indicators/TR/ATR are included, not merely trusted because they were previously accepted. Source blob mismatches block before projection; source parsing and vendor comparison do not import or execute either checkout (`:362`). Local Git use is limited to `rev-parse` (`:318`).
- `trading_system/tree_spec/admission_source.py:262` validates the original fetch/note statements and signature, then retains the entire original TFView constructor with the explicit note substitution. This checks the actual calculation expression used by `trading_system/tree_replay/_vendor/admission_matrix.py:146`, including tool order, ATR and bar timestamp.
- Required-aware clock adaptation is narrow and checked against original signatures/bodies (`trading_system/tree_spec/admission_source.py:247`, `:285`, `:303`). `trading_system/tree_replay/_vendor/admission_clocks.py:15` rejects missing/naive time instead of consulting the wall clock. Boundary/DST/equivalent-instant tests cover hunting and weekend/preclose policies (`tests/tree_replay/test_admission_calculations.py:42`, `:61`).
- Native behavior is preserved: NaN VWAP scoring (`trading_system/tree_replay/_vendor/admission_matrix.py:78`), distinct seeded SuperTrend versus unseeded TR ATR (`tests/tree_replay/test_admission_calculations.py:168`), and three-right-bar swing confirmation including ties (`:179`). Golden rising/falling/flat and mixed matrix cases assert concrete outputs and input immutability (`:85`, `:115`). These are behavioral tests, not only mocks of the calculation layer.
- Quality remains a supplied-evidence annotation (`trading_system/tree_replay/_vendor/admission_quality.py:134`); it adds no veto or rejection-history selection. Documentation explicitly limits causal-frame validation and future binding (`docs/architecture/ADMISSION-CALCULATIONS-USAGE.md:13`) and exposes the NaN anomaly (`:40`). Audit readiness stays false (`trading_system/tree_spec/admission_source.py:395`).
- Mutation tests cover constants, function bodies, dependency aliases, constructor fields, clock specialization, ordering and appended executable statements (`tests/tree_spec/test_admission_source.py:38`, `:69`, `:78`, `:153`); manifest edits cannot narrow the audited closure (`:180`). The fresh-process runtime guard exercises calculations without retained-source access, sockets or subprocesses (`:122`).

### Critical

None found.

### Important

None found.

### Minor

- `tests/tree_spec/test_admission_source.py:14`: the source fixture is hardcoded to one user's temporary checkout. The supplied environment satisfies it, but the tests cannot be reproduced in a relocated checkout or another runner without editing test code. Consider an explicit test option/environment variable for the retained parent root, with a clear prerequisite error when absent; keep the same identity/blob checks and do not silently skip parity verification. This is not a Task1 blocker because the brief explicitly supplied this retained root.

Open questions:

- Original RED evidence is unavailable, as acknowledged in `.superpowers/sdd/2026-09-09-admission-dependencies/task-1-report.md` and `docs/architecture/ADMISSION-CALCULATIONS-USAGE.md:66`. Passing mutation tests do not establish test-before-code history. No contrary history is inferred.
- The report claims 452 combined passes but does not supply that combined command. Treat it as controller-reported supporting evidence, not an independently reconstructed verification result here. Cross-task binding and final acceptance remain with the parent.

Recommended next action:
Parent may proceed with its remaining review/intake gates. No Task1 runtime revision is required by this review; optionally improve test-root portability. Preserve false readiness and the outstanding outer admission/lifecycle boundaries.

Verification reviewed:

- Read the scoped request first, then mandatory repository startup files and Codex inbox listing. Applied Superpowers 6.3.0 `skills/subagent-driven-development/task-reviewer-prompt.md`. Read the specified brief, recovered report, contract and complete supplied diff in sequential chunks; no changed file was separately reread. A later metadata-only pass extracted file:line citation anchors from the package. No other plan scratch was read.
- Inspected `git status --short` once. Reviewed the supplied complete new-file diff rather than regenerating it. No commit, index, runtime, master-document or inbox mutations; this requested report is the only write.
- Named unchanged-dependency risk: an omitted helper or wrong ATR implementation could break the claimed closure. Read `_vendor/tr.py:12`, `_vendor/atr.py:6`, `_vendor/indicators.py:14` and `_vendor/__init__.py:1` as text. Confirmed TR EMA/cloud dependencies terminate in the audited seeded helper/stdev, unseeded ATR is separate, and the vendor initializer contains only a docstring.
- Named source-specialization risk: rewritten imports or merged clocks could bind different source functions/constants. Inspected retained source import declarations and clock/read_tf definitions as inert text: `chartdesk/matrix.py:30`, `:173`; `chartdesk/toolkit.py:33`; `chartdesk/indicators.py:17`; `chartdesk/tr.py:26`; `chartdesk/entry_quality.py:22`; `chartdesk/zones.py:55`; `chartdesk/windows.py:39`, `:134`; `floor/marketclock.py:44`, `:55`, `:151`, `:177`. Their bindings and adaptations agree with the reviewed projection. Truncated search output was resolved with a narrow import/line-location follow-up. No retained source was imported or executed.
- Reported PASS, not rerun: `python -m pytest tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py -q --tb=short` — 93 passed in 21.01s, reported pristine output.
- Reported PASS, not rerun: `python tools/check_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149` — exit 0, source_subset_verified true, empty blockers, both readiness flags false.
- No test or audit suite was regenerated: static inspection left no specific unanswered runtime doubt requiring an additional execution. The diff package's LF/CRLF notices are packaging warnings, not evidence of noisy test output.
