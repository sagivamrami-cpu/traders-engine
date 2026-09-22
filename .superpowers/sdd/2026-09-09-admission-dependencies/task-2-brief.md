## Task 2: Causal source-advisory memory evidence

**Files:** Create `trading_system/tree_replay/state.py`,
`tests/tree_replay/test_state.py`, `docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md`.

**Consumes:** stdlib; existing timestamp helper may be reused after inspecting its
contract. No Task1 runtime dependencies, so local work can proceed alongside Task1.
**Produces:** frozen kw-only `MemoryEvent`, `MemoryJournal`,
`memory_asof(journal, decision_time) -> dict`, `checkpoint_memory(journal) -> dict`,
`restore_memory(checkpoint) -> MemoryJournal`, exact fields/schema in spec.

- [ ] Write failing tests. Representative fixture/assertion:

  ```python
  event = MemoryEvent(event_id='e1', sequence=1, stream='tracker', key='trade1',
      observed_at=t, available_at=t, payload_json='{"state":"PENDING"}')
  journal = MemoryJournal(journal_id='j1', origin='supplied_source_advisory',
      start_at=t, covered_through=t, complete=True, events=(event,))
  result = memory_asof(journal, t)
  assert result['tracker_state']['trade1']['state'] == 'PENDING'
  assert result['replay_ready'] is False
  assert restore_memory(checkpoint_memory(journal)) == journal
  ```

  Cover delayed/future revisions, tied time ordered by sequence, incomplete/empty,
  start/end coverage boundary, missing-state row retention, forged future ts/resolved_ts,
  duplicate IDs/sequences/JSON keys, native type rejection, invalid streams/origin,
  invalid JSON/nonfinite/nested payload, detached output and checkpoint tampering.
- [ ] Run `python -m pytest tests/tree_replay/test_state.py -q --tb=short`; record RED.
- [ ] Implement strict construction/validation and reduction. Decode JSON with
  duplicate-key rejection and finite numbers, normalize with sorted compact JSON.
  Select by actual publication time, never use final-state snapshots for earlier T.
  The hash input is the visible report excluding evaluation_hash itself; checkpoint
  checksum covers schema and entire canonical journal. Restore goes through normal
  constructors and fails on extra/missing fields, bad checksum or schema.
- [ ] Run GREEN, document usage/limitations, independently review and accept.

## Combined acceptance

- [ ] Run both new suites plus producer/frame/correction/state-adjacent suites.
- [ ] Run source CLI and independent combined review of this component's full diff.
- [ ] Record exact counts/commands; update tracker/memory without closing C/E/F.
- [ ] Continue next into original tracker gate closure and real producer binding,
  including rejection-log selection, OPEN vs PENDING, post-stop calculation inputs,
  same-level and episode gates. This plan does not substitute supplied booleans
  for executing those gates or claim lifecycle transitions were reconstructed.
