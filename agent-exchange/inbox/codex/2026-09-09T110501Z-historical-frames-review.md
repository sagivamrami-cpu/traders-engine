# Agent Exchange Request

Target:
Codex independent frame task reviewer

Sender:
Codex controller

Created at:
2026-09-09T11:05:01Z

Status:
ACCEPTED_BY_CODEX

Objective:
Independently review Task2 causal map-frame construction against its full contract.

Scope:
Task2 brief/report/actual diff in .superpowers/sdd/2026-09-09-historical-levelmap-core/.
Only frames.py, test_frames.py and HISTORICAL-FRAMES-USAGE.md are changed by Task2.

Required inputs:
Task2 extracted brief, task-2-report.md, task-2-review.diff; existing period/bar/
session/calendar interfaces only for concrete boundary risks.

Contracts:
Point-in-time closed-base prefix, explicit daily sequence and source labels,
explicit intraday origin, no compressed missing trading history, false readiness.

Non-negotiables:
- no invented thresholds, calendars, feeds or instrument mapping
- no production approval, source execution, data downloads, live trading or fitting
- read-only code review, no commits/worktrees/cleanup or nested agents

Deliverables:
Use review template to write agent-exchange/reviews/2026-09-09T110501Z-historical-frames-review.md;
spec/quality verdicts with file:line findings and any unverified requirements.

Verification commands:
Controller59 frame tests passed0.71s and baseline69 passed0.77s. No routine suite
rerun; a focused experiment is allowed for a concrete unaddressed doubt.

Out of scope:
Task1 source graph, Task3 map adapter, full-model or market-data certification.
