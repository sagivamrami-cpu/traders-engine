# Task1 implementation report

Status: DONE, awaiting independent task review. Main inline implementation.
Base/head c1b6071633c55376c64f0a98ece843706f420f49; no commits. Four new files
are packaged as full additions; tracked-only git diff would omit them.

Files: _vendor/matrix_reader.py (original two function projections),
tree_replay/tree_revalidation.py (actual raw-port composition),
tests/tree_replay/test_tree_revalidation.py (27 cases),
docs/architecture/TREE-REVALIDATION-BINDING-USAGE.md.

Source: chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
matrix.py blob28641487567c457b6922c2a63055659867bb4248. Original read/parse
only. Existing numerical/tree/revalidation/basis modules unchanged.

Runtime evidence:
- Initial normal missing-module RED19failed1.52s before runtime creation.
- Initial GREEN attempt17passed/2failed: source shadow name is news_window,
  not news; opposite-before-later-stop fixture needed finite price below all
  short targets (source stamp does not reject NaN). These were test expectation
  corrections, not strategy changes. Corrected19passed5.96s, no warnings.
- Seven further cases: actual earlier bias veto, splice20day boundary, raw deep
  failure, house variant despite metadata, missing/invalid pending timestamps.
- Prior last command output was lost; current process inspection found no
  Python process. Fresh planned fourfile run terminal29597/chunk9e9e89:
  239passed20.46s,exit0. No result inferred for lost output.
- Added hand-derived full-history ATR case: a range30 impulse just before last
  55rows yields 2+2*(13/14)**55, not2. Controlled in-memory candidate trim mutation
  fails that same real consumer test; original candidate passes. Probe terminal
  b17e6b exit0; local namespaces only, no production/original-source execution.
- Current planned command:
  python -B -m pytest tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_revalidation.py tests/tree_replay/test_admission_frames.py -q --tb=short -p no:cacheprovider
  terminal91972/chunkeaa544:240passed19.87s exit0, pristine. Includes27new cases;
  counts overlap, do not sum runs. Runtime/tests unchanged since this run.

Self-review: actual shape gate/matrix/tree used, raw final-verdict methods raise
if consumed. Construction inert; explicit ports preserve exceptions, operation
clocks and context manager lifetime. Hand-derived raw fixtures distinguish
opposition/stopped/unknown versus clean approval and exact age/shape boundaries.
No training labels, market data, credentials, live effects or strategy changes.

Task2 full projection/audit/CLI not implemented. Full causal integration and
master C/D/E-I remain. Usage intentionally says review/audit pending.
