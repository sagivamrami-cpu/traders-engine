# Human Decision

Approver: Human Data Owner

Created at: 2026-09-01T15:38:02Z

Scope: Record 30m as the human-approved first baseline candidate for planning, subject to Phase 23/24 dataset-contract gates. This does not freeze a training timeframe and does not authorize resampled dataset construction. The existing 4H order-flow CSV is reference and sanity-check material only, not the canonical first training source. Canonical feature construction should start from lower-timeframe GC sources, primarily the one-minute Parquet order-flow inputs, after session, bar-boundary, timestamp-role, missing-bar, and roll-policy decisions are explicit.

Decision: APPROVED

Evidence: Human approval in the active Codex session on 2026-09-01; human clarified that the 4H CSV is four-hour bars and that the project previously intended to start from a lower timeframe; Groq review required keeping 30m as a candidate until the dataset contract pins the resample recipe.
