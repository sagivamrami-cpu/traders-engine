# Controller verification — reversal producer slice

Scope: three-task2026-09-09-reversal-producer-asof plan; full master remains open.
HEAD c1b6071633c55376c64f0a98ece843706f420f49; dirty in-place, no commits/pushes.

Completed controller commands:

- python -m pytest tests/tree_replay/test_closed_prefix.py tests/tree_replay/test_periods.py tests/tree_replay/test_frames.py tests/tree_replay/test_levelmap.py -q --tb=short
  213passed6.54s,exit0; prefix-only62passed1.12s separately.
- python -m pytest tests/tree_replay/test_reversal_producer_source.py -q --tb=short
  105passed89.07s,exit0.
- python -m pytest tests/tree_replay/test_reversal_producer.py tests/tree_replay/test_reversal.py tests/tree_replay/test_pricing.py -q --tb=short
  200passed7.32s,exit0. Contains77producer and123legacy compatibility tests.
- All7 source CLI checks after final runtime: python tools/check_NAME_source_parity.py
  --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
  NAME=ema,reversal,pricing,range,correction,levelmap,reversal_producer.
  Each exit0/source_subset_verified=true/blockers[]/false replay+training.
  Six also expose subset_verified=true; EMA only its original source flag.

Pending at file creation:
- integration session36485 (now complete): python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q --tb=short
  exit0,1841passed296.24s. This collected the77-case producer version.
- broad session65395 (now complete): python -m pytest -q --ignore-glob='*validator*' --tb=short.
  exit0,2213passed383.07s,77-case producer collection. Latest78-case run separately
  passed5.19s on unchanged runtime. Counts overlap and are not cumulative.
  Explicit legacy-validator exclusion; no claim those tests pass.
- Minor M1 test-only clarification from original worker, then focused rerun.
- Final combined review and durable acceptance.

Both integration and broad completed without reported test warnings/failures.
git diff --check exit0 with disclosed LF/CRLF advisories on existing tracked
AGENTS/README; untracked files are represented in the explicit final delta.
No runtime changes after the checks. Final combined review now ready.
Final review121800Z subsequently PASS/APPROVED, M1closed, no component findings.
Durable controller acceptance: agent-exchange/status/2026-09-09T122023Z-codex-reversal-producer.md.

M1 follow-up completed: parent fresh producer78passed5.19s,exit0. New optional
overflow test keeps daily valid and asserts its AVAILABLE trace plus exact4h
fetch failure; daily error now separately asserted. Runtime fingerprints above
unchanged (producer/helper rechecked). Latest test blob:
c7ed22a041202e1cfaa9d6c710ec158d4671977b. Current broad/integration runs collected
the prior77-case version; latest78-case verification is separate, not falsely
included in their counts. Final package uses the latest split tests.

Runtime Git blob fingerprints after producer implementation (before test-only M1):

| File | Blob |
| --- | --- |
| periods.py | cb3081c0820d89ccd128f3294138a93cf1e9f4a9 |
| frames.py | 22d42b3ca8fb79e3ca8a6181bf919f97dfaaeda0 |
| levelmap.py | 23b36b5c336862de3bc695751530c7ab457fbfc3 |
| reversal.py | 0846218eedc8d4c83458f75e653e9a46c9dd0889 |
| reversal_producer.py | 1ab7add9928097ced8c4a27916d6459ac2142e7d |
| _vendor/reversal_producer.py | 09ec8d52356c933ba20f97e471237322849f3c98 |
| tools/check_reversal_producer_source_parity.py | 1bef66ef7aaf1ea2d8818fe2a47b469cc1641fa3 |
| configs/trees/reversal-producer-contracts.json | fefb9222f5ebf7c0f1a44a0fee7ae539daf35809 |

Task1/2 independently approved/accepted; Task3 scoped spec PASS/quality APPROVED,
minor M1 being clarified in tests only. Historical RED/fixture fixes are honestly
recorded in each worker/controller task report, not reconstructed as fake runs.
Task2 packaging advisory note is resolved by preserving qualification: LF/CRLF
warnings and new-file diff exit1 are not a clean zero-exit whitespace check.

Boundary: current map/feature clocks remain T, event confirmation separate;
source winner/refusal preserved; no future/unused dependency payload admitted;
default interfaces remain compatible; no live changes, market data, outcomes,
dataset or fitting. Outer operational/state/arbitration work is still required.
Source-intake doc is read-only mapping, not implemented gates or certification.
