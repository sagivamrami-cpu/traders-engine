"""Original journal behavior through raw memory IO, never a live queue."""
from collections import deque
from contextlib import contextmanager
import importlib
import importlib.util
import json

import pytest


def api():
    name = 'trading_system.tree_replay._vendor.outbox_journal'
    assert importlib.util.find_spec(name) is not None, 'outbox journal missing'
    return importlib.import_module(name)


def row(**changes):
    return dict(id='ae73500e104a8e28', ts=120., text='notice', to_group=False,
                kind='lifecycle', state='PENDING', attempts=0,
                sent_personal=False, sent_group=False) | changes


def lines(*rows):
    return ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)


class Raw:
    def __init__(self, text='', times=(120.,)):
        self.text = text
        self.times = deque(times)
        self.calls = []
        self.locked = False
        self.handle = object()
        self.state = {}
        self.offline = True
        self.read_error = self.write_error = self.acquire_error = None

    def now_epoch(self):
        value = self.times.popleft() if len(self.times) > 1 else self.times[0]
        self.calls.append(('clock', value))
        return value

    def journal_exists(self):
        self.calls.append(('exists', self.locked))
        return self.text is not None

    def journal_text(self, *, encoding):
        assert encoding == 'utf-8'
        self.calls.append(('read', self.locked))
        if self.read_error:
            raise self.read_error
        return self.text

    def mkdir(self, path, *, parents, exist_ok):
        assert (path, parents, exist_ok) == ('chart-desk/out', True, True)
        self.calls.append(('mkdir', self.locked))

    @contextmanager
    def open_append_lock(self, path, mode):
        assert (path, mode) == ('chart-desk/out/outbox.append.lock', 'a+')
        self.calls.append(('lock_open',))
        try:
            yield self.handle
        finally:
            self.calls.append(('lock_close',))

    def try_acquire(self, handle, *, timeout):
        assert handle is self.handle and timeout is None and not self.locked
        self.calls.append(('acquire', timeout))
        if self.acquire_error:
            raise self.acquire_error
        self.locked = True
        return True

    def release(self, handle):
        assert handle is self.handle and self.locked
        self.calls.append(('release',))
        self.locked = False

    def assert_offline(self):
        self.calls.append(('guard', self.locked))
        if not self.offline:
            raise RuntimeError('not an offline sink')

    @contextmanager
    def open_journal(self, mode, *, encoding):
        assert (mode, encoding) == ('a', 'utf-8') and self.locked
        self.calls.append(('write_open',))
        owner = self
        class Writer:
            def write(self, value):
                assert owner.locked and isinstance(value, str)
                owner.calls.append(('write', value))
                if owner.write_error:
                    raise owner.write_error
                owner.text = (owner.text or '') + value
        try:
            yield Writer()
        finally:
            self.calls.append(('write_close',))

    def load(self):
        self.calls.append(('load',))
        return self.state


def test_enqueue_twice_has_one_literal_row_and_preserves_order():
    raw = Raw(text=None)
    journal = api().OutboxJournal(raw)
    assert raw.calls == []
    assert journal.enqueue('notice', False) == 'ae73500e104a8e28'
    assert json.loads(raw.text) == row()
    assert raw.calls == [
        ('clock', 120.), ('mkdir', False), ('lock_open',), ('acquire', None),
        ('exists', True), ('guard', True), ('mkdir', True), ('write_open',),
        ('write', lines(row())), ('write_close',), ('release',), ('lock_close',),
    ]
    assert journal.enqueue('notice', False) == 'ae73500e104a8e28'
    assert len(raw.text.splitlines()) == 1
    assert journal.pending() == [row()]


@pytest.mark.parametrize('text', [None, [], ('not', 'text'), 0, '', ' \n\t'])
def test_invalid_message_never_reads_clock_or_queue(text, capsys):
    raw = Raw()
    assert api().OutboxJournal(raw).enqueue(text, True) == ''
    assert raw.calls == [] and raw.text == ''
    assert 'refused a non-message payload' in capsys.readouterr().err


@pytest.mark.parametrize('state', ['DELIVERED', 'RESOLVED'])
def test_terminal_same_id_never_resurrects_or_upgrades(state):
    original = lines(row(state=state, attempts=3, sent_personal=True))
    raw = Raw(original)
    assert api().OutboxJournal(raw).enqueue('notice', True) == 'ae73500e104a8e28'
    assert raw.text == original
    assert not any(c[0] in ('write', 'guard') for c in raw.calls)


@pytest.mark.parametrize('to_group', [False, True])
def test_pending_duplicate_preserves_attempts_and_delivery_flags(to_group):
    raw = Raw(lines(row(attempts=4, sent_personal=True)))
    journal = api().OutboxJournal(raw)
    assert journal.enqueue('notice', to_group) == 'ae73500e104a8e28'
    expected = row(attempts=4, sent_personal=True, to_group=to_group)
    if to_group:
        expected['last_ts'] = 120.
    assert journal.pending() == [expected]
    assert len(raw.text.splitlines()) == (2 if to_group else 1)
    if to_group:
        assert json.loads(raw.text.splitlines()[1]) == {
            'id': 'ae73500e104a8e28', 'ts': 120., 'state': 'PENDING', 'to_group': True}


@pytest.mark.parametrize('now,deduped', [(180., True), (720., True), (720.001, False)])
def test_cross_minute_exact_text_boundary(now, deduped):
    raw = Raw(lines(row(attempts=2, sent_group=True)), times=(now,))
    journal = api().OutboxJournal(raw)
    result = journal.enqueue('notice', False)
    assert (result == 'ae73500e104a8e28') is deduped
    assert len(raw.text.splitlines()) == (1 if deduped else 2)
    assert journal.pending()[0] == row(attempts=2, sent_group=True)
    if not deduped:
        latest = json.loads(raw.text.splitlines()[-1])
        assert latest['ts'] == 720.001 and latest['attempts'] == 0


def test_cross_minute_upgrade_keeps_original_ts_and_first_matching_id():
    raw = Raw(lines(row(id='first', attempts=3), row(id='second', ts=110.)), times=(180.,))
    journal = api().OutboxJournal(raw)
    assert journal.enqueue('notice', True) == 'first'
    assert json.loads(raw.text.splitlines()[-1]) == {
        'id': 'first', 'ts': 180., 'state': 'PENDING', 'to_group': True}
    assert journal.pending() == [row(id='second', ts=110.),
        row(id='first', attempts=3, to_group=True, last_ts=180.)]


def test_different_text_does_not_deduplicate():
    raw = Raw(lines(row()))
    journal = api().OutboxJournal(raw)
    other = journal.enqueue('notice changed', False, kind='park_lost')
    assert other != 'ae73500e104a8e28'
    assert len(journal.pending()) == 2
    assert journal.pending()[1]['kind'] == 'park_lost'


def test_jsonl_torn_lines_and_merged_pending_payloads():
    raw = Raw('\n{broken\n' + lines(row(),
        {'id': 'ae73500e104a8e28', 'ts': 140., 'attempts': 5, 'sent_personal': True},
        row(id='older', ts=100., text=None),
        {'id': 'orphan', 'ts': 1., 'state': 'PENDING'},
        row(id='finished', state='DELIVERED')))
    assert api().OutboxJournal(raw).pending() == [row(id='older', ts=100., text=None),
        row(attempts=5, sent_personal=True, last_ts=140.)]


@pytest.mark.parametrize('text,error', [('[]\n', TypeError), ('{}\n', KeyError)])
def test_parsed_malformed_rows_are_not_silently_hidden(text, error):
    raw = Raw(text)
    with pytest.raises(error):
        api().OutboxJournal(raw).enqueue('notice', False)
    assert raw.calls[-2:] == [('release',), ('lock_close',)] and not raw.locked


@pytest.mark.parametrize('failure', ['read', 'write', 'acquire', 'offline'])
def test_effect_failure_and_lock_cleanup(failure):
    raw = Raw()
    if failure == 'offline':
        raw.offline = False
        expected = RuntimeError
    else:
        setattr(raw, failure + '_error', OSError(failure))
        expected = OSError
    with pytest.raises(expected):
        api().OutboxJournal(raw).enqueue('notice', False)
    assert raw.text == '' and not raw.locked and raw.calls[-1] == ('lock_close',)
    assert (('release',) in raw.calls) is (failure != 'acquire')
    if failure == 'offline':
        assert not any(c[0] == 'write_open' for c in raw.calls)


@pytest.mark.parametrize('born,kept', [(100., True), (0., False), (120., False), (121., False)])
def test_born_must_be_truthy_and_older(born, kept):
    raw = Raw()
    journal = api().OutboxJournal(raw)
    journal.remember_born('notice', born)
    assert raw.calls == []
    journal.enqueue('notice', False)
    assert json.loads(raw.text) == (row(born=100.) if kept else row())


def test_born_is_consumed_on_terminal_enqueue_and_isolated_per_process():
    raw = Raw(lines(row(state='DELIVERED')))
    first = api().OutboxJournal(raw)
    first.remember_born('notice', 90.)
    second_raw = Raw()
    second = api().OutboxJournal(second_raw)
    second.enqueue('notice', False)
    assert json.loads(second_raw.text) == row()
    first.enqueue('notice', False)
    raw.times = deque([180.])
    first.enqueue('notice', False)
    latest = json.loads(raw.text.splitlines()[-1])
    assert latest['ts'] == 180. and 'born' not in latest


def test_invalid_born_raises_before_any_effect():
    raw = Raw()
    with pytest.raises(ValueError):
        api().OutboxJournal(raw).remember_born('notice', 'bad')
    assert raw.calls == [] and raw.text == ''


@pytest.mark.parametrize('duplicate_time', [120., 180.])
@pytest.mark.parametrize('upgrade', [False, True])
def test_pending_duplicate_consumes_birth_before_later_new_event(duplicate_time, upgrade):
    raw = Raw(lines(row(attempts=2)), times=(duplicate_time,))
    journal = api().OutboxJournal(raw)
    journal.remember_born('notice', 90.)
    assert journal.enqueue('notice', upgrade) == 'ae73500e104a8e28'
    existing = journal.pending()[0]
    assert existing['ts'] == 120. and existing['attempts'] == 2
    assert existing['to_group'] is upgrade
    raw.times = deque([721.])
    journal.enqueue('notice', False)
    latest = json.loads(raw.text.splitlines()[-1])
    assert latest['ts'] == 721. and latest['attempts'] == 0
    assert latest['state'] == 'PENDING' and 'born' not in latest


def test_actual_group_thread_context_precedes_append_lock_and_has_own_clock():
    raw = Raw(times=(120., 122.))
    raw.state = {'t': {'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110.,
                       'stop': 99.7, 'targets': [('target', 115.)], 'ts': 100., 'state': 'OPEN'}}
    journal = api().OutboxJournal(raw)
    journal.enqueue('▶️ XAUUSD BUY 110.00', True)
    saved = json.loads(raw.text)
    assert saved['ts'] == 120. and saved['reply_required'] is True
    assert saved['trade_context'] == {
        'symbol': 'OANDA:XAUUSD', 'direction': 'לונג', 'entry': 110., 'stop': 99.7,
        'targets': [['target', 115.]], 'style': None, 'trade_id': None,
        'ts': 100., 'event_ts': 122.}
    assert raw.calls[:4] == [('clock', 120.), ('load',), ('clock', 122.), ('mkdir', False)]


@pytest.mark.parametrize('text,group', [('notice', True), ('▶️ XAUUSD BUY 110.00', False)])
def test_no_thread_claim_avoids_tracker_load(text, group):
    raw = Raw()
    api().OutboxJournal(raw).enqueue(text, group)
    saved = json.loads(raw.text)
    assert 'reply_required' not in saved and 'trade_context' not in saved
    assert ('load',) not in raw.calls
    assert [c for c in raw.calls if c[0] == 'clock'] == [('clock', 120.)]


def test_supplied_context_avoids_load_and_second_clock():
    raw = Raw()
    api().OutboxJournal(raw).enqueue('▶️ XAUUSD BUY 110.00', True, trade_context={'entry': 110.})
    saved = json.loads(raw.text)
    assert saved['reply_required'] and saved['trade_context'] == {'entry': 110.}
    assert ('load',) not in raw.calls
    assert [c for c in raw.calls if c[0] == 'clock'] == [('clock', 120.)]


def test_resolve_and_resolve_text_use_new_clock_and_real_journal_marks():
    raw = Raw(lines(row(id='one'), row(id='two', ts=119.),
                    row(id='other', text='notice more'), row(id='done', state='DELIVERED')),
              times=(180., 181.))
    journal = api().OutboxJournal(raw)
    assert journal.resolve_text('notice', 'contradicted') == 2
    assert [json.loads(l) for l in raw.text.splitlines()[-2:]] == [
        {'id': 'two', 'ts': 180., 'state': 'RESOLVED', 'why': 'contradicted'},
        {'id': 'one', 'ts': 181., 'state': 'RESOLVED', 'why': 'contradicted'}]
    assert journal.pending() == [row(id='other', text='notice more')]
    assert journal.resolve_text('notice', 'again') == 0
    assert [c for c in raw.calls if c[0] == 'acquire'] == [('acquire', None)] * 2


def test_non_ascii_payload_is_written_as_utf8_text_with_one_newline():
    raw = Raw()
    api().OutboxJournal(raw).enqueue('הודעה', False)
    assert 'הודעה' in raw.text and '\\u05' not in raw.text
    assert raw.text.endswith('\n') and len(raw.text.splitlines()) == 1
