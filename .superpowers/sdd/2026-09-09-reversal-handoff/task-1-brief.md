# Reversal selected-Plan handoff implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Track checkbox steps.

**Goal:** Preserve the actual source-selected Plan for faithful downstream admission.
**Architecture:** One internal evaluator returns pre-admission report plus original
event/Plan; public dict API remains unchanged. No report-to-Plan reconstruction.
**Tech Stack:** Python dataclasses, existing pandas/NumPy offline pipeline, pytest.
**Spec:** docs/architecture/REVERSAL-HANDOFF-CONTRACT.md

## Global Constraints

- Preserve pinned chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9 behavior.
- No live imports, external I/O, source policy/threshold/symbol aliases or new data.
- Source-selected refusal remains refusal. Advisory OPEN is not economic fill.
- Public VERSION/schema/hash/readiness and raised validation errors unchanged.
- Preserve existing dirty checkout/branch. No commits, pushes, worktree creation or cleanup.
- Use apply_patch for every file edit; no subagents from implementer/reviewer.
- Scope is a prerequisite of full master C, not substitute for full source replay.

## Task 1: Retain actual source selection through the private evaluation

**Files:** Modify trading_system/tree_replay/reversal_producer.py.
Create tests/tree_replay/test_reversal_handoff.py and
docs/architecture/REVERSAL-HANDOFF-USAGE.md.
Do not modify source vendor modules, existing tests, public exports or manifests.

**Consumes:** Current find_reversal_asof keyword-only arguments; FrameSpec/
MapFrameRequest/ReversalFrameRequest and actual _vendor.reversal_producer.find_at.
Read relevant unchanged tests/tree_replay/test_reversal_producer.py fixtures
maps/reversal/find and refused case, and actual pricing.Plan/tracker.record fields.
**Produces:** _ReversalEvaluation and _evaluate_reversal_asof per contract; existing
public function returns evaluator.report without changing its public contract.

- [ ] Capture before-refactor public hashes using the real accepted fixture,
  newest-refused M15 fixture, quiet fixture, and unavailable daily fixture.
  Put literals and dependency versions in the report/test comments; no dynamic
  mirror expected values. Run existing producer tests once as baseline.
- [ ] Add behavioral tests with function lookup inside each test (missing helper
  should fail the test, not abort collection). Core shape:
  ```python
  result = adapter._evaluate_reversal_asof(
      snapshot_id="test", instrument=SYMBOL, decision_time=T,
      map_requests=maps(), reversal_requests=(reversal(), reversal("15m", short=True)))
  assert result.report["status"] == "PRODUCER_SELECTED_UNADMITTED"
  assert result.selected_plan.entry == 100.0
  assert result.selected_plan.stop == 93.0
  assert result.selected_plan.kind == "reversal"
  assert result.selected_plan.style == "scalp"
  ```
  Assert original close from hand-checked synthetic confirmation bar, target112,
  original event selection. Wrap actual find_at in a spy that calls the original,
  captures returned pair and counts one invocation; assert object identity plus
  real consumer results. This is not a fake selection.
- [ ] Run new tests RED, record exact failure/output. Add no runtime before RED.
- [ ] Extract, do not duplicate the current evaluator body. Implementation shape:
  ```python
  @dataclass(frozen=True)
  class _ReversalEvaluation:
      report: dict
      selected_event: level_reversal.Reversal | None
      selected_plan: pricing.Plan | None

  def find_reversal_asof(*, snapshot_id: str, instrument: str,
                        decision_time: datetime,
                        map_requests: tuple[MapFrameRequest, ...],
                        reversal_requests: tuple[ReversalFrameRequest, ...]) -> dict:
      return _evaluate_reversal_asof(
          snapshot_id=snapshot_id, instrument=instrument, decision_time=decision_time,
          map_requests=map_requests, reversal_requests=reversal_requests).report
  ```
  Private body keeps existing validation/lazy calls/result dictionaries/hashes.
  Retained locals start None, receive original event/plan only on complete
  successful selection serialization, clear on caught failure. Final return
  constructs private dataclass after report hashes; no Plan in report/hash.
- [ ] Add/verify late _source_plan and _pricing_snapshot fault tests using actual
  find, no selection/missing/unsupported None pairs, refused selection, original
  validation exceptions, private/public equality and pre-refactor golden hashes.
  Fault injection must name the concrete serialization path; restore via pytest.
- [ ] Add real producer -> real TrackerAdmission.record integration with test-only
  detached in-memory ports, explicit T, matrix readings and known empty quote.
  Assert recorded literal entry100/stop93/target112/kindreversal and plan.born_open
  matching actual fixture; stored reasons equal independently checked source
  fixture content. Confirm report remains unchanged after tracker mutates Plan.
  Test nested-list mutation isolation and repeated evaluations separately.
  Neither this direct record test nor private evaluator implements outer gates.
- [ ] Run `python -m pytest tests/tree_replay/test_reversal_handoff.py tests/tree_replay/test_reversal_producer.py tests/tree_replay/test_tracker_admission.py -q --tb=short`.
  Keep original tests and default pytest mode. Focus individual failures first.
- [ ] Self-review; document interface, mutable ownership, retained refusal, false
  readiness and missing causal ports. Full report includes RED/GREEN, before/after
  hashes, commands/results, files, concerns. No commit or external action.
- [ ] Parent independent verification, complete task diff/review, then final
  component review and acceptance before using handoff for actual causal binding.
