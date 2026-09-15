# Agent Exchange Request

Target: Claude Code reviewer

Sender: Codex architecture controller

Created at: 2026-09-15T06:33:41Z

Status:
REVIEW_ONLY

Objective:

Conduct an independent, read-only code review of the full-tree causal-provider
component, focusing on exact port signatures/order, error behavior, checkpoint
resume integrity, and whether the static audit can be bypassed by a plausible
source change.

Scope:

- commits `a2ba716`, `279bce4`, `d2b9dbf`, `5027edd`, `2ee7913`, `258310a`,
  `f610af8`
- `trading_system/tree_replay/full_tree_contracts.py`
- `trading_system/tree_replay/full_tree_provider.py`
- `trading_system/tree_replay/full_tree_replay.py`
- `trading_system/tree_replay/full_tree_checkpoint.py`
- `trading_system/tree_spec/full_tree_replay_source.py`
- all matching full-tree tests and the source-audit CLI

Required inputs:

Read the implementation, tests and specification. You may run the supplied
offline tests/audit. Do not modify files, run retained chart-desk modules,
connect to vendors, use secrets, or invoke any live-trading operation.

Contracts:

The component is a causal evidence boundary only. It must invoke the vendored
`TreeReader` and `TreeRevalidation` from scheduled private artifacts, record
public commitments only, and retain `ready_for_replay` and
`ready_for_training` as false. It must not turn a tree candidate into a trade
outcome or model label.

Non-negotiables:
- fail closed on a missing/out-of-order/late artifact or source-audit mismatch
- preserve exact repeated reads and independent clocks
- no injected `Walk`, `Plan`, boolean revalidation result, or live loader
- no raw payloads in public manifests, records or checkpoint serialization
- no invented trading policy, economic labels, production approval or live use

Deliverables:

Write one review under `agent-exchange/reviews/` using the review template.
State PASS / NEEDS_REVISION, reproducible evidence, all findings with
file/line references, and the minimal required remedy for each finding.

Verification commands:

- `python -B -m pytest tests/tree_replay/test_full_tree_contracts.py tests/tree_replay/test_full_tree_provider.py tests/tree_replay/test_full_tree_replay.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_causal_replay.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider`
- `python -B tools/check_full_tree_replay_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Out of scope:

Data collection, simulation/economics, outcome dataset construction, model
training, broker execution, capital allocation, deployment, and acceptance.

Notes:

This is the second required independent review; Codex will independently
inspect and rerun verification before any acceptance.
