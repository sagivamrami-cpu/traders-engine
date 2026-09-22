# GC → XAUUSD Order Flow context implementation status

Target: Codex

Sender: Codex

Created at: 2026-09-15T10:38:30Z

Request: `docs/superpowers/plans/2026-09-15-gc-order-flow-xauusd-context.md`

Status: IMPLEMENTED_AWAITING_CODEX_REVIEW

Summary:

- Added an immutable policy pin for `OANDA:XAUUSD` target identity and
  `CME:GC`/`DATABENTO/GLBX.MDP3` context identity.
- Added a caller-supplied, closed-minute GC aggregator with typed unavailable
  outcomes for bad identity, coverage, damaged 2017 interval, duplicate/gap,
  non-finite, late and aggregate-overflow inputs.
- Added a payload-private context sidecar bound to an existing full-tree pass,
  with a public provenance/commitment baseline that detects changed GC values.
- Added a static source audit and usage document. The pinned `TreeReader` has
  no Order Flow port, so no tree decision or alert behavior changed.

Changed files:

- `configs/data/xauusd-gc-crossmarket-order-flow-context.yaml`
- `schemas/xauusd_gc_crossmarket_order_flow_context.schema.json`
- `trading_system/tree_replay/cross_market_flow_policy.py`
- `trading_system/tree_replay/cross_market_flow.py`
- `trading_system/tree_replay/full_tree_cross_market_context.py`
- `trading_system/tree_replay/full_tree_checkpoint.py`
- `trading_system/tree_spec/cross_market_flow_source.py`
- focused tests and `docs/architecture/GC-XAUUSD-CROSSMARKET-FLOW-USAGE.md`

Verification results:

- PASS — `python -B -m pytest tests/tree_replay/test_cross_market_flow_policy.py tests/tree_replay/test_cross_market_flow.py tests/tree_replay/test_full_tree_cross_market_context.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_replay.py tests/tree_spec/test_cross_market_flow_source.py tests/tree_spec/test_full_tree_capture_source.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider` → 44 passed in 39.91s.
- PASS — `python -B -m pytest tests/research/test_gc_canonical_order_flow_input_manifest.py -q --tb=short -p no:cacheprovider` → 2 passed in 1.48s.
- PASS — `git diff --check`.

Decisions needed:

- None for the implemented sidecar. A future change that makes this context
  alter tree decisions needs a separately approved TreeReader/branch contract.

Blockers:

- Independent implementation review is pending.
- OANDA historical source coverage, historical news/options coverage,
  economics, dataset construction, model training and all live permissions are
  outside this increment and remain open.

Recommended next action:

- Obtain an independent review; after acceptance, use the sidecar only in the
  later source-faithful replay/dataset path.
