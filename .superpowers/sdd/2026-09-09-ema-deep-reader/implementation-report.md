# EMA/deep reader implementation evidence

Main inline per approved plan. Both tasks implemented, independent reviews pending.
No commits; HEAD c1b6071633c55376c64f0a98ece843706f420f49. Exact task briefs and
untracked-file diff packages are adjacent. Main read full source/spec/runtime.

Task1: all original classes/properties/calculations, EmaReader offline ports,
real CSV decoding/UTC parse and per-window deep prefix. Six exact adaptations;
no source execution. Existing public ema_snapshot unchanged. 43 runtime cases.
Initial pre-runtime RED36 failed0.94s was recorded in prior ledger; current
supplemental tests characterize duplicate handling, calculation errors after
successful parsing, raw nearzero classification and stable magnet ties.
They extend existing behavior without a runtime change. Runtime unchanged SHA
B632AD21C88DF94CD2D92732273E510A662F50DAC7D523CEA5EF25F5F321A774.
Test SHA981696E576516A4421540A2C7EF524FFC2A004E71D6A2475C15B5AD18383203F.

Task2: whole ordered AST projection, literal chart-desk commit/two blobs,
exact-count port substitutions, real inherited strict seededEMA auditor, CLI
required root/JSON/0or2, no imports/execution of source or runtime.
58audit cases normalmissingmoduleRED58failed0.46s then58passed6.63s, exit0.
Auditor SHA2EC14738974D42AE1FDD64B2A9AD0B0E1D9C2507552D70CB6F2CAED692060B01.
Audit tests SHAA32A37545DE2635E218AD6EEBBC16702C2D2D7ED087A57A70442998367836D22.

Main combined command:
`python -B -m pytest tests/tree_replay/test_ema_windows.py tests/tree_spec/test_ema_windows_source.py tests/tree_replay/test_ema.py tests/tree_replay/test_stretch.py tests/tree_spec/test_stretch_source.py -q --tb=short -p no:cacheprovider`
Session1533 terminal exit0:255passed14.13s, no warnings. Prior158passed3.03s
overlaps, not extra coverage. Explicit CLI VERIFIED/emptyblockers, false
replay/training readiness. CLI/importguard included in58audit cases.

Candidate-only mutation probes executed local vendor code in fresh process,
never retained source, with no file writes:
- Replace splice concat with head-only: existing actualCSV and shortlive
  tests both failed at convergence as expected (2failed/41deselected0.29s).
- Replace keep-last with keep-first: duplicate-live numerical test failed
  expected128.00499375780274 versus128.0 (1failed/42deselected0.26s).
Both outer commands exit0 after asserting expected pytest TESTS_FAILED.

Usage documents private rawports, no causal availability certification,
GC/spot seam unresolved, source3bar slope versus existing5bar adapter, and
actual spanATR may contain deep rows. Source rounding retained, not epsilon-fixed.
No live/data/dataset/model/commit/deployment actions. Fullmaster not completed.
No known open implementation findings; task and final review gates remain.

Task review210300Z: both specPASS and qualityapproved; Task1 M1minor requested
unequal even median and generated fully descending trend coverage. Main verified
the gap and added exactly two tests, no runtime changes. Current103runtime/audit
tests passed7.37s exit0. Candidate-only upper-median mutation made new test fail
7.0 vs expected5.0 (1failed44deselected0.25s); outerexit0, no files changed.
Runtime-test final SHAA7330C4F4D5BEB6FF689519C10BBFA5C28CD4E56D3B472CE86239578A35EBE49.
task-1-m1-diff.md supersedes only runtime-test section; original other five files
unchanged. Final review must verify M1 closure. Main inspected actual files and
source, current gitstatus/diff, read review and originalrequest, watcher snapshot.
Whitespace checks on newly edited code/tests report only Git CRLF conversion
warnings, no whitespace error. Task reviewer closed; no testprocesses live.
