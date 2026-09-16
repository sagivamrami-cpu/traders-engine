# Independent Re-review — Closed-Bar Causal Replay Task 1 Corrective Revision

Status: APPROVED

## Scope and method

Reviewed the Task 1 plan, prior independent review, revision report, complete
current contract module, and complete focused test module. No retained source was
imported or executed, and no implementation file was changed. The sole write for
this review is this requested report.

## Critical issues

- None.

  Exact evidence: the shared `_contains_forbidden_structured_field()` recurses
  through every `Mapping` and canonical tuple (`causal_replay_contracts.py:115-123`).
  Every payload is canonicalized before that guard (`:178-184`), candidates are
  canonicalized before it (`:304-311`), and each diagnostic is canonicalized
  before it (`:324-335`). Since canonical dictionaries are `MappingProxyType`s
  and canonical lists become tuples (`:50-62`), the guard covers normal mappings,
  mapping proxies, lists, and tuples after normalization. The permanent
  parametrized regression covers all four forbidden names × all three surfaces ×
  dict/list/tuple nesting (`test_causal_replay_contracts.py:169-191`).

- None.

  Exact evidence: `_payload_available_at()` rejects any decimal component longer
  than six digits before `datetime.fromisoformat()` is reached
  (`causal_replay_contracts.py:99-112`). The focused regression accepts the
  six-digit `Z` payload timestamp and rejects the former seven-digit payload
  timestamp (`test_causal_replay_contracts.py:133-139`).

## Important issues

- None.

  Exact evidence: the revision's permanent regressions specifically exercise the
  two formerly accepted boundary classes: nested forbidden fields in payload and
  diagnostics (`test_causal_replay_contracts.py:178-191`) and a serialized
  seven-digit payload availability (`:133-139`). Thus removing either the new
  all-surface guard or pre-parse precision check reintroduces a focused failure.

## Minor issues

- None.

## Prohibited-scope check

Approved. The reviewed module remains a supplied-data contract: its only imports
are dataclass/time/value-validation/canonical-serialization helpers
(`causal_replay_contracts.py:7-19`), and its module contract expressly excludes
tracker rows, outcomes, economic labels, datasets, models, and live work (`:1-5`).
Static inspection found no tracker record call, economic computation, dataset or
model/readiness field, delivery/network client, filesystem API, or retained-source
path. The revision is confined to recursive structured-field validation,
serialized-time precision validation, and focused tests.

## Verification

- `python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider` — PASS: `53 passed in 0.11s`.
- In-memory adversarial probe, importing only the local Task 1 contract and no
  retained source — PASS: rejected 36 combinations (four field names × three
  surfaces × mapping/list/tuple nesting) supplied as mapping proxies; accepted
  `2026-01-02T09:30:00.000001Z`; rejected
  `2026-01-02T09:30:00.0000001+00:00` before ISO parsing.

Conclusion: the corrective revision closes C1, C2, and I1 from the prior review.
