# Agent Exchange Review

Reviewer: Codex final combined component reviewer

Target request: `agent-exchange/inbox/codex/2026-09-09T121800Z-reversal-producer-final-review.md`

Created at: 2026-09-09T12:18:11Z

Status: REVIEW_READY_FOR_CODEX

Verdict: **Spec compliance PASS. Component quality APPROVED.** The combined three-task reversal-producer component is ready for controller acceptance. No Critical or Important findings; M1 is closed. This is not full-model acceptance or authorization to merge, deploy, promote, trade, obtain data, or generate labels.

## Scope and strengths

Reviewed the assigned plan and its Global Constraints, source contract, entire final package (3,206 lines, read in bounded contiguous chunks), verification record, ledger, Task3 report/follow-up and relevant acceptance/review records. The review concerns actual uncommitted beforeimage/new-file deltas at HEAD `c1b6071633c55376c64f0a98ece843706f420f49`, not an empty HEAD-to-HEAD comparison. Applied the requested requesting-code-review/code-reviewer guidance directly, without agents.

- **Clock interaction:** `trading_system/tree_replay/periods.py:73`, `trading_system/tree_replay/frames.py:170`, `trading_system/tree_replay/frames.py:237` and `trading_system/tree_replay/levelmap.py:174` floor only price observation. Publication, frame freshness, calendar coverage and current-period ownership retain actual T. The producer binds both map and frames to prefix mode at T (`trading_system/tree_replay/reversal_producer.py:86`, `:107`). Candidate and pricing observations are T while original confirmation/vector times survive (`:141`, `:237`). No map backdating or publication rewriting was introduced.
- **Default compatibility:** `trading_system/tree_replay/reversal.py:46` adds only the optional observation argument; omission still uses confirmation time at line 74. Prefix versions/fields are conditional and default validation paths remain intact. `tests/tree_replay/test_closed_prefix.py:120` and `:136` cover explicit-False equivalence and captured prechange hashes. `tests/tree_replay/test_reversal_producer.py:486` preserves the old `LEVELS_AFTER_CONFIRMATION` guard and original feature observation.
- **Source graph fidelity and selection:** `trading_system/tree_replay/_vendor/reversal_producer.py:8` retains map/daily gates, ordered M5/M15 requests, fetch continuation, 370-second bounds, newest/M5-tie selection and selected-only pricing. `conflicts` at line 35 remains the limited source predicate. `tools/check_reversal_producer_source_parity.py:71`, `:125` and `:152` check transformation preconditions, the complete ordered module, independent source/baseline identity, the sealed map manifest and inherited full graph audit. Runtime wrappers are appropriately tested separately from formula parity.
- **Winner/refusal preservation:** `trading_system/tree_replay/reversal_producer.py:218` delegates the choice to original find; lines 229 onward serialize that choice without ranking plans again. Real-map tests at `tests/tree_replay/test_reversal_producer.py:72` and `:322` establish M5 ties and a newer refused M15 winner despite a paying older M5 event. Inspected inherited `trading_system/tree_replay/_vendor/reversal_pricing.py:10`: pricing retains its original event-time history filter.
- **Availability and errors:** `trading_system/tree_replay/reversal_producer.py:110` distinguishes correction gates, volume unavailability and zero-row warmup. Unexpected post-fetch failures are retained before source catch-and-continue can hide them. Lines 221–249 prioritize calculation errors and required-map blocks, while ordinary missing timeframe input can coexist with another selected event. Inspected `trading_system/tree_replay/levelmap.py:79` and `:189` to confirm optional-map calculation errors survive source catches into the public report.
- **Evidence and boundaries:** `trading_system/tree_replay/reversal_producer.py:56`, `:141`, `:179` and `:252` provide upfront exact identity checks, separate episode/candidate/decision identities, deterministic evidence and false public readiness. Selected payloads are detached. Real closed-history PVSRA matches detector input; original source plan serialization preserves refusal and pricing evidence. Future prices/corrections and unused fallback payloads are covered by invariance tests. The five missing stages remain explicit. Controller documentation describes outer admission intake as dependency mapping only.

## Findings and ledger triage

### Critical

None.

### Important

None.

### Minor

No unresolved component defect found.

**M1 — CLOSED:** `tests/tree_replay/test_reversal_producer.py:446` now establishes success with valid daily plus optional 4h input, changes only optional base volumes, and asserts daily `AVAILABLE`/correction `ASSESSED`, the exact `4h/240` blocked fetch, and matching map/public `stage=fetch`, `exception_type=ValueError` diagnostics. It also requires no public selection or producer fetch. The separate daily-overflow test at line 472 requires `SOURCE_CALCULATION_ERROR` and `stage=build`/`FloatingPointError`. A required-daily failure can no longer satisfy the optional-error case. This closes the coverage finding without implying a runtime fix.

**Task2 packaging qualification — RETAINED, nonblocking:** `agent-exchange/status/2026-09-09T115800Z-codex-reversal-producer-source.md:27` and `.superpowers/sdd/2026-09-09-reversal-producer-asof/final-verification.md:59` correctly distinguish LF/CRLF advisories and new-file diff exit 1 from clean zero-exit whitespace evidence. The final package contains such advisories. They are not runtime or pytest failures; ordinary tracked `git diff --check` also does not certify untracked files. No cleanup or stronger whitespace claim is warranted.

## Verification reviewed

Parent-recorded PASS results, not rerun by this reviewer:

| Command | Recorded result |
| --- | --- |
| `python -m pytest tests/tree_replay/test_closed_prefix.py tests/tree_replay/test_periods.py tests/tree_replay/test_frames.py tests/tree_replay/test_levelmap.py -q --tb=short` | 213 passed, exit 0; separate prefix run 62 passed |
| `python -m pytest tests/tree_replay/test_reversal_producer_source.py -q --tb=short` | 105 passed, exit 0 |
| `python -m pytest tests/tree_replay/test_reversal_producer.py tests/tree_replay/test_reversal.py tests/tree_replay/test_pricing.py -q --tb=short` | 200 passed, exit 0; 77 producer plus 123 compatibility |
| `python -m pytest tests/tree_replay tests/tree_spec tests/data_foundation/test_sessions.py -q --tb=short` | 1,841 passed, exit 0; prior 77-case producer collection |
| `python -m pytest -q --ignore-glob='*validator*' --tb=short` | 2,213 passed, exit 0; prior 77-case collection; legacy validators explicitly excluded |
| `python -m pytest tests/tree_replay/test_reversal_producer.py -q --tb=short` | Latest 78 passed in 5.19s, exit 0, after test-only M1 clarification |

All seven recorded source commands passed with exit 0, empty blockers, true source-subset verification and false replay/training readiness. Each used `--source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`:

```text
python tools/check_ema_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
python tools/check_reversal_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
python tools/check_pricing_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
python tools/check_range_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
python tools/check_correction_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
python tools/check_levelmap_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
python tools/check_reversal_producer_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
```

Counts overlap and are not cumulative. The broad/integration totals do not include the new split test; the separate 78-case run supplies that evidence on unchanged runtime. No validator pass is claimed.

Independently inspected `git status --short` and ran read-only `git hash-object` for all eight runtime/audit/manifest paths listed in final-verification.md plus the latest producer test. Every blob matched the recorded fingerprint, including producer `1ab7add9928097ced8c4a27916d6459ac2142e7d`, helper `0846218eedc8d4c83458f75e653e9a46c9dd0889` and tests `c7ed22a041202e1cfaa9d6c710ec158d4671977b`. Historical beforeimage capture and test executions remain controller evidence. No concrete unresolved risk required another runtime check. No diff regeneration, suite/audit rerun, other-plan scratch read, code edit or agent dispatch occurred.

## Open questions and recommended next action

No blocking component question remains. Record durable combined component acceptance and synchronize the controller-owned plan/tracker status after intake of this report. Their pending final-review/task wording is not evidence that the full master is complete.

Full master B–I remains open: outer market-watch admission, tracker/episode state, cross-producer arbitration, other producer/feature paths, execution/outcomes, data coverage, dataset/model/evaluation work and human gates. Supplied calendar/provenance evidence is not real-data certification; open-only/partial-base observations and GC/spot equivalence remain unsupported. Merge, production readiness and full-model acceptance are outside this verdict.

Only this assigned report was written, via apply_patch.
