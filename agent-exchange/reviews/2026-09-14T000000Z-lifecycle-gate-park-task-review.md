# Agent Exchange Review

Reviewer: Codex independent Task 1 reviewer

Target request: `agent-exchange/inbox/codex/2026-09-14T000000Z-lifecycle-gate-park-task-review.md`

Created at: 2026-09-13T20:43:15Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:

- Spec compliance: NEEDS_REVISION.
- Task quality: NEEDS_REVISION.

Findings:

1. **M1 — stale group claims can lose their original group destination.** `gate` receives the destination as the message-local `to_group` value (runtime lines 61–62), but both stale paths call `_park(tr, text)` without carrying it (lines 80 and 89). `_park` instead persists `bool(tr.get('to_group'))` (line 117), and replay returns that persisted value (line 163). The contract requires the original boolean `to_group` to be retained and replayed (contract lines 53–56, 63–65). A group message whose matched state trade lacks `to_group` is therefore parked as personal and released personal. The only stale gate test supplies `to_group=False` (test lines 244–260); the direct park test adds the property directly to the trade (lines 149–168), so neither exposes this route.

   Recommendation: preserve the gate message destination at park time (while retaining the source signature/projection required by the source audit), and add stale-group-to-replay coverage using a matched trade without a `to_group` field.

2. **M2 — the focused tests do not prove several explicitly required source boundaries.** The plan requires empty persistence, multi-message ordering, silent unexpired missing-trade handling, replay contradiction/loss handling, courtesy-note enqueue failure, and strict expiry (plan lines 47–55). The test file checks an expiry only at 3,601 seconds (test lines 230–241), but has no 3,600-second equality case. It contains no test for an empty `_persist_gated_lifecycle`, ordered mixed-message input, an unexpired parked record with no matching trade, a contradictory replay record generating `park_lost`, or the `_park_lost` enqueue-error boundary. These omissions leave the requested stale-versus-contradictory and park/retry proof incomplete.

   Recommendation: add focused raw-tape tests for each listed boundary, including a 3,600-second retained record and 3,600.000…-second expired record, before source-audit acceptance.

The static review otherwise confirmed the intended shared receipt-cache binding (runtime line 22), strict `>` expiry comparison (line 150), stale diagnostic persistence skip (lines 33–35), blocked journal enqueue/resolve ordering (lines 36–37), and the documented no-delivery/no-fill/no-training-readiness limits (usage lines 3–5, 21, 45–50).

Open questions:

- None. The M1 path is determinable from the scoped runtime and contract; it should be corrected or explicitly reconciled with the retained source projection before acceptance.

Recommended next action:

Revise the Task 1 runtime/tests for M1 and M2, then request a fresh independent review. Do not treat this as source-audit acceptance.

Verification reviewed:

- PASS — full static read of all six required inputs.
- PASS — static parse of the scoped runtime and focused test module; no target module or retained original source was imported or executed.
- PASS — focused static checks of cache sharing, stale skip, blocked effect order, and strict expiry expression.
- NOT RUN — the controller-reported 160-case suite, replay runtime, original source, real IO, and all live effects, as required by the request.
