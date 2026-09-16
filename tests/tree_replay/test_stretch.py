"""Source-characterization tests use real ranges, seeded EMA and shape policy."""
import importlib
import importlib.util
import math

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from trading_system.tree_replay._vendor.correction import Correction, broker_shape_ok_at


NOW = pd.Timestamp('2026-09-09T16:00:00Z')
SYMBOL = 'OANDA:XAUUSD'
LONG, SHORT = 'לונג', 'שורט'
REQUESTS = [('1d', 400), ('15m', 20), ('1h', 60), ('4h', 240)]


def api():
    name = 'trading_system.tree_replay._vendor.stretch'
    assert importlib.util.find_spec(name) is not None, 'stretch calculation missing'
    return importlib.import_module(name)


def daily(close=116., high=126., low=100., n=22):
    # Old seven days have range200; the last14 completed days have range20.
    # A wrong20-day average or inclusion of today's range changes the result.
    widths = [200.] * max(0, n-15) + [20.] * min(14, n-1)
    return pd.DataFrame({
        'open': [100.]*n, 'high': [100.+w/2 for w in widths]+[high],
        'low': [100.-w/2 for w in widths]+[low],
        'close': [100.]*(n-1)+[close],
    }, index=pd.date_range(end=NOW.normalize(), periods=n, freq='D'))


def intraday(n=60, flat=False):
    closes = [100.] * n if flat else [100.+i for i in range(n)]
    width = 0. if flat else 1.
    return pd.DataFrame({'open': closes, 'high': [c+width for c in closes],
        'low': [c-width for c in closes], 'close': closes},
        index=pd.date_range(end=NOW, periods=n, freq='15min'))


class Ports:
    def __init__(self, frame=None, *, symbol=SYMBOL, corr=None):
        self.symbol = symbol
        self.corr = corr if corr is not None else Correction(symbol, 0., 'tv_daily', 'high', 'fixture')
        self.frames = dict(zip(REQUESTS, [daily() if frame is None else frame,
                                          intraday(), intraday(), intraday()]))
        self.calls = []
        self.now = NOW
        self.shape_error = None

    def fetch_corrected(self, symbol, timeframe, days):
        self.calls.append(('fetch', symbol, timeframe, days))
        assert symbol == self.symbol
        f = self.frames[timeframe, days]
        if isinstance(f, Exception):
            raise f
        # Intraday correction is deliberately unverified; original dev ignores it.
        c = self.corr if timeframe == '1d' else Correction(symbol, 0., 'none', 'unknown', 'fixture')
        return f, c

    def broker_shape_ok(self, correction, days):
        self.calls.append(('shape', correction, days))
        assert correction is self.corr
        if self.shape_error:
            raise self.shape_error
        return broker_shape_ok_at(correction, days, decision_time=self.now)


@pytest.mark.parametrize('symbol', [SYMBOL, 'OANDA:NAS100USD', 'BINANCE:BTCUSDT'])
@pytest.mark.parametrize('close,hi,lo,side,direction', [
    (116.,126.,100.,'up',LONG), (84.,100.,74.,'down',SHORT),
])
def test_full_source_uses_fourteen_prior_ranges_and_half_adr_rails(symbol, close, hi, lo, side, direction):
    m = api()
    p = Ports(daily(close,hi,lo), symbol=symbol)
    originals = {k:v.copy(deep=True) for k,v in p.frames.items()}
    s = m.StretchReader(p).state(symbol)
    assert (s.symbol,s.close,s.day_open,s.adr) == (symbol,close,100.,20.)
    assert (s.rail_hi,s.rail_lo,s.budget_used,s.beyond) == (110.,90.,1.3,.3)
    assert s.side == side and s.direction == direction and s.is_extended
    assert s.contradicts(direction)
    assert not s.contradicts(SHORT if direction == LONG else LONG)
    assert s.devs == pytest.approx({'15m':12.25,'1h':12.25,'4h':12.25}, rel=0, abs=1e-12)
    assert s.max_dev == pytest.approx(12.25, rel=0, abs=1e-12)
    assert p.calls == [('fetch',symbol,'1d',400),('shape',p.corr,20),
        ('fetch',symbol,'15m',20),('fetch',symbol,'1h',60),('fetch',symbol,'4h',240)]
    for k,f in originals.items():
        assert_frame_equal(p.frames[k],f)


@pytest.mark.parametrize('hi,close,want,side', [
    (124.99999,116.,False,'up'), (125.,116.,True,'up'),
    (125.,110.,False,None), (125.,110.0001,True,'up'),
    (125.,100.,False,None),
])
def test_budget_and_rail_boundaries_and_nonextended_still_read_deviations(hi, close, want, side):
    m = api()
    p = Ports(daily(close,hi,100.))
    s = m.StretchReader(p).state(SYMBOL)
    assert s.is_extended == want and s.side == side
    assert s.direction == (LONG if want else None)
    assert bool(s.contradicts(LONG)) == want
    assert len(s.devs) == 3
    assert [c[2:] for c in p.calls if c[0]=='fetch'] == REQUESTS


@pytest.mark.parametrize('fault', ['empty','none','short','zero','fetch_error','shape_error','proxy','bad_index'])
def test_unusable_daily_blocks_before_deviation_reads(fault):
    m = api()
    p = Ports()
    if fault == 'empty': p.frames['1d',400] = pd.DataFrame()
    elif fault == 'none': p.frames['1d',400] = None
    elif fault == 'short': p.frames['1d',400] = daily(n=14)
    elif fault == 'zero': p.frames['1d',400] = intraday(22,flat=True)
    elif fault == 'fetch_error': p.frames['1d',400] = OSError('offline failure')
    elif fault == 'shape_error': p.shape_error = OSError('shape unavailable')
    elif fault == 'proxy': p.corr = Correction(SYMBOL,0.,'cached_stale','low','proxy')
    elif fault == 'bad_index': p.frames['1d',400] = daily().reset_index(drop=True)
    assert m.StretchReader(p).state(SYMBOL) is None
    assert [c[2:] for c in p.calls if c[0]=='fetch'] == [('1d',400)]
    if fault in ('empty','none','fetch_error'):
        assert len(p.calls) == 1  # preserve original empty-before-shape short circuit


@pytest.mark.parametrize('microseconds,want', [(-1,False),(0,True),(1,True)])
def test_actual_shape_policy_uses_twenty_day_horizon_not_adr_length(microseconds,want):
    m = api()
    c = Correction(SYMBOL,0.,'tv_spliced','high','seam',NOW-pd.Timedelta(days=20))
    p = Ports(corr=c)
    p.now += pd.Timedelta(microseconds=microseconds)
    s = m.StretchReader(p).state(SYMBOL)
    assert (s is not None) == want
    if want:
        assert s.adr == 20. and s.rail_hi == 110.


def test_native_venue_shape_uses_original_policy_without_symbol_alias():
    m = api()
    sym='BINANCE:BTCUSDT'
    p=Ports(symbol=sym,corr=Correction(sym,0.,'none','n/a','native'))
    assert m.StretchReader(p).state(sym).direction == LONG
    assert all(c[1]==sym for c in p.calls if c[0]=='fetch')


@pytest.mark.parametrize('bad', ['short','zero','missing','error','none'])
def test_one_bad_deviation_drops_only_its_context_not_daily_state(bad):
    m = api()
    p=Ports()
    p.frames['1h',60]={'short':intraday(59),'zero':intraday(flat=True),
        'missing':pd.DataFrame(index=range(60)),'error':OSError('offline'), 'none':None}[bad]
    s=m.StretchReader(p).state(SYMBOL)
    assert s.is_extended and s.devs == pytest.approx({'15m':12.25,'4h':12.25}, rel=0, abs=1e-12)
    assert p.calls[-1] == ('fetch',SYMBOL,'4h',240)


def test_atr_is_unseeded_not_sma_seeded():
    m=api()
    f=pd.DataFrame({'high':[101.,120.],'low':[99.,100.],'close':[100.,110.]})
    assert m._atr(f) == pytest.approx(23/7)


def test_source_nan_deviation_is_not_silently_sanitized():
    m=api()
    p=Ports()
    p.frames['15m',20]['close']=float('nan')
    s=m.StretchReader(p).state(SYMBOL)
    assert '15m' in s.devs and math.isnan(s.devs['15m'])
    assert s.devs['1h'] == pytest.approx(12.25, rel=0, abs=1e-12) and s.is_extended


@pytest.mark.parametrize('close,wantword,wantrail', [
    (116.,'מתוח','העליון'), (120.,'מתיחה קיצונית','העליון'),
    (84.,'מתוח','התחתון'), (80.,'מתיחה קיצונית','התחתון'),
])
def test_render_retains_actual_extension_tier_side_and_cloud_distance(close,wantword,wantrail):
    m=api()
    p=Ports(daily(close,126. if close>100 else 100.,100. if close>100 else 74.))
    s=m.StretchReader(p).state(SYMBOL)
    line=s.line()
    assert f'⚠ {wantword}: 130% מ-ADR נוצל' in line
    assert f'מעבר לפס {wantrail}' in line
    assert 'מרחק מהענן: +12.2 ATR (15m)' in line
    assert s.render() == f'◈ XAUUSD — מצב מתיחה @ {close:,.2f}\n{line}'


def test_render_no_extension_and_cloud_wording_threshold_do_not_change_direction():
    m=api()
    s=m.StretchReader(Ports(daily(100.,110.,90.))).state(SYMBOL)
    assert s.render() == '◈ XAUUSD — מצב מתיחה @ 100.00\n  תקציב יומי 100% מ-ADR · בתוך הטווח מהפתיחה — אין מתיחה'
    s=m.StretchReader(Ports()).state(SYMBOL)
    s.devs={'15m':2.99999}
    assert 'מרחק מהענן' not in s.line()
    s.devs={'15m':2.,'4h':-3.}
    assert 'מרחק מהענן: -3.0 ATR (4h)' in s.line()
    assert s.direction == LONG
    s.devs={}
    assert s.max_dev == 0. and 'מרחק מהענן' not in s.line()
