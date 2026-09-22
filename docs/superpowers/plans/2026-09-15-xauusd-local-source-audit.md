# XAUUSD local source audit

Authority: User approval of source-profile recommendations and continuation.
Purpose: Reproducible read-only profiling of the already identified local files.

1. Add failing tests for CSV/gzip/Parquet content hashes, duplicate and unordered
   timestamps, missing/invalid timezone information, malformed OHLC/volume,
   event-list extent versus coverage, and missing source paths.
2. Implement `tools/audit_xauusd_local_sources.py`. Explicit sibling-repository
   root; only TV XAUUSD files, Dukascopy hourly XAUUSD cache, XAUUSD flow file,
   news calendar, and expected options report filenames are in scope. Report
   metadata/counts/hashes to stdout. Never invoke existing vendor loaders.
3. Verify on fixtures, then audit local files. Inspect raw gaps without treating
   weekends/maintenance as missing market data. Retain unknown publication and
   source semantics; a successful profile is not source certification.
4. Save an aggregate findings report, map blocking data gaps to owners, and
   update the work tracker. Do not commit market rows. Record independent
   provider/capture acceptance as still pending unless a review actually arrives.

The tool has no network client, automatic file repair, output-file writer,
economic labels or training flag promotion. Expected output includes false
training readiness because this is profiling only. Tests use synthetic files.

## Completion of this diagnostic slice

All four steps completed. Final 17 tests passed in 2.55s; local CLI exited 0.
The source snapshot and human handoff are in
`docs/architecture/XAUUSD-LOCAL-DATA-AUDIT.md` and
`agent-exchange/status/2026-09-15T101524Z-codex-xauusd-local-source-audit.md`.
This completes the audit utility, not the overall tree/model plan.
