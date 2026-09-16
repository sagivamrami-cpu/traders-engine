"""Lifecycle-gate source behavior over raw offline evidence and effects."""
from contextlib import contextmanager
import io
import importlib
import importlib.util
import json
from types import SimpleNamespace

import pandas as pd
import pytest


def api():
    name = 'trading_system.tree_replay._vendor.lifecycle_gate'
    assert importlib.util.find_spec(name) is not None, 'lifecycle gate missing'
    return importlib.import_module(name)


class Raw:
    """In-memory raw artifacts only; it supplies no gate/receipt/verdict answer."""
    def __init__(self):
        self.text = None
        self.parked = None
        self.locked = False
        self.handle = object()
        self.calls = []
        self.frame = None
        self.epoch = 120.
        self.offline = True
        self.atomic_failure = None
        self.receipt_mtime = FileNotFoundError('no delivery receipt')
        self.receipts = ''

    def now_epoch(self):
        self.calls.append(('clock',))
        return self.epoch

    def journal_exists(self):
        return self.text is not None

    def journal_text(self, *, encoding):
        assert encoding == 'utf-8'
        return self.text

    def mkdir(self, path, *, parents, exist_ok):
        self.calls.append(('mkdir', path))

    @contextmanager
    def open_append_lock(self, path, mode):
        assert (path, mode) == ('chart-desk/out/outbox.append.lock', 'a+')
        yield self.handle

    def try_acquire(self, handle, *, timeout):
        assert handle is self.handle and timeout is None and not self.locked
        self.locked = True

    def release(self, handle):
        assert handle is self.handle and self.locked
        self.locked = False

    def assert_offline(self):
        self.calls.append(('offline',))
        if not self.offline:
            raise RuntimeError('not an offline sink')

    @contextmanager
    def open_journal(self, mode, *, encoding):
        assert (mode, encoding) == ('a', 'utf-8') and self.locked
        owner = self
        class Writer:
            def write(self, value):
                owner.text = (owner.text or '') + value
        yield Writer()

    def park_exists(self):
        return self.parked is not None

    def park_text(self, *, encoding):
        assert encoding == 'utf-8'
        return self.parked

    def load(self):
        raise AssertionError('ordinary text must not load tracker state')

    def now_utc(self):
        return pd.Timestamp(self.epoch, unit='s', tz='UTC')

    def fetch_corrected(self, symbol, timeframe, days):
        assert (symbol, timeframe, days) == ('OANDA:XAUUSD', '15m', 3)
        return self.frame, None

    def fetch_json(self, url, *, timeout):
        raise AssertionError('non-Binance replay must not request venue JSON')

    def receipt_stat(self):
        if isinstance(self.receipt_mtime, Exception):
            raise self.receipt_mtime
        return SimpleNamespace(st_mtime_ns=self.receipt_mtime)

    def receipt_text(self, *, encoding):
        assert encoding == 'utf-8'
        return self.receipts

    def format_il_clock(self, epoch):
        return f'IL:{epoch:.0f}'

    def atomic_mkdir(self, path, *, parents, exist_ok):
        assert (path, parents, exist_ok) == ('chart-desk/out', True, True)
        self.calls.append(('atomic_mkdir',))

    def atomic_mkstemp(self, path, *, suffix):
        assert (path, suffix) == ('chart-desk/out', '.tmp')
        self.calls.append(('mkstemp',))
        return 7, 'temporary.json'

    @contextmanager
    def atomic_fdopen(self, fd, mode, *, encoding):
        assert (fd, mode, encoding) == (7, 'w', 'utf-8')
        self.temporary = io.StringIO()
        yield self.temporary

    def atomic_fsync(self, handle):
        assert handle is self.temporary
        self.calls.append(('fsync',))
        if self.atomic_failure:
            raise self.atomic_failure

    def atomic_replace(self, tmp, path):
        assert (tmp, path) == ('temporary.json', 'chart-desk/out/parked_claims.json')
        self.parked = self.temporary.getvalue()
        self.calls.append(('replace',))

    def atomic_unlink(self, tmp):
        assert tmp == 'temporary.json'
        self.calls.append(('unlink',))


def test_persist_unmatched_message_returns_original_and_enqueues_actual_journal():
    raw = Raw()
    msgs = [('ordinary status update', False)]
    assert api().LifecycleGate(raw)._persist_gated_lifecycle(msgs, {}) == msgs
    assert json.loads(raw.text) == {
        'id': '4c2d7776436c69e6', 'ts': 120., 'text': 'ordinary status update',
        'to_group': False, 'kind': 'lifecycle', 'state': 'PENDING', 'attempts': 0,
        'sent_personal': False, 'sent_group': False,
    }
    assert raw.parked is None and raw.calls == [
        ('clock',), ('mkdir', 'chart-desk/out'), ('offline',),
        ('mkdir', 'chart-desk/out'),
    ]


def test_empty_persistence_returns_before_any_gate_or_effect():
    raw = Raw()
    assert api().LifecycleGate(raw)._persist_gated_lifecycle([], {}) == []
    assert raw.calls == [] and raw.text is None and raw.parked is None


def test_persistence_keeps_original_mixed_message_order_in_actual_journal():
    raw = Raw()
    msgs = [('first ordinary update', False), ('second ordinary update', False)]
    assert api().LifecycleGate(raw)._persist_gated_lifecycle(msgs, {}) == msgs
    assert [json.loads(line)['text'] for line in raw.text.splitlines()] == [
        'first ordinary update', 'second ordinary update',
    ]


def test_park_keeps_first_full_claim_line_and_unparks_only_exact_text():
    raw = Raw()
    gate = api().LifecycleGate(raw)
    trade = {'symbol': 'OANDA:XAUUSD', 'entry': 110., 'to_group': True}
    first = '✅ XAUUSD BUY 110.00 · TP1 @ 115.00\nfirst journey'
    same_claim_later_detail = '✅ XAUUSD BUY 110.00 · TP1 @ 115.00\nchanged journey'
    gate._park(trade, first)
    first_image = raw.parked
    gate._park(trade, same_claim_later_detail)
    assert raw.parked == first_image
    key = 'OANDA:XAUUSD|110.0|✅ XAUUSD BUY 110.00 · TP1 @ 115.00'
    assert json.loads(raw.parked) == {key: {
        'text': first, 'ts': 120., 'symbol': 'OANDA:XAUUSD', 'entry': 110.,
        'to_group': True,
    }}
    gate._unpark_text(same_claim_later_detail)
    assert raw.parked == first_image
    gate._unpark_text(first)
    assert json.loads(raw.parked) == {}


def test_replay_absent_or_bad_parked_bytes_does_not_read_state_or_clock():
    raw = Raw()
    gate = api().LifecycleGate(raw)
    assert gate.replay_parked() == [] and raw.calls == []
    raw.parked = '{torn'
    assert gate.replay_parked() == [] and raw.calls == []


def test_replay_missing_trade_silently_drops_claim_and_writes_empty_keep_image():
    raw = Raw()
    raw.parked = json.dumps({'claim': {
        'text': '✅ XAUUSD BUY 110.00 · הושג @ 115.00', 'ts': 100.,
        'symbol': 'OANDA:XAUUSD', 'entry': 110., 'to_group': False,
    }}, ensure_ascii=False)
    assert api().LifecycleGate(raw).replay_parked({}) == []
    assert json.loads(raw.parked) == {} and raw.text is None


def test_replay_release_uses_actual_verifier_then_remembers_original_birth(capsys):
    raw = Raw()
    raw.frame = pd.DataFrame(
        [dict(open=110., high=115., low=109., close=114.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC')]),
    )
    text = '✅ XAUUSD BUY 110.00 · הושג @ 115.00'
    raw.parked = json.dumps({'claim': {
        'text': text, 'ts': 100., 'symbol': 'OANDA:XAUUSD', 'entry': 110.,
        'to_group': True,
    }}, ensure_ascii=False)
    trade = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99., 'targets': [('TP1', 115.)], 'ts': 0., 'state': 'OPEN'}
    gate = api().LifecycleGate(raw)
    assert gate.replay_parked({'trade': trade}) == [(text, True)]
    assert json.loads(raw.parked) == {}
    assert gate.outbox._BORN == {text: 100.}
    assert 'released after the tape caught up' in capsys.readouterr().err


def test_replay_stale_actual_verdict_keeps_the_original_parked_claim():
    raw = Raw()
    raw.frame = pd.DataFrame(
        [dict(open=110., high=112., low=109., close=111.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC')]),
    )
    text = '✅ XAUUSD BUY 110.00 · הושג @ 115.00'
    parked = {'claim': {'text': text, 'ts': 100., 'symbol': 'OANDA:XAUUSD',
                        'entry': 110., 'to_group': False}}
    raw.parked = json.dumps(parked, ensure_ascii=False)
    trade = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99., 'targets': [('TP1', 115.)], 'ts': 0., 'state': 'OPEN'}
    gate = api().LifecycleGate(raw)
    assert gate.replay_parked({'trade': trade}) == []
    assert json.loads(raw.parked) == parked
    assert gate.outbox._BORN == {}


def test_target_gate_uses_actual_tape_then_demotes_missing_group_receipt():
    raw = Raw()
    raw.frame = pd.DataFrame(
        [dict(open=110., high=115., low=109., close=114.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC')]),
    )
    trade = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99., 'targets': [('TP1', 115.)], 'ts': 0., 'state': 'OPEN'}
    text = '🔒 XAUUSD BUY 110.00 · TP1'
    assert api().LifecycleGate(raw).gate([(text, True)], {'trade': trade}) == (
        [(text, False)], [(text, 'no group receipt for the entry — sent to Sagiv only')],
    )


def test_expired_park_is_dropped_and_creates_only_a_courtesy_journal_note(capsys):
    raw = Raw()
    raw.parked = json.dumps({'claim': {
        'text': '✅ XAUUSD BUY 110.00 · הושג @ 115.00', 'ts': -3481.,
        'symbol': 'OANDA:XAUUSD', 'entry': 110., 'to_group': True,
    }}, ensure_ascii=False)
    assert api().LifecycleGate(raw).replay_parked({}) == []
    assert json.loads(raw.parked) == {}
    note = json.loads(raw.text)
    assert note['kind'] == 'park_lost' and note['to_group'] is False
    assert 'IL:-3481' in note['text'] and 'trade_admin resend' in note['text']
    assert 'expired unverified' in capsys.readouterr().err


def test_stale_claim_is_parked_but_never_persisted_as_a_blocked_journal_note():
    raw = Raw()
    raw.frame = pd.DataFrame(
        [dict(open=110., high=112., low=109., close=111.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC')]),
    )
    text = '✅ XAUUSD BUY 110.00 · הושג @ 115.00'
    trade = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99., 'targets': [('TP1', 115.)], 'ts': 0., 'state': 'OPEN'}
    msgs = [(text, False)]
    assert api().LifecycleGate(raw)._persist_gated_lifecycle(msgs, {'trade': trade}) == msgs
    assert raw.text is None
    parked = json.loads(raw.parked)
    assert list(parked.values()) == [{
        'text': text, 'ts': 120., 'symbol': 'OANDA:XAUUSD', 'entry': 110.,
        'to_group': False,
    }]


def test_source_park_uses_matched_trade_destination_not_message_destination():
    raw = Raw()
    raw.frame = pd.DataFrame(
        [dict(open=110., high=112., low=109., close=111.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC')]),
    )
    text = '✅ XAUUSD BUY 110.00 · הושג @ 115.00'
    trade = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99., 'targets': [('TP1', 115.)], 'ts': 0., 'state': 'OPEN'}
    gate = api().LifecycleGate(raw)
    assert gate._persist_gated_lifecycle([(text, True)], {'trade': trade}) == [(text, True)]
    assert list(json.loads(raw.parked).values())[0]['to_group'] is False
    raw.frame = pd.DataFrame(
        [dict(open=110., high=115., low=109., close=114.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC')]),
    )
    assert gate.replay_parked({'trade': trade}) == [(text, False)]


def test_exact_expiry_boundary_stays_parked_but_fractionally_later_expires():
    text = '✅ XAUUSD BUY 110.00 · הושג @ 115.00'
    trade = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99., 'targets': [('TP1', 115.)], 'ts': 0., 'state': 'OPEN'}
    retained = Raw()
    retained.epoch = 3700.
    retained.frame = pd.DataFrame([dict(open=110., high=112., low=109., close=111.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC')]))
    retained.parked = json.dumps({'claim': {'text': text, 'ts': 100.,
        'symbol': 'OANDA:XAUUSD', 'entry': 110., 'to_group': False}}, ensure_ascii=False)
    assert api().LifecycleGate(retained).replay_parked({'trade': trade}) == []
    assert json.loads(retained.parked)['claim']['ts'] == 100.
    expired = Raw()
    expired.epoch = 3700.001
    expired.parked = retained.parked
    assert api().LifecycleGate(expired).replay_parked({}) == []
    assert json.loads(expired.parked) == {}
    assert json.loads(expired.text)['kind'] == 'park_lost'


def test_contradicted_replay_drops_claim_and_journals_courtesy_loss_note(capsys):
    raw = Raw()
    raw.frame = pd.DataFrame(
        [dict(open=110., high=112., low=109., close=111.),
         dict(open=111., high=112., low=110., close=111.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC'),
                                pd.Timestamp(900, unit='s', tz='UTC')]),
    )
    text = '✅ XAUUSD BUY 110.00 · הושג @ 115.00'
    raw.parked = json.dumps({'claim': {'text': text, 'ts': 100.,
        'symbol': 'OANDA:XAUUSD', 'entry': 110., 'to_group': False}}, ensure_ascii=False)
    trade = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99., 'targets': [('TP1', 115.)], 'ts': 0., 'state': 'OPEN'}
    assert api().LifecycleGate(raw).replay_parked({'trade': trade}) == []
    assert json.loads(raw.parked) == {}
    assert json.loads(raw.text)['kind'] == 'park_lost'
    assert 'dropped, tape now contradicts it' in capsys.readouterr().err


def test_park_lost_catches_courtesy_enqueue_failure_and_only_reports_stderr(capsys):
    raw = Raw()
    raw.offline = False
    rec = {'text': '✅ XAUUSD BUY 110.00 · הושג @ 115.00', 'ts': 100.}
    api().LifecycleGate(raw)._park_lost(rec, 'test')
    assert raw.text is None
    assert 'could not queue the loss note: not an offline sink' in capsys.readouterr().err


def test_contradicted_claim_is_not_parked_and_is_resolved_as_blocked_lifecycle():
    raw = Raw()
    raw.frame = pd.DataFrame(
        [dict(open=110., high=112., low=109., close=111.),
         dict(open=111., high=112., low=110., close=111.)],
        index=pd.DatetimeIndex([pd.Timestamp(0, unit='s', tz='UTC'),
                                pd.Timestamp(900, unit='s', tz='UTC')]),
    )
    text = '✅ XAUUSD BUY 110.00 · הושג @ 115.00'
    trade = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99., 'targets': [('TP1', 115.)], 'ts': 0., 'state': 'OPEN'}
    assert api().LifecycleGate(raw)._persist_gated_lifecycle([(text, False)],
                                                               {'trade': trade}) == [(text, False)]
    assert raw.parked is None
    saved = [json.loads(line) for line in raw.text.splitlines()]
    assert saved[0]['kind'] == 'blocked_lifecycle' and saved[0]['state'] == 'PENDING'
    assert saved[1] == {
        'id': saved[0]['id'], 'ts': 120., 'state': 'RESOLVED',
        'why': 'blocked by gate: המחיר לא הגיע ל-115.00 אחרי המילוי (00:00) — הקיצון היה 112.00',
    }


def test_ambiguous_group_claim_uses_actual_receipt_evidence_without_verifying_price():
    raw = Raw()
    raw.receipt_mtime = 1
    raw.receipts = json.dumps({
        'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
        'style': 'intraday', 'trade_id': '10ae2e475aa244ab',
        'ts': '1970-01-01T00:00:00Z',
    })
    first = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99.7, 'targets': [('TP1', 115.)], 'style': 'intraday',
             'ts': 0., 'state': 'OPEN'}
    second = dict(first, stop=98.7, targets=[('TP1', 116.)])
    text = '✅ XAUUSD BUY 110.00'
    assert api().LifecycleGate(raw).gate([(text, True)], {'one': first, 'two': second}) == (
        [(text, True)], [],
    )


def test_ambiguous_group_claim_without_any_receipt_is_demoted_with_diagnostic():
    raw = Raw()
    first = {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
             'stop': 99.7, 'targets': [('TP1', 115.)], 'style': 'intraday',
             'ts': 0., 'state': 'OPEN'}
    second = dict(first, stop=98.7, targets=[('TP1', 116.)])
    text = '✅ XAUUSD BUY 110.00'
    assert api().LifecycleGate(raw).gate([(text, True)], {'one': first, 'two': second}) == (
        [(text, False)], [(text, 'ambiguous lifecycle with no group receipt')],
    )


def test_atomic_park_writer_cleans_its_temporary_artifact_after_sync_failure():
    raw = Raw()
    raw.atomic_failure = OSError('fsync unavailable')
    with pytest.raises(OSError, match='fsync unavailable'):
        api().LifecycleGate(raw)._atomic_json(api().PARK, {'claim': {}})
    assert raw.parked is None
    assert raw.calls[-3:] == [('mkstemp',), ('fsync',), ('unlink',)]
