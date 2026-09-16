# Human Decision

Approver: Human Data Owner

Created at: 2026-09-01T15:38:00Z

Scope: Approve profile-only intake of the supplied local Databento GC order-flow archive so Codex can produce sanitized metadata, schema, timestamp, quality, and era diagnostics. This approval does not satisfy `ORDER_FLOW_SOURCE_DECISION`, does not authorize `BUILD_ORDER_FLOW_FEATURES`, does not authorize dataset construction or training, and does not authorize Databento purchases, external uploads, model promotion, live trading, broker execution, or capital allocation.

Decision: APPROVED

Evidence: Human approval in the active Codex session on 2026-09-01; Codex read-only profiling confirmed GC one-minute order-flow aggregates and raw Databento trade-tick files are present in the supplied archive; Groq review required narrowing this record to profile-only intake before any source approval or feature build.
