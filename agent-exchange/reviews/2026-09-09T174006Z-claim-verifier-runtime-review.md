# Agent Exchange Review

Reviewer: Codex independent Task1 reviewer; no nested agents

Target request: agent-exchange/inbox/codex/2026-09-09T174006Z-claim-verifier-runtime-review.md

Created at: 2026-09-09T17:43:04Z

Status: REVIEW_READY_FOR_CODEX

## Verdict

Spec: PASS for the runtime/source contract; one Minor omission from the planned
persistent test coverage, detailed below. All three requested files exist and
match the supplied Task1 package.

Quality: PASS WITH MINOR FINDING. No Critical or Important findings and no
runtime correctness defect found. Suitable for Task1 runtime acceptance; this
is not Task2 or combined-component acceptance.

## Scope and method

Read AGENTS.md, agent-exchange/README.md and protocol.md; inspected the sorted
Codex inbox and executed only the named request. Read the complete task plan,
INDEPENDENT-CLAIM-VERIFIER-CONTRACT.md, USAGE, complete-verifier intake section,
all three actual Task1 files, complete pinned chartdesk/verify.py, and the
173529Z lifecycle acceptance including its terminal broad-test addendum.
Inspected DeskSuccess, ReplayClock, lifecycle geometry/voice and the actual
entry_zone/canonical_symbol dependency path.

Applied requesting-code-review and its code-reviewer template directly, and
verification-before-completion. No reviewer delegation, source execution,
network/data access, runtime/test edits, inbox/status edits, commits or cleanup.
Only this report is written, using apply_patch. Test bytecode and pytest cache
writes were disabled. Main's disjoint Task2 auditor was not used as evidence.

Inspected git status --short and git diff (including the pre-existing AGENTS.md
and README.md changes). HEAD is c1b6071633c55376c64f0a98ece843706f420f49. Task1
files are untracked additions; an empty HEAD-to-HEAD diff was not substituted
for their contents.

## Strengths and fidelity evidence

- Independently reconstructed the full expected AST from the retained source,
  without importing or executing it. Compared the complete runtime module
  after replacing only its module documentation and applying the declared
  import/class/port adaptations. All constants, pure functions, Verdict fields
  and truthiness, method signatures, ordering, constructor and bodies match.
- The seven methods retain source order. The comparison counted each individual
  adaptation: three UTC-clock replacements; one JSON transport replacement;
  one corrected-frame replacement; one entry_zone import redirect; removal of
  two local transport imports and one reached import; one real movement.reached
  binding; and nine self-call bindings. No resolver fill helper substitution,
  extra import, new veto, decoder rewrite or tolerance change was present.
- Runtime tests use real pandas calculations, ReplayClock, actual venue-row
  decoding and source-generated movement proof/messages. They distinguish
  independent fill slack/fill-bar extrema, stale versus contradiction,
  resolved_ts precedence, literal tolerances and router exception containment.
- Usage explicitly limits these supplied ports: neither causal feed coverage
  nor economic execution, full gate effects, historical replay or training is
  certified. The containing-bar OHLC limitation is stated, not hidden by the
  timestamp filter.

## Findings

Critical: none. Important: none.

Minor M1 — planned non-None empty venue-frame regression is absent.

- Location: tests/tree_replay/test_claim_verifier.py:193; runtime branch at
  trading_system/tree_replay/_vendor/claim_verifier.py:134.
- The existing parameterization exercises empty JSON/None and decoder failures,
  all of which return None and correctly trigger local fallback. It does not
  exercise a non-None empty DataFrame returned by _binance_bars. The plan at
  docs/superpowers/plans/2026-09-09-independent-claim-verifier.md:50 explicitly
  calls for characterizing that distinct policy.
- Current runtime is correct: my independent branch probe confirmed that an
  empty venue DataFrame wins, local fetch is never called, and target then
  rejects the missing tape. This is a coverage omission, not a runtime bug or
  a claim that ordinary empty JSON decodes to a DataFrame.
- Recommendation: add a focused branch regression supplying an empty venue
  DataFrame, asserting object identity/no local call and failed public claim.
  Preserve the current source condition; do not add a fallback for emptiness.

## Verification executed

PASS, exit 0:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest tests/tree_replay/test_claim_verifier.py -q --tb=short -p no:cacheprovider
```

Result: **55 passed in 0.81s**. This independently reruns the requested focused
suite. Main's reported RED55 and earlier combined184 were not independently
reproduced and are not claimed as fresh reviewer evidence.

PASS, source authority, using read-only git commands:

```powershell
git -C C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk rev-parse HEAD
git -C C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk hash-object chartdesk/verify.py
```

Results: commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
verify.py blob 3329fdb71f8aebdf13a6fa823e8be0d85e1ced03.

PASS, two independent in-memory Python probes (`@' ... '@ | python -B -`),
exit 0 each; no probe files created:

1. AST/package probe described above: complete AST equality; parsed all three
   addition hunks in task-1-diff.md and compared their complete added text with
   actual files (line endings normalized by text reading). All three match.
2. Boundary probe: non-None empty venue precedence; malformed timestamp decoder
   fallback; preservation of venue row order and duplicate stamps; strict send
   slack and inclusive claim horizon at one-microsecond boundaries; target and
   stop rejecting a future row then accepting it after ReplayClock advances;
   unchanged trade/frame inputs; six actual DeskSuccess-generated minimum
   messages across XAU/NAS/BTC and long/short, accepting valid proofs and
   rejecting changed identity and proof time one microsecond in the future.
   Minimum verification performed no frame/JSON reads and did not mutate trade.

The empty-venue probe isolated only the _bars boundary with this subclass:

```python
empty = pd.DataFrame(columns=['open', 'high', 'low', 'close'])
class EmptyVenue(ClaimVerifier):
    def _binance_bars(self, symbol, days):
        return empty
# Ports records every fetch_corrected/fetch_json call.
e = EmptyVenue(ports)
assert e._bars('BINANCE:BTCUSDT') is empty
assert ports.calls == []
assert not e.target(trade_with_binance_symbol, 110.)
assert ports.calls == []
```

The separate decoder probes exercised the unmodified decoder with supplied
rows; no original source module or live transport was executed.

Task1 SHA256 values, identical before and after verification:

| File | SHA256 |
| --- | --- |
| trading_system/tree_replay/_vendor/claim_verifier.py | 87d424e1c2d3c60c0897d655394c38fd158b9346d43436f165e81cbe9516c3c3 |
| tests/tree_replay/test_claim_verifier.py | da3ea00faabeff4803ab4807b92e3516e651d3345fac879a163809e7c0521732 |
| docs/architecture/INDEPENDENT-CLAIM-VERIFIER-USAGE.md | 07eb50fe3c7e949fc18b701b47033edfb09d02cff08da9d975908afe78b06e30 |

## Open questions and recommended next action

No blocking question. Controller may accept Task1 runtime with M1 recorded;
persisting that small regression would complete the stated Task1 test matrix.
Proceed through the separately owned Task2 and combined review before declaring
component acceptance. No broad suite, Task2 audit/CLI, full caller/lifecycle,
historical provider, economic labels, dataset or model readiness is certified
by this report. All reviewer verification processes terminated.
