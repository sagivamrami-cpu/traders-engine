Spec compliance: PASS for the supplied Task3 delta; cross-task verification items remain below.
Task quality: APPROVED with one Minor test-coverage finding; no Critical or Important findings.

# Agent Exchange Review

Reviewer: Codex scoped Task3 reviewer

Target request: `agent-exchange/inbox/codex/2026-09-09T120800Z-reversal-producer-asof-review.md`

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec compliant / quality approved for this task, subject to the controller's separate source and integration verification.

## Strengths

- `trading_system/tree_replay/reversal_producer.py:56`: exact request classes, associations, instrument identities, request keys and cross-map/producer frame IDs are checked before lazy execution. Unsupported instruments receive an explicit block at line 213.
- `trading_system/tree_replay/reversal_producer.py:86`, `trading_system/tree_replay/reversal_producer.py:154`, `trading_system/tree_replay/reversal_producer.py:237`: map construction and candidate/pricing observations use actual T; original event timestamps survive serialization. `tests/tree_replay/test_reversal_producer.py:99` asserts both clocks and literal vector evidence. The helper delta at `trading_system/tree_replay/reversal.py:46` and `:74` preserves the old default; the regression at `tests/tree_replay/test_reversal_producer.py:462` retains the old guard.
- `trading_system/tree_replay/reversal_producer.py:218`: selection and winner-only pricing are delegated to original find. Tests at `tests/tree_replay/test_reversal_producer.py:72` and `:322` exercise real tie-breaking and retention of a newer refused plan. No profitability-based reselection was introduced.
- `trading_system/tree_replay/reversal_producer.py:115`: closed-target volume checks distinguish absent volume from zero completed rows; post-fetch failures preserve a typed diagnostic at line 137. The result prioritizes recorded calculation failures at line 221 while retaining ordinary partial availability. The real timestamp-overflow regression is at `tests/tree_replay/test_reversal_producer.py:519`.
- `trading_system/tree_replay/reversal_producer.py:141`, `:179`, `:252`: episode/candidate identities, detached selection, deterministic evaluation IDs, false public readiness and the five missing stages are explicit. Canonical JSON and public flags are asserted at `tests/tree_replay/test_reversal_producer.py:252`. The usage guide documents the same limited scope at `docs/architecture/REVERSAL-PRODUCER-ASOF-USAGE.md:101`.

## Findings

Critical: None.

Important: None.

Minor M1 — `tests/tree_replay/test_reversal_producer.py:446` (especially lines 448–459): the test named for a caught optional-map numeric failure also corrupts the required daily input and asserts only a generic block/nonempty diagnostic. A daily calculation failure alone satisfies these assertions, so this test does not establish the optional-fetch error propagation promised by its name. Keep the daily input valid in a separate optional-error scenario and assert the affected optional fetch and diagnostic stage. This is a coverage weakness, not evidence of broken runtime propagation; the inspected inherited error path preserves `source.error`.

## Open questions / cannot verify

- Source parity and source-pin provenance are not established by this delta. The adapter delegates at `trading_system/tree_replay/reversal_producer.py:196` and `:218`; controller-owned Task1/2 acceptance and full source audits must establish equivalence to the pinned original, including `conflicts`.
- General frame/calendar/publication guarantees remain inherited from `_OfflineSource` at `trading_system/tree_replay/reversal_producer.py:107`. The new tests exercise concrete cases, but this task review does not certify the full inherited contracts, real feed provenance, or historical calendar coverage.
- The supplied package identifies both base/head as `c1b6071633c55376c64f0a98ece843706f420f49` and carries new files plus the saved-beforeimage helper delta. Beforeimage provenance, package completeness against the dirty checkout, and any later edits remain controller responsibilities; no Git commands were run.
- Full source audits, broad/full integration tests, legacy-validator exclusion, durable acceptance and controller-owned documentation updates are outside this review. Reported focused passes are reviewed evidence, not independently rerun results.

## Verification reviewed

- Read the assigned request, Task3 brief (including verbatim Global Constraints), complete implementation report, review template and requested task-reviewer instructions. Reviewed all three new-file hunks and the narrow helper delta. The first tool response truncated the test hunk; read that missing package segment separately. No changed source file was read separately.
- Named outside check: source catch-all fetch handling could hide calculation errors. Inspected `_vendor/reversal_producer.py:8` and `levelmap.py:68`; only fetch exceptions are skipped, and `_OfflineSource` retains unexpected errors. The new wrapper records post-fetch failures and checks the retained error before accepting a selection.
- Named outside check: vector evidence or winner pricing could use different history from the detector. Inspected `_vendor/level_reversal.py:63` and `:135`, `_vendor/pvsra.py:15`, `_vendor/reversal_pricing.py:10`, and `pricing.py:24`. The seam uses real closed-history PVSRA; original find passes the winner's frame to original pricing, which applies its own event-time filter. Finite plan serialization is inherited. General frame ordering/uniqueness remains an accepted upstream contract.
- Named outside check: map requests might escape the producer's structural validation. Inspected `levelmap.py:30`; its validator checks supported keys, matching frame timeframe, native age policy and correction association, while Task3 additionally enforces exact classes and cross-collection identities.
- Worker-reported PASS: `python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short` — 77 passed in 5.15s; compatibility command `python -m pytest tests/tree_replay/test_reversal.py tests/tree_replay/test_pricing.py -q --tb=short` — 123 passed in 2.80s. Request reports parent combined 200 passed in 7.32s. No suites were repeated; no new runtime check was needed to resolve a code-reading doubt.
- Report/package noise: Git LF-to-CRLF warnings are present, including new Task3 paths in the package. The report describes existing checkout line-ending warnings; the reported pytest summaries contain no warnings. These packaging warnings are not evidence of a runtime regression and were not cleaned up.

Recommended next action: Record this scoped approval, track M1 as a minor coverage improvement, and resolve the cannot-verify items through the controller's already-owned source/integration checks before durable acceptance. No production, deployment, admission or full-model readiness approval is implied.
