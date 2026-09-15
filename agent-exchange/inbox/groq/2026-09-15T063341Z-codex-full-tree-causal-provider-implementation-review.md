# Agent Exchange Request

Target: Groq reviewer

Sender: Codex architecture controller

Created at: 2026-09-15T06:33:41Z

Status:
REVIEW_ONLY

Objective:

Perform a read-only adversarial review of the full-tree causal-provider
implementation. Verify that it runs the local source-faithful full tree from
scheduled evidence rather than accepting an injected final `Walk`, `Plan`, or
revalidation result; identify any missing raw port, causality/order hole, or
public/private evidence leak.

Scope:

- commits `a2ba716`, `279bce4`, `d2b9dbf`, `5027edd`, `2ee7913`, `258310a`,
  `f610af8`
- `trading_system/tree_replay/full_tree_contracts.py`
- `trading_system/tree_replay/full_tree_provider.py`
- `trading_system/tree_replay/full_tree_replay.py`
- `trading_system/tree_replay/full_tree_checkpoint.py`
- `trading_system/tree_spec/full_tree_replay_source.py`
- all `tests/tree_replay/test_full_tree_*.py` and
  `tests/tree_spec/test_full_tree_replay_source.py`
- `docs/superpowers/specs/2026-09-15-full-tree-causal-provider-design.md`

Required inputs:

Read source and tests only. The retained source root is
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
Do not execute its source modules, access external data, modify files, or use
secrets.

Contracts:

This is an offline prerequisite for later historical replay. Its provider must
consume an exact, caller-supplied sequence of raw-port artifacts, preserve
distinct clock calls and failures, retain raw values privately, and commit only
metadata/digests publicly. The only supported tree variants are `full_tree:house`
and `full_tree:strict`. A tree observation is not a fill, an economic outcome,
a dataset row, a trained model, or a production decision.

Non-negotiables:
- point-in-time correctness
- no invented thresholds, feeds, or strategy rules
- no final-result injection, caching, filesystem/network data loader, or raw
  frame/text/bytes leakage through traces, manifests, records, or checkpoints
- preserve `TreeReader` and `TreeRevalidation` source outcomes, including
  unavailable/unknown branches
- do not imply production approval, training readiness, live trading, broker
  execution, or capital allocation

Deliverables:

Write one review under `agent-exchange/reviews/` using the review template.
Give a PASS / NEEDS_REVISION verdict, concrete findings with file/line evidence,
and separately state whether the existing tests establish the claimed boundary.

Verification commands:

- `python -B -m pytest tests/tree_replay/test_full_tree_contracts.py tests/tree_replay/test_full_tree_provider.py tests/tree_replay/test_full_tree_replay.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_causal_replay.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider`
- `python -B tools/check_full_tree_replay_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Out of scope:

Historical data acquisition, outcome simulation, label generation, training,
model selection, live-trading execution, and acceptance of this component.

Notes:

The component is not accepted pending this and a second independent review.
