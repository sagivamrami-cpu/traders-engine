# Task2 fix round1 — missing specified test evidence

Read original Task2 brief/report and public review
agent-exchange/reviews/2026-09-09T110501Z-historical-frames-review.md. Address both
numbered findings exactly. The reviewer identified missing test evidence and an
ineffective test, not a demonstrated production defect.

Own only tests/tree_replay/test_frames.py; append fix evidence to task-2-report.md
in this scratch directory. No production edits unless a new failing behavioral
case proves a real bug; then report the case to controller before expanding scope.
No subagents, commits, worktrees, cleanup, live source imports or data access.

Add literal cross-UTC-day/month source-label checks with actual observation/
publication unchanged; valid late-start/early-end calendar coverage cases,
including coverage ending between required daily periods; exact 1h/4h closed
rows followed by a forming row with literal OHLC/state/actual time. All blocked
frames must withhold rows and timestamps. Correct the upsampling case so it
actually reaches the target/base duration guard using consistent base bars or
empty bars, and check the upsampling-specific rejection. Existing unrelated
cases and source work belong to others; do not modify them.

Run python -m pytest tests/tree_replay/test_frames.py -q --tb=short. Additions that
characterize already-correct behavior need not manufacture RED; report honestly.
If you observe a genuine new failure, preserve the failing test and escalate it.
Append covering cases, exact command/output and self-review to task-2-report.md.
Also leave template result agent-exchange/status/2026-09-09T110900Z-worker-frame-tests.md,
referencing the original public review request. Return only status/test summary,
concerns and report paths. Controller will independently rerun and re-review.
