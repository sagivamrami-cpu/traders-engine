# Causal tracker storage

Use `TrackerStateSeed` and `CausalTrackerStorage` from
`trading_system.tree_replay.tracker_storage`. This binds original tracker
load/save to an in-memory artifact, not live open_trades.json or broker state.

```python
seed = TrackerStateSeed(
    seed_id="approved-input-state", source="supplied-source-artifact",
    observed_at=observed, available_at=published, covered_through=coverage_end,
    status="PRESENT", text=original_ordered_json,
)
store = CausalTrackerStorage(seed=seed, decision_time=decision_time)
rows = store.load()
# Original tracker calculations may update rows before the original save:
store.save(rows)
next_seed = store.snapshot()
```

The names in the example describe inputs, not automatic approval. `source` and
coverage are caller attestations. Coverage asserts no unrepresented external
state changes between observation and covered_through. At T use only a published,
covered artifact. The full replay will own authoritative source-generated
changes and must establish this coverage, not repeatedly load a final live file.

## Input semantics

- PRESENT: exact UTF-8 text, including malformed JSON. JSON parsing is deferred
  until the original read; source root ordering is retained.
- ABSENT: explicit evidence the source file did not exist; no text. load returns{}.
- UNREADABLE: known existing artifact with read error; no text. load raises;
  ordinary save quarantines and refuses; explicit allow_shrink can replace it.
- UNKNOWN: no reliable state evidence; no text. All reads/saves/handoffs blocked.

Times must be aware/microsecond-exact; observed<=available<=covered. Before
publication or after coverage, even allow_shrink=True is unavailable. A missing
history is never treated as an empty desk. Identity/text are UTF-8 checked.
Supplied raw payload timestamps and malformed values are not silently rewritten.

## Source storage behavior

`load()` returns freshly parsed JSON: modifying a returned dictionary has no
effect until save. `save(d, allow_shrink=False)` preserves original unsorted
ensure_ascii=False/indent1 serialization and rereads current state, not an old
load. It rejects unreadable/null current state or losing more than half the keys
when at least four existed. Exactly half may be removed. Smaller dictionaries
follow the source rule. This is fidelity, not a new recommended safety policy.
The first creation from an absent artifact has no original creation audit.

Rejected writes become separate in-memory open_trades.rejected-<integer epoch>
artifacts before the original RuntimeError. Same-second refusals replace that
same quarantine name. Main content stays unchanged. Successful writes replace
the text as one local operation. No runtime filesystem, network or wall clock.
Source live-test guard is retained through an explicit port; concrete in-memory
backend cannot target a real file. Source JSON quirks are retained, not promoted
to acceptable training values. The later dataset allowlist remains mandatory.

`creation_effects` is a detached, explicitly replay_creation_effect list. It
keeps original new-key extraction/serialization failure boundaries and timestamp,
but does not invent historical PID, argv or stack. These are not byte-identical
trade_creations.jsonl records. Per-set iteration ordering is not deterministic.
`quarantine_artifacts` and `trace` are detached snapshots as well. Trace retains
ordered load/save/port attempts and failures even when TrackerAdmission catches
the exception. Do not mutate private backend attributes to create evidence.
Each attempted creation effect has its own trace entry. A BLOCKED creation_effect
retains its exception even when the enclosing best-effort audit and state save
succeed; AVAILABLE on a parent operation does not mean every child effect succeeded.

`snapshot()` returns current text/status observed and available at this fixed T,
retaining coverage and provenance. Another instance can consume it at a later
covered T; old instances are unaffected. This is one artifact handoff, NOT a
complete loop checkpoint. Quarantines/effects/traces, lock state, clock, pending
orders, watch state, logs, feed cursors and lifecycle need full-run ownership.

## Verification and limits

```text
python -m pytest tests/tree_replay/test_tracker_storage.py tests/tree_spec/test_tracker_storage_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_admission_frames.py tests/tree_replay/test_state.py -q --tb=short
python tools/check_tracker_storage_source_parity.py --source-root <retained-source-parent>
```

Tests can set TR_TREE_SOURCE_ROOT for the retained source parent; no audit is
silently skipped if unavailable. The auditor pins actual repo/commit/blob and
checks the entire projected load/save module with exact enumerated substitutions.
It never executes the retained source. Changed thresholds, removed reread/audit,
sorted serialization, altered initialization or extra imports fail its checks.
The AST audit covers private load/save, not the new in-memory backend, simulated
forensic effects or actual OS atomicity; those have separate behavioral tests.

Real tracker record/exposure and first same-level selection use this store in
tests. Other matrix/quote/lock ports are controlled fixtures there. This does
not certify lock timeout/fail-open/reentrancy, multiwriter races, real I/O fault
recovery, full watch ordering, quotes/raw logs, lifecycle or economic execution.
No labels/dataset/model/live readiness. See latest exchange review/acceptance.

Component accepted after task/fix/full reviews without outstanding findings:
agent-exchange/status/2026-09-09T160544Z-codex-tracker-storage.md.
Current planned309tests and sourceaudit2passed. Supplemental broad2280 run
started before the tracing fix and is not clean post-fix certification.
