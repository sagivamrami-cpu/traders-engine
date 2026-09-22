# Task 2: Static proof and acceptance

Implement Task 2 only from `docs/superpowers/plans/2026-09-14-lifecycle-open-zone-return-source.md`.

Create a read-only source auditor, explicit-root JSON CLI and tests for the zone-return runtime. Pin retained `tracker.py` helper lines 1046–1106 and live-call boundary 2751–2759 at commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, blob `b616b34022e436545d8c1daf85eced51614fd74e`. Read/parse source only; never import/execute it.

The auditor must compare exact helper source behavior and runtime AST, including revalidation child construction/call, no-excursion, marker parse/rearm, directional band, full message sequence, and only marker direct mutation. Require accepted lifecycle transitions, lifecycle primitives/entry-band and revalidation child proof graphs. Revalidation's inherited offline-port effects must be documented; do not claim the composition is feed/effect-free.

All source/root/blob/runtime/child/report/serialization/CLI failure paths must produce valid `BLOCKED` JSON with replay/training readiness false. Tests must mutate helper order, `<=` rearm, reached, band direction, child identity and runtime direct-marker/revalidation behavior. Run Task 1 plus audit tests and CLI. Write report to `.superpowers/sdd/2026-09-14-lifecycle-open-zone-return-source/task-2-report.md`.

No source execution, commit/push, live trading, economic/replay/dataset/model behavior or unrelated modifications.
