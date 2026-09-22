# Task2 causal memory implementation report

Request: approved continuation, Task2 brief in this plan workspace.
Status: DONE, awaiting independent review. No commits.

Changed: trading_system/tree_replay/state.py; tests/tree_replay/test_state.py;
docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md.

Implemented immutable typed append evidence, bounded complete coverage,
publication-time reductions with full-row replacements and ordered rejections,
detached JSON-safe reports with event trace/hashes, complete checkpoint/restore.
No admission, lifecycle transition generation or provenance certification claimed.
Source ts/resolved_ts check compares original JSON decimals to exact observed T.

TDD: `python -m pytest tests/tree_replay/test_state.py -q --tb=short`
RED before implementation: 66 failed1.51s, Missing causal memory adapter assertion.
Initial GREEN:66 passed0.72s. Self-review found binary-float epoch boundary risk:
literal1788775200.123456 expands to1788775200.12345600128173828125 in Decimal(float).
Additional regression RED:1 failed77passed0.94s, exact microsecond rejected as future.
Original JSON Decimal parsing fixes cause; finer future fractions remain rejected.
Final GREEN:79 passed0.90s, pristine. Added recomputed-checksum corruption cases
to exercise restore structure/time/sequence validation rather than checksum alone.

Self-review: immutable payload ownership, coverage boundaries, true/false/zero,
missing source state retained, future revisions excluded from early hash, exact
timestamp serialization, no I/O or hidden readiness. No known open findings.
Coverage/provenance are explicitly supplied assertions; checksum is not authentication.

## Review fixes, local fallback after agent quota termination

Review: agent-exchange/reviews/2026-09-09T125000Z-memory-review.md was saved in
full even though the reviewer handle subsequently terminated with usage limit.
It requested two Important fixes and a Minor false-positive test correction.
Controller read original request and review, inspected git status/diff and
reproduced findings before editing. No claim of independent re-review yet.

I1: Decimal arithmetic used ambient precision. RED3failed83passed0.96s confirmed
future50ms was accepted at precisions1/6/10. Exact integer-microsecond string
construction removes context arithmetic; GREEN86passed0.76s.
I2: raw epoch could round into a different/future stored epoch at2255. RED1failed
92passed1.51s showed ingestion still accepted an unrepresentable timestamp.
Now reject any timestamp whose decimal value changes under JSON normalization.
The representable2255case and negative1969epoch round-trip under precisions1/10/28.
M3: rejection parameter now uses valid event identity and matches the temporal
error; valid rejection timestamp control proves that branch can pass.
Latest state command unchanged:93passed0.76s, pristine.

All review fixes are implementation-verified, not independently re-reviewed.
Tradeoff: unrepresentable numeric epoch payloads are rejected instead of rounded;
caller must supply faithfully representable evidence, not a silently altered time.

## Parent integration evidence attachment

Re-review125200Z approved I1/I2/M3 and found no new Important/Critical issue.
Its combined-count visibility question is resolved by the authoritative result
agent-exchange/status/2026-09-09T125300Z-admission-dependencies-progress.md:
exact452-case command/result and expanded670-case command/result are recorded
there. Expanded command includes state, source calculations/audit, producer,
bars, session bars, frames and corrections;670passed25.77s. These are controller
runs, not reviewer executions. Current resumed verification of state93passed0.83s.
