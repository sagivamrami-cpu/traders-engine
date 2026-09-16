# Task 2 implementation report

Scope: audited EMA/EMA-cloud source subset, typed as-of snapshot adapter, source
mapping and read-only AST/blob parity CLI. No candidate generation or market data.

RED: python -m pytest tests/tree_replay/test_ema.py -q --tb=no — 22 failed,
missing vendor/adapter/bar modules and CLI; observed before production code.
Initial implementation: 21 passed, 1 failed. Root cause was the tie fixture:
constant100 in the original recursion yields EMA200=100.0000000000001, while
the other periods equal100. This was confirmed with the verbatim source subset;
no rounding or numerical rule was changed. Constant128 gives exact ties; fixed
that fixture and added preservation of the tiny original difference plus mixed
order coverage. Task1+adapter then passed162tests (138bars +24adapter).

Added real temporary source/vendor fixture tests of parity verification: identical
subset accepted, altered source/body/import/top-level/duplicate/missing blocked.
The fixture exercises parsing and hashing without executing either input file.
Latest focused run: python -m pytest tests/tree_replay/test_ema.py -q —31passed
in6.22s (24calculation/integration cases and7parity verifier cases).

Actual pinned-source parity CLI succeeded, all blobs and selected ASTs matching:
python tools/check_ema_source_parity.py --source-root
C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
source_subset_verified=true; both readiness flagsfalse. No source imports.

Changed paths: trading_system/tree_replay/__init__.py, _vendor/__init__.py,
_vendor/indicators.py, _vendor/tr.py, ema.py; configs/trees/ema-feature-contracts.json;
tests/tree_replay/test_ema.py; tools/check_ema_source_parity.py.

Limitations: per-frame closed contiguous segment only, not live partial bars,
session-calendar integration or full-tree parity. The exported delta5 is source
T3's numerator; normalized slope/ATR/compression are not implemented. Optional
observations do not create vetoes; snapshot eligible is only inherited metadata.
Prices are unrounded; source floating-point tie quirks remain visible. The policy
needs explicit history anchor/freshness and authenticated availability externally.
No commits, feeds, raw market inputs, notifications, labels or training.

Error-path hardening: malformed contract CLI lacked readiness flags; dedicated
RED test failed with missing ready_for_replay. Added explicit false flags on
the error path and reran the focused suite (final result in parent handoff).
Final Task2 focused run:32passed in5.96s. Task2 independent review approved spec
and quality; no findings. Task1 submicrosecond hardening reviewed separately.
