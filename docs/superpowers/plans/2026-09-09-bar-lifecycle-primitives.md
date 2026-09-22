# Original bar lifecycle primitives implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Preserve original position-window geometry and movement-success proof.
**Architecture:** Private audited original source functions plus explicit-clock
DeskSuccess methods; exact voice formatting and accepted pricing dependency.
No new execution policy, causal feed provider or whole-resolver claim.
**Tech Stack:** Python/pandas/dataclasses/ast, ReplayClock test ports, pytest.
**Spec:** docs/architecture/BAR-LIFECYCLE-PRIMITIVES-CONTRACT.md

## Global constraints

- Current approved feature checkout, preserve all existing changes.
- Exact source pins and behavior, no invented thresholds/fees/fills/times.
- apply_patch edits; no source execution/live IO/market acquisition/commits/cleanup.
- Broad suite78562 is terminal:2529passed339.40s, recorded171652Z; baseline is
  verified before starting this runtime work. Current component acceptance is
  agent-exchange/status/2026-09-09T173529Z-codex-lifecycle-primitives.md.
- Main implementation inline; independent review reports only, no nestedagents.
- Full master stays active; accepted primitives are not complete trading outcomes.

## Task1: Actual geometry, voice and movement proof

Create trading_system/tree_replay/_vendor/lifecycle_bars.py,
trading_system/tree_replay/_vendor/lifecycle_voice.py,
trading_system/tree_replay/_vendor/desk_success.py,
tests/tree_replay/test_lifecycle_bars.py, tests/tree_replay/test_desk_success.py,
docs/architecture/BAR-LIFECYCLE-PRIMITIVES-USAGE.md.

Consumes: accepted pricing.entry_zone/basis_symbols.canonical_symbol, pandas.
Produces: five exact module-level position functions, original voice functions,
DeskSuccess(source).reached/observe/observe_bars/classification/stop_note and
module minimum(symbol), VERSION/FLOOR. Source ports now_epoch() and now_utc().

- [x] Read exact source functions/completevoice/desk_success and spec. Write normal
  RED tests using importlib.find_spec assertion, not broken fixture imports.
  Example geometry fixture, with explicit expected values:
  ```python
  frame = pd.DataFrame({"open": [105., 100.], "high": [120., 106.],
                        "low": [99., 100.], "close": [100., 105.]},
                       index=pd.to_datetime(["2026-09-09T16:15Z", "2026-09-09T16:30Z"]))
  trade = {"symbol": "OANDA:XAUUSD", "direction": "לונג", "entry": 100.,
           "ts": pd.Timestamp("2026-09-09T16:00Z").timestamp(), "state": "PENDING"}
  assert bars._open_extremes(frame, trade) == (106., 99.)
  ```
  Add mirrored short, exactsend/no-fill, OPENfillstamp and include_fill_bar cases.
  Movement tests use source trade_id/ts/state/stop/targets and ReplayClock ports:
  ```python
  class ClockPorts:
      def __init__(self, at): self.clock = ReplayClock(at)
      def now_epoch(self): return self.clock.now.timestamp()
      def now_utc(self): return self.clock.now
  ```
  A long100/stop90/TP120 whose fillbar high120 and later payingbar high104
  succeeds at XAU4points; fillbar alone does not. A stop in that payingbar
  prevents newproof. Assertion uses literal proof identity/price104/times/source,
  state stays OPEN and original stop/targets unchanged. Mirror short and symbols.
- [x] Run `python -m pytest tests/tree_replay/test_lifecycle_bars.py tests/tree_replay/test_desk_success.py -q --tb=short`;
  verify normal missingmoduleRED for each implementation group before writing it.
- [x] Add exact original functions/source projections. DeskSuccess redirects only
  internal method calls and explicit clock ports; observe_bars uses the real
  lifecycle_bars helper and original voice. No replacement score/fill stubs.
- [x] Run focusedGREEN and `python -m pytest tests/tree_replay/test_lifecycle_bars.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_admission_context.py -q --tb=short`.
  Inspect unsupported/missing/time/side-effect behavior against spec; usage/report/
  full new-file package and independent task review, preserve runtime meanwhile.

## Task2: Independent complete projections and inherited source audit

Create trading_system/tree_spec/lifecycle_primitives_source.py,
tools/check_lifecycle_primitives_source_parity.py,
tests/tree_spec/test_lifecycle_primitives_source.py.

- [x] Write audit RED and mutation tests before auditor implementation:
  ```python
  r = api().audit_lifecycle_primitives_source(SOURCE)
  assert r["status"] == "VERIFIED" and not r["blockers"]
  assert not r["ready_for_replay"] and not r["ready_for_training"]
  ```
  Mutate source and each candidate module in memory; strictafter/inclusivefill,
  exclude-fillbar/firststop, proofidentity/time/units, clock substitution and
  extraimport/classbody must fail. Pricing/canonical mutation must fail inherited
  audit too. Check missingroot/files, wrongHEAD/baseline and CLI from unrelatedcwd.
- [x] Implement audit from independent pinned text, exact ordered selected symbols,
  body/class substitutions and wholemodule AST. Call accepted admission audit
  for pricing/canonical closure and propagate blockers. CLIexplicit source-root,
  JSONreport, source_subset_verified drives0/2exit; no runtime source execution.
- [x] Run source tests and combined runtime/audit/inherited suites:
  `python -m pytest tests/tree_replay/test_lifecycle_bars.py tests/tree_replay/test_desk_success.py tests/tree_spec/test_lifecycle_primitives_source.py tests/tree_spec/test_tracker_admission_source.py tests/tree_replay/test_admission_context.py -q --tb=short`.
  Run CLI retainedroot, inspect whitespace/package, independent Task2review.
- [x] Fix actual findings with RED/GREEN; combined final review then authoritative
  acceptance/memory/implementationtracker update. No full-goal completion claim.

## Continuation

Bind causal lifecycle feed requests and revalidation/independent verifier/effects,
then original stateful resolvers and caller. Source intake records required3day,
400day/60day requests and different verification tape, distinct from admission.
Full economic simulation/dataset/models and all other branches remain required.
