# Task 2 — original reversal producer source sidecar

Request: `agent-exchange/inbox/codex/2026-09-09T114500Z-reversal-producer-source.md`
Brief: `.superpowers/sdd/2026-09-09-reversal-producer-asof/task-2-brief.md`
Worker: Codex, scoped source implementer. Date: 2026-09-09.
Status: IMPLEMENTED_AWAITING_CODEX_REVIEW; focused verification complete.

## Scope and implementation

Read the brief first, then the source contract, AGENTS/exchange startup files,
original inbox request, accepted dependency audits/source usage and latest map
acceptance. Read the complete TDD skill and its adjacent `writing-good-tests.md`
before writing implementation. The initial attempted `references/` location did
not exist; the actual adjacent reference was read in full before implementation.
The approved design was not reopened. No subagents, worktrees or commits.

Exactly five deliverable files were created, plus this report and the requested
template result:

- `trading_system/tree_replay/_vendor/reversal_producer.py`
- `tools/check_reversal_producer_source_parity.py`
- `configs/trees/reversal-producer-contracts.json`
- `tests/tree_replay/test_reversal_producer_source.py`
- `docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md`
- `.superpowers/sdd/2026-09-09-reversal-producer-asof/task-2-report.md`
- `agent-exchange/status/2026-09-09T114500Z-worker-reversal-producer-source.md`

All workspace edits used `apply_patch`. Existing dirty files were preserved.
The controller's separate period/frame/map runtime work is outside this task.
No Task 3 public producer implementation was started by this worker.

The sidecar imports exactly the five prescribed imports, in order. Its API is:

```python
def find_at(symbol: str, *, decision_time, source, map_source, detector):
```

The original docstring is followed by `basis = source`, `levelmap = map_source`,
`detect_frame = detector`, and `now = _utc(decision_time)`. Every subsequent
original statement is retained, including `levelmap.build(symbol)`, daily and
bar correction gates, M5/M15 request order, ten-day requests, per-fetch exception
continuation, the 370-second dependency values, candidate sort, and pricing only
the selected event. Complete original `conflicts` is retained unchanged.
Detector constants/dataclass/normalization and original pricing are imported
from the accepted dependencies. No dependency/auditor was edited or recopied.

The new auditor independently fixes commit, source blob, whole producer manifest,
allowed imports/order and transformed module AST. It proves original signatures,
clock assignment/count and injection binding-name preconditions before projection.
It requires exactly one baseline chart-desk pin. Every invocation calls the
complete existing map audit and requires both subset flags to be literal true,
empty blockers, and literal false readiness. The accepted map manifest is sealed
by independently recorded canonical JSON SHA256:

`0cd26630c3274cdaf7c4959c87d8ac06be89652229ed24c541fd46c7cd76a5ab`

Canonicalization is UTF-8 `json.dumps(value, sort_keys=True, allow_nan=False)`
using its default separators. Source newlines are normalized to Git LF. Expected
read/parse/import/input errors yield `BLOCKED` JSON, exit 2. Success is `VERIFIED`,
exit 0. Replay/training readiness remains false on every report. Root precedence
is explicit argument, environment, retained default. The tool imports audit tools
only; source and vendor calculations and runtime wrappers are parsed/read only.

## TDD and exact verification record

All pytest invocations below used the exact requested command:

```powershell
python -m pytest tests/tree_replay/test_reversal_producer_source.py -q --tb=short
```

1. RED before sidecar/auditor/manifest implementation: exit 1, **103 failed in
   2.29s**. Failures were explicit assertions that the assigned source sidecar or
   audit module did not yet exist, not collection/import exceptions.
2. First implementation run: exit 1, **2 failed, 101 passed in 65.14s**.
   Both failures were mutation fixture defects: `replace(..., 1)` changed the
   detector's earlier identical clock expression, leaving `find` unchanged.
   Scoped source mutation to the `def find(` portion; no production change.
3. Added explicit `levels=None` and reversed-import-order cases. Next run: exit 1,
   **1 failed, 104 passed in 64.43s**. The new null-map test found a test fixture
   conflating explicit `None` with its default levels. Corrected that fixture to
   use the existing explicit sentinel. No source behavior changed.
4. Final GREEN: exit 0, **105 passed in 68.07s**. No test warnings or failures.

The behavior tests run the accepted real detector/PVSRA/pricer/ATR/ladder/Plan
math on hand-derived synthetic bars. There are no mocked detector/pricer outputs.
The detector instrumentation records arguments and delegates the real call.
Selected-only pricing instrumentation also delegates the real calculation.
Low-level maps/corrections and unavailable fetch exceptions are explicit offline
fixtures, not public ready-map inputs or claims of feed certification.

Literal pricing fixture: OANDA:XAUUSD M5 long through 100, confirming close 101,
sweep 98, original source stop 93, paying target `UP` at 112, no refusal.
An older version of that paying long competes with a newer M15 short when the
map has no downside paying level: the M15 short remains selected with empty
targets and exact refusal `אין רמה שמשלמת על הסטופ`. Only its plan is priced
in that combined evaluation; a separate real older-only evaluation proves the
paying alternative existed. No formula is used as its own expected-value oracle.

Coverage includes empty/null map, missing/unverified daily correction, verified
proxy/replay/none daily guard semantics, missing/unverified/none bar correction,
both fetch exception branches, both empty detections, literal 5m then 15m/10
requests, same real T/370 detector arguments, opposing M5/M15 tie, newer M15,
older confirmation despite newest nonsignal bar, both timeframe 370-second
inclusive and +1 microsecond boundaries, nearest eligible anchor/per-episode
dedup, refused-winner selection, and source conflict direction/symbol/absence/
tradeability asymmetry using the real Plan class.

Mutation tests operate only on relocated source/vendor/manifests/audit tools.
They exercise missing/malformed files, signature/clock/binding/guard/request/
freshness/import/order/exception/conflict mutations, extra executable statements,
source blob changes, baseline duplicate/missing/wrong pins, whole-manifest
relaxations including false versus zero, independent map-manifest sealing,
inherited detector/pricer/map/EMA/range/correction drift, malformed dependency
report booleans/blockers, CLI root precedence and absent roots. Poisoned runtime
period/frame/map files prove those wrappers are outside the formula audit.
Only dependency *audit reports* are replaced in protocol-boundary tests; no
calculation outputs are replaced.

Standalone command:

```powershell
python tools/check_reversal_producer_source_parity.py
```

PASS, exit 0: `status=VERIFIED`, both subset flags true, `blockers=[]`, both
readiness flags false. Full inherited map/range/pricing/detector/EMA/correction
verification passed. The output retained the nested dependency reports.

Read-only source identity commands:

```powershell
git -C C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk rev-parse HEAD
git -C C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk rev-parse 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9:chartdesk/level_reversal.py
```

Returned respectively `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and
`7c0eee53d97a1ba9280626fdb2d20eba61b5aa1b`. Checkout text was never executed.

Before implementation and again after implementation:

```powershell
Get-ChildItem trading_system/tree_replay/_vendor/*.py, tools/check_*source_parity.py, configs/trees/*.json | Get-FileHash -Algorithm SHA256 | Select-Object Path,Hash | ConvertTo-Json -Compress
```

All **29** pre-existing files in that inventory retained exactly the same SHA256.
The only additions in that inventory were this producer, auditor and manifest.
Runtime clock wrappers are outside that inventory and were never edited by this
worker. Controller changes there remain disjoint.

Whitespace checks (one per assigned deliverable):

```powershell
git diff --no-index --check -- NUL trading_system/tree_replay/_vendor/reversal_producer.py
git diff --no-index --check -- NUL tools/check_reversal_producer_source_parity.py
git diff --no-index --check -- NUL configs/trees/reversal-producer-contracts.json
git diff --no-index --check -- NUL tests/tree_replay/test_reversal_producer_source.py
git diff --no-index --check -- NUL docs/architecture/REVERSAL-PRODUCER-SOURCE-USAGE.md
```

No whitespace-error output; LF/CRLF advisories only. The combined shell returned
exit 1 for these new-file diffs, not a zero-exit check. `git diff --stat` showed
the pre-existing tracked AGENTS/README changes; assigned additions are untracked.
No commits, index updates, cleanup, broad suites or integration reviews were run.

## Self-review, concerns and handoff

Self-review compared the small vendor body to pinned source text, reviewed the
auditor and mutation scope, and checked every requested behavior against the
focused cases. Independent review belongs to the controller; this report is not
an acceptance decision. No known implementation blocker remains at handoff.

Preserved low-level limitations: this sidecar does not validate timestamps,
instrument support, histories, source provenance or public inputs. Its internal
detector seam must delegate the accepted real detector. The next public bridge
must construct actual map/correction evidence at T and maintain observation,
publication and confirmation distinctions. It must not backdate a current map
or change the older newest-confirmation API's guard. Unexpected errors outside
the original fetch try-block remain exceptions for the public adapter to report.

The source Plan's pricing property may be true; that is essential for exact
`conflicts`. It is not public trade admission. Documentation explicitly requires
false public tradeability/readiness. The preserved `conflicts` docstring says
"fresh" but its implementation checks no timestamp: callers must not advertise
it as whole market-watch admission or complete cross-producer arbitration.

The audit trusts repository audit-tool code and standard-library parsing; it
independently seals source identities/manifests, not the machine or toolchain.
The retained source checkout is required for parity tests; a missing checkout
blocks rather than skips. Runtime wrapper certification remains separate.

Outer market-watch scoring/windows/calendar/tracker/dedup/arbitration, other
producers, execution/outcomes, data coverage, datasets and fitting remain open.
No real-data download/access, source feed execution, live behavior changes,
broker operations, instrument alias, promotion or deployment occurred.

Recommended next action: controller independent Task 2 review and acceptance,
then its planned integration with accepted Task 1 and later Task 3. Broad tests
and full-plan status changes remain controller-owned.
