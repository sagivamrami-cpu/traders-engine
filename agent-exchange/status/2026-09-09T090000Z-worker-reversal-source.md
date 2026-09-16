# Agent Exchange Result

Target:
Codex parent

Sender:
Codex source-sidecar worker

Created at:
2026-09-09T09:06:29Z

Request:
agent-exchange/inbox/codex/2026-09-09T090000Z-reversal-source-sidecar.md

Status:
IMPLEMENTED_AWAITING_CODEX_REVIEW

Summary:

Implemented Task 1 of docs/superpowers/plans/2026-09-09-level-reversal-asof.md.
Vendored the exact pinned detector constants, Reversal dataclass and requested
helper/detect_frame ASTs. Its sole local calculation import is
`from . import pvsra as tr`. Added `pvsra(df: pd.DataFrame, lookback: int = 10)`
as an explicitly documented default non-auction specialization using only
numpy/pandas imports and unchanged retained source statement ASTs.

The text-only verifier fixes all three source blob hashes independently of
manifest content, requires exact coverage and imports, compares entire ordered
vendor module ASTs, and verifies PVSRA defaults, setup/branch preconditions and
auction.resolve_slots' immediate None return for auction=False. Extra code,
duplicates, omissions and altered specialization statements fail closed.
It never imports or executes either the supplied checkout or vendored modules.
Successful output has subset_verified=true (also source_subset_verified=true
for consistency with the existing checker), with both readiness flags false.

Changed files:

- trading_system/tree_replay/_vendor/level_reversal.py
- trading_system/tree_replay/_vendor/pvsra.py
- tools/check_reversal_source_parity.py
- configs/trees/level-reversal-contracts.json
- tests/tree_replay/test_reversal_source.py
- agent-exchange/status/2026-09-09T090000Z-worker-reversal-source.md

Verification results:

- TDD initial RED: `python -m pytest tests/tree_replay/test_reversal_source.py -q`
  exited 1: 29 failed, 36 setup errors in 2.79s. Detector/PVSRA/checker were
  absent; checker-dependent fixture setup could not import the missing tool.
  Tests were written and run before any implementation files were added.
- After implementation, 62 passed / 3 failed. Two M15 short fixtures accidentally
  admitted a warmup doji through the inclusive spread-volume rule; changed the
  synthetic warmup geometry to isolate the intended setup. The remaining test
  compared pandas frequency metadata that source normalization does not retain;
  disabled only that metadata comparison. Corrected the independent bullish
  equality fixture after the warmup change. Source detector behavior was not
  changed to accommodate fixture expectations.
- Final GREEN: `python -m pytest tests/tree_replay/test_reversal_source.py -q`
  PASS, 65 passed in 5.56s, exit 0.
- `python tools/check_reversal_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`
  PASS, exit 0, blockers=[], subset_verified=true,
  source_subset_verified=true, ready_for_replay=false, ready_for_training=false.
- Read-only `git -C C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk rev-parse HEAD`
  confirmed 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
  `git ls-tree HEAD chartdesk/level_reversal.py chartdesk/tr.py chartdesk/auction.py`
  confirmed the three pinned blob identities now checked by the CLI.
- `git -c core.autocrlf=false diff --no-index --check -- NUL <path>` for each
  of the five code/config/test paths above: PASS, no whitespace diagnostics.
  Removed a trailing blank line identified by the initial whitespace check.
- Scoped git status confirms these implementation paths are new/untracked;
  this worker created no commits and did not alter unrelated workspace changes.

Decisions needed:

None for Task 1. Parent owns wrapper integration and acceptance review.

Blockers:

None for the scoped source sidecar. Full replay/training remains uncertified.

Recommended next action:

Parent should inspect these files, rerun the two required verification commands,
and integrate the concurrently implemented as-of wrapper. This is a worker
delivery, not a claim of independent parent acceptance or combined-suite success.

Notes:

- Synthetic tests cover both directions and timeframes, M5 climax-only and M15
  rising tiers, prior-10 exclusion of current volume, inclusive climax/volume
  thresholds, missing/zero volume, custom lookback, exact eligible names,
  level-order ties, nearest-close priority, stale/unfinished/gapped candles,
  directional arrival, revision normalization, and event/dedup bucket differences.
- Portable audit fixtures use inert synthetic source text with raising sentinels;
  tests locally replace trusted hashes only for those fixtures. The separate CLI
  above verifies the unchanged production pins against the actual retained source.
- Event IDs use vector-open 15-minute buckets; dedup keys use confirmation-close
  15-minute buckets. A source event ID can therefore differ from its dedup bucket.
- Pure source normalization keeps the last duplicate revision. Rejecting ambiguous
  revisions and enforcing historical level availability remain wrapper duties.
- The source detector's optional wall clock default and max_age_s API are retained
  exactly. Offline callers should pass explicit now; tests always do so.
- No build_plan/find/conflicts, pricing, source-package execution, installs,
  network/data downloads, notifications, live effects, commits, cleanup or edits
  outside the six listed owned paths. Parent-owned wrapper files were untouched.
