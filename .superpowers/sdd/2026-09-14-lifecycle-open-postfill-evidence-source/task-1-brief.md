# Task 1 — OPEN post-fill evidence runtime

Read the plan and intake first. Create only the runtime collector, its focused
tests and usage doc named by the plan, plus
`.superpowers/sdd/2026-09-14-lifecycle-open-postfill-evidence-source/task-1-report.md`.

Use TDD. The collector accepts one OPEN trade, supplied spot and raw corrected
tape port, and returns `(low, high, minimum_message)`. It must mirror source
2647-2689: spot first; fetch `15m,2`; correction gate; accepted historical
safety and fill locator; `fill_bar_first=True`; combine post-fill extrema with
spot; broad tape exception falls back to spot. Reuse accepted helpers. No
state mutation/effects/readiness. Never execute original source. No commit,
push, subagents or changes outside these files. Report RED/GREEN evidence.
