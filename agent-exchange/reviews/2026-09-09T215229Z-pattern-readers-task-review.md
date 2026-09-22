# Agent Exchange Review

Reviewer: Independent Codex Task1 reviewer; no nested agents

Target request: agent-exchange/inbox/codex/2026-09-09T215229Z-pattern-readers-task-review.md

Request: agent-exchange/inbox/codex/2026-09-09T215229Z-pattern-readers-task-review.md

Created at: 2026-09-09T21:54:54Z

Status: REVIEW_READY_FOR_CODEX

Verdict:

- Spec compliance: Issues found — one Minor missing regression (M1); runtime and interface requirements otherwise match the reviewed Task1 diff.
- Task quality: Approved. No Critical or Important findings; the focused probe confirms M1 concerns regression coverage, not an observed runtime defect.

Findings:

Strengths:

- All seven requested additions are present. Reader boundaries retain the original arguments and actual numerical composition: `trading_system/tree_replay/_vendor/wm.py:94`, `liquidity.py:89`, `liquidity.py:123`, `brinks.py:69`, and `checklists.py:103`. `pattern_tr.py:1` contains precisely the two required dependency reexports.
- Real raw-frame fixtures exercise the second liquidity read with different replies (`tests/tree_replay/test_pattern_readers.py:146`), the original short/equal-close policy (`:166`), clock/window and minimum-row boundaries (`:178`, `:189`), and actual Brinks/vector composition with inclusive boundary membership (`:288`). No final-reader verdict doubles replace the numerical graph.
- `docs/architecture/TREE-PATTERN-READERS-USAGE.md:14` documents supplied ports and repeated reads; `:21` preserves forming-row and causal limitations; `:36` explicitly withholds full-tree/model readiness.

Critical: None.

Important: None.

Minor M1 — Missing explicitly requested Brinks vector-error regression.

`tests/tree_replay/test_pattern_readers.py:199` tests a successful actual vector count, and `:189` tests zero. The failure test at `:288` targets the subsequent checklist zone fetch, not the `BrinksReader.today_box` vector-calculation catch at `trading_system/tree_replay/_vendor/brinks.py:99`. Task1 explicitly requests actual vector memory or `None` on captured input error. Add a raw frame with valid OHLC/index and nonnumeric volume; assert the box remains formed with unchanged bounds/current close, `open_vectors_inside is None`, and the original clock/fetch order. This protects unknown versus zero without mocking either numerical dependency. The independent probe below passed, so this is a missing persistent regression, not a demonstrated implementation failure.

Open questions:

- Whole-module ordered AST/blob identity, mutation sensitivity, and inherited dependency audits remain Task2. This Task1 review does not certify those requirements. Equal-age W/M selection is structurally unreachable through the actual mutually exclusive swing indices; retaining its strict source comparison is appropriate, with the reported audit mutation still required.
- Dependency acceptance was checked in `agent-exchange/status/2026-09-09T215229Z-codex-tree-tr-memory.md`; it is explicitly accepted. No production, causal-feed, full-tree or economic certification follows.

Recommended next action:

Add M1's small regression during review follow-up, then have the controller integrate Task2 audit evidence and obtain the planned component final review. No runtime change is requested.

Verification reviewed:

- Read startup/exchange instructions, assigned inbox request, complete brief/report/spec, task-reviewer rubric, and all seven complete additions in `.superpowers/sdd/2026-09-10-tree-pattern-readers/task-1-diff.md` in consecutive chunks. Base/HEAD declared by package: `c1b6071633c55376c64f0a98ece843706f420f49`; additions are untracked. Initial `git status --short` and `git diff --stat` were diagnostic only; no Git writes. No changed runtime/test file was separately reread.
- Named external risk: accidental live imports or altered composed-reader requests. Inspected only original import/signature/fetch/composition lines in retained `wm.py`, `liquidity.py`, and `checklists.py`. Named external risk: Brinks unknown-vector catch semantics. Read retained `brinks.py` and local `pvsra.py`. Original sources were read only, never executed. These focused inspections do not substitute for Task2's full audit.
- Implementer reports initial 50 missing-module RED and subsequent 66 runtime / 182 combined GREEN in 1.77s, exit 0, no warnings, using `python -B -m pytest tests/tree_replay/test_pattern_readers.py tests/tree_replay/test_tree_tr.py tests/tree_replay/test_reversal.py -q --tb=short -p no:cacheprovider`. Reviewed as reported evidence; did not rerun the suite under the task-reviewer rubric. Package LF/CRLF notices are Git packaging diagnostics, not reported test warnings.
- Independent narrow probe: PowerShell literal here-string piped to `python -B -`. Imported only the candidate `BrinksReader` and pandas; supplied eight UTC five-minute rows starting `2026-09-09 14:00Z`, OHLC `100/101/99/100`, volume `'bad'`, and clock `2026-09-09 15:00Z`. Asserted non-None box, `(hi,lo,close)==(101.,99.,100.)`, vector count `is None`, and calls `[('clock',),('X','5m',2)]`. PASS, exit 0, no warnings. No files or persistent test additions were created by this probe.
- Only this requested review report was written. Task2 files, inbox, source checkout, branch/index, live behavior and data/model state were not modified.
