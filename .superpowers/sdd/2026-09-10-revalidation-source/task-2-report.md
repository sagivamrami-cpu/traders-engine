# Task2 implementation report

Full independent ordered AST projection of original tracker revalidation and
tradeplan calendar helpers; literal source commit/blobs/root/baseline validation;
exact one-count boundary replacements and15shadow occurrences. All seven actual
dependency auditors run, including nested dependencies. Failed or inconsistent
dependency verdicts cannot produce success. CLI works from unrelated cwd without
source/runtime imports; both readiness flags remain false.

Files: trading_system/tree_spec/revalidation_source.py,
tools/check_revalidation_source_parity.py, tests/tree_spec/test_revalidation_source.py.
No source/runtime strategy edits in this task; source only parsed as text/AST.

TDD: first command
`python -B -m pytest tests/tree_spec/test_revalidation_source.py -q --tb=short -p no:cacheprovider`
59normal missingauditor failures0.49s. After implementation same command:
59passed99.45s exit0 (session57707 terminal). No runtime/auditor changes since.
Four test-only additions verify top-level order and dependency false-empty,
raised OSError and inconsistent true-with-blocker reports. Command:
`python -B -m pytest tests/tree_spec/test_revalidation_source.py -q --tb=short -p no:cacheprovider -k 'dependency_failure or top_level_order'`
4passed59deselected7.59s exit0. Current total63tests; no runtime changes.

Task1 review211924Z PASS/Approved/no findings,77fresh runtime cases passed3.84s.
Main local-candidate-only mutation probes disabled with_trade_at_send veto and
changed30min news window to15min; existing real-composition behavioral tests
raised AssertionError for each. No original execution or on-disk mutation.

Self-review: source helper order from AST line positions independently checked;
reversal auditor supplies source_subset_verified in addition to subset_verified;
all reports' blockers retained even if flag true. No unresolved self-review finding.
Combined current verification completed after task review:
`python -B -m pytest tests/tree_replay/test_revalidation.py tests/tree_spec/test_revalidation_source.py tests/tree_replay/test_ema_windows.py tests/tree_replay/test_stretch.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_calculations.py tests/tree_replay/test_lifecycle_bars.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_watch_storage.py -q --tb=short -p no:cacheprovider`
539passed114.26s exit0, session80757terminal. No runtime/test edits during run.
Earlier invocation used nonexistent test_lifecycle_primitives.py and stopped
before collection; corrected command above resolves actual filenames. Not a
product failure or a skipped test. Final component review remains outstanding.
