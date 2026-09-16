# Task2 controller implementation report

Requirements: Task2, docs/superpowers/plans/2026-09-09-historical-levelmap-core.md.
Status: IMPLEMENTED_AWAITING_CODEX_REVIEW (independent task review pending).
Files: frames.py, test_frames.py, HISTORICAL-FRAMES-USAGE.md only.

Implemented frozen FrameSpec/LabeledDailyPeriod contracts; complete calendar/
period ownership checks, causal daily/intraday construction, forming target bars,
separate source labels and actual observation/publication, explicit freshness,
missing-volume semantics and canonical selected-evidence hashes. No real data,
source imports, full-map/admission or training claims.

Verification:
- Baseline python -m pytest tests/tree_replay/test_periods.py
  tests/tree_replay/test_session_bars.py -q --tb=short:69 passed0.77s, exit0.
- RED python -m pytest tests/tree_replay/test_frames.py -q --tb=short:
  55 failed1.49s, exit1, before frames.py existed. All failure classes were
  expected Missing assigned causal frame builder assertions. Repeated long
  traceback output was tool-truncated, not claimed as an untruncated log.
- Initial implementation:45passed/10failed. Root cause traced to the existing
  bar selector requiring a strictly positive age budget while FrameSpec allows
  zero. Retained selector contract, passed a one-second internal compatibility
  floor and enforced the exact frame policy after selection. This does not
  relax the supplied age limit. No source or trading threshold changed.
- After correction:55 passed0.77s, exit0.
- Self-review regression for list/dict timeframe:2failed/2passed/55deselected
  before string guard; TypeError at dictionary membership violated the intended
  ValueError contract. Added the type guard; other2cases characterized already
  correct empty-prefix/zero-age and policy-hash behavior, no separate RED claim.
- Final python -m pytest tests/tree_replay/test_frames.py -q --tb=short:
  59 passed0.71s, exit0, no warnings.

Self-review checked daily period ownership versus missing-price completeness,
actual current row, closure skipping, label/publication separation, future
extension invariance, target-grid anchoring, base-grid resolution, zero budget,
volume overflow and no hidden I/O/clock. No open finding identified. Source
metadata and price provenance remain caller attestations. Base-partial/open-only
precision remains unsupported and documented; higher-timeframe partial state
from known closed base bars is supported. Component is not accepted yet.

## Task2 fix round1 - test evidence only (2026-09-09T11:11:31Z)

Status: IMPLEMENTED_AWAITING_CODEX_REVIEW.
Contract: `.superpowers/sdd/2026-09-09-historical-levelmap-core/task-2-fix-brief.md`.
Original public request: `agent-exchange/inbox/codex/2026-09-09T110501Z-historical-frames-review.md`.
Review addressed: `agent-exchange/reviews/2026-09-09T110501Z-historical-frames-review.md`, findings 1 and 2.

Changed only `tests/tree_replay/test_frames.py`, this append, and the authorized
result `agent-exchange/status/2026-09-09T110900Z-worker-frame-tests.md`.

Coverage added for finding 1:

- Two literal label cases: minus three hours moves January 1 to December 31
  (also crossing the year), and plus one day moves every label to the following
  UTC date, including the current row's label beyond decision time. All three
  rows assert literal actual observation/publication times; every non-label
  row field is also checked unchanged against the original frame.
- Six valid shortened-calendar cases: late start and early end for daily and
  intraday frames; daily coverage ending at January 2 midnight between required
  periods; and coverage ending at January 2 noon between active daily sessions.
  Intervals are clipped to coverage before constructing SessionSchedule, while
  original bars and periods remain supplied and metadata is already published.
  Every case reaches CALENDAR_COVERAGE and asserts BLOCKED, rows=[], and null
  observed_at/available_at.
- Literal complete row dictionaries for 5m-to-1h and 5m-to-4h aggregation at the
  exact first target close and one closed base bar later. Assertions cover OHLC,
  volume, source label, interval endpoints, CLOSED/FORMING state and actual
  observation/publication at row and frame level. Another future base bar is
  supplied but excluded from the literal expected prices and volume.

Finding 2: removed only the ineffective upsample parameter/branch from the
general grid-rejection test and replaced it with a dedicated empty-bar fixture.
The 30m base, 15m target, midnight origin/history and empty periods are otherwise
consistent. The test matches the entire specific error:
`^cannot upsample a coarser base timeframe$`.

Verification (fresh worker execution):

```text
python -m pytest tests/tree_replay/test_frames.py -q --tb=short
.....................................................................    [100%]
69 passed in 0.72s
```

Exit 0; no warnings. Ten additional parameterized cases and one replacement
case increase the original 59 collected cases to 69. All additions passed on
their first run against unchanged production code. These are characterization
tests; no RED is claimed and no new failing behavioral case was observed.
The earlier controller report's historical RED claims were not rerun/certified.

Self-review:

- Reviewed the actual before/after test contents using an in-memory line diff,
  because the pre-existing test file is untracked. The only removed content is
  the old ineffective upsampling parameter/branch. Unrelated tests are intact.
- Literal expected prices/times are independent of production aggregation.
  Coverage fixtures pass constructor constraints and specifically assert the
  frame coverage blocker; upsampling cannot pass on the earlier identity error.
- `git hash-object trading_system/tree_replay/frames.py docs/architecture/HISTORICAL-FRAMES-USAGE.md tests/tree_replay/test_frames.py`
  returned, respectively:

```text
97c741b9d5d200bcf201d06d31ff6b35b069e5a2
aaed9b9aa44f7453b29f8a13f73af8ecbb76907d
fcae2be30241ae93096e2cba722d150eeae81797
```

The production and usage-document hashes match the pre-edit hashes and public
review. `git diff --check -- tests/tree_replay/test_frames.py` exited 0 with no
output; this does not inspect untracked content and is not the delta evidence.
An ancillary timestamp command, `Get-Date -AsUTC -Format 'yyyy-MM-ddTHH:mm:ssZ'`,
failed because this PowerShell does not support `-AsUTC` ("A parameter cannot
be found that matches parameter name 'AsUTC'."). The clock tool supplied
`2026-09-09 11:11:31 UTC` instead; the pytest invocation separately exited 0.

No production changes, source imports, data access, subagents, commits, worktrees
or cleanup. Mandatory AGENTS/exchange startup and relevant inbox request were
read. Verification-before-completion skill guided fresh evidence and bounded
claims; the explicit fix contract governs the absence of a manufactured RED.
No new concern or blocker found. Controller must independently rerun/re-review
the delta before acceptance; source provenance and full-map readiness remain
outside this test-only result.
