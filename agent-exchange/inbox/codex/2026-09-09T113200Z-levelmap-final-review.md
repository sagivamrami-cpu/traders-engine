# Agent Exchange Request

Target:
Codex independent combined reviewer

Sender:
Codex controller

Created at:
2026-09-09T11:32:00Z

Status:
ACCEPTED_BY_CODEX

Objective:
Review complete historical-map core and frame/correction/map/reversal/pricing
integration against its plan, including documentation and remaining-scope truth.

Scope:
docs/superpowers/plans/2026-09-09-historical-levelmap-core.md;
actual final-review.diff in this plan's own .superpowers/sdd directory.
No commits; preserved dirty branch c1b6071633c55376c64f0a98ece843706f420f49.

Required inputs:
Full component plan, same scratch progress.md and task reports, actual diff.
Task reviews in exchange:111600Z source,110501Z frames plus own scratch scoped
fix review,112900Z adapter. Prerequisite acceptance recorded in status.

Contracts:
Exact original source formulas/order/gates; explicit causal lower-bar histories
and metadata; common decision time, stable IDs/hashes, missing-data distinction.
No full producer/dataset/model readiness inferred from synthetic component tests.

Non-negotiables:
- no invented thresholds, calendars, feeds, GC mapping or approval
- no source/feed execution or real data; no nested agents or implementation edits
- preserve dirty checkout, no commits/worktrees/cleanup

Deliverables:
agent-exchange/reviews/2026-09-09T113200Z-levelmap-final-review.md using review
template. Give spec/quality verdicts, named integration risks, severity and
file:line for findings, and all unverified obligations. Controller owns acceptance.

Verification commands:
Parent215 combined source/frame tests and40 adapter tests PASS, six sourceaudit
CLIs PASS; integration and broad ongoing and result will be supplied. No routine
suite reruns. Focused experiment allowed if an actual unresolved doubt needs one.
Broad excludes legacy validators explicitly.

Out of scope:
Reopening unrelated previously accepted components, finishing/merging branch,
full master completion, real-data certification, live trading or training.

Notes:
No parked/deferred findings or domain rulings in this plan. Prior Task2 findings
were missing required test coverage, both resolved and reviewed. Source formulas
were not modified to satisfy idealized expected floats.
