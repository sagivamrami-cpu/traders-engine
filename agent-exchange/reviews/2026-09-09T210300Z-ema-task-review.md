# Agent Exchange Review

Reviewer: Codex independent task reviewer; both tasks reviewed in one seat

Target request: agent-exchange/inbox/codex/2026-09-09T210300Z-ema-task-review.md

Created at: 2026-09-09T21:03:44Z

Status: REVIEW_READY_FOR_CODEX

Verdict:

| Task | Spec compliance | Code quality |
| --- | --- | --- |
| 1: Complete reader, state, runtime tests and usage | PASS, with nonblocking coverage note M1 | Approved with minor note |
| 2: Full source/dependency auditor, CLI and audit tests | PASS | Approved |

These are task-scoped verdicts for the six additive files in the supplied packages. Final combined review and controller acceptance remain separate.

Findings:

Task 1 strengths and compliance evidence:

- `trading_system/tree_replay/_vendor/ema_windows.py:8` preserves the five exact symbol mappings, all six lengths and original thresholds. The complete Window/EmaState bodies retain strict/loose asymmetry, unknown versus zero, cascade, stable nearest-window selection, magnitude weighting, coverage, median strength, glued variants and rendering.
- `trading_system/tree_replay/_vendor/ema_windows.py:222` retains real seeded EMA calls, per-window `2*n` convergence, strict pre-live prefix, splice-only keep-last deduplication, live close/window ATR and three-bar slope with the source's 20-row ATR rule. The full original source module was read as text to check omitted behavior and exception boundaries; no source was imported or executed.
- `trading_system/tree_replay/_vendor/ema_windows.py:259` contains exactly the requested reader port adaptations. Fetch stays outside the optional deep-read catch; calculation stays after it. The logical path, map lookup, BytesIO parsing, UTC conversion, default truthiness and ordered repeated stack reads match the contract.
- `tests/tree_replay/test_ema_windows.py:55`, `:87`, `:228`, `:239`, `:250`, `:269` and `:280` exercise actual calculations and CSV bytes with independent numeric expectations, convergence and overlap boundaries, varying ATR, duplicate handling and post-parse calculation failure. These are meaningful behavioral tests rather than finished-window substitutions for the numerical path.
- `docs/architecture/EMA-DEEP-READER-USAGE.md:39` accurately distinguishes live window ATR from potentially deep-inclusive slope ATR, preserves raw rounding, and leaves causal availability and GC/spot seam certification open.

Task 1 issues:

- **M1 — Minor, nonblocking test coverage:** `tests/tree_replay/test_ema_windows.py:176` and `:190` cover flat, mixed and unknown trends and an odd-count nonuniform slope median. The six-window ascending test covers an even median only with effectively equal magnitudes. There is no discriminating even-count median case with unequal middle magnitudes, nor a generated descending frame asserting the fully negative strict-trend branch. The requested full property edge matrix would be stronger with those two small cases. For example, absolute slopes `[1, 3, 7, 9]` should produce strength `5`, and a sufficiently long descending frame should produce the original strict-down label. This is a coverage gap, not an observed runtime defect; full source AST comparison already protects the copied branches.
- No Critical or Important findings.

Task 2 strengths and compliance evidence:

- `trading_system/tree_spec/ema_windows_source.py:14` fixes commit and both blob identities independently of the supplied baseline. `:36` constructs the complete ordered projection with exact-count method substitutions, preserved bodies and the required reader class layout. `:56` blocks invalid identity, unreadable source/candidate, projection mismatch and dependency failures; replay/training readiness stays false.
- `trading_system/tree_spec/ema_windows_source.py:99` invokes the actual strict seeded-EMA auditor. Named dependency risk checked: a standalone reader match might conceal modified or reordered indicator code. Inspection of `tools/check_levelmap_source_parity.py:43`, `:238` and `:249` confirms literal dependency blobs, ordered imports/symbols and comparison against the real local indicators/TR files. Inspection of `trading_system/tree_replay/_vendor/indicators.py:15` confirms the runtime call reaches the existing seeded recursion.
- Named helper risk checked: selection could silently reorder/collapse symbols or tolerate missing/extra substitutions. `trading_system/tree_spec/tracker_admission_source.py:149` requires exactly one replacement and `:167` compares the selected sequence directly with the required sequence. Its `:225` and `:244` helpers perform read-only Git identity checks and duplicate-rejecting JSON reads. No retained source execution is introduced by these helpers.
- `tests/tree_spec/test_ema_windows_source.py:40` exercises candidate drift across imports, constants, classes, numerical rules, parsing, routing, catches and properties. `:97`, `:105`, `:116` and `:143` cover source pins, actual indicator drift, identity and projection collisions. `:155` checks fresh-process forbidden imports and unrelated-CWD CLI behavior. `tools/check_ema_windows_source_parity.py:12` requires an explicit root and emits the specified JSON/exit-code result.
- No Critical, Important or Minor findings for Task 2.

Open questions:

- No blocking implementation questions. Task 2's post-review authoritative status/memory/tracker updates and final combined review are controller workflow steps outside the six-file package; this report does not certify their completion.
- The implementation report supplies summarized RED/GREEN and mutation evidence, not complete terminal transcripts. Current hashes match all four hashes quoted there. Historical test execution order and absence of live actions cannot be independently established from the diff; neither is claimed here.

Recommended next action:

- Proceed to the separately scoped final combined review. Add M1's focused property cases when convenient; no runtime changes or broad-suite reruns are requested by this task review.

Verification reviewed:

- Read AGENTS.md, exchange README/protocol, inspected the Codex inbox, and read the exact request, both briefs, both complete diff packages, implementation report, source contract and task-reviewer prompt. Truncated tool output was recovered from the affected package portions; changed source files were not separately reread for review.
- Initial `git status --short` and `git diff --stat`: completed; six scoped files are uncommitted additions amid pre-existing unrelated work. No subsequent Git commands or mutations.
- `Get-FileHash <six scoped paths> -Algorithm SHA256`: PASS; runtime, runtime-test, auditor and audit-test hashes match the implementation report. Additional observed hashes: usage `C7A0931657E12543851C5A332E05C3CB7AD8F8F8B4A9E0E32E6B57F5B0910257`; CLI `29B56167AF1AF45A1774A1E2185364F69DB4A0F19FC4DB81C5C9BA085CC67D93`.
- Main's reported command: `python -B -m pytest tests/tree_replay/test_ema_windows.py tests/tree_spec/test_ema_windows_source.py tests/tree_replay/test_ema.py tests/tree_replay/test_stretch.py tests/tree_spec/test_stretch_source.py -q --tb=short -p no:cacheprovider` — reported PASS, 255 tests, 14.13s, exit 0, no warnings. The 58 audit cases are included, not additional coverage. Reviewed, not rerun.
- Main's reported candidate-only head-replacement and keep-first probes produced the intended numerical-test failures. Reviewed the corresponding assertions; probes were not rerun.
- Independent review used static source/helper inspection and hashes only. No concrete unresolved runtime doubt warranted a focused execution. One timestamp command used unsupported Windows PowerShell `Get-Date -AsUTC`; the clock tool supplied UTC instead. This was a shell compatibility error, not a test failure.
- Only this named review artifact was written, using apply_patch. No nested agents, source execution, live/data/training actions, commits, cleanup or production approval.
