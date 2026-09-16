# Human Decision

Approver: Human Data Owner

Created at: 2026-09-01T15:38:01Z

Scope: Record 2017-01-01 through 2017-05-31 as a known damaged-aggressor interval for the supplied GC order-flow archive. This is a mandatory exclusion for any future training or evaluation path that uses affected order-flow features, but it is not the complete order-flow era policy. Phase 23 must measure the archive's full schema and availability eras before any feature build; cumulative features such as CVD must be gapped or recomputed at damaged-era boundaries.

Decision: APPROVED

Evidence: Human approval in the active Codex session on 2026-09-01; local archive README and Codex profiling both reported dead or partially dead delta signal during the excluded interval; Groq review required treating this as one measured damaged window, not the entire order-flow era gate.
