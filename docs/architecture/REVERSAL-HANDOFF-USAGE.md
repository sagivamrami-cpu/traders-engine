# Private selected reversal Plan handoff

This prerequisite retains the actual event and `pricing.Plan` selected by the
pinned chart-desk producer (`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`).
It does not complete causal admission or full replay. See
[the handoff contract](REVERSAL-HANDOFF-CONTRACT.md).

## Interface

`trading_system.tree_replay.reversal_producer._evaluate_reversal_asof` takes the
same keyword-only inputs as `find_reversal_asof`:

```python
evaluation = _evaluate_reversal_asof(
    snapshot_id=snapshot_id,
    instrument=instrument,
    decision_time=decision_time,
    map_requests=map_requests,            # tuple[MapFrameRequest, ...]
    reversal_requests=reversal_requests, # tuple[ReversalFrameRequest, ...]
)
report = evaluation.report
event = evaluation.selected_event
plan = evaluation.selected_plan
```

The private frozen `_ReversalEvaluation` dataclass contains `report: dict`,
`selected_event: level_reversal.Reversal | None`, and
`selected_plan: pricing.Plan | None`. The existing public `find_reversal_asof`
returns only `evaluation.report`. Its signature, validation exceptions,
VERSION, schema, report content, decision ID, and evaluation hash are unchanged.
There are no new public exports.

The evaluator invokes the original source selection once and retains that exact
event/Plan pair. It does not rebuild a Plan from evidence, rerun selection, or
reprice the result. Original `close`, `kind`, direction, style, ordered targets,
reasons, warnings, and obstacles are therefore available to a future consumer.

Both objects are present only when status is `PRODUCER_SELECTED_UNADMITTED` and
the selected evidence has serialized successfully. They are both `None` for
unsupported instruments, no selection, unavailable inputs, source errors, and
pricing/snapshot serialization failures. Invalid input still raises the existing
validation exception. A newest selected `PRICE_REFUSED` Plan is retained with
its original refusal and geometry; an older paying candidate does not replace it.

## Ownership

The dataclass freezes field bindings; the original Plan remains mutable. A
consumer may stamp `born_open`, `cooldown_release`, entry labels/quality, or other
source attributes. Each evaluation owns fresh source objects. The materialized
report is detached from Plan lists and later consumer mutations, and repeated
evaluations do not share Plan state. The report itself remains a mutable dict,
as before; its stored hashes describe the original materialized report, not any
caller edits. No Plan is inserted into report content or hash inputs.

This is an in-process private interface, not a serializable capability,
authentication guarantee, persistence format, or public training feature.

## Verification and remaining scope

`tests/tree_replay/test_reversal_handoff.py` exercises real synthetic
FrameSpec/calendar/correction inputs through the real map, detector, selector,
and pricer. Its single-call spy retains the actual source return pair. The
accepted M5 fixture has close 101, entry 100, stop 93, and ordered targets
112/125/150; tests also retain the newer refused M15, inject late serialization
failures, and check unchanged public hashes and validation.

The direct `TrackerAdmission.record` integration uses the actual retained Plan
with **controlled test-only ports**: detached in-memory state, explicit decision
time T, supplied synthetic matrix readings, and a known empty quote payload.
Close 101 is inside the original [98, 102] entry zone. With that empty quote
payload the original tracker sets `born_open=True` and advisory state `OPEN`,
marked `born_open_not_broker_verified`; the pre-admission report remains unchanged.
This direct consumer test does not implement or certify outer gates, live quotes,
causal providers, or economic fills. Evaluation itself does not record, save,
notify, or admit anything, including a retained refused Plan.

Actual causal matrix/swing FrameSpec/correction providers, coverage-checked
state/quotes/raw-log prefixes, heterogeneous watch memory and deletions,
branch-specific caller ordering/publication, lifecycle, other producers,
simulation, dataset creation, and models remain follow-on work. As clarified
in [the source intake](MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md), LOOKBACK requests
depth and does not prove delivered days; original TV/MT5 paths return the full
file, and matrix `read_tf` has neither the producer's unverified veto nor its
closed-target filter. Controlled test ports here certify none of those provider
semantics. All seven tracker final-review boundary requirements remain in force.

Public `tradeable`, `ready_for_replay`, and `ready_for_training` remain false.
Independent parent verification, task review, and final component acceptance
must precede use for actual causal binding.

Component acceptance is now recorded in
`agent-exchange/status/2026-09-09T134259Z-codex-reversal-handoff.md`.
Task and final reviews are clean. Parent208combined tests and24focused tests
passed (overlapping counts). This closes the handoff, not the remaining providers.

```text
python -m pytest tests/tree_replay/test_reversal_handoff.py tests/tree_replay/test_reversal_producer.py tests/tree_replay/test_tracker_admission.py -q --tb=short
```
