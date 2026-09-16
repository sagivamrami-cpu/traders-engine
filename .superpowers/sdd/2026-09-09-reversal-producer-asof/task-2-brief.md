# Task 2 brief

## Global Constraints

- Approved pinned source is authoritative; no invented thresholds, calendars, feeds or GC/spot equivalence.
- Observation cutoff is not decision time. No backdating maps or rewriting publication to force availability.
- Existing default APIs, validation and result/hash behavior remain unchanged.
- All readiness flags and public tradeable remain false; selected source pricing is not external market-watch admission or execution.
- No source/feed execution, real-data access/downloads, fitting, live changes, broker operations or deployment.
- Preserve dirty in-place branch; no commits, pushes, worktrees, cleanup or nested implementer agents.
- Main owns acceptance/master/README/AGENTS/tracker. Source Task2 can run alongside controller Task1 because their files are disjoint. Task3 depends on accepted1/2.
- Full objective remains B-I, not merely this producer. Outer market-watch windows/calendar/tracker/deduplication/arbitration remain explicit next work, never silently considered done.

## Task 2: Exact original find and conflicts source sidecar

Owner: one source worker; independent of Task1. Create _vendor/reversal_producer.py,
tools/check_reversal_producer_source_parity.py, configs/trees/reversal-producer-contracts.json,
tests/tree_replay/test_reversal_producer_source.py, docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md.

Source root/commit/blob exactly as named in the source contract. Read as text only.
Retain original full find and conflicts. Existing detector, constants, dataclass,
normalization and build_plan are imported, not copied or changed. Allowed imports
in this exact order:
```python
from __future__ import annotations
import pandas as pd
from .level_reversal import Reversal, _utc, LIVE_MAX_AGE_S
from .reversal_pricing import build_plan
from . import pricing as tradeplan
```
Adapt find to:
```python
def find_at(symbol: str, *, decision_time, source, map_source, detector):
    # Original docstring, then these bindings:
    basis = source
    levelmap = map_source
    detect_frame = detector
    now = _utc(decision_time)
    # Original remaining body exactly, including levelmap.build(symbol).
```
The detector argument is an internal instrumentation seam; public callers never
provide it. It must delegate to the accepted real detector. map_source.build
returns actual levels/correction at the same T. All other statements, guards,
request10,370 freshness, sort order, exceptions and selected-only pricing remain
exact. conflicts is copied unchanged, not falsely described as outer admission.

New audit uses fixed independent commit/blob, exact whole manifest and ordered
module AST. Prove original signature/clock and binding-name preconditions before
transformation. Verify exactly one baseline chart-desk pin. Invoke existing full
check_levelmap_source_parity (inherits all calculation dependencies) and require
true subset/empty blockers/false readiness. Independently seal accepted map
manifest canonical JSON hash; do not trust a mutated manifest. Expected errors
become BLOCKED reports; source/vendor never executes in auditing. CLI rootarg >
TR_CHARTDESK_SOURCE_ROOT > retained default; success0, missing/mutation2.

- [ ] TDD source behavior using real detector/pricer and explicit offline feed/map
  fixtures: no map/none/unverified daily gates; valid proxy/replay daily not
  blanket-vetoed; bar none/unverified/source=none skip; request5m then15m/10;
  per-TF fetch exceptions continue; literal M5/M15 tie, newerM15 vs olderM5;
  older fresh confirmation when latestbar has no signal;370 inclusive and one
  microsecond older excluded; original per-episode/nearest-level behavior.
- [ ] Test newest refused plan is still selected, not replaced with an older
  accepted plan; source conflicts exact same/opposite/empty directions, same/
  different symbol and tradeability. Hand-derived real input fixtures; no
  mocked detector/pricer or formula outputs. Instrumentation may record calls
  while delegating real math. Low-level supplied map fixtures are permitted.
- [ ] Mutation tests relocate source/vendor/manifests; changedsignature/clock/
  binding/guard/request/freshness/order/imports/extra statements/sourceblob/
  baseline duplicates/false-vs0/dependency drift/missing root all rejected.
  Do not modify production pins or existing auditors. Verify prefix-clock Task1
  wrappers are not part of the source formula audit, and no accepted dependency
  is modified by this worker.
- [ ] Run python -m pytest tests/tree_replay/test_reversal_producer_source.py -q
  --tb=short RED/GREEN and python tools/check_reversal_producer_source_parity.py.
  Report self-review and evidence; independent task review before acceptance.
