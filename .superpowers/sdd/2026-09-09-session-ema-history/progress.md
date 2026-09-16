# SDD ledger — plan: docs/superpowers/plans/2026-09-09-session-ema-history.md

Continuation of approved architecture, not new trading design. Existing branch retained.
Baseline249passed in2.77s (tree_replay + data_foundation/test_sessions).
Task 1: pending; delegated schedule contract/normal-hours bridge.
Task 2: pending; parent critical-path selector/EMA integration.
Task 3: pending; combined review/verification/docs.

| Task/pair | Preflight contract check |
|---|---|
| 1 | Explicit intervals and bounded normal-template bridge; overlays rejected |
| 2 | All seed-history gaps checked; wall-clock freshness unchanged; calendar opt-in |
| 3 | Synthetic evidence only, no readiness or market claims |
| 1/2 | SessionSchedule UTC immutable canonical intervals join; disjoint files |
| 2/3 | Original strict calls preserved; actual-source calculation subset unchanged |

Process adaptation: native apply_patch creates briefs/ledger; bash helpers use shell writes.
Parent handles critical-path integration while sidecar builds calendar contract.
No worktrees, commits or scratch cleanup; review packages include untracked file diffs.

Task1 worker DONE: 124focused/293adjacentpassed, original RED117failures,
self-review equality guard RED5failed119passed; exact template types/fold hardened.
Parent read full worker result and actual calendar/test changes, inspected git state.
Task2 GREEN39passed in0.91s after missing-module/API RED; independent task reviews dispatched.
Parent combined761passed in27.08s (tree_replay/tree_spec/session resolver), source CLI
exit0 and source_subset_verified=true. Broad run active. No readiness flags enabled.
Documented loader boundary: SessionCalendar does not retain YAML special_sessions;
bridge certifies represented supplied fields only, not full raw-config coverage.

Task2: spec+quality approved by Hume, no findings. Parent combined run resolves
reviewer's integration-verification boundary.
Task1: fix round1/5, Important exact-template timezone-bearing time equality
bypass confirmed by parent (equal and same ISO despite tzinfo present).
Original worker resumed for tzinfo-is-None validation + four regressions.

Task1: fix round1/5 closed, RED4failed124passed, GREEN128passed in0.70s.
Descartes scoped re-review: addressed, no new breakage or remaining findings.
Task1: complete (no commits, review clean).
Task2: complete (no commits, review clean).
Parent final combined765passed in20.63s; final broad still running.
Final combined review package includes complete code/tests/EMA before-after/usage.

Parent final broad1137passed in75.49s; source CLI reverified after fix exit0,
source_subset_verified=true, both readinessfalse. No suites still running.
Zeno final review active. Acceptance still pending final review, not test results.

FINAL: Zeno approved combined local slice, no findings, all seven packaged
files matched current files. Task3: complete (no commits, final review clean).
Codex accepted in agent-exchange/status/2026-09-09T084708Z-codex-session-ema-history.md.
Final765combined/1137broad passed; source CLI verified. Branch/dirty work retained,
no cleanup or integration mutation. No raw calendar-overlay authority inferred.
