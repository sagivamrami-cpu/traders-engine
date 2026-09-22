# Task 3 implementer report

Status: DONE — IMPLEMENTED_AWAITING_CODEX_REVIEW

Request: `agent-exchange/inbox/codex/2026-09-09T112000Z-historical-levelmap.md`

Brief: `.superpowers/sdd/2026-09-09-historical-levelmap-core/task-3-brief.md`

## Scope and instructions followed

Read the Task 3 brief first, then AGENTS, exchange README/protocol, Codex inbox
listing and original request. Read both acceptance statuses: Task1
`2026-09-09T112000Z-codex-levelmap-source.md` and Task2
`2026-09-09T111800Z-codex-historical-frames.md`. Inspected the dirty worktree.
Did not read the full historical-levelmap plan.

Read the complete superpowers TDD skill and its `writing-good-tests.md`
reference before writing tests or production implementation. Followed the
subagent-driven-development `implementer-prompt.md` work/self-review/report
contract. The user's explicit no-commit/no-agent/no-worktree and focused-test
instructions superseded generic template steps. No nested agents, commits,
pushes, worktrees, cleanup, dependency edits, live imports, downloads, data
access, training or external writes were performed.

## Files authored

Only these five assigned files were authored with apply_patch:

- `trading_system/tree_replay/levelmap.py`
- `tests/tree_replay/test_levelmap.py`
- `docs/architecture/HISTORICAL-LEVELMAP-USAGE.md`
- `.superpowers/sdd/2026-09-09-historical-levelmap-core/task-3-report.md`
- `agent-exchange/status/2026-09-09T112000Z-worker-historical-levelmap.md`

Accepted frames/corrections/levels/vendor graph dependencies were read without
modification. Master plan, README, AGENTS, tracker and acceptance belong to the
controller; pre-existing dirty/untracked work was preserved.

## Implementation

The frozen keyword-only MapFrameRequest validates original request keys, exact
frame timeframe and correction frame/instrument association, and native integer
policies. The public builder validates exact map instrument, tuple/request types,
unique request keys/frame IDs and explicit aware microsecond-exact T.

An invocation-local source object reconstructs only frames actually fetched by
the original graph. It invokes accepted frame construction and zero-day
correction assessment at the same T. Only available frames plus ASSESSED
evidence return a new DataFrame and local source Correction. Missing/unavailable
inputs use a private `_DataUnavailable` exception, retaining original source
exception boundaries and missing-string generation. No source offset is applied
again and no caller-provided DataFrame/readiness flag is accepted as proof.

The source's actual broker-shape calls are independently recomputed at T, with
actual 20-day and seven-day arguments retained in a separate shape trace.
Unverified/proxy/replay corrections are not universally vetoed. The pinned
build_at graph retains all family calculation/order/warmup/asymmetric gates,
including the PSY preference and fetch-exception behavior.

Results preserve original source levels `{name,price,kind}`, source_missing
strings and selected correction evidence. Missing daily input blocks with no
levels/snapshot. Nonpositive/nonfinite emitted source levels block the entire
map with a diagnostic rather than being filtered. Uncaught source errors block;
unexpected adapter/frame errors cannot be hidden by optional fetch catches.
Exception diagnostics retain type/stage without echoing arbitrary payloads.

The snapshot uses stable hashes of name/kind/price for level IDs, including
distinct same-name quarter prices. Snapshot observed_at/available_at equal T,
because source sessions/splice age can change the evaluated map without a new
price bar. Actual frame observation/publication timestamps remain in fetch
evidence. Canonical result hashing excludes its own hash and includes only
selected trace policies/evidence, under historical-levelmap-asof-v1.

The documentation covers the exact API, conversion to LevelSnapshot, lazy PSY
behavior, evidence schema, false readiness, unsupported precision and remaining
producer/model scope.

## TDD and verification evidence

All focused runs used:

`python -m pytest tests/tree_replay/test_levelmap.py -q --tb=short`

1. RED before production file creation: **31 failed in 1.10s**, exit 1.
   Each failure was the explicit assertion `Task3 public adapter is missing`
   in the test module's adapter loader. Tests collected and executed; this was
   the intended missing-feature assertion, not a collection/import typo.
2. First implementation run: **1 failed, 30 passed in 8.82s**, exit 1.
   The remaining integration assertion expected stop exactly 93. Inspection of
   the real output showed EMA200-1h = 100.0000000000001, source entry equal to
   that value, and stop 93.0000000000001. Source geometry and calculations were
   correct; the test was corrected to use pytest.approx for the stop, matching
   its existing floating-point EMA/entry assertions. No dependency or source
   calculation was changed to satisfy the test.
3. GREEN: **31 passed in 4.66s**, exit 0.
4. Self-review added nine parameterized characterization cases for already
   implemented boundaries: optional delayed/missing input, exact zero-age
   correction timing and unavailable payload invariance, GC/native-BTC identity,
   real numeric overflow and real uncaught resampling error. These passed
   immediately; they are supplementary characterization evidence, not claimed
   as an additional pre-implementation RED cycle.
5. Final focused GREEN after those additions: **40 passed in 5.65s**, exit 0.
   No uncaptured warnings or errors. The deliberate source overflow case uses
   pytest.warns to assert/capture its real RuntimeWarning and checks blocked,
   JSON-finite output.

No calculation dependency was mocked. Synthetic fixtures supply accepted
ClosedBar, SessionSchedule, DailyPeriod/LabeledDailyPeriod and CorrectionEvidence
objects. Expected source family prices/order are literal hand-derived fixtures,
not another call to the calculator as an expected-value oracle.

Read-only diagnostic probes exercised numeric overflow and pandas label limits.
An exploratory year-9999 frame conversion produced OutOfBoundsDatetime (and a
format-inference warning); the committed uncaught-source regression instead
uses valid pandas input labels near April 2262 so the actual weekly resampling
raises beyond the representable edge. A one-off diagnostic command initially
hit PowerShell quoting/NameError and was rerun correctly with a literal here-string.
Neither diagnostic wrote files or changed production code.

The controller explicitly reported all six source audit CLIs successful during
implementation and instructed this worker not to duplicate them or broad suites.
That is controller-provided status, not an independent worker verification claim.
The following remain controller-owned and were **not run by this worker**:

- All source audit CLIs.
- `python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q --tb=short`
- `python -m pytest -q --ignore-glob='*validator*' --tb=short`

The latter explicitly excludes the legacy validator; no broad-suite or validator
acceptance is claimed here.

## Coverage and self-review

Reviewed actual untracked diffs using `git diff --no-index -- /dev/null <file>`
for each of the three Task3 deliverables, and read the test excerpt again where
tool output was truncated. No-index exit 1 means new-file differences. Ran
no-index `--check` on all three: no whitespace-error diagnostics. Git printed
the repository's LF-to-CRLF notices; no line-ending configuration was changed.
Inspected tracked diff summary and scoped status without mutating existing work.

Coverage includes:

- All 41 source levels in exact family order/kinds on a complete synthetic map,
  including all range/open/back-day/PSY/EMA/quarter families.
- A forming 4h row from completed 1h base bars and future-price suffix invariance.
- Missing required request, current bar, delayed bar, frame metadata, correction,
  stale/future/delayed correction with payload exclusion.
- Optional missing/delayed inputs and stale correction preserve built daily map
  while recording omissions and the original PSY exception boundary.
- Broker/replay/unverified/proxy family asymmetry; fallback only after assessed
  hourly shape rejection; unused fallback and request-order hash invariance.
- Zero-day preflight distinct from actual 20-day source predicate, with a
  one-microsecond splice boundary and a clock-only gate transition.
- Zero correction age, a one-microsecond stale observation, unavailable evidence
  payload changes, stable duplicate-name IDs and no caller/output cross-mutation.
- Exact request types/policies, identity/duplicate errors, genuine CME:GC staying
  distinct and Binance retaining the original exchange-native shape behavior.
- Whole-map rejection for negative and nonfinite source rails; real uncaught
  source resample failure yields diagnostic BLOCKED output.
- Map -> LevelSnapshot -> real reversal detector -> accepted pricing wrapper,
  without supplied manual map prices. Observed EMA200-1h reversal has source
  entry approximately 100, stop approximately 93, risk 7, TP1 110, subsequent
  targets 115 and 125, and session-open obstacles 103 and 107. Result remains
  unadmitted/nontradeable. Flat bars with the same map yield NO_CANDIDATE.

Self-review found no unresolved implementation defect. The sole integration
failure was the corrected floating-point assertion described above. Supplementary
boundary tests required no further production changes.

## Concerns and remaining boundaries

No blocking contract ambiguity or unresolved implementation concern was found.
Controller review, integration/broad verification and acceptance remain pending.

Frame/evidence identities are supplied attestations. Available frame hashes
retain the accepted builder's calendar/provenance identity; changing that
attestation is a dependency change, whereas appending unobserved future price
bars is invariant. Not every original source family omission has a source
missing-string; source strings, row counts and actual shape/fetch traces are
preserved without inventing new family gates or claiming complete availability.

Completed observation precision is closed base bars and higher-timeframe known
prefixes, not open-only ticks or partial base bars. No historical vendor
certification or exact GC-to-source variant decision was made. Full producer
find/admission/arbitration, state machine, simulator, real datasets, models,
evaluation and all human approval gates remain open. Both readiness flags and
tradeable remain false. No commits were created.
