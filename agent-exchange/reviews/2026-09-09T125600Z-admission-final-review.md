# Agent Exchange Review

Reviewer:
Codex final component reviewer; Superpowers 6.3.0 requesting-code-review/code-reviewer.md; no nested agents.

Target request:
agent-exchange/inbox/codex/2026-09-09T125600Z-admission-final-review.md

Created at:
2026-09-09

Status:
REVIEW_READY_FOR_CODEX

Verdict:

- Spec alignment: PASS WITH MINOR EXCEPTION for the complete admission-dependencies component. The identity-validation edge case below weakens the accepted-journal serialization guarantee; no material source-fidelity, causal-selection or scope deviation was found.
- Quality/integration: APPROVED WITH NON-BLOCKING MINORS. No Critical or Important findings. Both tasks provide suitable dependencies for the next binding implementation, subject to the explicitly outstanding inputs and gates below.
- Ready for parent component acceptance: YES, with the two Minors recorded. This is a review recommendation, not an acceptance action, merge, full admission certification, or replay/training/live readiness.

Findings:

### Strengths and complete-component alignment

- The complete package contains all 15 planned runtime, audit, manifest, CLI, test and usage deliverables. Task1 and Task2 share no new mutable runtime state. All 15 working-tree files match the supplied full new-file hunks after CRLF normalization; the four full artifact hashes in status125300Z also match.
- Exact chart-desk and trading-floor commits, source blobs, ordered definitions, imports and inherited dependencies have independent fixed authority in `trading_system/tree_spec/admission_source.py:18`. The manifest cannot narrow that authority. `_project` checks the original fetch statements and retains the entire TFView constructor, with only declared frame/ATR/clock specializations (`:255`). `_git` uses local rev-parse; source and vendor checking parse text rather than importing or executing the retained desks (`:318`, `:333`). Shared TR, unseeded ATR and seeded EMA dependencies are included in complete-module comparisons.
- Matrix/toolkit/quality/swing code preserves the source behavior, including separate seeded and unseeded ATR, UTC-day VWAP, its NaN anomaly, source tool order and three-right-bar swing confirmation. The required-aware clock functions retain source reasons and Jerusalem boundaries. Golden calculation, DST/boundary, swing, mutation and fresh-process no-source-I/O tests cover these contracts (`tests/tree_replay/test_admission_calculations.py:42`, `:85`, `:168`, `:179`; `tests/tree_spec/test_admission_source.py:38`, `:122`, `:153`). Source quirks are not silently converted to new policies or probabilities.
- Frozen events own canonical JSON text, journals reject corrupt append order, and coverage is explicitly bounded (`trading_system/tree_replay/state.py:92`, `:121`). Publication cutoff reduction cannot backdate a later revision; observation is already constrained to publication time. Unavailable state remains null, an explicit complete empty interval remains distinct, and malformed source rows such as a missing state remain visible (`:170`). PENDING is retained without being turned into OPEN.
- Available snapshot hashes exclude future events and coverage extensions; checkpoints separately cover the whole journal. Restore validates canonical timestamps, structure and constructors even after a checksum is recomputed (`trading_system/tree_replay/state.py:206`, `:224`, `:238`). Tests cover detached nested output, delayed revisions, equal-time ordering, resumed append, forged timestamps and recomputed-checksum corruption (`tests/tree_replay/test_state.py:47`, `:100`, `:142`, `:190`, `:245`). This proves evidence-store properties, not source-generated lifecycle transitions.
- Original memory findings I1/I2/M3 remain ADDRESSED in the combined code: exact integer-to-Decimal boundary construction, rejection of precision-changing epoch normalization, and a rejection-stream regression that reaches timestamp validation with valid identity (`trading_system/tree_replay/state.py:67`, `:77`; `tests/tree_replay/test_state.py:142`, `:278`, `:288`, `:293`). The deliberate rejection of unrepresentable epochs is documented and preserves the agreed microsecond contract.
- Public memory readiness/tradeability stays false (`trading_system/tree_replay/state.py:187`); source audit readiness stays false (`trading_system/tree_spec/admission_source.py:395`). Private quality evaluation only annotates supplied evidence. No gate orchestration, lifecycle simulator, labels, economic state, instrument alias, source execution or live behavior change is introduced.

### Critical

None found.

### Important

None found.

### Minor

1. Deferred test-root portability: retain as NON-BLOCKING, address before another runner/CI.
   `tests/tree_spec/test_admission_source.py:14` hardcodes the supplied user's temporary retained-source root. Relocation requires editing test code even though the runtime auditor and CLI already accept an explicit root. Provide an explicit test option or environment setting and a clear missing-prerequisite failure; do not silently skip parity checks. This does not block the reviewed local component because the specified root and matching verification evidence are available.

2. Identity validation accepts non-UTF-8 strings that cannot be serialized.
   `trading_system/tree_replay/state.py:24` validates identity type, trimming and nonemptiness, but not UTF-8 encoding. A lone surrogate such as `"\ud800"` in `event_id`, tracker `key`, or `journal_id` passes MemoryEvent/MemoryJournal construction. Both `memory_asof` and `checkpoint_memory` subsequently raise `ValueError: memory must contain finite UTF-8 JSON values` through `_json_text` (`:29`, `:203`, `:215`). Thus an accepted journal can be unusable for snapshots/checkpoints, unlike the promised ingestion/serialization invariant. Validate identity UTF-8 encoding in `_identity` and add focused negative cases plus a valid non-ASCII identity round-trip. Severity is Minor: this requires malformed text, fails closed, and does not leak future evidence, falsely admit a candidate, or corrupt stored state. The new in-memory reproduction below confirmed all three fields; no runtime fix was made.

Open questions:

- No unresolved domain choice blocks acceptance of this dependency component. Original Task1 worker RED history remains unavailable; neither passing tests nor this review establishes test-before-code history. This process limitation is acknowledged in the report and usage documentation.
- The components can support the next binding but are not sufficient alone to claim it is complete. `read_frame` accepts caller-supplied frames without publication/timeframe validation (`docs/architecture/ADMISSION-CALCULATIONS-USAGE.md:13`). The binding must obtain causal frames at actual T, retain availability/anomaly provenance, apply the pinned gate order and preserve source refusal/error distinctions.
- Semantic rejection rows cannot reproduce the original full-log byte tail. Non-rejection bytes and line boundaries influence source selection (`docs/architecture/MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md:134`). Full historical log-prefix evidence or an explicitly named alternative policy is still required before selector parity is claimed. Quality `evaluate` itself supplies neither freshness selection nor a veto.
- Tracker/episode rows are supplied advisory evidence, not lifecycle transitions generated from prices. Actual OPEN/PENDING, post-stop, same-level, episode, record-time dedupe and publication-mode binding remain open; fixed-TP1 economic exits must not be substituted. Source calculation success and AVAILABLE memory are not admission evidence.
- Older pending-review prose in the usage opening, implementation plan and master/tracker predates the accepted task statuses125400Z/125500Z. The ledger and latest exchange statuses resolve the current task state. Parent should synchronize those current-status summaries during acceptance while preserving historical reports; no readiness overclaim was found.

Recommended next action:

Parent may record component acceptance with these Minors and proceed to a scoped contract for actual source gate/record binding, retaining explicit causal frame and full-log evidence prerequisites. Keep full outer admission, other producers/arbitration, source lifecycle replay, economic simulation, data coverage, dataset/model and live approvals outstanding. No runtime revision is required by a Critical/Important finding from this review.

Verification reviewed:

- Read the target request first; completed AGENTS.md, exchange README/protocol and Codex inbox inspection. Read the full component contract, plan, ledger, both task reports, Task1 review125100Z, original/fix memory reviews125000Z/125200Z, and progress/acceptances125300Z/125400Z/125500Z. Consulted the current master design, economic decision, implementation tracker and named admission source intake for scope and binding risks. No other plan scratch or nested agents.
- Read all 2,547 lines of the combined diff in bounded sequential chunks. Inspected git status and diff summary. A read-only PowerShell comparison reconstructed every new-file hunk and checked all 15 against disk with CRLF normalization: PASS. `git hash-object trading_system/tree_replay/state.py tests/tree_replay/test_state.py trading_system/tree_spec/admission_source.py configs/trees/admission-source-contracts.json`: all four identities match125300Z.
- Named unchanged-dependency checks only: inspected `bars.py:35` and its imports for exact timestamp normalization and hidden I/O; inspected the package initializers and `_vendor/tr.py`, `_vendor/indicators.py`, `_vendor/atr.py` for inherited calculation closure and seeded/unseeded ATR binding. No earlier component was re-audited wholesale; no retained live source was executed.
- Reported PASS, not rerun: `python -m pytest tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py -q --tb=short` — 93 passed in 21.01s on controller recovery;125500Z also records a passing intake rerun.
- Reported PASS, not rerun: `python -m pytest tests/tree_replay/test_state.py -q --tb=short` — 93 passed in 0.83s at Task2 intake125400Z.
- Reported PASS, not rerun: `python tools/check_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149` — exit0, source_subset_verified true, empty blockers, both readiness flags false.
- Exact expanded integration command in125300Z: `python -m pytest tests/tree_replay/test_state.py tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py tests/tree_replay/test_reversal_producer.py tests/tree_replay/test_bars.py tests/tree_replay/test_session_bars.py tests/tree_replay/test_frames.py tests/tree_replay/test_corrections.py -q --tb=short` — controller-reported 670 passed in25.77s, pristine. This resolves the task reviewers' missing combined-command attachment. Counts overlap; no full-repository or gate-binding test claim is inferred.
- Ran only the following new focused reproduction, because static inspection raised the identity serialization doubt. Exit0; all three construction paths were accepted and both subsequent operations failed with the stated UTF-8 ValueError. No suite was rerun, no test files were created, and `-B` disabled bytecode writes.

```powershell
@'
from datetime import datetime, timezone
from trading_system.tree_replay.state import MemoryEvent, MemoryJournal, memory_asof, checkpoint_memory

t = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
for field in ('event_id', 'key', 'journal_id'):
    event_args = dict(event_id='e1', sequence=1, stream='tracker', key='trade1', observed_at=t, available_at=t, payload_json='{}')
    journal_args = dict(journal_id='j1', origin='supplied_source_advisory', start_at=t, covered_through=t, complete=True)
    (journal_args if field == 'journal_id' else event_args)[field] = '\ud800'
    event = MemoryEvent(**event_args)
    journal = MemoryJournal(events=(event,), **journal_args)
    failures = []
    for name, operation in (('snapshot', lambda: memory_asof(journal, t)), ('checkpoint', lambda: checkpoint_memory(journal))):
        try:
            operation()
        except ValueError as exc:
            failures.append(name + ': ' + str(exc))
    assert len(failures) == 2, (field, failures)
    print(field + ': construction accepted; ' + '; '.join(failures))
'@ | python -B -
```

This requested review artifact is the only write. No acceptance/status, inbox, runtime, test, master, plan, index, branch or commit changes were made by this reviewer.
