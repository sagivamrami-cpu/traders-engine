# Final acceptance review — closed-bar causal replay vertical slice

**Verdict:** ACCEPTED

**Critical findings:** 0  
**Important findings:** 0

## Scope and method

Read-only final review of Tasks 1–5 against the approved design, implementation
plan, SDD progress record, Task 4 independent rejection and binding-fix
re-review, and the public usage contract. Reviewed the current contracts,
checkpoint/provider baseline, runner, admission-context schedule view,
parse-only source auditor/CLI, and the relevant replay/source/dependency test
suites.

No implementation, test, retained source, branch, commit, push, or subagent was
used. The only retained-source interaction was the prescribed static auditor:
it reads and AST-parses the pinned `chart-desk/scripts/market_watch.py` text and
uses local `git rev-parse` to check its explicit commit/blob pins. It neither
imports, compiles, nor executes retained source.

## Findings

### Critical

None.

### Important

None.

### Informational verification evidence

1. **Immutable, ordered supplied evidence and precision/field boundaries**
   - `ReplayEvidenceBundle` requires exact tuples, unique IDs, strict
     `(available_at, sequence)` event order and strictly increasing anchors
     (`causal_replay_contracts.py`, `ReplayEvidenceBundle.__post_init__`).
   - `ReplayEvent` canonicalizes/detaches its JSON payload, requires its declared
     availability to equal the event availability, rejects timestamps beyond
     microsecond precision, validates exact all-or-nothing evidence bindings,
     and rejects recursive `net_pnl`, `net_R`, `success`, and `failure` fields.
   - `ReplayPassRecord` applies the same forbidden-field policy to candidates
     and diagnostics; its evidence diagnostic is canonical and reconstructs
     only immutable `ReplayEventCommitment` objects. The ledger is append-only
     and hash-chained.

2. **Static-only source audit**
   - `causal_replay_source.py` contains an AST/text audit only. It pins commit
     `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and blob
     `f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b`, checks the complete projected
     outer ordering, and proves the six outer gates retain their rejecting
     control paths before record.
   - The auditor and CLI expose `ready_for_replay=False` and
     `ready_for_training=False` in both verified and blocked reports. The
     runtime does not import this module.

3. **Single monotonic clock and checkpoint/provider baseline**
   - `ClosedBarCausalReplay.__init__` requires the exact same `ReplayClock`
     object for watch and admission providers. `CausalAdmissionContext` uses
     this clock for ordered publication application and its
     `replay_publications_through()` view is read-only.
   - `ReplayProviderBaseline` captures detached initial evidence, and
     checkpoints retain only its fingerprint. Restore validates bundle and
     baseline fingerprints, ledger prefix/hash, clock/anchor chronology,
     provider snapshot, and consumed-schedule suffixes before reconstructing
     providers on the supplied shared clock.

4. **Exact event-to-provider binding before advance and record-covered
   commitments**
   - Before `admission.advance_to()` or any watch/lifecycle/producer operation,
     `_validate_bound_evidence()` requires exactly one required event and proves
     that the event itself is the unique eligible `INTERNAL_REVERSAL_INPUT`
     binding for the pass and exact canonical input digest
     (`causal_replay.py`).
   - Every due admission publication likewise requires one unique eligible
     `ADMISSION_PUBLICATION` binding whose event kind/channel, availability,
     ID, and canonical artifact digest agree. Missing, future, duplicate, or
     substituted evidence blocks the pass before context mutation.
   - `_append()` commits every event eligible at the anchor as an ID/time/
     sequence/full-payload-digest/binding commitment plus the provider-baseline
     fingerprint. Raw payloads are absent from the ledger; the commitment is
     covered by each record digest and the ledger hash chain.
   - This directly addresses the prior Task 4 C1 finding. The fix re-review’s
     required-event/non-required-substitute regressions are present and pass.

5. **Bounded replay behavior and public readiness**
   - Selected internal-reversal reports become detached `OBSERVE_ONLY`
     candidates. The runner has no call to `TrackerAdmission.record`; existing
     supplied tracker state alone flows through `TrackerLifecycleCaller` and
     `LifecycleClosedResolver` via an in-memory-only tape.
   - The runner limits lifecycle evidence to the caller-supplied context rows
     and producer inputs. Unsupported variants, absent/malformed bindings,
     provider failures, and no-candidate reports remain explicit ledger
     outcomes.
   - Reviewed modules contain no network or broker client. The only subprocess
     is the auditor’s local, no-fetch/no-prompt `git rev-parse`; the runner’s
     lifecycle tape is memory-only and its delivery-receipt ports fail closed.
     There is no economic calculation, outcome label, dataset, training, model,
     or live-execution path.

6. **Documentation/API consistency**
   - `CAUSAL-REPLAY-USAGE.md` correctly describes caller-supplied construction,
     explicit baseline capture, `run_until()`/`restore()` arguments, binding
     schema, raw-payload-free commitments, source-audit command, false
     readiness, and exclusions. The examples use exported/current interfaces;
     no `start_at` bundle API is asserted.

## Verification run

The execution host cut off aggregate pytest commands at 30 seconds, so the
prescribed focused files were completed in terminal, disjoint batches rather
than treated as a partial aggregate result:

```text
python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider
60 passed in 3.76s

python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py -q --tb=short -p no:cacheprovider -k 'checkpoint_resume or tampered or wrong_bundle or incompatible or future_schedule_substitution or future_publication_addition'
10 passed, 7 deselected in 12.66s

python -B -m pytest tests/tree_replay/test_causal_replay_checkpoint.py -q --tb=short -p no:cacheprovider -k 'clock_before or backdate or same_clock or submicrosecond'
7 passed, 10 deselected in 9.13s

python -B -m pytest tests/tree_replay/test_causal_replay.py -q --tb=short -p no:cacheprovider
20 passed in 8.26s

python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
38 passed in 13.73s

python -B -m pytest tests/tree_replay/test_admission_context.py -q --tb=short -p no:cacheprovider
58 passed in 12.69s

python -B -m pytest tests/tree_replay/test_lifecycle_closed_resolver.py tests/tree_replay/test_reversal_producer.py -q --tb=short -p no:cacheprovider
85 passed in 16.15s
```

Total terminal focused results: **278 passed**.

```text
python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

Returned JSON `status: "VERIFIED"`, `source_subset_verified: true`, no
blockers, the eight required projections, the pinned chart-desk commit, and
both readiness flags `false`.

## Verified limitations (not findings)

- This is a bounded, supplied-evidence, offline closed-bar spine—not a general
  historical replay or feed-certification system.
- The source-owned outer-admission gates are statically proven but intentionally
  remain unbound in runtime; newly selected plans remain `OBSERVE_ONLY` even
  when activation evidence says enabled. No tracker row is created.
- Only the `level_reversal:5m` internal-reversal path is executable. Other
  variants are explicit `UNSUPPORTED` outcomes.
- Vendor data acquisition/retention, revised/open-only bars, calendar or venue
  synthesis, delivery, broker/fill handling, economics/P&L/costs, labels,
  datasets, training, models, promotion, and live trading remain outside this
  acceptance. Both public readiness flags remain false by design.
