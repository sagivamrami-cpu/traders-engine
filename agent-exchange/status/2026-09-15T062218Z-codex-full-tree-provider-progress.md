# Full-tree causal provider — implementation progress

Created at: 2026-09-15T06:22:18Z

Status: IN_PROGRESS

## Completed, unaccepted increments

1. `a2ba716 feat: add full-tree causal evidence contracts`
   - Private artifacts, public manifests, point-in-time windows, ordered
     operations, variant/mode identity and operation-to-artifact type binding.
2. `279bce4 feat: add ordered full-tree evidence provider`
   - In-memory scheduled raw ports; repeated reads, clocks, options, calendar,
     deep artifacts, scheduled errors and shadow-write commitments.
3. `d2b9dbf feat: replay full tree from causal evidence`
   - Actual `TreeReader` runs for literal house and strict evidence tapes;
     observations classify stop/refusal/no-plan/candidate without raw payloads
     or economic outcomes.
4. `5027edd feat: commit private pending plans for revalidation`
   - An explicit revalidation pass can privately retain a pending plan while
     committing only its digest in the public manifest. Runtime dispatch is not
     implemented yet.

## Current verification

`python -B -m pytest tests/tree_replay/test_full_tree_contracts.py tests/tree_replay/test_full_tree_provider.py tests/tree_replay/test_full_tree_replay.py tests/tree_replay/test_tree_revalidation.py -q --tb=short -p no:cacheprovider`

Result: 48 passed in 5.88s.

Earlier full-tree runner verification also passed 166 focused tree-replay
tests, including actual full `house` and `strict` source walks over literal
scheduled evidence. Counts overlap and do not constitute full repository,
historical-feed, simulation, dataset or model verification.

## Remaining work

- Dispatch the explicit pending-plan pass through actual `TreeRevalidation`
  while preserving its three-result semantics and source shadow operations.
- Add full-tree checkpoint/resume and tamper rejection.
- Add the static source/API parity audit and independent reviews.
- Integrate accepted components into the later historical replay, economic
  simulation, outcome dataset and model-evaluation workstreams.

## Boundaries

No raw market payload has been written here. This status does not assert
historical-feed readiness, economic simulation, labels/dataset creation,
model training/promotion, broker execution, capital allocation or live trading.
