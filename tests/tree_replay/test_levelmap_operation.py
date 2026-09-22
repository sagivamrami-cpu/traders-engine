"""Literal market-map outcomes over raw frame and advancing clock ports."""

import importlib
import importlib.util

import pandas as pd
import pytest

from trading_system.tree_replay._vendor.correction import Correction


SYMBOL = 'OANDA:XAUUSD'
NOW = pd.Timestamp('2026-09-09T14:00Z')


def api(name='levelmap_operation'):
    path = 'trading_system.tree_replay._vendor.' + name
    assert importlib.util.find_spec(path) is not None, f'Missing operation reader: {path}'
    return importlib.import_module(path)


def bars(count=1, end='2026-09-09T07:00Z', freq='5min', row=(103, 110, 90, 100)):
    return pd.DataFrame([row] * count, columns=['open', 'high', 'low', 'close'],
                        index=pd.date_range(end=end, periods=count, freq=freq))


def corr(source='tv_daily', seam=None, symbol=SYMBOL):
    return Correction(symbol, 0, source, 'n/a', 'synthetic', seam)


class RawSource:
    def __init__(self, frames=None, now=NOW, after=None):
        self.frames = {} if frames is None else frames
        self.now = now
        self.after = {} if after is None else after
        self.calls = []

    def fetch_corrected(self, symbol, timeframe, lookback):
        self.calls.append(('fetch', symbol, timeframe, lookback))
        key = (timeframe, lookback)
        if key in self.after:
            self.now = self.after[key]
        value = self.frames.get(key, LookupError('no synthetic frame'))
        if isinstance(value, Exception):
            raise value
        return value

    def now_utc(self):
        self.calls.append(('clock',))
        if isinstance(self.now, Exception):
            raise self.now
        return self.now


def named(levels):
    return [(x.name, x.price) for x in levels]


def test_session_uses_time_after_fetch_crosses_open():
    s = RawSource({('5m', 3): (bars(), corr())},
                  pd.Timestamp('2026-09-09T06:59:59Z'),
                  {('5m', 3): pd.Timestamp('2026-09-09T07:00Z')})
    assert named(api().LevelmapOperation(s)._session_open_levels(SYMBOL)) == [('LONDON-OPEN', 103)]
    assert s.calls == [('fetch', SYMBOL, '5m', 3), ('clock',)]


@pytest.mark.parametrize('now,opening,want', [
    ('2026-09-09T06:59:59Z', '2026-09-09T07:00Z', []),
    ('2026-09-09T07:00Z', '2026-09-09T07:00Z', [('LONDON-OPEN', 103)]),
    ('2026-09-09T15:29:59Z', '2026-09-09T07:00Z', [('LONDON-OPEN', 103)]),
    ('2026-09-09T15:30Z', '2026-09-09T07:00Z', []),
    ('2026-09-09T13:30Z', '2026-09-09T13:30Z', [('NY-OPEN', 103)]),
    ('2026-09-09T19:59:59Z', '2026-09-09T13:30Z', [('NY-OPEN', 103)]),
    ('2026-09-09T20:00Z', '2026-09-09T13:30Z', []),
    ('2026-01-07T07:59:59Z', '2026-01-07T08:00Z', []),
    ('2026-01-07T08:00Z', '2026-01-07T08:00Z', [('LONDON-OPEN', 103)]),
    ('2026-01-07T14:30Z', '2026-01-07T14:30Z', [('NY-OPEN', 103)]),
    ('2026-09-12T08:00Z', '2026-09-12T07:00Z', []),
    ('2026-09-13T08:00Z', '2026-09-13T07:00Z', []),
    ('2026-09-10T08:00Z', '2026-09-09T07:00Z', []),
])
def test_venue_boundaries_and_no_yesterday_carry(now, opening, want):
    s = RawSource({('5m', 3): (bars(end=opening), corr())}, pd.Timestamp(now))
    assert named(api().LevelmapOperation(s)._session_open_levels(SYMBOL)) == want


@pytest.mark.parametrize('value,missing', [
    (OSError('unavailable'), []), (None, []), ('empty', []),
    ('no_corr', ['פתיחות סשן לא זמינות — בסיס המחיר לא אומת']),
    ('none', ['פתיחות סשן לא זמינות — בסיס המחיר לא אומת']),
])
def test_early_returns_do_not_read_clock(value, missing):
    if value is None:
        value = (None, corr())
    elif isinstance(value, str):
        value = (bars(0), corr()) if value == 'empty' else (bars(), None if value == 'no_corr' else corr('none'))
    s = RawSource({('5m', 3): value}, RuntimeError('clock must not be read'))
    absent = []
    assert api().LevelmapOperation(s)._session_open_levels(SYMBOL, absent) == []
    assert absent == missing
    assert s.calls == [('fetch', SYMBOL, '5m', 3)]


@pytest.mark.parametrize('now', ['2026-09-09T07:00', '2026-09-09T10:00+03:00'])
def test_explicit_time_bypasses_clock_but_not_fetch(now):
    s = RawSource({('5m', 3): (bars(), corr())}, RuntimeError('not called'))
    assert named(api().LevelmapOperation(s)._session_open_levels(SYMBOL, now=now)) == [('LONDON-OPEN', 103)]
    assert s.calls == [('fetch', SYMBOL, '5m', 3)]
    s.frames = {}
    assert api().LevelmapOperation(s)._session_open_levels(SYMBOL, now=now) == []


def test_missing_exact_open_is_not_nearest_and_duplicate_uses_first():
    s = RawSource({('5m', 3): (bars(end='2026-09-09T07:05Z'), corr())},
                  pd.Timestamp('2026-09-09T08:00Z'))
    missing = []
    reader = api().LevelmapOperation(s)
    assert reader._session_open_levels(SYMBOL, missing) == []
    assert missing == ['LONDON-OPEN לא זמינה — נר הפתיחה לא בקלטת']
    duplicate = pd.concat([bars(), bars(row=(199, 200, 90, 100))])
    s.frames[('5m', 3)] = (duplicate, corr())
    assert named(reader._session_open_levels(SYMBOL)) == [('LONDON-OPEN', 103)]


@pytest.mark.parametrize('seam,want', [
    ('2026-09-09T07:00Z', [('LONDON-OPEN', 103)]),
    ('2026-09-09T07:00:00.000001Z', []),
])
def test_session_splice_is_per_opening_bar(seam, want):
    s = RawSource({('5m', 3): (bars(), corr('tv_spliced', pd.Timestamp(seam)))},
                  pd.Timestamp('2026-09-09T08:00Z'))
    missing = []
    assert named(api().LevelmapOperation(s)._session_open_levels(SYMBOL, missing)) == want
    assert missing == ([] if want else ["LONDON-OPEN לא זמינה — נר הפתיחה מהפרוקסי, לא מהצ'ארט"])


def test_native_btc_session_still_rejects_source_none():
    symbol = 'BINANCE:BTCUSDT'
    s = RawSource({('5m', 3): (bars(), corr('none', symbol=symbol))}, RuntimeError('unused'))
    assert api().LevelmapOperation(s)._session_open_levels(symbol) == []
    assert s.calls == [('fetch', symbol, '5m', 3)]


@pytest.mark.parametrize('failure', ['clock', 'index', 'open'])
def test_post_fetch_failures_are_not_silently_swallowed(failure):
    frame = bars()
    now = pd.Timestamp('2026-09-09T08:00Z')
    if failure == 'clock':
        now = RuntimeError('raw clock')
    elif failure == 'index':
        frame.index = ['not a date']
    else:
        frame = frame.drop(columns='open')
    s = RawSource({('5m', 3): (frame, corr())}, now)
    with pytest.raises({'clock': RuntimeError, 'index': ValueError, 'open': KeyError}[failure]):
        api().LevelmapOperation(s)._session_open_levels(SYMBOL)
    assert s.calls == [('fetch', SYMBOL, '5m', 3)] + ([] if failure == 'index' else [('clock',)])


@pytest.mark.parametrize('source,symbol,seam,want', [
    (None, SYMBOL, None, False), ('tv_daily', SYMBOL, None, True),
    ('mt5_broker', SYMBOL, None, True), ('none', SYMBOL, None, False),
    ('tv_live', SYMBOL, None, False), ('tv_spliced', SYMBOL, None, False),
    ('none', 'BINANCE:BTCUSDT', None, True),
    ('tv_spliced', 'BINANCE:BTCUSDT', NOW, True),
])
def test_shape_early_branches_never_read_clock(source, symbol, seam, want):
    s = RawSource(now=RuntimeError('unneeded clock'))
    c = None if source is None else corr(source, seam, symbol)
    assert api('basis_operation').BasisOperation(s).broker_shape_ok(c, 20) is want
    assert s.calls == []


@pytest.mark.parametrize('days', [7, 20])
@pytest.mark.parametrize('offset,want', [(-1, False), (0, True), (1, True)])
def test_shape_splice_threshold_uses_current_operation_time(days, offset, want):
    s = RawSource(now=NOW + pd.Timedelta(microseconds=offset))
    c = corr('tv_spliced', NOW - pd.Timedelta(days=days))
    assert api('basis_operation').BasisOperation(s).broker_shape_ok(c, days) is want
    assert s.calls == [('clock',)]


def full_source():
    daily = bars(220, end='2026-09-09T00:00Z', freq='1D', row=(100, 110, 90, 100))
    daily.iloc[-1] = [100, 115, 95, 110]
    opening = pd.concat([bars(), bars(end='2026-09-09T13:30Z', row=(107, 110, 90, 100))])
    return RawSource({
        ('1d', 400): (daily, corr()), ('5m', 3): (opening, corr()),
        ('1h', 20): (bars(33, end='2026-09-07T06:00Z', freq='1h', row=(100, 150, 80, 100)), corr()),
        ('1h', 240): (bars(1600, freq='1h', row=(100, 110, 90, 100)), corr()),
        ('4h', 240): (bars(400, freq='4h', row=(100, 110, 90, 100)), corr()),
    })


def test_full_map_real_calculations_prices_identity_and_operation_order():
    s = full_source()
    missing = []
    levels, c = api().LevelmapOperation(s).build(SYMBOL, missing)
    assert named(levels) == [
        ('ADR-HI', 115), ('ADR-LO', 95), ('AWR-HI', 110), ('AWR-LO', 95),
        ('RW-HI', 110), ('RW-LO', 95), ('AMR-HI', 110), ('AMR-LO', 95),
        ('ADR50-HI', 110), ('ADR50-LO', 90), ('AWR50-HI', 110), ('AWR50-LO', 90),
        ('AMR50-HI', 110), ('AMR50-LO', 90), ('RD-HI', 115), ('RD-LO', 95),
        ('YDAY-HI', 110), ('YDAY-LO', 90), ('YDAY-CLOSE', 100),
        ('D2-HI', 110), ('D2-LO', 90), ('D3-HI', 110), ('D3-LO', 90),
        ('D4-HI', 110), ('D4-LO', 90), ('LWEEK-HI', 110), ('LWEEK-LO', 90),
        ('DAY-OPEN', 100), ('WEEK-OPEN', 100), ('LONDON-OPEN', 103), ('NY-OPEN', 107),
        ('PSY-HI', 150), ('PSY-LO', 80), ('EMA200-1h', pytest.approx(100, abs=1e-10)),
        ('EMA800-1h', pytest.approx(100, abs=1e-10)), ('CLOUD50-4h', 100),
        ('EMA200-4h', pytest.approx(100, abs=1e-10)),
        ('Q-WHOLE', 100), ('Q-QUARTER', 125), ('Q-QUARTER', 75), ('Q-HALF', 150),
    ]
    from trading_system.tree_replay._vendor.levelmap_build import NamedLevel
    assert all(type(x) is NamedLevel for x in levels)
    assert [x.kind for x in levels] == ['level'] * 31 + ['psy'] * 2 + ['ema'] * 4 + ['quarter'] * 4
    assert c is s.frames[('1d', 400)][1]
    assert missing == []
    assert s.calls == [('fetch', SYMBOL, '1d', 400), ('fetch', SYMBOL, '5m', 3), ('clock',),
                       ('fetch', SYMBOL, '1h', 20), ('fetch', SYMBOL, '1h', 240), ('fetch', SYMBOL, '4h', 240)]


def test_daily_fetch_failure_stops_build():
    s = RawSource()
    missing = []
    assert api().LevelmapOperation(s).build(SYMBOL, missing) == ([], None)
    assert missing == []
    assert s.calls == [('fetch', SYMBOL, '1d', 400)]


def test_late_shape_clocks_and_separate_family_gates():
    s = full_source()
    before = pd.Timestamp('2026-09-09T06:59:59Z')
    opened = pd.Timestamp('2026-09-09T07:00Z')
    s.now = before
    s.frames[('1d', 400)] = (s.frames[('1d', 400)][0], corr('tv_spliced', opened - pd.Timedelta(days=20)))
    s.frames[('1h', 20)] = (s.frames[('1h', 20)][0], corr('tv_spliced', opened - pd.Timedelta(days=7)))
    s.after = {('5m', 3): opened}
    levels, _ = api().LevelmapOperation(s).build(SYMBOL)
    prices = dict(named(levels))
    assert 'ADR-HI' not in prices and 'RD-HI' not in prices
    assert prices['ADR50-HI'] == 110 and prices['LONDON-OPEN'] == 103
    assert prices['PSY-HI'] == 150 and prices['PSY-LO'] == 80
    assert 'NY-OPEN' not in prices
    assert s.calls == [('fetch', SYMBOL, '1d', 400), ('clock',), ('fetch', SYMBOL, '5m', 3),
                       ('clock',), ('fetch', SYMBOL, '1h', 20), ('clock',),
                       ('fetch', SYMBOL, '1h', 240), ('fetch', SYMBOL, '4h', 240)]


@pytest.mark.parametrize('first,fallback', [('proxy', True), ('empty', True), ('error', False)])
def test_psy_fallback_preserves_original_outer_catch(first, fallback):
    s = full_source()
    frame, c = s.frames[('1h', 20)]
    s.frames[('15m', 20)] = (frame, c)
    s.frames[('1h', 20)] = {'proxy': (frame, corr('none')), 'empty': (frame.iloc[:0], c),
                           'error': OSError('failed hourly fetch')}[first]
    levels, _ = api().LevelmapOperation(s).build(SYMBOL)
    assert [(x.name, x.price) for x in levels if x.kind == 'psy'] == ([('PSY-HI', 150), ('PSY-LO', 80)] if fallback else [])
    assert (('fetch', SYMBOL, '15m', 20) in s.calls) is fallback
    assert [x.name for x in levels if x.kind == 'ema'] == ['EMA200-1h', 'EMA800-1h', 'CLOUD50-4h', 'EMA200-4h']
