"""Actual lifecycle identity reads raw receipts/queue geometry, not verdicts."""
from copy import deepcopy
import importlib
import importlib.util
import json
from types import SimpleNamespace

import pandas as pd
import pytest

NOW = pd.Timestamp('2026-09-10T12:00:00Z').timestamp()
SYMBOL = 'OANDA:XAUUSD'
IDS = {'scalp': 'e25720e7d43c384f', 'intraday': '10ae2e475aa244ab', 'swing': '6d9c3b196be7b935'}
# IDs calculated from literal sorted compact JSON geometry with SHA256, not
# the implementation's _trade_identity. No final verdicts are injected.


def api():
    name = 'trading_system.tree_replay._vendor.lifecycle_identity'
    assert importlib.util.find_spec(name) is not None, 'lifecycle identity missing'
    return importlib.import_module(name)


def trade(**changes):
    return dict(dict(symbol=SYMBOL, direction='לונג', entry=110., stop=99.7,
                     targets=[('target', 115.)], style='intraday', ts=NOW,
                     state='OPEN'), **changes)


def receipt(**changes):
    return dict(dict(symbol=SYMBOL, direction='לונג', entry=110., style='intraday',
                     trade_id=IDS['intraday'], ts='2026-09-10T12:00:00Z'), **changes)


class Raw:
    def __init__(self, rows=None):
        self.calls = []
        self.mtime = 1
        self.text = '\n'.join(json.dumps(r) for r in (rows if rows is not None else [receipt()]))
        self.queues = {}
        self.state = {'trade': trade()}
        self.now = NOW + 17

    def receipt_stat(self):
        self.calls.append(('stat',))
        if isinstance(self.mtime, Exception):
            raise self.mtime
        return SimpleNamespace(st_mtime_ns=self.mtime)

    def receipt_text(self, *, encoding):
        self.calls.append(('receipt_text', encoding))
        if isinstance(self.text, Exception):
            raise self.text
        return self.text

    def queue_exists(self, path):
        self.calls.append(('queue_exists', path))
        return path in self.queues

    def queue_text(self, path, *, encoding):
        self.calls.append(('queue_text', path, encoding))
        value = self.queues[path]
        if isinstance(value, Exception):
            raise value
        return value

    def load(self):
        self.calls.append(('load',))
        if isinstance(self.state, Exception):
            raise self.state
        return self.state

    def now_epoch(self):
        self.calls.append(('clock',))
        return self.now


def test_same_entry_uses_named_target_to_identify_actual_trade():
    first, second = trade(), trade(stop=98., targets=[('other', 116.)])
    got, ambiguous = api()._match_trade_for_text('✅ XAUUSD BUY 110.00 · TP1 @ 115.00', {'one': first, 'two': second})
    assert got is first and ambiguous == []


def test_same_entry_uses_named_stop_to_identify_actual_trade():
    first, second = trade(), trade(stop=98.)
    got, ambiguous = api()._match_trade_for_text('🛑 XAUUSD BUY 110.00 · stop @ 99.70', {'one': first, 'two': second})
    assert got is first and ambiguous == []


@pytest.mark.parametrize('text,rows,winner,ambiguous', [
    ('XAUUSD BUY 110.00', [trade(), trade(entry=120.)], 0, []),
    ('XAUUSD BUY 99.70', [trade(), trade(entry=99.7)], 1, []),
    ('XAUUSD BUY 99.70', [trade(), trade(entry=120., stop=90.)], 0, []),
    ('XAUUSD BUY 99.70', [trade(), trade(entry=120.)], None, [0, 1]),
    ('XAUUSD BUY 110.00', [trade(), trade(stop=98.)], None, [0, 1]),
    ('XAUUSD BUY 110.00 115.00', [trade(), trade()], None, [0, 1]),
    ('XAUUSD BUY status', [trade(state='PENDING'), trade()], 1, []),
    ('XAUUSD BUY status', [trade(state='DONE'), trade(state='PENDING')], 1, []),
    ('XAUUSD BUY status', [trade(state='DONE')], 0, []),
    ('XAUUSD BUY status', [trade(), trade()], None, [0, 1]),
    ('XAUUSD BUY status', [trade(state='CANCELLED')], None, []),
    ('XAUUSD BUY 110.00', [trade(state='CANCELLED')], 0, []),
    ('XAUUSD SELL 110.00', [trade(), trade(direction='שורט')], 1, []),
    ('NAS100USD BUY 110.00', [trade()], None, []),
])
def test_matching_precedence_and_ambiguity(text, rows, winner, ambiguous):
    before = deepcopy(rows)
    got, matches = api()._match_trade_for_text(text, dict(enumerate(rows)))
    assert got is (None if winner is None else rows[winner])
    assert len(matches) == len(ambiguous)
    assert all(a is rows[i] for a, i in zip(matches, ambiguous))
    assert rows == before


def test_decimal_price_parser_and_tolerance_are_consumed_by_matcher():
    m = api()
    assert m._prices_in_text('TP1 110 1,234.50 0.02') == [1234.5, .02]
    assert m._text_has_price('0.02', 0.)
    assert not m._text_has_price('0.0201', 0.)
    a, b = trade(entry=0.), trade(entry=10.)
    assert m._match_trade_for_text('XAUUSD BUY 0.02', {'a': a, 'b': b}) == (a, [])
    assert m._match_trade_for_text('XAUUSD SELL BUY', {'a': a}) == (None, [])


@pytest.mark.parametrize('prefix', ['', '⏰ עדכון באיחור — נכון ל-10:00\n'])
@pytest.mark.parametrize('supplied', [False, True])
def test_context_uses_real_identity_matching_and_current_clock(prefix, supplied):
    raw = Raw()
    reader = api().LifecycleIdentity(raw)
    assert raw.calls == []
    text = prefix + '✅ XAUUSD BUY 110.00 · TP1 @ 115.00'
    got = reader.context(text, raw.state) if supplied else reader.context(text)
    assert got == dict(symbol=SYMBOL, direction='לונג', entry=110., stop=99.7,
                       targets=[('target', 115.)], style='intraday', trade_id=None,
                       ts=NOW, event_ts=NOW + 17)
    assert raw.calls == ([('clock',)] if supplied else [('load',), ('clock',)])


@pytest.mark.parametrize('price,accepted', [('0.011', True), ('0.0111', False)])
def test_context_entry_guard_is_stricter_than_matching_tolerance(price, accepted):
    raw = Raw()
    raw.state = {'a': trade(entry=0.)}
    got = api().LifecycleIdentity(raw).context('▶️ XAUUSD BUY ' + price)
    assert (got is not None) is accepted
    assert raw.calls == [('load',)] + ([('clock',)] if accepted else [])


@pytest.mark.parametrize('text,rows,calls', [
    ('ordinary text', {'a': trade()}, []),
    ('✅ XAUUSD BUY 110.00', {}, [('load',)]),
    ('✅ XAUUSD BUY 110.00', {'a': trade(), 'b': trade()}, [('load',)]),
])
def test_context_refusals_do_not_read_a_clock(text, rows, calls):
    raw = Raw()
    raw.state = rows
    assert api().LifecycleIdentity(raw).context(text) is None
    assert raw.calls == calls


@pytest.mark.parametrize('delta,allowed', [(-120., True), (-120.001, False), (86400., True)])
def test_actual_geometry_receipt_and_delivery_slack(delta, allowed):
    stamp = pd.Timestamp(NOW + delta, unit='s', tz='UTC').isoformat()
    raw = Raw([receipt(symbol='GOLD', ts=stamp)])
    reader = api().LifecycleIdentity(raw)
    assert raw.calls == []
    assert reader._group_has(trade()) is allowed
    assert raw.calls == [('stat',), ('receipt_text', 'utf-8')]


@pytest.mark.parametrize('change', [dict(trade_id='different'), dict(style='swing'),
    dict(direction='שורט'), dict(entry=111.), dict(symbol='NAS100'), dict(ts='bad time')])
def test_wrong_receipt_identity_or_old_unknown_time_does_not_authorize(change):
    assert not api().LifecycleIdentity(Raw([receipt(**change)]))._group_has(trade())


def test_receipt_cache_retains_same_mtime_then_refreshes_without_leaking_between_instances():
    raw = Raw()
    first = api().LifecycleIdentity(raw)
    assert first._group_has(trade())
    raw.text = ''
    assert first._group_has(trade())
    second = api().LifecycleIdentity(raw)
    assert not second._group_has(trade())
    raw.mtime = 2
    assert not first._group_has(trade())
    assert raw.calls == [('stat',), ('receipt_text', 'utf-8'), ('stat',),
                         ('stat',), ('receipt_text', 'utf-8'), ('stat',), ('receipt_text', 'utf-8')]


def test_initial_zero_mtime_and_missing_stat_preserve_original_no_read():
    raw = Raw()
    reader = api().LifecycleIdentity(raw)
    raw.mtime = 0
    assert not reader._group_has(trade())
    raw.mtime = FileNotFoundError('absent')
    assert not reader._group_has(trade())
    assert raw.calls == [('stat',), ('stat',)]


def test_receipt_read_failure_does_not_cache_a_false_success():
    raw = Raw()
    reader = api().LifecycleIdentity(raw)
    raw.text = OSError('cannot read')
    assert not reader._group_has(trade())
    raw.text = json.dumps(receipt())
    assert reader._group_has(trade())
    assert raw.calls == [('stat',), ('receipt_text', 'utf-8')] * 2


def test_torn_and_incomplete_lines_are_distinct_from_malformed_parsed_rows():
    raw = Raw([{}, receipt()])
    raw.text = '\n{torn\n' + raw.text
    assert api().LifecycleIdentity(raw)._group_has(trade())
    raw.text = '[]'
    with pytest.raises(AttributeError):
        api().LifecycleIdentity(raw)._group_has(trade())


@pytest.mark.parametrize('style', ['scalp', 'intraday', 'swing'])
def test_legacy_receipt_uses_queue_geometry_for_each_original_style(style):
    raw = Raw([receipt(style=None, trade_id=None, file='old.json')])
    raw.queues['chart-desk/out/group_queue/done/old.json'] = json.dumps(trade())
    # Root queue holds different geometry; done must win, not both read.
    raw.queues['chart-desk/out/group_queue/old.json'] = json.dumps(trade(stop=98.))
    assert api().LifecycleIdentity(raw)._group_has(trade(style=style))
    assert raw.calls == [('stat',), ('receipt_text', 'utf-8'),
        ('queue_exists', 'chart-desk/out/group_queue/done/old.json'),
        ('queue_text', 'chart-desk/out/group_queue/done/old.json', 'utf-8')]


def test_legacy_root_fallback_returns_literal_three_geometry_ids():
    raw = Raw()
    raw.queues['chart-desk/out/group_queue/old.json'] = json.dumps(trade())
    got = api().LifecycleIdentity(raw)._receipt_from_queue_file({'file': 'old.json'})
    assert got == [{'style': 'scalp', 'trade_id': 'e25720e7d43c384f'},
                   {'style': 'intraday', 'trade_id': '10ae2e475aa244ab'},
                   {'style': 'swing', 'trade_id': '6d9c3b196be7b935'}]
    assert raw.calls == [('queue_exists', 'chart-desk/out/group_queue/done/old.json'),
        ('queue_exists', 'chart-desk/out/group_queue/old.json'),
        ('queue_text', 'chart-desk/out/group_queue/old.json', 'utf-8')]


@pytest.mark.parametrize('body', ['{torn', '{}', '{"stop": 1}', OSError('unreadable')])
def test_bad_done_queue_does_not_fall_back_to_other_geometry(body):
    raw = Raw([receipt(style=None, trade_id=None, file='old.json')])
    raw.queues['chart-desk/out/group_queue/done/old.json'] = body
    raw.queues['chart-desk/out/group_queue/old.json'] = json.dumps(trade())
    assert not api().LifecycleIdentity(raw)._group_has(trade())
    assert ('queue_exists', 'chart-desk/out/group_queue/old.json') not in raw.calls


def test_non_json_receipt_filename_skips_queue_and_load_errors_propagate():
    raw = Raw()
    reader = api().LifecycleIdentity(raw)
    assert reader._receipt_from_queue_file({'file': 'direct:1'}) == []
    assert raw.calls == []
    raw.state = OSError('unknown state')
    with pytest.raises(OSError, match='unknown state'):
        reader.context('✅ XAUUSD BUY 110.00')
    assert raw.calls == [('load',)]
