# Causal quote/watch IO ledger

Plan2026-09-09-causal-quote-watch-io, specCAUSAL-QUOTE-WATCH-IO-CONTRACT.
HEADc1b6071633c55376c64f0a98ece843706f420f49, existing feature branch,
.git==common; in-place approved workflow, no new worktree or cleanup.
Task1 planned; main implements critical-path task inline with independent reviews.
Master C already approves causal reads/state/trace; source thresholds untouched.
Previous goal turn: progress, tracker storage implemented and accepted160544Z,
309current tests/sourceaudit2 and clean task/fix/final reviews. No blocker streak.
Preflight source dependencies: current_session not in existing map_sessions,
known source _log creates file before serialization and mutates caller sessions
before open. Quotes absent-file differs from state absent->{}; raw log must not
drop non-rejection bytes. Chunked append/seek preserves source tail efficiency.
No domain ruling, no real data/live action. Entire master remains active.
Task1 implemented: baseline196; runtimeRED57/GREEN57; auditRED13, annotation
selector issue diagnosed/fixed locally; GREEN70 then post-GREEN coverage tests,
planned269passed10.01s. Newwatchaudit4 and tracker-audit7 verified/no blockers.
Same-process handles76177/38847 observed terminal. No active test process.
Task report and8file package next, independent review required. Full master active.
Task review161821Z returned spec/qualityPASS with no findings; original request
and report read, actual status/diff inspected, planned suite rerun269passed16.30s.
Task accepted162401Z; independent final review requested. No runtime changes.
Final review162401ZPASS, no findings; independent source audit and4,936reader/tail
comparisons passed. Main read report/request and scoped status/diff, source audits
4/7passed, suite269passed16.30s. Full component accepted162759Z; memory updated.
Goal remains active; next source lock/caller/lifecycle, no dataset/model.
