# Task 2 implementation report
Request: task-2-brief.md; user continued the previously described calendar/missing-history integration.
Changed session_bars.py, ema.py and test_session_bars.py/test_session_ema.py.
No edits to original bars.py, vendored numerics, legacy sessions or policies.

RED: python -m pytest tests/tree_replay/test_session_bars.py -q --tb=line:
27failed in0.54s (missing new session_bars/calendar modules).
RED: test_session_ema.py11failed in0.65s while calendar sidecar was not yet present.
Isolated API RED: test_calendar_mode_requires_a_valid_schedule_contract failed
in0.60s with TypeError unexpected session_schedule keyword before EMA modification.
GREEN after real calendar sidecar landed:
python -m pytest tests/tree_replay/test_session_bars.py tests/tree_replay/test_session_ema.py -q --tb=short
39passed in0.91s, exit0.

Opt-in calendar mode uses complete interval containment, explicit fixedUTC grid,
coverage/publication blockers and entire expected seed history. Scheduled closures
do not reset EMA. Off-session and straddling eligible inputs counted separately.
Known feature availability includes the schedule dependency. No readiness flags enabled.
No gap inferred as holiday; empty explicit schedule means declared closed.
Wall-clock freshness unchanged; even a recent last bar cannot conceal a missing
latest expected slot. Current future suffix invariance tested.

Self-review: membership binary search covers internal breaks, exact close and
opening equality; original selector still validates all input records/revisions.
Schedule normalization/immutable intervals are the task1 contract. Snapshot hash
includes canonical complete schedule identity; calendar evidence is not ML features.
Scope limits: supplied schedule truth/coverage/availability are caller evidence,
normal-hours template not full historical overlay, no resampling/partial bars.
No feeds, candidates, labels, models, commits, pushes or live effects.
