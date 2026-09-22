"""Synthetic evidence-store tests: publication order, not economic simulation."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import localcontext
import importlib
import importlib.util
import hashlib
import json

import pandas as pd
import pytest


T = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
US = timedelta(microseconds=1)
HOUR = timedelta(hours=1)


def api():
    name = 'trading_system.tree_replay.state'
    assert importlib.util.find_spec(name) is not None, 'Missing causal memory adapter'
    return importlib.import_module(name)


def event(**changes):
    return api().MemoryEvent(**(dict(event_id='e1', sequence=1, stream='tracker',
        key='trade1', observed_at=T, available_at=T,
        payload_json='{"state":"PENDING"}') | changes))


def journal(events=(), **changes):
    return api().MemoryJournal(**(dict(journal_id='j1',
        origin='supplied_source_advisory', start_at=T, covered_through=T + HOUR,
        complete=True, events=events) | changes))


def test_pending_row_is_preserved_without_becoming_open_or_a_label():
    r = api().memory_asof(journal((event(),)), T)
    assert r['status'] == 'AVAILABLE'
    assert r['tracker_state'] == {'trade1': {'state': 'PENDING'}}
    assert r['episode_state'] == {}
    assert r['rejection_events'] == []
    assert r['selected_event_ids'] == ['e1']
    assert r['tradeable'] is r['training_ready'] is r['replay_ready'] is False


def test_delayed_revision_cannot_rewrite_earlier_memory_or_hash():
    first = event()
    later = event(event_id='e2', sequence=2, observed_at=T + US,
                  available_at=T + HOUR, payload_json='{"state":"STOPPED"}')
    old = api().memory_asof(journal((first,), covered_through=T), T)
    extended = journal((first, later))
    assert api().memory_asof(extended, T) == old
    assert api().memory_asof(extended, T + HOUR - US)['tracker_state']['trade1']['state'] == 'PENDING'
    assert api().memory_asof(extended, T + HOUR)['tracker_state']['trade1']['state'] == 'STOPPED'


def test_equal_publication_instants_use_global_sequence_and_replace_full_rows():
    a = event(payload_json='{"state":"PENDING","old":true}')
    b = event(event_id='e2', sequence=2, payload_json='{"state":"OPEN"}')
    r = api().memory_asof(journal((a, b)), T)
    assert r['tracker_state'] == {'trade1': {'state': 'OPEN'}}
    assert r['selected_event_ids'] == ['e1', 'e2']


def test_episode_and_rejection_streams_stay_separate_and_rejections_keep_order():
    events = (event(stream='episode', key='symbol:episode', payload_json='{"entry":10}'),
              event(event_id='e2', sequence=2, stream='rejection', key='e2', payload_json='{"close":11}'),
              event(event_id='e3', sequence=3, stream='rejection', key='e3', payload_json='{"close":12}'))
    r = api().memory_asof(journal(events), T)
    assert r['tracker_state'] == {}
    assert r['episode_state'] == {'symbol:episode': {'entry': 10}}
    assert r['rejection_events'] == [{'close': 11}, {'close': 12}]


@pytest.mark.parametrize('time,complete,reason', [
    (T - US, True, 'BEFORE_COVERAGE'),
    (T + HOUR + US, True, 'AFTER_COVERAGE'),
    (T, False, 'INCOMPLETE_HISTORY'),
])
def test_unavailable_memory_never_looks_like_usable_empty_state(time, complete, reason):
    r = api().memory_asof(journal((event(),), complete=complete), time)
    assert r['status'] == 'UNAVAILABLE'
    assert r['blocker'] == reason
    assert r['tracker_state'] is r['episode_state'] is r['rejection_events'] is None
    assert r['selected_event_ids'] == []


@pytest.mark.parametrize('time', [T, T + HOUR])
def test_explicit_complete_empty_history_is_available_at_inclusive_boundaries(time):
    r = api().memory_asof(journal(), time)
    assert r['status'] == 'AVAILABLE'
    assert r['tracker_state'] == {}


def test_source_row_missing_state_remains_visible_for_fail_closed_gate():
    r = api().memory_asof(journal((event(payload_json='{"symbol":"OANDA:XAUUSD"}'),)), T)
    assert r['tracker_state'] == {'trade1': {'symbol': 'OANDA:XAUUSD'}}


def test_payload_normalization_and_detachment_including_nested_values():
    e = event(payload_json=' { "state": "OPEN", "x": [false, {"v": 0}] } ')
    assert e.payload_json == '{"state":"OPEN","x":[false,{"v":0}]}'
    j = journal((e,))
    r = api().memory_asof(j, T)
    r['tracker_state']['trade1']['x'][1]['v'] = 999
    assert api().memory_asof(j, T)['tracker_state']['trade1']['x'] == [False, {'v': 0}]


@pytest.mark.parametrize('payload', [
    '[]', 'null', '1', '{broken', '{"x":NaN}', '{"x":Infinity}',
    '{"x":1e999}', '{"x":[{"a":1,"a":2}]}', '{"x":1,"x":2}',
])
def test_ambiguous_or_nonfinite_json_is_rejected(payload):
    with pytest.raises(ValueError):
        event(payload_json=payload)


@pytest.mark.parametrize('field,value', [
    ('event_id', ''), ('event_id', ' x'), ('event_id', 1),
    ('sequence', True), ('sequence', -1), ('sequence', 1.0),
    ('stream', 'economic'), ('stream', []), ('key', ''),
    ('payload_json', {}), ('observed_at', T.replace(tzinfo=None)),
    ('available_at', T - US), ('observed_at', pd.Timestamp(T) + pd.Timedelta(nanoseconds=1)),
])
def test_invalid_event_contract_is_rejected(field, value):
    with pytest.raises(ValueError):
        event(**{field: value})


@pytest.mark.parametrize('field,value', [('ts', '123'), ('ts', True),
    ('ts', None), ('resolved_ts', '123'), ('resolved_ts', True)])
def test_source_timestamp_fields_must_be_real_finite_epochs(field, value):
    with pytest.raises(ValueError):
        event(payload_json=json.dumps({field: value}))


@pytest.mark.parametrize('stream,field', [('tracker', 'ts'), ('tracker', 'resolved_ts'),
    ('episode', 'ts'), ('rejection', 'ts')])
def test_source_payload_cannot_smuggle_a_future_resolution(stream, field):
    with pytest.raises(ValueError, match='cannot exceed observed_at'):
        event(stream=stream, key='e1' if stream == 'rejection' else 'trade1',
              payload_json=json.dumps({field: (T + HOUR).timestamp()}))


def test_rejection_key_must_be_its_append_only_event_id():
    with pytest.raises(ValueError):
        event(stream='rejection', key='shared')


@pytest.mark.parametrize('events', ['list', 'duplicate_id', 'duplicate_sequence', 'reversed',
    'reversed_publication', 'before_start', 'beyond_coverage', 'untyped'])
def test_journal_rejects_corrupt_order_or_coverage_instead_of_sorting(events):
    a = event()
    b = event(event_id='e2', sequence=2)
    cases = {
        'list': [a], 'duplicate_id': (a, replace(b, event_id='e1')),
        'duplicate_sequence': (a, replace(b, sequence=1)), 'reversed': (b, a),
        'reversed_publication': (replace(a, available_at=T + US), b),
        'before_start': (replace(a, observed_at=T - US),),
        'beyond_coverage': (replace(a, available_at=T + HOUR + US),),
        'untyped': ({'state': 'OPEN'},),
    }
    with pytest.raises(ValueError):
        journal(cases[events])


@pytest.mark.parametrize('field,value', [('journal_id', ''), ('origin', 'economic_tp1'),
    ('complete', 1), ('complete', 'true'), ('start_at', T.replace(tzinfo=None)),
    ('covered_through', T - US)])
def test_journal_metadata_validation(field, value):
    with pytest.raises(ValueError):
        journal(**{field: value})


def test_memory_requires_typed_journal_and_exact_aware_decision_time():
    with pytest.raises(ValueError):
        api().memory_asof({}, T)
    with pytest.raises(ValueError):
        api().memory_asof(journal(), T.replace(tzinfo=None))
    with pytest.raises(ValueError):
        api().memory_asof(journal(), pd.Timestamp(T) + pd.Timedelta(nanoseconds=1))


def test_checkpoint_json_roundtrip_and_resumed_append_match_continuous_journal():
    a = event()
    b = event(event_id='e2', sequence=2, available_at=T + US,
              observed_at=T + US, payload_json='{"state":"OPEN"}')
    first = journal((a,), covered_through=T)
    restored = api().restore_memory(json.loads(json.dumps(api().checkpoint_memory(first))))
    assert restored == first
    resumed = replace(restored, events=restored.events + (b,), covered_through=T + HOUR)
    continuous = journal((a, b))
    assert api().memory_asof(resumed, T + US) == api().memory_asof(continuous, T + US)
    assert api().memory_asof(resumed, T) == api().memory_asof(first, T)


@pytest.mark.parametrize('mutation', ['payload', 'schema', 'checksum', 'extra', 'missing', 'sequence'])
def test_checkpoint_tampering_rejected(mutation):
    c = api().checkpoint_memory(journal((event(),)))
    if mutation == 'payload':
        c['journal']['events'][0]['payload_json'] = '{"state":"DONE"}'
    elif mutation == 'schema':
        c['schema'] = 'other'
    elif mutation == 'checksum':
        c['checksum'] = '0' * 64
    elif mutation == 'extra':
        c['unknown'] = True
    elif mutation == 'missing':
        del c['journal']['origin']
    else:
        c['journal']['events'][0]['sequence'] = True
    with pytest.raises(ValueError):
        api().restore_memory(c)


def test_events_and_journals_are_frozen_and_checkpoints_detached():
    e = event()
    j = journal((e,))
    with pytest.raises(FrozenInstanceError):
        e.sequence = 99
    with pytest.raises(FrozenInstanceError):
        j.complete = False
    c = api().checkpoint_memory(j)
    c['journal']['events'].clear()
    assert api().memory_asof(j, T)['selected_event_ids'] == ['e1']


def test_epoch_json_decimal_at_exact_microsecond_is_not_a_future_event():
    t = T.replace(microsecond=123456)
    e = event(observed_at=t, available_at=t,
              payload_json='{"ts":1788775200.123456}')
    assert api().memory_asof(journal((e,)), t)['tracker_state']['trade1']['ts'] == 1788775200.123456


@pytest.mark.parametrize('epoch', ['1788775200.1234562', '1788775200.12345601'])
def test_submicrosecond_future_epoch_is_not_rounded_back_into_snapshot(epoch):
    t = T.replace(microsecond=123456)
    with pytest.raises(ValueError):
        event(observed_at=t, available_at=t, payload_json='{"ts":' + epoch + '}')


@pytest.mark.parametrize('mutation', ['extra_event_field', 'extra_journal_field',
    'nanosecond_string', 'naive_string', 'noncanonical_payload', 'bad_sequence',
    'duplicate_id', 'out_of_coverage', 'wrong_origin', 'bad_events_container'])
def test_restore_validates_structure_even_when_checksum_is_recomputed(mutation):
    c = api().checkpoint_memory(journal((event(),)))
    row = c['journal']['events'][0]
    if mutation == 'extra_event_field':
        row['ignored'] = True
    elif mutation == 'extra_journal_field':
        c['journal']['ignored'] = True
    elif mutation == 'nanosecond_string':
        row['observed_at'] = '2026-09-07T10:00:00.000000001+00:00'
    elif mutation == 'naive_string':
        row['observed_at'] = '2026-09-07T10:00:00'
    elif mutation == 'noncanonical_payload':
        row['payload_json'] = '{ "state" : "PENDING" }'
    elif mutation == 'bad_sequence':
        row['sequence'] = True
    elif mutation == 'duplicate_id':
        c['journal']['events'].append(dict(row, sequence=2))
    elif mutation == 'out_of_coverage':
        row['available_at'] = (T + HOUR + US).isoformat()
    elif mutation == 'wrong_origin':
        c['journal']['origin'] = 'economic_tp1'
    else:
        c['journal']['events'] = {}
    unsigned = {key: c[key] for key in ('schema', 'journal')}
    c['checksum'] = hashlib.sha256(json.dumps(unsigned, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
    with pytest.raises(ValueError):
        api().restore_memory(c)


@pytest.mark.parametrize('precision', [1, 6, 10, 16, 28, 50])
def test_causal_epoch_boundary_does_not_depend_on_ambient_decimal_precision(precision):
    t = T.replace(microsecond=900000)
    with localcontext() as ctx:
        ctx.prec = precision
        with pytest.raises(ValueError, match='cannot exceed observed_at'):
            event(observed_at=t, available_at=t, payload_json='{"ts":1788775200.95}')
        e = event(observed_at=t, available_at=t, payload_json='{"ts":1788775200.9}')
        assert e.payload_json == '{"ts":1788775200.9}'


def test_rejection_valid_timestamp_reaches_projection():
    e = event(stream='rejection', key='e1', payload_json='{"ts":1788775200}')
    assert api().memory_asof(journal((e,)), T)['rejection_events'] == [{'ts': 1788775200}]


def test_epoch_that_loses_precision_in_json_normalization_is_rejected_at_ingestion():
    t = datetime(2255, 1, 1, microsecond=1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match='loses precision'):
        event(observed_at=t, available_at=t, payload_json='{"ts":8993721600.000001}')


@pytest.mark.parametrize('precision', [1, 10, 28])
@pytest.mark.parametrize('t,payload', [
    (datetime(2255, 1, 1, microsecond=2, tzinfo=timezone.utc), '{"ts":8993721600.000002}'),
    (datetime(1969, 12, 31, 23, 59, 59, 900000, tzinfo=timezone.utc), '{"ts":-0.1}'),
])
def test_representable_epochs_roundtrip_without_numeric_context_dependence(precision, t, payload):
    with localcontext() as ctx:
        ctx.prec = precision
        e = event(observed_at=t, available_at=t, payload_json=payload)
        j = journal((e,), start_at=t, covered_through=t)
        restored = api().restore_memory(api().checkpoint_memory(j))
        assert restored == j
        assert api().memory_asof(restored, t) == api().memory_asof(j, t)


@pytest.mark.parametrize('field', ['event_id', 'key', 'journal_id'])
@pytest.mark.parametrize('invalid', ['\ud800', 'name\udfff'])
def test_non_utf8_identity_is_rejected_before_journal_can_be_accepted(field, invalid):
    with pytest.raises(ValueError, match=field + ' must be UTF-8'):
        if field == 'journal_id':
            journal(journal_id=invalid)
        else:
            event(**{field: invalid})


def test_non_ascii_identities_survive_snapshot_and_checkpoint():
    e = event(event_id='אירוע-😀', key='עסקה-זהב')
    j = journal((e,), journal_id='יומן-é')
    restored = api().restore_memory(api().checkpoint_memory(j))
    snapshot = api().memory_asof(restored, T)
    assert snapshot['journal_id'] == 'יומן-é'
    assert snapshot['selected_event_ids'] == ['אירוע-😀']
    assert snapshot['tracker_state'] == {'עסקה-זהב': {'state': 'PENDING'}}
