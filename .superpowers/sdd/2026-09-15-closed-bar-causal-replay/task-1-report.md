# Task 1 Result: Immutable replay evidence, ledger and activation contracts

Status: DONE

## Scope completed

Implemented the data-only, immutable contracts for the first closed-bar causal
replay slice. The implementation accepts supplied offline evidence only and
does not orchestrate a replay, load files or network data, invoke a broker or
delivery path, calculate an economic outcome, build a dataset/train a model,
promote readiness, or create a tracker row.

## Exact files changed

- `trading_system/tree_replay/causal_replay_contracts.py` (created)
- `tests/tree_replay/test_causal_replay_contracts.py` (created)
- `.superpowers/sdd/2026-09-15-closed-bar-causal-replay/task-1-report.md` (this required task report)

## Implemented contracts

- Frozen `TrackerActivationEvidence`, with microsecond-aware activation state
  checks for unavailable, expired, mismatched, enabled and disabled evidence.
- Frozen `ReplayEvent`, `ReplayPassAnchor`, and `ReplayEvidenceBundle`, with
  exact `OANDA:XAUUSD` identity, immutable schedule collections, strict
  `(available_at, sequence)` ordering, payload-availability agreement, and
  pre-selection validation.
- `canonical_digest`, which rejects non-finite/non-JSON-compatible input and
  hashes canonical UTF-8 JSON with SHA-256.
- Frozen `ReplayPassRecord` and append-only `ReplayRunLedger`, with detached
  immutable mappings, permitted diagnostic outcomes only, predecessor hash
  chaining, contiguous indices, unique pass IDs and nondecreasing decision
  time.
- Candidate validation recursively rejects `net_pnl`, `net_R`, `success`, and
  `failure`, including when hidden in a nested object.

## TDD evidence

RED:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider
ModuleNotFoundError: No module named 'trading_system.tree_replay.causal_replay_contracts'
```

Additional RED after the initial implementation:

```text
test_candidate_cannot_hide_an_economic_or_outcome_label_field_in_a_nested_object
FAILED: DID NOT RAISE ValueError
```

GREEN:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider
16 passed in 0.07s
```

Additional verification:

```text
python -B -m py_compile trading_system/tree_replay/causal_replay_contracts.py tests/tree_replay/test_causal_replay_contracts.py
PASS
```

`git diff --check --no-index` reported no whitespace errors for either created
implementation/test file (only the workspace's LF-to-CRLF warning).

## Self-review

- Used `bars._utc`, `bars._number`, `bars._validate_identity`, and
  `state._identity`; no alternative timestamp or identity parser was added.
- Confirmed public collections are tuples or detached mapping proxies; mutating
  a caller-owned candidate after construction does not change the record.
- Confirmed activation evidence cannot record a tracker row: this module has
  no tracker import, no `record` call, and no runtime orchestration.
- Confirmed no readiness, P&L, net-R, training, model, broker, delivery,
  network, or filesystem discovery behavior was introduced.
- Scoped status showed only the two required implementation/test files before
  this required report was written; pre-existing dirty workspace files were not
  changed.

## Concerns

None for Task 1. The contracts are intentionally not a replay runner,
checkpoint implementation, source-order audit, outer-admission binding, or
economic/dataset/model component; those remain later approved tasks.
