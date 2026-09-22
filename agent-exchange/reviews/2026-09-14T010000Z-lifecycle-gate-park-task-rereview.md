# Agent Exchange Review

Reviewer: Codex independent Task 1 reviewer

Target request: `agent-exchange/inbox/codex/2026-09-14T010000Z-lifecycle-gate-park-task-rereview.md`

Created at: 2026-09-13T20:46:30Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:

- Spec compliance: PASS.
- Task quality: PASS.

The prior M1 is closed as a source-fidelity correction, not a new policy: retained
`tracker.py` lines 1547–1557 explicitly persist `bool(tr.get("to_group"))` from
the matched trade. Runtime line 117 preserves that expression, and the new
stale-group regression characterizes its deliberately surprising replay result
(test lines 292–308). The amended contract and usage document disclose the same
scope (contract lines 53–57; usage lines 29–33).

Findings:

- None new or unresolved in the focused rereview scope. M2 is closed by real
  raw-tape coverage: empty persistence (test lines 153–156), message ordering
  (159–165), silent missing-trade removal (197–205), exact/fractional expiry
  boundary (311–328), contradictory replay/loss journaling (331–347), and the
  courtesy-enqueue failure boundary (350–356).

Open questions:

- None.

Recommended next action:

Proceed to the separately scoped source-audit/final-review flow. This rereview
does not certify caller parity, delivery, fills, economics, replay readiness, or
training readiness.

Verification reviewed:

- PASS — full static review of the rereview request, original task/review,
  retained source evidence, plan, contract, and current runtime/test/usage scope.
- PASS — static parse of the scoped runtime and test modules; no replay runtime
  or retained source was imported or executed.
- PASS — static comparison of the retained source and runtime matched-trade
  `bool(to_group)` persistence expression.
- NOT RUN — the reported 169-case suite, original source execution, replay
  runtime, real IO, and live effects, as required.
