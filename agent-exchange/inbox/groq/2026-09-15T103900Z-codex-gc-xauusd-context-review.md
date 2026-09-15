# Agent Exchange Request

Target:
Groq

Sender:
Codex

Created at:
2026-09-15T10:39:00Z

Status:
REVIEW_ONLY

Objective:

Independently review the completed GC futures Order Flow context sidecar for
the XAUUSD full-tree research path.

Scope:

Review git range `5fbcfcc..298d6f6`, especially:

- `configs/data/xauusd-gc-crossmarket-order-flow-context.yaml`
- `trading_system/tree_replay/cross_market_flow_policy.py`
- `trading_system/tree_replay/cross_market_flow.py`
- `trading_system/tree_replay/full_tree_cross_market_context.py`
- `trading_system/tree_replay/full_tree_checkpoint.py`
- `trading_system/tree_spec/cross_market_flow_source.py`
- corresponding tests and `docs/architecture/GC-XAUUSD-CROSSMARKET-FLOW-USAGE.md`.

Required inputs:

- `docs/superpowers/specs/2026-09-15-gc-order-flow-xauusd-context-design.md`
- `docs/superpowers/plans/2026-09-15-gc-order-flow-xauusd-context.md`
- human decision `agent-exchange/decisions/2026-09-15T103500Z-human-gc-xauusd-context-implementation-approved.md`.

Contracts:

- XAUUSD target/trade identity remains `OANDA:XAUUSD`; source identity is
  `CME:GC` and `DATABENTO/GLBX.MDP3` only.
- Only closed, available one-minute `volume`, `delta`, `trades` may enter a
  caller-declared window. The 2017 damaged interval is unavailable.
- No GC price mapping, CVD/cumulative state, imputation, tree-decision change,
  dataset/model/live claim, or raw payload in public checkpoint/commitment.
- The pinned `TreeReader` has no order-flow port; the component must be an
  additive sidecar, not a stealth strategy change.

Non-negotiables:

- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:

Write a review under `agent-exchange/reviews/` using the review template.
Classify findings Critical/Important/Minor with exact file/line references and
state an explicit verdict. Review is read-only: do not mutate workspace files.

Verification commands:

`python -B -m pytest tests/tree_replay/test_cross_market_flow_policy.py tests/tree_replay/test_cross_market_flow.py tests/tree_replay/test_full_tree_cross_market_context.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_replay.py tests/tree_spec/test_cross_market_flow_source.py tests/tree_spec/test_full_tree_capture_source.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider`

Out of scope:

Source acquisition, historical archive reading, OANDA adapter, economics,
dataset construction, model training, and any live behavior.

Notes:

Prior local verification is 44 focused tests plus 2 canonical-manifest tests;
do not treat that as independent acceptance.
