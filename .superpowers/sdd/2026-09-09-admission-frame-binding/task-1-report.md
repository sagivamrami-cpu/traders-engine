# Admission frame Task1 implementation report

Status: DONE / awaiting independent task and final review.
Request: agent-exchange/inbox/codex/2026-09-09T134600Z-admission-frame-binding.md
Brief: task-1-brief.md in this plan's scratch.
Spec: docs/architecture/ADMISSION-FRAME-BINDING-CONTRACT.md
Implementer: Codex controller inline, after explicit canceled agent shutdown.

## Implementation

Three new files only: trading_system/tree_replay/admission_frames.py,
tests/tree_replay/test_admission_frames.py,
docs/architecture/ADMISSION-FRAME-BINDING-USAGE.md. No prior runtime/vendor edits.
Frozen exact requests validate six source keys and correction association.
Constructor validates all bindings and exact producer instrument at actualT.
Source subclasses accepted _OfflineSource with closed_base_prefix=True, adding
traced rejection of foreign/unsupported calls and ordered original read_tf logic.
No source formula duplication or score inputs, no history trim/min-day/backfill,
no new correction veto/target filter. Source catches cannot erase matrix_trace.

## TDD and verification

- Existing5file baseline before implementation:395passed401.11s, exit0. Tool
  response delayed; same process39965 observed terminal, never restarted.
- New test file first, runtime absent:
  `python -m pytest tests/tree_replay/test_admission_frames.py -q --tb=short`
  RED39failed2.62s, exit1. Tests collected; all hit in-test lookup assertion
  "causal admission frame provider missing". Output was truncated by display
  budget but head/tail and summary observed; not a collection error.
- Before runtime, refined forming fixture's explicit correction-age policy
  to3600seconds to cover its301second delayed-publication scenario, instead of
  inadvertently testing60second correction staleness. No source rule changed.
- Added runtime after RED. Same focused command GREEN39passed2.85s, exit0.
- Added a combined actual producer Plan->real provider->tracker record test as
  integration strengthening after initial GREEN; it was not part of39RED.
  Focused command then40passed7.12s, exit0, process95362 observed terminal.
- Planned6file default pytest command from usage/brief:
  PASS435 in16.10s, exit0, process19154 observed terminal. Includes40new cases;
  counts overlap baseline/focused, not additive new coverage.
- `python tools/check_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`
  PASS, VERIFIED, no blockers,10inherited projections, readinessfalse. No source
  claim inferred solely from new tests; thin read_tf call order compared with
  inert original matrix.read_tf/read_symbol previously read at173/188.
- Tracked `git diff --check` and explicit new runtime/test no-index whitespace
  checks reported only LF/CRLF advisories, no whitespace defects.

Runtime SHA2568fd5b1bb6a2da0d01c758f17d880eb86aae6b78373c5c4df54de34516774952f.
Test SHA25697ac5ba6856b74a838210b73bc34643c20bdf36c509c690a0b66be23b303cfb7.

## Test evidence and scope

Before implementation the audited source was characterized on120constant rows:
OHLC100/102/98/100 volume1 yieldsATR4/net-41.25 with TR(0,20),supertrend(-1,90),
VWAP(-1,100),structure(0,0). New tests use these literal readings and rising data
with close219/positive net, plus distinct15m55vs15m5 prices. They do not calculate
expected nets by calling the same helper under test or insert score stubs.
Typed historical frames, publication/correction/calendar gaps, actual forming
targets, future exclusion, ordered aborts, detached outputs and native identities
are covered. Real tracker post-stop uses4h240/1h240 then15m5, and a controlled
matrix failure remains recorded despite _higher_bias returningNone.

Additional actual selected Plan integration uses the existing real synthetic
producer and this provider at producerT. Original geometry100/93/TP1=112 is
stored with actual computed bias-41.25 and broken long thesis, advisoryOPEN and
revalidation_verifiedFalse, unchanged report. State/quote inputs are controlled;
matrix seeds and producer fixture are independently supplied, not a claimed
single coherent historical tape. Full-data lineage/coverage remains mandatory.

## Self-review, recovery ruling and limits

Self-read all new runtime/test and usage; inspected original matrix methods,
_OfflineSource and tracker consumers. No source logic change or unrelated file
mutation. The assigned agent authored nothing and was explicitly terminated;
shutdown confirmed before inline work. Cause of agent stall unknown.
Ruling: inline recovery under the same spec, with independent reviews retained;
cost is controller implementation context and separate review. No domain ruling.
No source new-input-state/quote/log providers, full caller/lifecycle, economic
execution, labels, dataset or training implemented. Full master remains active.
No live/data/network/broker/deployment actions, commits/pushes or cleanup.

## Task-review M1 refinement and fresh verification (15:46 UTC)

Independent task review153900Z passed spec/quality with only Minor M1: the
original no-trim cases used history shorter than each requested lookback.
Added test_history_older_than_requested_days_is_not_trimmed with600 M15 bars
for15m/5: all600 rows and earliest2026-09-03T10:00Z must survive. This is a
post-GREEN test-only refinement, not part of original39-case RED. Runtime unchanged.
The prior tool output was lost to truncation; no result inferred from that call.
Fresh current-state verification after confirming no Python process remained:
- Planned full6file pytest:436passed4.63s, exit0 (41component cases).
- In-memory unittest.mock.patch of _OfflineSource.fetch_corrected to trim rows
  to T-days caused this exact regression assertion to fail: mutation DETECTED,
  exit0 diagnostic. No runtime file edited. This demonstrates M1 catches its
  named break, not a claim that the unmodified implementation was faulty.
- Source parity CLI with same retained root:VERIFIED10/no blockers/readinessfalse.
- Tracked git diff --check: no whitespace defects; LF/CRLF advisories only.
These runs are main-implementer verification, not an independent agent rerun.
Separate complete-component review remains required; master goal remains active.
