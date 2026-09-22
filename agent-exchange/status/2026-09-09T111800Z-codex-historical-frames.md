# Agent Exchange Result

Target:
Project memory and Codex

Sender:
Codex controller

Created at:
2026-09-09T11:18:00Z

Request:
agent-exchange/inbox/codex/2026-09-09T110501Z-historical-frames-review.md

Status:
ACCEPTED_BY_CODEX

Summary:
Task2 causal frame construction accepted, including scoped test-evidence fix.
Daily frames require supplied current-period ownership and source labels;
intraday frames use explicit grids and only published closed base prefixes.
Calendar gaps, publication, exact identity and age policies remain enforced.

Changed files:
- trading_system/tree_replay/frames.py
- tests/tree_replay/test_frames.py
- docs/architecture/HISTORICAL-FRAMES-USAGE.md

Verification results:
- Parent independently ran python -m pytest tests/tree_replay/test_frames.py -q
  --tb=short: 69 passed0.57s, exit0 (fresh intake run).
- Read original request, public review, worker result, fix contract and complete
  scoped re-review; inspected git status, production code and actual before/after
  test diff. Source worker files remain separate and unaccepted by this note.
- Initial review required missing boundary tests and a guard-reaching upsampling
  regression. Scoped re-review task-2-fix-1-review.md marks both ADDRESSED, with
  no new breakage. No runtime defect was claimed by those review findings.
- Earlier controller RED/GREEN history remains in task-2-report.md. New fix tests
  characterized existing behavior; no fabricated RED or independent recertification.

Decisions needed:
None for this component. Existing real-data and GC/source-variant questions remain.

Blockers:
None for Task2. Full map integration and broader plan remain unfinished.

Recommended next action:
Accept independently reviewed Task1, then implement Task3 public map adapter.

Notes:
No real data, live changes, dataset, training, model promotion or readiness claim.
Calendar/source metadata are attestations, not historical vendor certification.
Closed-base precision only; no open-only or partially observed base bar support.
Both readiness flags remain false. No commits or cleanup.
