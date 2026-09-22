# Task2 source proof report

Status: DONE, awaiting task review. Three new files: tree_spec/tree_revalidation_source.py,
tools/check_tree_revalidation_source_parity.py, tests/tree_spec/test_tree_revalidation_source.py.
Base/head c1b6071633c55376c64f0a98ece843706f420f49; full additions, no commits.

Proof scope: independent matrix commit/blob/imports/two ordered signatures,
complete function projections with exact-count substitutions. Original TFView
expression is replaced only as a whole by existing actual matrix.read_frame.
Complete facade AST compared with literal composition; only module/class docs
excluded, all executable imports/bases/signatures/order/forwards retained.
Actual audit_tree_walk_source runs and covers accepted tree/matrix/revalidation/
basis dependencies. Blockers, nonverified empty reports and input/StopIteration
failures propagate. No runtime/original imports; readiness always false.

Tests and evidence:
- Normal lazy import RED51failed0.74s exit1 (fa4ff3), before auditor/CLI creation.
- GREEN command: python -B -m pytest tests/tree_spec/test_tree_revalidation_source.py -q --tb=short -p no:cacheprovider
  terminal72424/4daa34,51passed32.46s exit0, pristine.
- Candidate mutation tests isolate the unchanged expensive child graph; they
  exercise real new source parsing/projection/identity/CLI boundaries. Separate
  tests run actual inherited graph, real nested tree drift, missing baseline
  pin through actual CLI/EMA dependency, valid/invalid subprocess CLI from
  unrelated cwd and subprocess guard against original/runtime imports.
- Explicit CLI python -B tools/check_tree_revalidation_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
  fresh exit0 VERIFIED, checked matrix_reader/tree_revalidation, blockers[],
  actual fulltree dependency report, ready_for_replay/trainingFalse.
- Combined planned command26887 is running at report creation; terminal result
  will be appended. No runtime/test files changed during it.

Task1 accepted195318Z after independent task spec/qualityPASS/no findings.
Self-review found no open issue. Source authority is separate from candidate;
private docs normalization is restricted to module/class string docs, not
executable behavior. Errors are reported fail-closed without market defaults.
This is not full causal feed/caller/lifecycle/dataset/model certification.

Combined terminal addendum19:55UTC: same26887/chunkf4139c completed250passed
49.26s exit0, pristine, runtime/tests unchanged. Command:
python -B -m pytest tests/tree_replay/test_tree_revalidation.py tests/tree_spec/test_tree_revalidation_source.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider
No live test processes remain from these runs. Review and final gates pending.
