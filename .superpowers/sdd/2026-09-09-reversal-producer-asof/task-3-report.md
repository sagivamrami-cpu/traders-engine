# Task 3 implementation report

Status: DONE — implemented, awaiting parent review/acceptance.
Completed at: 2026-09-09T12:06:59Z.
Request: `agent-exchange/inbox/codex/2026-09-09T115900Z-reversal-producer-asof.md`.
Requirements: this directory's `task-3-brief.md`, read first.

## Delivered behavior

Added the frozen typed `ReversalFrameRequest` and keyword-only
`find_reversal_asof` boundary. Exact request types, identities, frame IDs,
timeframes, correction association, native nonnegative age policies, snapshot
identity and aware microsecond-exact decision clocks are validated before lazy
source calls. Unsupported exact instruments return
`BLOCKED / PRODUCER_UNSUPPORTED_INSTRUMENT`; no GC/spot equivalence is introduced.

The real historical map builds with prefix mode at actual T. The bridge
reconstructs original `NamedLevel` and daily `Correction` values from available
map evidence. Producer requests reuse accepted `levelmap._OfflineSource` with
prefix mode and retain fetched frames. All selection and winner-only pricing
remain in original `find_at`; the seam calls the real detector with its actual
TF / `370.0` / T and uses real PVSRA evidence. A newer refusal is retained as a
source selection, not replaced by an older paying candidate.

Map, candidate-feature and pricing-feature observations/publications are T.
Original event confirmation/vector timestamps are unchanged. Original per-episode
IDs and per-TF candidate IDs coexist with deterministic per-evaluation decision
IDs and a canonical JSON hash. Available dependencies remain lazy; unavailable
correction payloads, future bars and unused fallback payloads do not affect it.
Returned selected snapshots are detached from candidate snapshots and future
evaluations. Public tradeability/readiness flags remain false.

The old helper alone gains optional `observed_at=None`; omission still uses
`event.confirmed_at` exactly. No detector/pricer public guard or default changes.

## TDD and verification evidence

Used the requested `superpowers:test-driven-development` skill and read its
complete `writing-good-tests.md` reference before writing tests. Its influence:
tests begin from explicit wrong-clock/gate/selection/availability mutations,
exercise real map/detector/pricer math, and use literal expectations. No mocks,
source stubs, nested agents or test-only production seams were added.

Every producer test run below used this exact command:

```text
python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short
```

| Stage | Exact pytest summary | Interpretation |
| --- | --- | --- |
| Initial RED, before producer/helper implementation | `52 failed in 1.84s` | All cases failed the explicit assertion `Task3 typed producer is missing`; collection succeeded. |
| First implementation check | `1 failed, 51 passed in 3.39s` | Test fixture expected the wrong XAU entry zone. |
| Second implementation check | `1 failed, 51 passed in 3.26s` | Test expected one target name instead of original merged coincident names. |
| Initial GREEN | `52 passed in 3.26s` | Literal expectations corrected from pinned source: zone 98–102, stop 93 and full merged target name. No source/pricing behavior changed to satisfy an incorrect test. |
| Expanded coverage first check | `2 failed, 72 passed in 5.24s` | Forming-only warmup exposed a missing detection trace; an added invariance fixture also had datetime-addition parentheses wrong. |
| Warmup RED after fixture/assertion correction | `1 failed, 73 passed in 5.00s` | Explicit assertion expected one detector trace but received zero: empty closed-target history was mislabeled missing volume. |
| Warmup GREEN | `74 passed in 6.16s` | Zero completed targets reach real detector warmup. Missing/all-zero volume on existing completed targets still blocks that TF. |
| Parent-risk regression RED | `1 failed, 74 passed in 4.61s` | Real pandas target-close overflow left the successful-fetch trace `AVAILABLE` instead of `BLOCKED`. |
| Parent-risk regression GREEN | `75 passed in 4.57s` | All post-super fetch processing now records unexpected exceptions with stage/type before original find can skip them. |
| Final focused GREEN | `77 passed in 5.15s` | Added one-missing-volume and zero-age-policy checks; also strengthened repeated episode/per-TF ID assertions. |

Exact old-default compatibility command and result:

```text
python -m pytest tests/tree_replay/test_reversal.py tests/tree_replay/test_pricing.py -q --tb=short
123 passed in 2.80s
```

The 74-case producer run and compatibility run executed independently in
parallel. Later producer-only changes did not modify the shared helper again.
The final 77-case run includes an explicit old-detector regression preserving
`LEVELS_AFTER_CONFIRMATION` and default feature observation at confirmation.

Additional checks: AST parsing passed for all three owned Python files; no
trailing whitespace was found in the implementation/test/usage files. Inspected
the helper's optional keyword/default directly. `git diff --check` passed with
only pre-existing AGENTS/README line-ending warnings. These implementation
directories are already untracked in the dirty workspace, so Git's ordinary
diff does not independently prove their before/after contents; the parent owns
the saved helper beforeimage comparison.

## Coverage and self-review

- Source choice: same-confirmation opposite M5/M15 selects M5; newer M15 wins;
  a latest nonsignal bar does not erase an older fresh confirmation; one missing
  timeframe preserves selection from the other; only the winner has a plan.
- Freshness/publication: exactly 370 seconds accepted and the next microsecond
  excluded for both TFs; producer-bar publication between close and T; daily
  bar/calendar/frame/correction publication only at actual publication time;
  current map timestamps remain T while source event timestamps remain earlier.
- Source gates: real daily source/confidence branches, including verified
  `source=none` versus unverified `none/unknown`; real intraday source/confidence
  branches for both TFs, missing/future/delayed/stale correction, and descriptive
  gate flags that do not replace original find's selection.
- Availability: required daily absence; optional map failures; quiet versus
  unavailable; 11-row warmup and zero-closed-row forming-only warmup; one missing,
  all missing, and all-zero volume; forming-row missing volume cannot veto
  completed history. No synthetic volume is substituted in production.
- Numeric containment: real volume overflow, real map numeric failure and a
  legal native 2262-04-11 23:40 UTC source index whose 15-minute target close
  overflows pandas nanosecond arithmetic. The latter exercises the private
  shared fetch boundary directly without a mock; it verifies the failure
  recording that original find's catch-all fetch continuation relies on.
  The public numeric-overflow test verifies error propagation dominates another
  TF's otherwise valid source selection.
- Evidence: exact source entry/stop/zone, merged target names, exact refusal and
  obstacle geometry; real vector volume/average/ratio/spread values; current-T
  feature provenance; canonical hash; future price/correction and unused map
  fallback invariance; request-order invariance; detached outputs; original
  source episode IDs versus per-TF candidate and per-decision IDs.
- Structural validation: wrong collection/type/subclass, duplicate key/TF/ID,
  cross-map/producer frame-ID collision, instrument mismatch, unsupported GC,
  correction association, frozen request, invalid snapshot identity, naive and
  finer-than-microsecond clocks, invalid age policies and accepted native zero.
- Safety/scope: no send/fill/label outputs, public tradeability/readiness false,
  exact five `missing_stages` retained. Reviewed original find delegation,
  map-clock construction, fetch catch boundaries, selected-only serialization,
  and mutable result separation. No known unresolved implementation defect.

Parent's two concrete integration risks were both addressed in this scope:
zero-closed-row warmup had already been fixed when the parent message arrived;
post-super timestamp/volume exception recording was then reproduced RED and
fixed GREEN. No changes to source math or default wrappers were needed.

## Files

Implementation ownership, and only these implementation files:

1. `trading_system/tree_replay/reversal_producer.py` — new typed producer bridge.
2. `tests/tree_replay/test_reversal_producer.py` — new real synthetic tests.
3. `docs/architecture/REVERSAL-PRODUCER-ASOF-USAGE.md` — new usage/contract guide.
4. `trading_system/tree_replay/reversal.py` — narrow helper signature/observation extension.

Requested reporting files:

5. `.superpowers/sdd/2026-09-09-reversal-producer-asof/task-3-report.md` — this report.
6. `agent-exchange/status/2026-09-09T115900Z-worker-reversal-producer-asof.md`.

## Concerns, boundaries and next action

No concrete blocker or unresolved domain-policy choice. Private trace/error
interfaces remain deliberate package-internal coupling. Extreme native datetime
inputs outside pandas arithmetic capacity produce a diagnostic block, not a
claim of wider source numeric support. Supplied provenance/calendars are not
historical feed certification; no real-data claims are made.

Parent owns independent review, all source audits, broad integration, full-suite
verification, durable acceptance, master/tracker/README/AGENTS updates and any
later integration. No such review/audit/acceptance is claimed here. No broad
suite was run. In particular the parent's requested eventual broad invocation
`python -m pytest -q --ignore-glob='*validator*' --tb=short` retains its explicit
legacy validator exclusion; the worker neither ran it nor treats validator
coverage as verified.

No whole plan or other plan scratch was read. No other files were intentionally
edited. No nested agents, commits, pushes, worktrees, cleanup, real-data access,
feed execution, live actions, fitting, deployment or broker operations occurred.
Outer admission, tracker state, cross-producer arbitration, execution/outcomes
and full tree dataset/training remain open; completion here is Task 3 only.

## M1 test-only follow-up — 2026-09-09T12:12:23Z

Status: DONE. Addressed Minor M1 from
`agent-exchange/reviews/2026-09-09T120800Z-reversal-producer-asof-review.md`.
The review approved the task and identified that the previous optional-error
test also corrupted required daily inputs, permitting daily failure to satisfy
its generic assertions. This was a test coverage defect, not a discovered
runtime defect.

Only `tests/tree_replay/test_reversal_producer.py` changed in implementation
scope; this report and the requested exchange result were appended. No runtime,
source-math or usage-documentation edits occurred. SHA-256 comparisons before
and after this follow-up confirmed unchanged `reversal.py`,
`reversal_producer.py` and `REVERSAL-PRODUCER-ASOF-USAGE.md`.

The optional scenario now retains valid daily input throughout. It first
verifies selection with valid daily plus optional 4h/240 input, then changes
only optional one-hour base-bar volumes to finite `1e308`. Real four-hour
aggregation overflows while summing those volumes. Assertions require:

- required daily fetch `1d/400` remains `AVAILABLE`, without a blocker, and
  its correction assessment remains `ASSESSED`;
- optional fetch `4h/240`, frame ID `4h-240`, is `BLOCKED` with
  `FRAME_CALCULATION_ERROR`;
- map and public diagnostics identify `stage=fetch`, `exception_type=ValueError`,
  `timeframe=4h`, `lookback_days=240`;
- the public result blocks with no selected event or producer timeframe fetch.

Separate required-daily coverage retains real daily range overflow and now
requires `SOURCE_CALCULATION_ERROR`, `stage=build`,
`exception_type=FloatingPointError`, and a trace containing only the required
daily fetch. A daily failure can no longer satisfy the optional-error test.
Both cases exercise real calculations without mocks or runtime mutations.

Exact focused command:

```text
python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short
78 passed in 5.52s
```

This increases focused coverage from 77 to 78 tests by splitting the conflated
case. No new runtime RED/GREEN cycle was needed: the isolated regression passes
against the already-approved runtime. No broad, integration, source-audit or
compatibility reruns were performed by this worker. Parent broad/integration
runs already started against the original 77 tests; this follow-up supplies
the exact new focused result without claiming those parent runs include it.
No blocker or runtime defect found; ready for parent final review.
