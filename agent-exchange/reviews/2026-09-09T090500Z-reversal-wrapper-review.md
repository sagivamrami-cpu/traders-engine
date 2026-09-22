# Agent Exchange Review

Reviewer:
Codex independent task reviewer; no nested agents.

Target request:
agent-exchange/inbox/codex/2026-09-09T090500Z-reversal-wrapper-review.md

Created at:
2026-09-09T09:06:30Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
PASS for Task 2 plan alignment and code quality. No blocking or other actionable
defects found in the reviewed files. This is a wrapper review, not acceptance of
the separately developed source-parity tool or completion of Task 3.

Findings:

- Reviewed actual untracked `trading_system/tree_replay/levels.py`,
  `trading_system/tree_replay/reversal.py`, and
  `tests/tree_replay/test_reversal.py`, against the full
  `docs/superpowers/plans/2026-09-09-level-reversal-asof.md`. HEAD is
  `c1b6071633c55376c64f0a98ece843706f420f49`; an empty HEAD comparison would not
  represent this review. Read the startup protocol, current design and relevant
  baseline/session plans and status. Inspected existing bars, session selection,
  calendar and snapshot contracts, plus the vendored detector/PVSRA dependencies.
- `levels.py:14` and `levels.py:27`: frozen records enforce explicit, trimmed
  metadata, exact instrument identity, finite positive prices, UTC normalization,
  publication ordering, immutable level collections and unique names. Source
  ordering survives equal-price ties.
- `reversal.py:97` and `reversal.py:172`: existing selectors establish eligible
  history; only events confirmed at the latest selected close can be returned.
  Although the source function scans the supplied frame, its newest-first dedup
  cannot let an older confirmation suppress the latest one. Earlier detections
  are discarded, so the supplied level snapshot is not emitted as retrospective
  evidence for historical signals.
- `reversal.py:111`: missing/unavailable/future/stale levels, warmup and missing
  or all-zero volume remain explicit blockers. Valid empty/ineligible levels and
  failed source patterns return NO_CANDIDATE. No economic failure labels result.
- `reversal.py:158`: the wrapper delegates strict pattern, eligible-level, sort,
  tie and dedup behavior to the vendored subset; it does not add trading
  thresholds. Calendar closures may occur within seed history, while source
  adjacency checks still forbid a pattern spanning a closure.
- `reversal.py:30`, `reversal.py:44` and `reversal.py:167`: overflow checks and
  scalar snapshot validation protect finite output. Undefined volume ratios are
  UNKNOWN/null. Feature availability conservatively includes every selected bar,
  supplied levels and supplied calendar; no emitted feature is available after T.
- `reversal.py:106` and `reversal.py:174`: selected-window, level, calendar,
  freshness, decision-time and declared calculation/runtime versions contribute
  to evaluation identity. Source episode identity is preserved separately.
  Outputs stay unpriced, nontradeable and explicitly unready for replay/training.

Non-blocking limitations (not defects):

- `levels.py:30`: caller metadata cannot establish that the levels were computed
  causally or that the feed lineage is authentic. Input evidence must be retained
  separately; this is an explicit approved interface limitation.
- `reversal.py:174`: candidate_id hashes source commit, producer, source event ID
  and confirmation time, not level values or snapshot content. Replacing the
  fixture's level price 100 with 100.2 retains candidate_id while changing
  evaluation_sha256. Consumers must retain evaluation identity alongside event
  identity when storing revisions. The source's 15-minute episode grouping is
  not a unique fill or lifecycle identifier, and candidate_id is producer-specific.
- `reversal.py:167`: feature publication is the maximum dependency availability,
  not a per-input lineage ledger. Declared source/version hashes are not runtime
  proof of source AST parity; that verifier remains in the separate task.

Open questions:
None requiring a Task 2 revision. Historical level construction, pricing,
admission/arbitration, source-verifier acceptance and full integration remain
outside this task's verdict. Test-first chronology cannot be established from
the final untracked files; no independent RED-run claim is made here.

Recommended next action:
Accept this bounded wrapper task after parent intake. Complete the separately
scoped source review and planned integration verification. Preserve the stated
provenance and identity limitations in the parent-owned usage documentation.

Verification reviewed:

1. Fresh independent targeted run, with Python bytecode and pytest cache writes
   disabled to respect the read-only review:

   ```powershell
   $env:PYTHONDONTWRITEBYTECODE='1'
   python -m pytest tests/tree_replay/test_reversal.py -q -p no:cacheprovider
   ```

   PASS: 91 passed in 1.23s, exit 0. This executes the requested test target;
   the additional flag only disables cache persistence.

2. Read-only `python -B -` synthetic probe using
   `runpy.run_path('tests/tree_replay/test_reversal.py')` fixture helpers and
   `dataclasses.replace`: PASS, nine assertions, exit 0. Reproduction cases:

   - Set schedule intervals to (): NO_EXPECTED_BARS.
   - End schedule coverage and its interval at the final bar's open:
     CALENDAR_COVERAGE.
   - Delay final bar availability by 1 microsecond beyond T with an open schedule:
     HISTORY_GAP.
   - End the open interval two minutes into the final M5 bar, supplying levels
     observed at the predecessor's close: one straddling bar, 12 selected bars,
     no candidate.
   - End the session at confirmation close, cover the following 371 seconds:
     detection at close+370s, STALE at close+370s+1us.
   - Set final M15 fixture volume to 350 for long and short mirrors: detected
     red and green climax setups respectively; strict JSON serialization passes.
   - Change the M5 fixture level from 100 to 100.2: same candidate_id, different
     evaluation_sha256.

3. Read-only git status/diff and file inspection completed. Reviewed file SHA256:

   - levels.py: `37a83e3712dbc7675d8040c8be5094daadd71ec54bb14b4498c7911d8f0fe02b`
   - reversal.py: `abc20964b8591d0a5c58cc2907c1ea681d5fb65b3eec3878920d63cafe65a3dd`
   - test_reversal.py: `b1e308f94a7637584dd867095ad194fb539e0cc095baa733317309b683651d60`

No broad-suite or source-parity CLI pass is claimed. Parent documentation changes
were concurrent and are not accepted by this review. No source-checkout execution,
network, nested agents, implementation edits, commits or inbox mutation occurred.
This review note is the only file written by this reviewer.

Supplemental package consistency confirmation — 2026-09-09T09:10:22Z:

PASS. `.superpowers/sdd/2026-09-09-level-reversal-asof/task-2-review.patch`
contains exactly the three reviewed new files, with one full addition hunk each:
levels.py (53 lines), reversal.py (190 lines), and test_reversal.py (399 lines).
Read-only PowerShell reconstruction of each hunk matched the actual file text
exactly, including its final newline. Each actual file's SHA256 also matched
the corresponding reviewed hash recorded above. No implementation changes were
found relative to the reviewed files.

Package SHA256:
`4a9339d750e63d7af2ed5719ac0cad1608786f7dab33dea5505f6d68803a4228`.

This supplements the existing verdict with package consistency only. No new
code review or test reruns were performed; only this note was appended.
