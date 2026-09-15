# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-15T10:39:00Z

Status:
REVIEW_ONLY

Objective:

Perform a separate, read-only implementation review of the GC Order Flow
context sidecar added for the `OANDA:XAUUSD` tree research path.

Scope:

Review `5fbcfcc..298d6f6` against the approved design and implementation plan:

- `docs/superpowers/specs/2026-09-15-gc-order-flow-xauusd-context-design.md`
- `docs/superpowers/plans/2026-09-15-gc-order-flow-xauusd-context.md`
- all files matching `*cross_market*` changed in that range, plus
  `full_tree_checkpoint.py` and tests.

Required inputs:

The human implementation approval is
`agent-exchange/decisions/2026-09-15T103500Z-human-gc-xauusd-context-implementation-approved.md`.

Contracts:

- `CME:GC` is context only and cannot masquerade as `OANDA:XAUUSD` price or
  execution data.
- Minute start is eligible only after its end and declared availability;
  damaged 2017, missing, late, duplicate, unordered and non-finite inputs must
  be fail-closed typed unavailable results.
- Public commitments must not disclose raw flow values but must change when a
  private value changes.
- No direct TreeReader behavior change is allowed in this increment.

Non-negotiables:

- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:

Write an independent review under `agent-exchange/reviews/` with strengths,
Critical/Important/Minor findings, file/line evidence, verification run, and
clear Ready/Not-ready assessment. Do not modify the working tree.

Verification commands:

`python -B -m pytest tests/tree_replay/test_cross_market_flow_policy.py tests/tree_replay/test_cross_market_flow.py tests/tree_replay/test_full_tree_cross_market_context.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_replay.py tests/tree_spec/test_cross_market_flow_source.py tests/tree_spec/test_full_tree_capture_source.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider`

Out of scope:

Source download/access, raw data retention, dataset/model work, economics,
and live/trading execution.

Notes:

The full tree currently exposes no direct Order Flow port. Flag any accidental
strategy mutation, rather than recommending an unapproved direct injection.
