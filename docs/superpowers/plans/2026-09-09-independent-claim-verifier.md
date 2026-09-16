# Independent claim verifier implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans or superpowers:subagent-driven-development. Track checkbox steps.

**Goal:** Run the complete original price-claim checker through offline inputs.
**Architecture:** Exact independent verifier plus decoder/router over explicit
clock, corrected-frame and JSON-response ports; no resolver helper substitution.
**Tech Stack:** Python/pandas/dataclass/ast/pytest, existing ReplayClock/DeskSuccess.
**Spec:** docs/architecture/INDEPENDENT-CLAIM-VERIFIER-CONTRACT.md

## Global constraints

- Approved existing feature checkout; preserve unrelated work.
- Exact chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 and
  verify.py blob3329fdb71f8aebdf13a6fa823e8be0d85e1ced03.
- All edits apply_patch. No original source execution or runtime network access.
- No market acquisition/labels/training/live notifications/commits/cleanup.
- Finish acceptance of bar-lifecycle-primitives before this runtime implementation.
- Main critical path inline, independent review-only sidecars, no nestedagents.
- No new domain choice: preserve fillbar/slack/tolerances even when differing
  from resolver; explicitly no economic execution certification.

## Task1: Complete original verifier through local ports

Create trading_system/tree_replay/_vendor/claim_verifier.py,
tests/tree_replay/test_claim_verifier.py,
docs/architecture/INDEPENDENT-CLAIM-VERIFIER-USAGE.md.

Consumes: DeskSuccess(source), pricing.entry_zone, pandas and explicit ports.
Produces: ClaimVerifier(source)._bars/_binance_bars/target/_claim_clock/fill/stop/
check_message; original Verdict and purehelpers/constants from the spec.

- [x] Read complete source/spec. Write normal RED tests:
  ```python
  def api():
      name = 'trading_system.tree_replay._vendor.claim_verifier'
      assert importlib.util.find_spec(name) is not None, 'claim verifier missing'
      return importlib.import_module(name)
  ```
  Fixture ports use actual ReplayClock; fetch_corrected asserts symbol,15m,3;
  fetch_json captures exact URL/timeout and returns supplied rows or raises.
  Hand-computed long100/stop90 fixture: sent16:00, firstbar16:00 low99/high120
  qualifies independent slack fill and target110; resolver strictsend doesnot.
  Separate pending send16:14 frame16:00 qualifies onebarslack. Mirror shorts.
  Claim16:15 with later16:30 targetbar must fail; stop resolved16:15 must not
  consume later touch merely because claim_ts16:30. Delayed tape gives stale,
  closedpast tape gives contradiction. Price tolerance boundaries literal.
  Binance decoder row `[epoch_ms, '100','105','99','104']` yields expectedOHLC;
  exact URL includes operationnow minus3days,limit1000/interval15m,timeout15.
  Empty JSON returnsNone/fallback, decodednonNoneemptyframe policy characterized;
  malformed rows/transportfailure fallsback. Localunverified returnsNone.
  check_message uses actual source-generated minimum message and proof; invalid
  identity blocks. Targetmissingprice blocks; actual fill/stop/target routes run
  real calculations. Nofactualclaim passes, throwninput exception blocks.
- [x] Run `python -m pytest tests/tree_replay/test_claim_verifier.py -q --tb=short`;
  observe normal missingmodule failures, not collectionerrors.
- [x] Create source projection with all functions/constants as spec, imports and
  constructor only; exact source replacements (no algorithm rewrite):
  ```python
  class ClaimVerifier:
      def __init__(self, source):
          self.source = source
          self.movement = DeskSuccess(source)
  # _bars: basis.fetch_corrected -> self.source.fetch_corrected
  # _binance_bars: _json.load(_rq.urlopen(url, timeout=15))
  #             -> self.source.fetch_json(url, timeout=15)
  # pd.Timestamp.now(tz='UTC') -> pd.Timestamp(self.source.now_utc())
  # check_message: reached(trade) -> self.movement.reached(trade)
  ```
  Keep full original tryblocks/decoder/URL and explicit per-function selfcalls.
- [x] Run focusedGREEN plus lifecycle_bars/desk_success/admission_context tests.
  Usage explains rawport/caller evidence, independent algorithm and no effects.
  Record evidence/fullnewfile package; independent Task1 spec/qualityreview.

## Task2: Independent verifier source audit

Create trading_system/tree_spec/claim_verifier_source.py,
tools/check_claim_verifier_source_parity.py,
tests/tree_spec/test_claim_verifier_source.py.

- [x] Write normalRED auditor tests and mutation cases:
  ```python
  r = api().audit_claim_verifier_source(SOURCE)
  assert r['status'] == 'VERIFIED' and r['blockers'] == []
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Actual runtime mutations must reject changed tolerance/slack/claimclock/
  firstbar behavior/router, extra imports, URL limit/timeout/parser, venue-first
  ordering and inherited proof. Wrong sourceHEAD/blob/baseline/missingfile and
  CLI outsidecwd must failclosed. No candidate or source execution by auditor.
- [x] Implement literal authority and ordered wholemodule/class/signature
  projection, exact per-function statement/expression substitutions/counts.
  Invoke actual lifecycle_primitives source audit; propagate its blockers.
  CLI pattern argparse required--source-root, JSONreport, verified0/blocked2.
- [x] Run source tests, CLI and combined runtime/audit/lifecycle suites:
  `python -m pytest tests/tree_replay/test_claim_verifier.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_bars.py tests/tree_spec/test_claim_verifier_source.py tests/tree_spec/test_lifecycle_primitives_source.py -q --tb=short`.
  Full package and independent Task2review; fix actual findings with RED/GREEN.
- [x] Combined final review; current-file verification and authoritative
  acceptance/memory/tracker updates only after all findings addressed.

## Continuation

Bind distinct causal verifier/lifecycle requests and original still_valid,
tree revalidation and shadow/effects before full resolver. Full caller/other
branches/economic simulation/dataset/models remain in master, not optionalized.
