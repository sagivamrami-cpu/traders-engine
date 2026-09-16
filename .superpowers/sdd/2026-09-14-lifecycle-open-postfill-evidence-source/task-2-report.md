# Task 2 report — OPEN post-fill evidence source audit

Status: IMPLEMENTED_AWAITING_CODEX_REVIEW

## Scope completed

- Added fail-closed AST auditor:
  `trading_system/tree_spec/lifecycle_open_postfill_evidence_source.py`.
- Added explicit-root JSON CLI:
  `tools/check_lifecycle_open_postfill_evidence_source_parity.py`.
- Added mutation, child-proof, identity, CLI-shape and failure-path tests:
  `tests/tree_spec/test_lifecycle_open_postfill_evidence_source.py`.

The auditor reads/parses the retained `chart-desk` source only. It requires the
pinned commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`, verifies the physical leading
OPEN branch at source lines 2647–2689, then compares the permitted offline
projection with the existing runtime collector by AST. It also requires fresh,
shape-valid proofs from the accepted live-evidence and lifecycle-primitives
children. Any unreadable input, contradictory report, identity drift, child
failure, source mismatch, vendor mismatch or serialization failure is BLOCKED.

The report and CLI retain `ready_for_replay=false` and
`ready_for_training=false` on both VERIFIED and BLOCKED paths. No runtime file
was changed; no resolver, economics, outcome, replay, dataset, training or
model behavior was added.

## TDD evidence

RED before the auditor and CLI existed:

```text
python -m pytest -q tests/tree_spec/test_lifecycle_open_postfill_evidence_source.py
15 failed in 0.75s
AssertionError: OPEN post-fill source auditor missing
```

GREEN after the minimal auditor/CLI implementation and the source-branch
boundary repair:

```text
python -m pytest -q tests/tree_spec/test_lifecycle_open_postfill_evidence_source.py
15 passed in 10.00s
```

Current combined evidence:

```text
python -m pytest -qq tests/tree_replay/test_lifecycle_open_postfill_evidence.py tests/tree_spec/test_lifecycle_open_postfill_evidence_source.py
22 passed

python -m pytest -qq tests/tree_spec/test_lifecycle_live_evidence_source.py tests/tree_spec/test_lifecycle_primitives_source.py
48 passed
```

The explicit-root parity CLI returned VERIFIED against the retained source,
with both child proofs verified and both readiness flags false. The no-argument
CLI path returned valid BLOCKED JSON and exit code 2.

## Blockers

None for Task 2 implementation. Independent review and Codex acceptance remain
outside this task's authorized scope.
