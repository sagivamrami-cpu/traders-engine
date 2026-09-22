# Task1 implementation report

Status: DONE, awaiting independent spec/quality review.
Base=head c1b6071633c55376c64f0a98ece843706f420f49; no commits.
Three files: outbox_journal runtime, behavioral tests, usage (full task diff).

Actual retained outbox source read/parsed only.14selected functions plus original
LATE_AFTER_S and checked empty annotated_BORN; pure3helpers and11instance methods.
Exact original bodies and scoped substitutions, actual LifecycleIdentity(source),
process-local BORN. No original/live imports, default file sinks, transport or
precomputed queue/identity verdicts. Logical paths and raw context-managed IO.

RED: python -B -m pytest tests/tree_replay/test_outbox_journal.py -q --tb=line -p no:cacheprovider
35failed0.17s cc2e22exit1, expected missingmodule assertions before runtime.
GREEN: python -B -m pytest tests/tree_replay/test_outbox_journal.py tests/tree_replay/test_lifecycle_identity.py -q --tb=short -p no:cacheprovider
83passed0.90s493ddbexit0, pristine, no subsequent runtime/test edits.
Literal eventID ae73500e104a8e28 independently calculated using hashlib on
b'2|notice' before test writing, not runtime _eid. Full expected row and operation
trace asserted, repeated actual raw writes feed reads and merge. Context tests
use actual retained matcher, literal geometry and independent120/122clocks.

Coverage: nine spec behavioral groups, terminal resurrection prevention,
pending flag-preserving upgrades,600exact/justafter, original iterationwinner,
mergefirstts/last_ts, malformed/torn/payload handling, process birth memory,
lock cleanup on read/write/acquire errors, offlineguard refusal, real context,
actual resolve_text journal marks/newclocks and non-ASCII JSON newline.

Self-review: original _write guard is replaced by mandatory raw assert_offline,
not an implicit no-op; every supplied raw effect must already be offline because
lock setup precedes _write. Usage explicitly states this limit. Scope does not
certify actual locks/durability/provider isolation or historical datasets.
Independent full source graph proof belongs to Task2; no acceptance inferred yet.

SHA256 before review:
- runtime AEAF88184E23C313B61ACA349B1569C3C544222CA52F584CCF628AA97CDE84C3
- tests 159299C6FCC3B57295CF2130BCD3A6F722A219F07C6CE7AF5AB253DEC3BF5E14

## Fix round1 — I1 pending duplicate birth consumption

Verified review gap: only terminal consumption was explicitly tested. Added
four raw-journal cases (same minute120/cross-minute180, upgradeFalse/True),
then new event at721 beyond original600-second window must have no born.
No runtime changes. Covering original combinedcommand ->87passed0.87s,
c1d414exit0 pristine (39journal+48identity). Saved pending-birth-probe.py
runs each actual test and each against a local _BORN.pop->get mutant; original
runtime is not patched and no retained source is executed. Probe result follows
in controller ledger. Scoped task-1-fix-review.diff contains only fourcases.

Terminal probe: `python -B .superpowers/sdd/2026-09-10-outbox-journal-source/pending-birth-probe.py`
printed `PASS four actual pending-duplicate regressions; four retained-birth
mutants rejected`, exit0 (f50011). The preceding namespace-package import
failure was a helper-only issue, fixed by explicitly loading the local test
file; runtime and test behavior were never changed to address it.
