# Agent Exchange Review

Reviewer: Codex final complete-component reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T132300Z-tracker-admission-final-review.md

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec PASS. Whole-component quality/integration APPROVED for the private tracker admission/recording source closure. No actionable Critical, Important or Minor findings. Ready for controller component acceptance and subsequent scoped causal-binding work; not full-master completion or replay/live readiness.

## Scope and review method

Read the target request first; repository startup instructions and Codex inbox;
the complete source contract, implementation plan, current-plan brief, progress
ledger and implementation report including rename addendum; task review132000Z,
parent intake132100Z and task acceptance132200Z, with their original requests.
Read the additional final section of MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md
following the user's clarification. Its findings constrain subsequent binding;
they do not expand this eight-file component's implementation requirements.

Applied superpowers:requesting-code-review and its code-reviewer.md checklist
directly as the final reviewer, without nested agents. Reviewed the complete
task-1-diff.md in contiguous passes through the closing fence: all eight new
files, 2,247 added lines. BASE/HEAD is
c1b6071633c55376c64f0a98ece843706f420f49; this is an uncommitted new-file package,
not a committed revision range. Inspected git status and the existing tracked
diff without changing either.

Read-only PowerShell comparison confirmed every packaged added line matches
the current eight files after CRLF/LF normalization, including terminal blank
lines. Current SHA256 values for runtime, symbols, auditor, manifest, CLI and
both tests match the worker's snapshots. Current usage documentation matches
the renamed-test package; its initial historical hash predates that correction.
Only this requested review artifact was written, using apply_patch. No source
execution, suite reruns, runtime/test/status/master edits, git mutations or
external actions were performed.

## Strengths and spec assessment

- `trading_system/tree_replay/_vendor/tracker_admission.py:110`: explicit
  per-instance ports preserve method arguments, without a live source import,
  global monkeypatch or default clock/provider. `:115` computes bias, thesis and
  born state before locking; `:163` reloads and rechecks OPEN inside the lock,
  applies geometry dedup/archive, persists complete source rows and propagates
  save failure. The source's archive-suffix collision behavior is preserved.
- `trading_system/tree_replay/_vendor/tracker_admission.py:208`, `:425` and
  `:499`: exposure, post-stop and same-level remain distinct gates with original
  catches, first/latest-row selection and early-return order. PENDING is not
  OPEN exposure. Four-hour expiry precedes matrix/frame work; signed summed
  bias precedes confirmed swing and pip-crossing release. Optional telemetry
  has not been promoted into a new policy veto.
- `trading_system/tree_replay/_vendor/tracker_admission.py:39` and `:299`:
  the reader factory opens inside the original tail catch. Seek/expand/drop,
  malformed-byte handling, equal-time first selection and full-prefix fallback
  remain intact. The lazy interface ruling is implemented, including its
  exception boundary, rather than only described in the ledger.
- `trading_system/tree_replay/_vendor/tracker_admission.py:76`, `:137`, `:260`
  and `:525`: the required original build-band helper closes the dependency
  omitted from earlier pricing; quote validation and one-sided reached tests
  retain source behavior. Higher/lower thesis readings and their deadband are
  retained. Born OPEN remains explicitly broker-unverified at `:186`.
- `trading_system/tree_spec/tracker_admission_source.py:40`, `:150`, `:174`,
  `:209` and `:255`: independent fixed authority covers full ordered adapted
  runtime and inherited projections, exact substitution preconditions,
  imports/constants, source blobs and repository identities. The manifest
  cannot narrow the check. Full pure symbols are preserved, including pip
  resolution at `trading_system/tree_replay/_vendor/tracker_symbols.py:155`.
  The required inherited closure includes pricing/Plan, basis aliases,
  quarters, quality and swing, not merely references to earlier passing audits.
- `configs/trees/tracker-admission-source-contracts.json:1` declares matching
  fixed authority and false readiness. The CLI at
  `tools/check_tracker_admission_source_parity.py:13` requires an explicit root
  and returns failure for blocked evidence. Runtime does not claim to run this
  audit automatically.
- `tests/tree_replay/test_tracker_admission.py:112`, `:163`, `:171`, `:181`,
  `:200`, `:267`, `:327`, `:354` and `:483` exercise stored rows, lock-time
  state changes, save failure, signed boundaries, actual swings, raw-log
  selection, bounded reads and hidden-I/O attempts. Source tests at
  `tests/tree_spec/test_tracker_admission_source.py:22`, `:50`, `:66` and `:106`
  require source evidence and reject body/port/order/dependency/manifest and
  substitution-precondition mutations. Distinct test basenames implement the
  ledger's collection fix without changing global pytest configuration.
- `docs/architecture/TRACKER-ADMISSION-SOURCE-USAGE.md:27`, `:36`, `:104` and
  `:132` document caller responsibilities, exact ports, swallowed-error limits
  and unfinished binding. The component makes no new feed-alias, economic,
  policy or training claim.

## Whole-component integration assessment

Named cross-component risk: compatibility with the actual Plan and matrix
interfaces, without mistaking the synthetic probe for producer integration.
Inspected unchanged `pricing.Plan` fields at
`trading_system/tree_replay/_vendor/pricing.py:148` and TFView/read_frame at
`trading_system/tree_replay/_vendor/admission_matrix.py:116` and `:146`.
They provide the geometry/mutable annotations and net/bar_ts consumed here.
Inspected the small inherited basis/swing implementations for symbol identity
and confirmed-swing semantics. Broader unchanged source audits were not repeated;
their evidence and scope are reconciled in task acceptance132200Z.

Named cross-component risk: treating serialized producer evidence as a complete
recordable Plan. `trading_system/tree_replay/pricing.py:24` serializes selected
pricing evidence, and `trading_system/tree_replay/reversal_producer.py:230`
returns it in the public unadmitted result. That payload is not a Plan object
and does not serialize every input used by record, notably build close and
kind. Subsequent binding must retain or explicitly reconstruct the original
selected Plan with proven provenance; passing the dictionary directly or
inventing omitted values is not supported. This is an outstanding binding
requirement, not a defect in the scoped generic source-port component.

Named cross-component risk: unavailable or semantic-only memory masquerading
as complete state/log evidence. Inspected `memory_asof` at
`trading_system/tree_replay/state.py:174` and its accepted usage/acceptance.
It returns detached tracker dictionaries only within attested coverage;
unavailable state is null, not empty. Its rejection list is semantic evidence,
not byte-faithful full-log history. Its object-row replacement model does not
implement the full heterogeneous watch state or deletions. The component's
ports leave these responsibilities explicit and do not claim to solve them.

## Findings

Critical: none.

Important: none.

Minor: no actionable component finding. The earlier dependency component's
retained-source test-root portability Minor remains owned by acceptance125556Z;
it is not a new finding here. These new source tests expose TR_TREE_SOURCE_ROOT
and fail on missing required evidence. No deferred Task 1 finding remains.

## Exact outstanding boundary requirements

1. Bind actual source-selected Plan geometry and branch admission at actual T.
   Supply causal frames through the original matrix and swing calculations,
   with exact symbols, lookbacks, seed histories, calendars, publication/price
   cutoffs and correction provenance. A hand-supplied Plan or net/approval
   boolean is not evidence of full producer admission. Preserve refused source
   selections and original lazy dependency order.
2. Bind detached, coverage-checked advisory state and a real offline lock/save
   implementation. Trace every unavailable/error dependency even when a source
   catch returns no block or defaults thesis to held. Do not turn a failed
   memory lookup into an empty dictionary or certify a quiet source catch as
   complete historical evidence. Verify transactional failure and resume
   behavior of the eventual providers separately.
3. Generate or supply the exact full causal raw-log prefix at each reader call:
   include non-rejection events, sessions, original encoding/newlines/JSON
   spacing, failed/blocked/slot/quality events and intra-pass appends. In
   particular, scoring precedes level_reversal_detected logging, while
   post-stop telemetry reads after that append. One frozen tail per pass or a
   reserialized rejection-only journal is insufficient. The source tail cap
   does not prohibit its pathological full-read fallback.
4. Implement full watch state separately from the existing object-only memory
   abstraction: scalar cooldown epochs, object episodes, deletions, stable
   ordering and the original persistence boundaries. Intake
   `docs/architecture/MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md:209` records
   separate watch-state writes at source905/1599 and the tracker lock/save;
   do not collapse them into one alleged atomic source transaction.
5. Preserve branch-specific publication/record/episode/arbitration order from
   that intake: reversal/trend activate arbitration before dedupe and update
   episodes only after publication permits successful record; tree updates its
   cooldown before logging and the Telegram-gated record, so a false record
   can still leave state updated; engine dedupe precedes conflicts/clocks and
   its record is not Telegram-gated. A universal publication_enabled gate
   would change the baseline. Observational brain logs/state effects still
   contribute to full-log reconstruction, without becoming a trade producer.
6. Generate subsequent source lifecycle independently of fixed-stop/full-TP1
   economic execution. OPEN-at-send, sent-quality annotations, tree_trade logs,
   target ladders and successful record are not broker fills or outcome labels.
   Preserve quality/anchor/rejection telemetry as advisory. Other producer
   paths, whole-loop arbitration, simulation, data coverage, dataset/model work
   and explicit costs/time-exit contracts remain outstanding.
7. Preserve exact-instrument/feed boundaries and false public replay/training/
   tradeable readiness. Private symbols resolution does not authorize GC/OANDA
   aliasing, real-data access, promotion, deployment or live trading. Full-master
   completion and controller status/master updates are outside this review.

## Verification reviewed

Parent intake132100Z reports the following exact default-mode command PASS:

```powershell
python -m pytest tests/tree_replay/test_tracker_admission.py tests/tree_spec/test_tracker_admission_source.py tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py tests/tree_replay/test_pricing_source.py tests/tree_replay/test_pricing.py tests/tree_replay/test_state.py -q --tb=short
```

428 passed in36.09s, exit0; worker's identical command passed428 in35.45s.
These are overlapping runs of the same selected suite, not additive coverage
or a full-repository result. Historical RED/GREEN and the resolved basename
collision were reviewed as reported evidence, not independently reproduced.

Parent's exact source command:

```powershell
python tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

Reported PASS, exit0, VERIFIED, seven checked projections, empty blockers,
source_subset_verified true and both readiness flags false. Task
acceptance132200Z explicitly reconciles this unchanged-source evidence.

The parent also reports PASS for a bounded synthetic interoperation diagnostic:
4,800 shared5m bars with an explicit continuous calendar, actual as-of
5m/15m/30m/1h/4h frames at2026-09-07T09:00:00.000001Z, original matrix readings,
memory_asof state and TrackerAdmission.record. It excludes a delayed future
OPEN, preserves PENDING and immutable input memory, creates broker-unverified
advisory OPEN and blocks a subsequent record. This is reported integration
evidence with manually supplied Plan geometry and finite synthetic seed
history, not complete source lookback, producer, causal-port or loop evidence.

No unanswered concrete runtime doubt warranted a new probe or repetition of
these suites. This review's own verification was read-only inspection,
SHA256 comparison and all-eight-file package/current-content equality.

## Recommendations and assessment

Open questions: none blocking this source component. The numbered requirements
above belong to the next binding and remaining master work.

Ready to merge? Yes, for this component's scoped code/spec quality; this is not
a merge action or controller acceptance record. The full eight-file package
implements the prescribed private source closure and integrates with the
accepted dependency interfaces without overstating its historical guarantees.

Recommended next action: controller may record final component acceptance and
route causal-binding work under explicit contracts incorporating the latest
full-watch state and branch-ordering intake. Keep full replay, economic labels,
training and live readiness unaccepted.
