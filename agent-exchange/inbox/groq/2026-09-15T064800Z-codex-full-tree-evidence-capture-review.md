# Agent Exchange Request

Target: Groq reviewer

Sender: Codex architecture controller

Created at: 2026-09-15T06:48:00Z

Status:
REVIEW_ONLY

Objective:

Perform a read-only adversarial review of the full-tree supplied-evidence
capture component. Determine whether it records actual source calls causally,
preserves missing/error behavior, and prevents raw-data/live-loader/final-result
shortcuts.

Scope:

- commits `3bde463`, `13b7524`, `dfd2f53`, `d39763b`
- `trading_system/tree_replay/full_tree_capture.py`
- `trading_system/tree_spec/full_tree_capture_source.py`
- `tests/tree_replay/test_full_tree_capture.py`
- `tests/tree_spec/test_full_tree_capture_source.py`
- `docs/superpowers/specs/2026-09-15-full-tree-evidence-capture-design.md`
- `docs/architecture/FULL-TREE-EVIDENCE-CAPTURE-USAGE.md`

Required inputs:

Read code/docs/tests and optionally run listed offline checks. Do not modify
files, execute retained source modules, contact a vendor, read raw market data
or use secrets.

Contracts:

The capture module may only receive caller-supplied values with explicit time
windows and digests. It runs the local `TreeReader`/`TreeRevalidation` merely
to discover port calls; it must discard source Walk/Plan/result objects. Its
bundle is later replayed independently. A capture receipt is payload-free.

Non-negotiables:
- no filesystem/network/vendor loader or fallback
- no invented availability rule, empty response or trading policy
- a missing/late/wrong-kind response fails closed; a supplied `ERROR` occurs at
  its source call
- no raw frames/text/bytes or private pending plan in receipt/public outputs
- no data acquisition, outcome economics, dataset/model or live permission

Deliverables:

Write one review under `agent-exchange/reviews/` using the review template.
Give PASS / NEEDS_REVISION with evidence and identify any causality, source
ordering, digest, replay-equivalence or privacy gap.

Verification commands:

- `python -B -m pytest tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_contracts.py tests/tree_replay/test_full_tree_provider.py tests/tree_replay/test_full_tree_replay.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_causal_replay.py tests/tree_spec/test_full_tree_capture_source.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider`
- `python -B tools/check_full_tree_capture_source.py`

Out of scope:

Vendor/client work, raw-data handling, simulation, labels, dataset, training,
model promotion, broker execution, capital allocation, deployment and live use.
