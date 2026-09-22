# Task2 working-tree diff
BASE and HEAD: c1b6071633c55376c64f0a98ece843706f420f49. No commits. New files compared to NUL.
warning: in the working copy of 'trading_system/tree_replay/state.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/state.py b/trading_system/tree_replay/state.py
new file mode 100644
index 0000000..ca22943
--- /dev/null
+++ b/trading_system/tree_replay/state.py
@@ -0,0 +1,258 @@
+"""Causal supplied advisory-memory evidence, not a tracker or trade simulator.
+
+Completeness and provenance are caller attestations. No disk, wall clock, feed,
+or trading service is accessed. Fixed-TP1 economic state is deliberately excluded.
+"""
+
+from dataclasses import dataclass, fields
+from datetime import datetime, timezone
+from decimal import Decimal
+import hashlib
+import json
+from math import isfinite
+
+from .bars import _utc
+
+
+_SCHEMA = 'causal-admission-memory-v1'
+_CHECKPOINT_SCHEMA = 'causal-admission-memory-checkpoint-v1'
+_ORIGIN = 'supplied_source_advisory'
+_STREAMS = ('tracker', 'episode', 'rejection')
+_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
+
+
+def _identity(value, field):
+    if type(value) is not str or not value or value != value.strip():
+        raise ValueError(f'{field} must be a nonempty trimmed string')
+
+
+def _json_text(value):
+    try:
+        text = json.dumps(value, sort_keys=True, separators=(',', ':'),
+                          ensure_ascii=False, allow_nan=False)
+        text.encode('utf-8')
+        return text
+    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
+        raise ValueError('memory must contain finite UTF-8 JSON values') from exc
+
+
+def _hash(value):
+    return hashlib.sha256(_json_text(value).encode('utf-8')).hexdigest()
+
+
+def _pairs(pairs):
+    result = {}
+    for key, value in pairs:
+        if key in result:
+            raise ValueError('duplicate JSON key')
+        result[key] = value
+    return result
+
+
+def _constant(value):
+    raise ValueError(f'nonfinite JSON constant: {value}')
+
+
+def _payload(text, stream, observed_at):
+    if type(text) is not str:
+        raise ValueError('payload_json must be text')
+    try:
+        result = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
+    except (ValueError, RecursionError) as exc:
+        raise ValueError('payload_json must be unambiguous finite JSON') from exc
+    if type(result) is not dict:
+        raise ValueError('payload_json must encode an object')
+    normalized = _json_text(result)
+    elapsed = observed_at - _EPOCH
+    observed_epoch = (Decimal(elapsed.days * 86400 + elapsed.seconds)
+                      + Decimal(elapsed.microseconds) / 1_000_000)
+    time_fields = ('ts', 'resolved_ts') if stream == 'tracker' else ('ts',)
+    # Compare the JSON decimal, not binary float expansion. An ordinary source
+    # timestamp ending .123456 otherwise expands just past that microsecond.
+    # Parsing original text also prevents finer future fractions being rounded
+    # down by json.loads before this causal check.
+    epoch_values = json.loads(text, parse_float=Decimal)
+    for name in time_fields:
+        if name not in result:
+            continue
+        value = result[name]
+        if type(value) not in (int, float) or (type(value) is float and not isfinite(value)):
+            raise ValueError(f'payload {name} must be a finite numeric epoch')
+        if Decimal(epoch_values[name]) > observed_epoch:
+            raise ValueError(f'payload {name} cannot exceed observed_at')
+    return normalized
+
+
+@dataclass(frozen=True, kw_only=True)
+class MemoryEvent:
+    """One fully observed source-row replacement or append-only rejection."""
+
+    event_id: str
+    sequence: int
+    stream: str
+    key: str
+    observed_at: datetime
+    available_at: datetime
+    payload_json: str
+
+    def __post_init__(self):
+        _identity(self.event_id, 'event_id')
+        _identity(self.key, 'key')
+        if type(self.sequence) is not int or self.sequence < 0:
+            raise ValueError('sequence must be a native nonnegative integer')
+        if type(self.stream) is not str or self.stream not in _STREAMS:
+            raise ValueError('stream must be tracker, episode or rejection')
+        if self.stream == 'rejection' and self.key != self.event_id:
+            raise ValueError('rejection key must equal event_id')
+        for name in ('observed_at', 'available_at'):
+            object.__setattr__(self, name, _utc(getattr(self, name), name))
+        if self.available_at < self.observed_at:
+            raise ValueError('available_at cannot precede observed_at')
+        object.__setattr__(self, 'payload_json',
+                           _payload(self.payload_json, self.stream, self.observed_at))
+
+
+@dataclass(frozen=True, kw_only=True)
+class MemoryJournal:
+    """Append-ordered evidence and explicit bounded completeness attestation."""
+
+    journal_id: str
+    origin: str
+    start_at: datetime
+    covered_through: datetime
+    complete: bool
+    events: tuple[MemoryEvent, ...]
+
+    def __post_init__(self):
+        _identity(self.journal_id, 'journal_id')
+        if type(self.origin) is not str or self.origin != _ORIGIN:
+            raise ValueError('origin must be supplied_source_advisory')
+        if type(self.complete) is not bool:
+            raise ValueError('complete must be an explicit bool')
+        for name in ('start_at', 'covered_through'):
+            object.__setattr__(self, name, _utc(getattr(self, name), name))
+        if self.covered_through < self.start_at:
+            raise ValueError('covered_through cannot precede start_at')
+        if type(self.events) is not tuple:
+            raise ValueError('events must be an immutable tuple')
+        seen = set()
+        previous = None
+        for event in self.events:
+            if type(event) is not MemoryEvent:
+                raise ValueError('events must contain exact MemoryEvent objects')
+            if event.event_id in seen:
+                raise ValueError('duplicate event_id')
+            seen.add(event.event_id)
+            if previous is not None and (event.sequence <= previous.sequence
+                    or event.available_at < previous.available_at):
+                raise ValueError('events must preserve increasing sequence/publication order')
+            if event.observed_at < self.start_at or event.available_at > self.covered_through:
+                raise ValueError('events lie outside declared journal coverage')
+            previous = event
+
+
+def _journal(value):
+    if type(value) is not MemoryJournal:
+        raise ValueError('journal must be an exact MemoryJournal')
+
+
+def _event_record(event):
+    return {field.name: (getattr(event, field.name).isoformat()
+                        if field.name in ('observed_at', 'available_at')
+                        else getattr(event, field.name)) for field in fields(MemoryEvent)}
+
+
+def memory_asof(journal: MemoryJournal, decision_time: datetime) -> dict:
+    """Project only available evidence; revisions never backdate a state row."""
+    _journal(journal)
+    decision_time = _utc(decision_time, 'decision_time')
+    blocker = None
+    if not journal.complete:
+        blocker = 'INCOMPLETE_HISTORY'
+    elif decision_time < journal.start_at:
+        blocker = 'BEFORE_COVERAGE'
+    elif decision_time > journal.covered_through:
+        blocker = 'AFTER_COVERAGE'
+    result = dict(schema=_SCHEMA, status='UNAVAILABLE' if blocker else 'AVAILABLE',
+        blocker=blocker, decision_time=decision_time.isoformat(),
+        journal_id=journal.journal_id, origin=journal.origin,
+        start_at=journal.start_at.isoformat(),
+        tracker_state=None if blocker else {}, episode_state=None if blocker else {},
+        rejection_events=None if blocker else [], selected_event_ids=[], event_trace=[],
+        tradeable=False, replay_ready=False, training_ready=False)
+    if not blocker:
+        for event in journal.events:
+            if event.available_at > decision_time:
+                break
+            value = json.loads(event.payload_json)
+            if event.stream == 'rejection':
+                result['rejection_events'].append(value)
+            else:
+                result[f'{event.stream}_state'][event.key] = value
+            result['selected_event_ids'].append(event.event_id)
+            trace = _event_record(event)
+            trace['payload_hash'] = _hash(value)
+            del trace['payload_json']
+            result['event_trace'].append(trace)
+    result['evaluation_hash'] = _hash(result)
+    return result
+
+
+def checkpoint_memory(journal: MemoryJournal) -> dict:
+    """Serialize the entire supplied journal, not an engine checkpoint."""
+    _journal(journal)
+    data = dict(journal_id=journal.journal_id, origin=journal.origin,
+                start_at=journal.start_at.isoformat(),
+                covered_through=journal.covered_through.isoformat(),
+                complete=journal.complete,
+                events=[_event_record(event) for event in journal.events])
+    result = dict(schema=_CHECKPOINT_SCHEMA, journal=data)
+    result['checksum'] = _hash(result)
+    return result
+
+
+def _keys(value, expected, name):
+    if type(value) is not dict or set(value) != set(expected):
+        raise ValueError(f'{name} has an invalid structure')
+
+
+def _parse_time(value, name):
+    if type(value) is not str:
+        raise ValueError(f'{name} must be an ISO timestamp')
+    try:
+        result = _utc(datetime.fromisoformat(value), name)
+    except (TypeError, ValueError, OverflowError) as exc:
+        raise ValueError(f'{name} must be an aware ISO timestamp') from exc
+    # Checkpoints use the exact canonical serializer. In particular, never
+    # truncate nanosecond strings accepted by datetime.fromisoformat.
+    if result.isoformat() != value:
+        raise ValueError(f'{name} must use canonical microsecond-exact UTC encoding')
+    return result
+
+
+def restore_memory(checkpoint: dict) -> MemoryJournal:
+    """Validate version/checksum/types, then reconstruct through public contracts."""
+    _keys(checkpoint, ('schema', 'journal', 'checksum'), 'checkpoint')
+    if checkpoint['schema'] != _CHECKPOINT_SCHEMA:
+        raise ValueError('unsupported memory checkpoint schema')
+    content = {key: checkpoint[key] for key in ('schema', 'journal')}
+    if type(checkpoint['checksum']) is not str or checkpoint['checksum'] != _hash(content):
+        raise ValueError('invalid memory checkpoint checksum')
+    data = checkpoint['journal']
+    _keys(data, (f.name for f in fields(MemoryJournal)), 'journal')
+    if type(data['events']) is not list:
+        raise ValueError('checkpoint events must be a list')
+    events = []
+    for row in data['events']:
+        _keys(row, (f.name for f in fields(MemoryEvent)), 'event')
+        values = dict(row)
+        for name in ('observed_at', 'available_at'):
+            values[name] = _parse_time(values[name], name)
+        events.append(MemoryEvent(**values))
+    values = dict(data, events=tuple(events))
+    for name in ('start_at', 'covered_through'):
+        values[name] = _parse_time(values[name], name)
+    restored = MemoryJournal(**values)
+    if checkpoint_memory(restored) != checkpoint:
+        raise ValueError('checkpoint must use canonical payload encoding')
+    return restored

warning: in the working copy of 'tests/tree_replay/test_state.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_state.py b/tests/tree_replay/test_state.py
new file mode 100644
index 0000000..1dbd7c3
--- /dev/null
+++ b/tests/tree_replay/test_state.py
@@ -0,0 +1,272 @@
+"""Synthetic evidence-store tests: publication order, not economic simulation."""
+
+from dataclasses import FrozenInstanceError, replace
+from datetime import datetime, timedelta, timezone
+import importlib
+import importlib.util
+import hashlib
+import json
+
+import pandas as pd
+import pytest
+
+
+T = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
+US = timedelta(microseconds=1)
+HOUR = timedelta(hours=1)
+
+
+def api():
+    name = 'trading_system.tree_replay.state'
+    assert importlib.util.find_spec(name) is not None, 'Missing causal memory adapter'
+    return importlib.import_module(name)
+
+
+def event(**changes):
+    return api().MemoryEvent(**(dict(event_id='e1', sequence=1, stream='tracker',
+        key='trade1', observed_at=T, available_at=T,
+        payload_json='{"state":"PENDING"}') | changes))
+
+
+def journal(events=(), **changes):
+    return api().MemoryJournal(**(dict(journal_id='j1',
+        origin='supplied_source_advisory', start_at=T, covered_through=T + HOUR,
+        complete=True, events=events) | changes))
+
+
+def test_pending_row_is_preserved_without_becoming_open_or_a_label():
+    r = api().memory_asof(journal((event(),)), T)
+    assert r['status'] == 'AVAILABLE'
+    assert r['tracker_state'] == {'trade1': {'state': 'PENDING'}}
+    assert r['episode_state'] == {}
+    assert r['rejection_events'] == []
+    assert r['selected_event_ids'] == ['e1']
+    assert r['tradeable'] is r['training_ready'] is r['replay_ready'] is False
+
+
+def test_delayed_revision_cannot_rewrite_earlier_memory_or_hash():
+    first = event()
+    later = event(event_id='e2', sequence=2, observed_at=T + US,
+                  available_at=T + HOUR, payload_json='{"state":"STOPPED"}')
+    old = api().memory_asof(journal((first,), covered_through=T), T)
+    extended = journal((first, later))
+    assert api().memory_asof(extended, T) == old
+    assert api().memory_asof(extended, T + HOUR - US)['tracker_state']['trade1']['state'] == 'PENDING'
+    assert api().memory_asof(extended, T + HOUR)['tracker_state']['trade1']['state'] == 'STOPPED'
+
+
+def test_equal_publication_instants_use_global_sequence_and_replace_full_rows():
+    a = event(payload_json='{"state":"PENDING","old":true}')
+    b = event(event_id='e2', sequence=2, payload_json='{"state":"OPEN"}')
+    r = api().memory_asof(journal((a, b)), T)
+    assert r['tracker_state'] == {'trade1': {'state': 'OPEN'}}
+    assert r['selected_event_ids'] == ['e1', 'e2']
+
+
+def test_episode_and_rejection_streams_stay_separate_and_rejections_keep_order():
+    events = (event(stream='episode', key='symbol:episode', payload_json='{"entry":10}'),
+              event(event_id='e2', sequence=2, stream='rejection', key='e2', payload_json='{"close":11}'),
+              event(event_id='e3', sequence=3, stream='rejection', key='e3', payload_json='{"close":12}'))
+    r = api().memory_asof(journal(events), T)
+    assert r['tracker_state'] == {}
+    assert r['episode_state'] == {'symbol:episode': {'entry': 10}}
+    assert r['rejection_events'] == [{'close': 11}, {'close': 12}]
+
+
+@pytest.mark.parametrize('time,complete,reason', [
+    (T - US, True, 'BEFORE_COVERAGE'),
+    (T + HOUR + US, True, 'AFTER_COVERAGE'),
+    (T, False, 'INCOMPLETE_HISTORY'),
+])
+def test_unavailable_memory_never_looks_like_usable_empty_state(time, complete, reason):
+    r = api().memory_asof(journal((event(),), complete=complete), time)
+    assert r['status'] == 'UNAVAILABLE'
+    assert r['blocker'] == reason
+    assert r['tracker_state'] is r['episode_state'] is r['rejection_events'] is None
+    assert r['selected_event_ids'] == []
+
+
+@pytest.mark.parametrize('time', [T, T + HOUR])
+def test_explicit_complete_empty_history_is_available_at_inclusive_boundaries(time):
+    r = api().memory_asof(journal(), time)
+    assert r['status'] == 'AVAILABLE'
+    assert r['tracker_state'] == {}
+
+
+def test_source_row_missing_state_remains_visible_for_fail_closed_gate():
+    r = api().memory_asof(journal((event(payload_json='{"symbol":"OANDA:XAUUSD"}'),)), T)
+    assert r['tracker_state'] == {'trade1': {'symbol': 'OANDA:XAUUSD'}}
+
+
+def test_payload_normalization_and_detachment_including_nested_values():
+    e = event(payload_json=' { "state": "OPEN", "x": [false, {"v": 0}] } ')
+    assert e.payload_json == '{"state":"OPEN","x":[false,{"v":0}]}'
+    j = journal((e,))
+    r = api().memory_asof(j, T)
+    r['tracker_state']['trade1']['x'][1]['v'] = 999
+    assert api().memory_asof(j, T)['tracker_state']['trade1']['x'] == [False, {'v': 0}]
+
+
+@pytest.mark.parametrize('payload', [
+    '[]', 'null', '1', '{broken', '{"x":NaN}', '{"x":Infinity}',
+    '{"x":1e999}', '{"x":[{"a":1,"a":2}]}', '{"x":1,"x":2}',
+])
+def test_ambiguous_or_nonfinite_json_is_rejected(payload):
+    with pytest.raises(ValueError):
+        event(payload_json=payload)
+
+
+@pytest.mark.parametrize('field,value', [
+    ('event_id', ''), ('event_id', ' x'), ('event_id', 1),
+    ('sequence', True), ('sequence', -1), ('sequence', 1.0),
+    ('stream', 'economic'), ('stream', []), ('key', ''),
+    ('payload_json', {}), ('observed_at', T.replace(tzinfo=None)),
+    ('available_at', T - US), ('observed_at', pd.Timestamp(T) + pd.Timedelta(nanoseconds=1)),
+])
+def test_invalid_event_contract_is_rejected(field, value):
+    with pytest.raises(ValueError):
+        event(**{field: value})
+
+
+@pytest.mark.parametrize('field,value', [('ts', '123'), ('ts', True),
+    ('ts', None), ('resolved_ts', '123'), ('resolved_ts', True)])
+def test_source_timestamp_fields_must_be_real_finite_epochs(field, value):
+    with pytest.raises(ValueError):
+        event(payload_json=json.dumps({field: value}))
+
+
+@pytest.mark.parametrize('stream,field', [('tracker', 'ts'), ('tracker', 'resolved_ts'),
+    ('episode', 'ts'), ('rejection', 'ts')])
+def test_source_payload_cannot_smuggle_a_future_resolution(stream, field):
+    with pytest.raises(ValueError):
+        event(stream=stream, payload_json=json.dumps({field: (T + HOUR).timestamp()}))
+
+
+def test_rejection_key_must_be_its_append_only_event_id():
+    with pytest.raises(ValueError):
+        event(stream='rejection', key='shared')
+
+
+@pytest.mark.parametrize('events', ['list', 'duplicate_id', 'duplicate_sequence', 'reversed',
+    'reversed_publication', 'before_start', 'beyond_coverage', 'untyped'])
+def test_journal_rejects_corrupt_order_or_coverage_instead_of_sorting(events):
+    a = event()
+    b = event(event_id='e2', sequence=2)
+    cases = {
+        'list': [a], 'duplicate_id': (a, replace(b, event_id='e1')),
+        'duplicate_sequence': (a, replace(b, sequence=1)), 'reversed': (b, a),
+        'reversed_publication': (replace(a, available_at=T + US), b),
+        'before_start': (replace(a, observed_at=T - US),),
+        'beyond_coverage': (replace(a, available_at=T + HOUR + US),),
+        'untyped': ({'state': 'OPEN'},),
+    }
+    with pytest.raises(ValueError):
+        journal(cases[events])
+
+
+@pytest.mark.parametrize('field,value', [('journal_id', ''), ('origin', 'economic_tp1'),
+    ('complete', 1), ('complete', 'true'), ('start_at', T.replace(tzinfo=None)),
+    ('covered_through', T - US)])
+def test_journal_metadata_validation(field, value):
+    with pytest.raises(ValueError):
+        journal(**{field: value})
+
+
+def test_memory_requires_typed_journal_and_exact_aware_decision_time():
+    with pytest.raises(ValueError):
+        api().memory_asof({}, T)
+    with pytest.raises(ValueError):
+        api().memory_asof(journal(), T.replace(tzinfo=None))
+    with pytest.raises(ValueError):
+        api().memory_asof(journal(), pd.Timestamp(T) + pd.Timedelta(nanoseconds=1))
+
+
+def test_checkpoint_json_roundtrip_and_resumed_append_match_continuous_journal():
+    a = event()
+    b = event(event_id='e2', sequence=2, available_at=T + US,
+              observed_at=T + US, payload_json='{"state":"OPEN"}')
+    first = journal((a,), covered_through=T)
+    restored = api().restore_memory(json.loads(json.dumps(api().checkpoint_memory(first))))
+    assert restored == first
+    resumed = replace(restored, events=restored.events + (b,), covered_through=T + HOUR)
+    continuous = journal((a, b))
+    assert api().memory_asof(resumed, T + US) == api().memory_asof(continuous, T + US)
+    assert api().memory_asof(resumed, T) == api().memory_asof(first, T)
+
+
+@pytest.mark.parametrize('mutation', ['payload', 'schema', 'checksum', 'extra', 'missing', 'sequence'])
+def test_checkpoint_tampering_rejected(mutation):
+    c = api().checkpoint_memory(journal((event(),)))
+    if mutation == 'payload':
+        c['journal']['events'][0]['payload_json'] = '{"state":"DONE"}'
+    elif mutation == 'schema':
+        c['schema'] = 'other'
+    elif mutation == 'checksum':
+        c['checksum'] = '0' * 64
+    elif mutation == 'extra':
+        c['unknown'] = True
+    elif mutation == 'missing':
+        del c['journal']['origin']
+    else:
+        c['journal']['events'][0]['sequence'] = True
+    with pytest.raises(ValueError):
+        api().restore_memory(c)
+
+
+def test_events_and_journals_are_frozen_and_checkpoints_detached():
+    e = event()
+    j = journal((e,))
+    with pytest.raises(FrozenInstanceError):
+        e.sequence = 99
+    with pytest.raises(FrozenInstanceError):
+        j.complete = False
+    c = api().checkpoint_memory(j)
+    c['journal']['events'].clear()
+    assert api().memory_asof(j, T)['selected_event_ids'] == ['e1']
+
+
+def test_epoch_json_decimal_at_exact_microsecond_is_not_a_future_event():
+    t = T.replace(microsecond=123456)
+    e = event(observed_at=t, available_at=t,
+              payload_json='{"ts":1788775200.123456}')
+    assert api().memory_asof(journal((e,)), t)['tracker_state']['trade1']['ts'] == 1788775200.123456
+
+
+@pytest.mark.parametrize('epoch', ['1788775200.1234562', '1788775200.12345601'])
+def test_submicrosecond_future_epoch_is_not_rounded_back_into_snapshot(epoch):
+    t = T.replace(microsecond=123456)
+    with pytest.raises(ValueError):
+        event(observed_at=t, available_at=t, payload_json='{"ts":' + epoch + '}')
+
+
+@pytest.mark.parametrize('mutation', ['extra_event_field', 'extra_journal_field',
+    'nanosecond_string', 'naive_string', 'noncanonical_payload', 'bad_sequence',
+    'duplicate_id', 'out_of_coverage', 'wrong_origin', 'bad_events_container'])
+def test_restore_validates_structure_even_when_checksum_is_recomputed(mutation):
+    c = api().checkpoint_memory(journal((event(),)))
+    row = c['journal']['events'][0]
+    if mutation == 'extra_event_field':
+        row['ignored'] = True
+    elif mutation == 'extra_journal_field':
+        c['journal']['ignored'] = True
+    elif mutation == 'nanosecond_string':
+        row['observed_at'] = '2026-09-07T10:00:00.000000001+00:00'
+    elif mutation == 'naive_string':
+        row['observed_at'] = '2026-09-07T10:00:00'
+    elif mutation == 'noncanonical_payload':
+        row['payload_json'] = '{ "state" : "PENDING" }'
+    elif mutation == 'bad_sequence':
+        row['sequence'] = True
+    elif mutation == 'duplicate_id':
+        c['journal']['events'].append(dict(row, sequence=2))
+    elif mutation == 'out_of_coverage':
+        row['available_at'] = (T + HOUR + US).isoformat()
+    elif mutation == 'wrong_origin':
+        c['journal']['origin'] = 'economic_tp1'
+    else:
+        c['journal']['events'] = {}
+    unsigned = {key: c[key] for key in ('schema', 'journal')}
+    c['checksum'] = hashlib.sha256(json.dumps(unsigned, sort_keys=True,
+        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
+    with pytest.raises(ValueError):
+        api().restore_memory(c)

warning: in the working copy of 'docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md b/docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md
new file mode 100644
index 0000000..a69ad85
--- /dev/null
+++ b/docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md
@@ -0,0 +1,61 @@
+# Causal admission memory evidence
+
+`trading_system.tree_replay.state` is an offline evidence store, not a simulator.
+It preserves what a source-advisory tracker, episode map and rejection log said
+as of a decision. It does not generate their transitions or certify provenance.
+
+```python
+from datetime import datetime, timezone
+from trading_system.tree_replay.state import (
+    MemoryEvent, MemoryJournal, memory_asof, checkpoint_memory, restore_memory,
+)
+
+t = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
+event = MemoryEvent(
+    event_id='observation-1', sequence=1, stream='tracker', key='trade-1',
+    observed_at=t, available_at=t,
+    payload_json='{"symbol":"OANDA:XAUUSD","state":"PENDING"}',
+)
+journal = MemoryJournal(
+    journal_id='synthetic-example', origin='supplied_source_advisory',
+    start_at=t, covered_through=t, complete=True, events=(event,),
+)
+snapshot = memory_asof(journal, t)
+assert snapshot['tracker_state']['trade-1']['state'] == 'PENDING'
+assert snapshot['replay_ready'] is False
+restored = restore_memory(checkpoint_memory(journal))
+assert restored == journal
+```
+
+## Contracts
+
+- `complete=True` explicitly attests complete state history over
+  `[start_at, covered_through]`. No records plus incomplete history is not empty
+  state. Queries outside coverage return UNAVAILABLE with null state outputs.
+- Event sequence is globally unique/increasing and publication time is
+  nondecreasing. Equal-time sequence order is preserved. Wrong ordering is
+  rejected, never silently sorted. Event IDs are globally unique.
+- Tracker/episode events replace the entire row at `key`. Rejections append,
+  with `key == event_id`. No deletion command or implicit row merge exists.
+- Both timestamps must be aware, microsecond-exact and observed <= available.
+  Numeric source `ts` and tracker `resolved_ts` cannot exceed event observation.
+  Epoch comparison uses original JSON decimal tokens, avoiding binary-float
+  artifacts and rejecting finer future fractions before JSON float rounding.
+- Payload is immutable canonical JSON text. Duplicate keys, nonfinite numbers,
+  non-object roots and non-UTF8 text are rejected. Missing source fields remain
+  visible for downstream source gates to handle; malformed rows are not dropped.
+- Actual T selects published events only. `event_trace` carries their times,
+  sequence, keys and payload hashes. Later publications do not alter an earlier
+  snapshot or its hash. Output objects are detached from journal memory.
+- Checkpoints contain full history with schema/checksum. Restore checks fields,
+  canonical timestamps/payload, ordering and coverage even with a recomputed
+  checksum. This checksum detects corruption, not malicious forgery or false
+  provenance. It is not cryptographic authentication of market history.
+
+The only supported origin is supplied_source_advisory. Do not insert TP1 economic
+exits as source advisory transitions. This component neither evaluates the actual
+OPEN/PENDING exposure gate nor executes post-stop/same-level/episode admission.
+Those gates and source-generated lifecycle replay are the next integration work.
+No real state/log files, market data, labels, model or live service is accessed.
+
+Verification: `python -m pytest tests/tree_replay/test_state.py -q --tb=short`.


