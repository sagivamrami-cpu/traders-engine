# Agent Exchange Request

Target: original independent Task 1 reviewer
Sender: Codex controller
Created at: 2026-09-14 01:00:00 UTC
Status: REVIEW_ONLY

Objective: verify closure of M1/M2 in
`reviews/2026-09-14T000000Z-lifecycle-gate-park-task-review.md`.

Required inputs: original task request/review; retained source
`chart-desk/chartdesk/tracker.py` lines 1547-1557; current runtime/test/usage
files from that request; plan and contract.

Required judgment: distinguish source fidelity from a new policy. Confirm the
source itself persists `bool(tr.get('to_group'))`, that the new stale-group
regression characterizes it, and that M2 boundaries now have real raw-tape
coverage. Return separate spec/quality verdicts and only new or unresolved
findings in `agent-exchange/reviews/2026-09-14T010000Z-lifecycle-gate-park-task-rereview.md`.

Verification: focused static review only; do not rerun reported 169-case suite
or execute original/replay runtime. No edits, nested agents, live effects,
commits/pushes or scope expansion.
