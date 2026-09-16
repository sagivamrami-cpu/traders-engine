# Agent Exchange Request

Target: Codex task reviewer
Sender: Codex controller
Created at: 2026-09-09
Status: REVIEW_ONLY

Objective: Review Task1 closed-base-prefix clocks for spec compliance and quality.
Scope: periods.py, frames.py, levelmap.py delta; new prefix tests and usage doc.
Required inputs: .superpowers/sdd/2026-09-09-reversal-producer-asof/task-1-brief.md,
task-1-report.md and task-1-review-package.diff in that same directory.
Contracts: Global Constraints in the task brief bind the review.
Non-negotiables:
- point-in-time correctness; no invented thresholds or feeds
- no production approval, live trading, broker execution or capital allocation
- no nested agents, commits, pushes, cleanup or implementation changes
Deliverables: agent-exchange/reviews/2026-09-09T120000Z-closed-prefix-review.md
using review template; both spec and quality verdicts, evidence and findings.
Verification commands: Review reported213/62test evidence; only run a targeted
test for a concrete unanswered doubt. Do not rerun suite routinely.
Out of scope: Task2 source worker, Task3, whole-branch merge readiness.
Notes: Runtime delta is against captured beforeimages, not HEAD's missing files.
