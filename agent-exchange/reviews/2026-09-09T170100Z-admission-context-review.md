# Agent Exchange Review

Reviewer: Codex independent Task2 reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T170100Z-admission-context-review.md

Created at: 2026-09-09

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec PASS; code quality PASS. No actionable Critical, Important, or Minor findings. Ready for Task2 acceptance and the separately required combined final review. This is not whole-loop, historical-data, economic-label, or training acceptance.

## Scope and method

Read AGENTS.md, exchange README/protocol, own inbox listing and the requested review contract. Read the full causal-context contract, Task2 plan, implementation report, progress ledger and usage; Task1 acceptance165135Z was dependency evidence only. Applied superpowers:requesting-code-review and its code-reviewer.md template directly, without nested agents.

Reviewed actual untracked runtime/test/usage files, not an empty HEAD range. HEAD is c1b6071633c55376c64f0a98ece843706f420f49. Inspected git status and tracked diff, preserving existing changes. Read the full Task2 package and compared all added lines with actual files using PowerShell after CRLF/LF normalization: all three match, including terminal blank lines (322 runtime, 362 test, 112 usage lines).

Inspected the accepted frame, storage, quote/log, tracker and lock implementations and relevant source contracts, including the seven subsequent-binding requirements in review132300Z. No source policy changes are introduced by this context. The separate caller/lifecycle source intake remains controller work, outside this review.

Reviewed file SHA256 values:

| File | SHA256 |
| --- | --- |
| trading_system/tree_replay/admission_context.py | D86A897B784FFA20419E1336D7A2F454B50E7275C044202DB65192B842E67DB7 |
| tests/tree_replay/test_admission_context.py | 96C692AD7C0E439FC967A1004E98C72C817700ED201231219C5F55ED5DE22C0A |
| docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md | 6F1737C512DBA505B99FB15E177F76C4973DF13A51A877453B4AE99709AE80F9 |

## Strengths and spec assessment

- `trading_system/tree_replay/admission_context.py:114`: validates the entire publication and lock schedules before running ports, including future frame identities/duplicate requests, exact types, order and unique IDs. Artifact availability must match publication time; no sorting or merging silently repairs supplied evidence.
- `trading_system/tree_replay/admission_context.py:195`: applies complete images at their supplied times in sequence. The shared clock stays independent of artifact coverage, while consumption guards enforce visibility. Generated state survives advances and explicit replacements retain old traces/effects and opened log-reader prefixes.
- `trading_system/tree_replay/admission_context.py:231`: constructs real AdmissionFrameSource instances at operation time. The tracker performs original pre-lock matrix/thesis/quote work and post-lock state reads/timestamps. Tests assert actual matrix values and dependency reads rather than substituted scores.
- `trading_system/tree_replay/admission_context.py:246`: actual lock calls require matching operation, time, timeout and local handle evidence. Matched calls retain step ID/source and apply publications through their supplied completion. Original nesting, writer fallback, resolver skip/stall and finally cleanup remain in the accepted TrackerLock implementation.
- `trading_system/tree_replay/admission_context.py:297`: busy-marker reads/writes/clears retain causal coverage and original best-effort catches. UNKNOWN is distinguishable from known absence or unreadability. No inferred duration, OS lock, or historical descriptor claim is added.
- `trading_system/tree_replay/admission_context.py:308`: reports detach context and child evidence, including child failures swallowed by original source logic. False readiness and omission of unconsumed future payloads prevent the record boolean from being presented as replay or economic certification.
- `docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md:1`: accurately limits this to provider composition and documents complete-image replacement, source fallback behavior, partial save effects and the supplied close-error convention. It leaves caller/watch-state/lifecycle, mixed-time producer binding and economics open.

## Findings

Critical: none.

Important: none.

Minor: none actionable in the three-file Task2 scope.

Missing or mismatched lock evidence can also prevent a subsequent cleanup step from matching; this remains explicitly blocked and traced rather than fabricating historical cleanup. A matched close OSError ends the local handle exactly as the contract declares. Neither behavior is an OS-lock certification.

## Verification reviewed

Independent focused test command, PASS, exit0: **55 passed in 3.97s**.

```powershell
python -B -m pytest tests/tree_replay/test_admission_context.py -q --tb=short -p no:cacheprovider
```

Independent source audit commands, all PASS/exit0/VERIFIED, empty blockers; checked projection counts respectively 7, 2, 4 and 4. Both readiness flags remain false. These audits inspect retained source; they do not execute it.

```powershell
python -B tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
python -B tools/check_tracker_storage_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
python -B tools/check_watch_io_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
python -B tools/check_tracker_lock_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

The implementation report's planned seven-file 362-test runs and earlier RED/GREEN history were read as reported evidence, not independently reproduced. The prior 2,404-test broad run predates Task1/2. No broad suite was duplicated.

Independent in-memory risk probes: all six PASS, exit0. Exact command below exercises timed release/close cleanup, publication during a failed release, successful reuse after close, genuine sequential PENDING deduplication, swallowed creation-effect failure, nested report detachment, future quote visibility, busy coverage expiry, and invalid future frame prevalidation. All fixtures are synthetic; no files are written by the probe.

```powershell
@'
import sys
sys.path.insert(0, 'tests/tree_replay')
from test_admission_context import *

# A timed release failure still applies publications; timed close completes;
# a later independent lock proves local handle/depth cleanup.
a = T + timedelta(seconds=2)
b = T + timedelta(seconds=4)
d = T + timedelta(seconds=5)
rows = steps()[:3] + (step('release', a, b, index=3, error='release probe'), step('close', b, d, index=4))
rows += tuple(replace(s, step_id='next:'+s.step_id) for s in steps(start=d, seconds=0))
pubs = (publication('quotes', seed('quotes', at=T+timedelta(seconds=3), value=json.dumps({SYMBOL:{'lp':222,'ts':b.timestamp()}})), name='release-publication'),)
c = context(lock_steps=rows, publications=pubs)
try:
    c.tracker.record(plan())
    raise AssertionError('release must fail')
except OSError as exc:
    assert str(exc) == 'release probe'
assert c.decision_time == d and len(c.load()) == 1 and c.quote_payload()[SYMBOL]['lp'] == 222
with c.locked():
    pass
assert c.report()['lock_steps_consumed'] == 10
release = next(e for e in c.report()['events'] if e['operation'] == 'lock.release')
assert release['step_id'] == '3:release' and release['completed_at'] == b.isoformat()
print('PASS timed release failure/publication/close/subsequent lock')

# Supplied close OSError ends local handle and does not discard the saved row.
a = T + timedelta(seconds=2)
b = T + timedelta(seconds=3)
rows = steps()[:-1] + (step('close', a, b, index=4, error='close probe'),)
rows += tuple(replace(s, step_id='next:'+s.step_id) for s in steps(start=b, seconds=0))
c = context(lock_steps=rows)
try:
    c.tracker.record(plan())
    raise AssertionError('close must fail')
except OSError as exc:
    assert str(exc) == 'close probe'
assert c.decision_time == b and len(c.load()) == 1
with c.locked():
    pass
assert c.report()['lock_steps_consumed'] == 10
print('PASS timed close failure/local handle cleanup')

# Sequential genuine tracker records preserve generated PENDING and reject duplicate.
a = T + timedelta(seconds=2)
rows = steps() + tuple(replace(s, step_id='next:'+s.step_id) for s in steps(start=a, seconds=0))
c = context(lock_steps=rows, quote_seed=seed('quotes', value=json.dumps({SYMBOL:{'lp':200,'ts':T.timestamp()}})))
assert c.tracker.record(plan())
assert next(iter(c.load().values()))['state'] == 'PENDING'
before = c.load()
assert c.tracker.record(plan()) is False and c.load() == before
print('PASS sequential generated PENDING/deduplication')

# Child creation audit is deliberately best-effort; outer save success cannot hide it.
c = context()
c.save({'bad_creation': 1})
r = c.report()
assert c.load() == {'bad_creation':1}
assert any(e['operation'] == 'save' and e['status'] == 'AVAILABLE' for e in r['events'])
assert any(e['operation'] == 'creation_effect' and e['status'] == 'BLOCKED' for a in r['artifacts'] for e in a['trace'])
r['artifacts'][0]['trace'][0]['status'] = 'MUTATED'
assert c.report()['artifacts'][0]['trace'][0]['status'] != 'MUTATED'
print('PASS source-caught child failure and nested detached report')

# Future initial images and expired busy coverage cannot be consumed early/late.
a = T + timedelta(seconds=1)
c = context(quote_seed=seed('quotes', at=a), busy_seed=seed('busy', through=T, status='ABSENT'))
try:
    c.quote_payload()
    raise AssertionError('future quote must block')
except InputUnavailable as exc:
    assert 'NOT_YET_AVAILABLE' in str(exc)
c.advance_to(a)
assert c.quote_payload()[SYMBOL]['lp'] == 100
for method, args in ((c.read_busy,()), (c.write_busy,('123',)), (c.clear_busy,())):
    try:
        method(*args)
        raise AssertionError('expired busy must block')
    except StateUnavailable as exc:
        assert 'COVERAGE_EXPIRED' in str(exc)
print('PASS future initial quote and expired busy read/write/clear')

# Structurally invalid future frame image is rejected at context construction.
r = request('5m',55)
p = publication('frames', (r,r), at=a)
try:
    context(publications=(p,))
    raise AssertionError('duplicate future requests must be prevalidated')
except ValueError as exc:
    assert 'duplicate admission request keys' in str(exc)
print('PASS duplicate future frame publication prevalidation')
'@ | python -B -
```

## Recommendations and assessment

Open questions: none blocking Task2.

Ready to merge? Yes for the scoped Task2 implementation/spec quality; no merge action or final component acceptance is performed here. The controller can proceed to its combined final review while continuing its separate caller/lifecycle intake.

Only this requested report was written, using apply_patch. No implementation, tests, inboxes, status records, git state, or source packages were edited. No nested agents, live IO/data/network, commits, cleanup, or training actions were used.
