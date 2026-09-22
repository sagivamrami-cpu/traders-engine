# Agent Exchange Review

Reviewer: Codex independent combined final reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T170447Z-admission-context-final-review.md
Request: agent-exchange/inbox/codex/2026-09-09T170447Z-admission-context-final-review.md

Created at: 2026-09-09T17:08:01Z

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec PASS. Combined code quality/integration PASS. No actionable Critical, Important or Minor findings. Ready for controller acceptance of the scoped shared causal admission context; this does not certify the complete caller, historical replay or model readiness.

## Scope and method

Executed only this request. Read repository startup instructions and inspected the Codex inbox. Applied requesting-code-review and its code-reviewer.md checklist directly without nested agents. Read the complete causal-context plan, contract, both usages, both implementation reports and progress ledger, task reviews164824Z/170100Z, acceptances165135Z/170447Z and their original requests. Read the current master design, prior storage/IO/lock acceptance records and usages, and review132300Z including all seven subsequent-binding requirements.

Inspected git status and tracked diff at HEAD `c1b6071633c55376c64f0a98ece843706f420f49`. The files are untracked; an empty commit range was not used as evidence. Read all eight actual files and reconstructed their full added contents from both task packages. All eight match after CRLF/LF normalization, including terminal blank lines. Compared the two modified artifact wrappers with the accepted tracker-storage final package and quote/watch task package: the differences are optional clock plumbing and associated documentation, with original storage and IO operations retained.

| File | Lines | SHA256 |
| --- | ---: | --- |
| trading_system/tree_replay/clock.py | 24 | 69990180D058E687C0CEF84126BEDC9E8D71E19C733B1072D61021D7C1C9C433 |
| trading_system/tree_replay/tracker_storage.py | 179 | DE9C0E626D3260CCA83EDBE21E2A236DFB397FCD3D082CA36F6CA725F3644ADC |
| trading_system/tree_replay/admission_io.py | 262 | 8D42227B2518C9DC9F3C7CD7327FF5786B730E19C3BAAF79D61037EEEF9DA668 |
| tests/tree_replay/test_shared_clock.py | 160 | 0EC21FC3A9974BD4A39D5692323B806B5921EF83443772446529349D883B5742 |
| docs/architecture/SHARED-REPLAY-CLOCK-USAGE.md | 38 | A7A8D203BFDA65E35337B67C74135889BDF0F81228C4834625502B9E1428C380 |
| trading_system/tree_replay/admission_context.py | 322 | D86A897B784FFA20419E1336D7A2F454B50E7275C044202DB65192B842E67DB7 |
| tests/tree_replay/test_admission_context.py | 362 | 96C692AD7C0E439FC967A1004E98C72C817700ED201231219C5F55ED5DE22C0A |
| docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md | 112 | 6F1737C512DBA505B99FB15E177F76C4973DF13A51A877453B4AE99709AE80F9 |

All eight hashes remained unchanged after verification. Separate watch_storage work was excluded.

## Strengths and assessment

- `trading_system/tree_replay/clock.py:15`, `tracker_storage.py:69`, and `admission_io.py:68`: equal/forward microsecond UTC clock movement is independent of artifact availability. Exact binding validation and supported standalone defaults remain intact. State, creation/quarantine effects and captured log prefixes survive advancement.
- `trading_system/tree_replay/admission_context.py:114` and `:195`: schedules are validated before execution; equal-time publications follow explicit sequence and replace whole images. No early future image selection, implicit history merge or coverage extension is introduced. Old artifact evidence and readers survive replacement.
- `trading_system/tree_replay/admission_context.py:231` and `:246`: the context uses actual AdmissionFrameSource, TrackerAdmission and TrackerLock. Original pre-lock bias/thesis/born calculations remain separate from post-lock state reads and timestamps. Lock completion applies publications before subsequent reads, with exact operation/time/timeout evidence and local handle checks.
- `trading_system/tree_replay/admission_context.py:297` and `:308`: busy-artifact failures remain visible through source catches. Detached context/child traces retain partial effects, including successful storage writes preceding release failures. Reporting leaves both readiness flags false.
- `docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md:89`: the documented distinction between an available operation, source fallback and complete historical evidence matches the implementation. No new trading veto or economic interpretation is added.

## Findings

Critical: none.

Important: none.

Minor: none actionable in this eight-file scope.

## Independent verification

Focused runtime suite: PASS, exit0, **75 passed in 3.33s**.

```powershell
python -B -m pytest tests/tree_replay/test_shared_clock.py tests/tree_replay/test_admission_context.py -q --tb=short -p no:cacheprovider
```

All four source audits independently PASS, exit0, VERIFIED, empty blockers and false replay/training readiness. Projection counts respectively2,4,7,4. These inspect retained source without executing it.

```powershell
python -B tools/check_tracker_storage_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
python -B tools/check_watch_io_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
python -B tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
python -B tools/check_tracker_lock_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

Concrete cross-component probe: PASS, exit0. A single acquired lock crosses quote/log/frame publications and a tracker-image replacement, with independently expiring tracker and busy coverage. It verifies current post-lock storage, preserved pre-lock PENDING/bias, unchanged quote payload freshness, old-reader isolation, real rejection selection, retained prior creation effects, and a caught busy-clear failure. The boundary pair then proves actual record succeeds exactly at storage coverage and fails one microsecond later while consuming release/close evidence. Exact in-memory command follows; it writes no probe file.

```powershell
@'
import sys
sys.path.insert(0, 'tests/tree_replay')
from test_admission_context import *

a = T + timedelta(seconds=1)
b = T + timedelta(seconds=2)
p = plan()
rejection = dict(ts=a.timestamp(), kind='rejection', symbol=SYMBOL,
    direction=p.direction, zone_lo=98, zone_hi=102, levels=['PSY'], close=100, wick_atr=.5)
raw = b'non-rejection prefix\n' + json.dumps(rejection).encode() + b'\n'
publications = (
    publication('quotes', seed('quotes', at=a, value=json.dumps({SYMBOL:{'lp':100,'ts':(T-timedelta(seconds=420)).timestamp()}})), seq=0, name='stale-tap'),
    publication('watch_log', seed('watch_log', at=a, value=raw), seq=1, name='raw-image'),
    publication('frames', tuple(request(tf, days, price=110.) for tf, days in KEYS), at=a, seq=2, name='new-frames'),
    publication('tracker', seed('tracker', at=b), seq=0, name='state-at-acquire'),
)
c = context(tracker_seed=seed('tracker', through=a), busy_seed=seed('busy', through=T, status='ABSENT'),
    quote_seed=seed('quotes', value=json.dumps({SYMBOL:{'lp':200,'ts':T.timestamp()}})),
    log_seed=seed('watch_log', value=b'captured\n'), publications=publications)
c.save({'generated':{'state':'PENDING'}})
old_reader = c.event_log_reader()
c.log({'kind':'before_acquire'})
assert c.tracker.record(p) is True
stored = c.load()
assert len(stored) == 1 and 'generated' not in stored
row = next(iter(stored.values()))
assert row['state'] == 'PENDING' and row['ts'] == b.timestamp()
assert row['bias_at_send'] == {'4h':-41.25,'1h':-41.25}
assert c.pass_anchor == T and c.decision_time == b
assert c.tracker._live_prices() == {}, 'publication must not rejuvenate old tap ts'
assert c.read_symbol(SYMBOL, ('4h',))['4h'].close == 110.
assert old_reader.read() == b'captured\n'
assert c.event_log_reader().read() == raw
assert c.tracker._recent_rejection(SYMBOL, p.direction, T.timestamp()-10, b.timestamp(), 100.)['age_s'] == 1.
r = c.report()
assert r['publications_consumed'] == 4 and r['lock_steps_consumed'] == 5
assert [e['publication_id'] for e in r['events'] if e['operation']=='publication'] == ['stale-tap','raw-image','new-frames','state-at-acquire']
assert any(e['operation']=='busy.clear' and e['status']=='BLOCKED' and e['blocker']=='STATE_COVERAGE_EXPIRED' for e in r['events'])
assert any(e['operation']=='clear' and e['status']=='BLOCKED' for art in r['artifacts'] if art['channel']=='busy' for e in art['trace'])
stores = [art for art in r['artifacts'] if art['channel']=='tracker']
assert len(stores)==2 and stores[0]['creation_effects'][0]['key']=='generated'
assert stores[1]['creation_effects'][0]['ts']==b.timestamp()
assert [f['decision_time'] for f in r['frames']][:2]==[T.isoformat(),T.isoformat()]
assert not r['ready_for_replay'] and not r['ready_for_training']
print('PASS combined acquire: publication order, full-image state, pre/post-lock reads, stale quote, raw reader, swallowed busy expiry')

for delta, expected in ((timedelta(0), True), (timedelta(microseconds=1), False)):
    end = b + delta
    rows = steps()[:2] + (step('acquire', T, end, index=2), step('release', end, index=3), step('close', end, index=4))
    c = context(tracker_seed=seed('tracker', through=b), lock_steps=rows)
    if expected:
        assert c.tracker.record(plan()) is True
        assert next(iter(c.load().values()))['ts']==b.timestamp()
    else:
        try:
            c.tracker.record(plan())
            raise AssertionError('expired storage must block actual post-lock load')
        except StateUnavailable as exc:
            assert str(exc)=='STATE_COVERAGE_EXPIRED'
        events=c.report()['events']
        assert any(e['operation']=='load' and e['status']=='BLOCKED' for e in events)
        assert not any(e['operation']=='save' for e in events)
        assert [e['operation'] for e in events][-2:]==['lock.release','lock.close']
    assert c.decision_time==end and c.pass_anchor==T
    assert c.report()['lock_steps_consumed']==5
print('PASS storage coverage exact edge and edge+1us with actual record/cleanup')
'@ | python -B -
```

The controller's seven-file362-test run and prior task-review probes were read as reported evidence, not independently repeated. The prior2404-test broad run predates this component. Counts overlap; probe scenarios are not additional pytest cases. No broad suite was duplicated.

## Limits and recommended next action

Open questions: none blocking scoped component acceptance.

Ready to merge? Yes for this component's spec and code quality; this review performs no merge or controller acceptance action. Controller may record combined acceptance. The separate watch_storage implementation is neither reviewed nor accepted here.

Synthetic supplied Plans and frame/artifact evidence establish engineering behavior only. Full original caller/branch order, mixed-time producer binding, watch-state persistence and separate lock, generated lifecycle, historical coverage/checkpoint equivalence, remaining producers and economic/dataset/model work remain open. In particular, record success with source-caught failures is not full input-quality approval; local handle cleanup is not OS acquisition/permission certification. Readiness remains false.

Only this requested report was written, via apply_patch. No implementation, tests, inbox/status records, data, live IO, network, git state, commits or cleanup were changed; no nested agents were used.
