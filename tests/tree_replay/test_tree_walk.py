"""Actual original tree decisions from raw synthetic tapes, not final read mocks."""

import ast
import importlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from trading_system.tree_replay._vendor.correction import Correction

SYMBOL = 'OANDA:XAUUSD'
NOW = pd.Timestamp('2026-09-09T14:00Z')
STAGES = ['DATA', 'CONTEXT', 'LEVELS', 'SESSION', 'PATTERN', 'LOCATION',
          'VECTOR', 'MTF', 'TRAP', 'MEMORY', 'TRIGGER', 'TARGET']


def api(part='tree_walk'):
    name = 'trading_system.tree_replay._vendor.' + part
    assert importlib.util.find_spec(name) is not None, 'Missing complete tree reader: ' + part
    return importlib.import_module(name)


def correction(source='tv_daily', confidence='exact'):
    return Correction(SYMBOL, 0, source, confidence, 'synthetic')


def frame(count=1001, freq='15min', rising=True, close=128., width=2.):
    prices = [100 + i / 100 for i in range(count)] if rising else [close] * count
    return pd.DataFrame({'open': [p - .005 for p in prices], 'close': prices,
                         'high': [p + width / 2 for p in prices], 'low': [p - width / 2 for p in prices],
                         'volume': [100.] * count},
                        index=pd.date_range(end=NOW, periods=count, freq=freq))


class RawSource:
    def __init__(self, frames=None):
        self.frames = {} if frames is None else frames
        self.calls = []
        self.now = NOW
        self.calendar = json.dumps([{'dateline': NOW.timestamp() + 86400, 'impact': 'Low', 'title': 'future'}])

    def fetch_corrected(self, symbol, timeframe, lookback):
        self.calls.append(('fetch', symbol, timeframe, lookback))
        value = self.frames.get((timeframe, lookback), LookupError('raw tape unavailable'))
        if isinstance(value, list):
            value = value.pop(0)
        if isinstance(value, Exception):
            raise value
        df, c = value
        return df.copy(deep=True), c

    def now_utc(self):
        self.calls.append(('clock',))
        return self.now

    def calendar_text(self, path):
        self.calls.append(('calendar', path))
        assert path == 'news-desk/data/ff_calendar.json'
        if isinstance(self.calendar, Exception):
            raise self.calendar
        return self.calendar

    def list_reports(self):
        self.calls.append(('options-list',))
        return []

    def read_report(self, path):
        self.calls.append(('options-read', path))
        raise FileNotFoundError(path)

    def read_tv_csv(self, filename):
        self.calls.append(('tv-read', filename))
        raise FileNotFoundError(filename)


def full_source():
    c = correction()
    frames = {('15m', 10): (frame(), c), ('4h', 60): (frame(freq='4h'), c)}
    for tf in ('1h', '30m', '15m', '5m'):
        frames[(tf, 30)] = (frame(freq={'1h': '1h', '30m': '30min', '15m': '15min', '5m': '5min'}[tf]), c)
    daily = frame(220, '1D', False, close=100, width=20)
    daily.index = pd.date_range(end='2026-09-09T00:00Z', periods=220, freq='1D')
    daily['open'] = 100.
    daily.iloc[-1, daily.columns.get_loc('high')] = 115.
    daily.iloc[-1, daily.columns.get_loc('low')] = 95.
    daily.iloc[-1, daily.columns.get_loc('close')] = 110.
    frames[('1d', 400)] = (daily, c)
    frames[('1d', 30)] = (daily, c)
    opening = frame(2, rising=False)
    opening.index = pd.to_datetime(['2026-09-09T07:00Z', '2026-09-09T13:30Z'])
    opening['open'] = [103., 107.]
    frames[('5m', 3)] = (opening, c)
    frames[('1h', 240)] = (frame(1600, '1h', False, close=100), c)
    frames[('4h', 240)] = (frame(400, '4h', False, close=100), c)
    return RawSource(frames)


def test_data_fetch_failure_is_structured_stop_without_downstream_reads():
    source = RawSource()
    w = api().TreeReader(source).walk(SYMBOL)
    assert w.reached == 'DATA' and not w.complete
    assert w.stopped_because == 'אין נתונים (LookupError)'
    assert w.passed == []
    assert source.calls == [('fetch', SYMBOL, '15m', 10)]


def test_data_four_hour_exception_after_successful_fifteen_minute_read():
    source = full_source()
    source.frames[('4h', 60)] = OSError('raw four-hour failure')
    w = api().TreeReader(source).walk(SYMBOL)
    assert not w.complete and w.reached == 'DATA' and w.passed == []
    assert w.stopped_because == 'אין נתונים (OSError)'
    assert source.calls == [('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '4h', 60)]


@pytest.mark.parametrize('key', [('15m', 10), ('4h', 60)])
@pytest.mark.parametrize('fault', ['unverified', 'stale', 'short'])
def test_both_initial_frames_are_gated(key, fault):
    source = full_source()
    df, c = source.frames[key]
    if fault == 'unverified':
        c = correction('none', 'unknown')
    elif fault == 'stale':
        c = correction('tv_stale')
    else:
        df = df.iloc[-4:]
    source.frames[key] = (df, c)
    w = api().TreeReader(source).walk(SYMBOL)
    assert not w.complete and w.reached == 'DATA' and w.stopped_because
    assert source.calls == [('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '4h', 60)]


@pytest.mark.parametrize('high,low,kind,sv,trend,want,verdict', [
    (True, False, 'green', False, None, 'שורט', 'trap'),
    (True, False, 'blue', False, 'שורט', 'שורט', 'trap'),
    (False, True, 'red', False, None, 'לונג', 'trap'),
    (False, True, 'violet', False, 'לונג', 'לונג', 'trap'),
    (False, True, 'green', False, 'שורט', 'לונג', 'committed'),
    (False, True, 'blue', False, 'שורט', 'לונג', 'committed'),
    (True, False, 'red', False, 'לונג', 'שורט', 'committed'),
    (True, False, 'violet', False, 'לונג', 'שורט', 'committed'),
    (True, False, None, True, 'לונג', 'שורט', 'trap'),
    (False, True, None, True, 'שורט', 'לונג', 'trap'),
    (False, False, 'green', True, 'שורט', 'שורט', 'trend'),
    (False, False, None, False, None, None, 'trend'),
])
def test_trap_follows_vector_side_and_completed_edge(high, low, kind, sv, trend, want, verdict):
    assert api('tree_core').trap_direction(high, low, kind, sv, trend) == (want, verdict)


@pytest.mark.parametrize('row,vol,want', [
    ((123, 140, 120, 130), 150, True),
    ((123, 140, 120, 130.001), 150, False),
    ((124, 139, 120, 130), 150, False),
    ((123, 140, 120, 130), 149.999, False),
    ((123, 140, 120, 130), 100, False),
])
def test_stopping_volume_requires_body_wick_and_volume(row, vol, want):
    df = frame(12, rising=False)
    for name, value in zip(('open', 'high', 'low', 'close'), row):
        df.iloc[-2, df.columns.get_loc(name)] = value
    df.iloc[-2, df.columns.get_loc('volume')] = vol
    df.iloc[-1, df.columns.get_loc('volume')] = 1000000.
    assert api('tree_core')._stopping_volume(df) is want


@pytest.mark.parametrize('variant', ['house', 'strict'])
def test_real_full_tree_visits_all_stages_and_builds_a_source_plan(variant):
    source = full_source()
    reader = api().TreeReader(source)
    w = reader.walk(SYMBOL, variant)
    assert w.complete and w.stopped_because is None and w.direction == 'לונג'
    assert w.passed == STAGES and w.reached == 'TARGET'
    assert w.decided_close == 110.
    assert w.decided_bar == str(source.frames[('15m', 10)][0].index[-1])
    assert w.facts['commitment'].startswith('אין (')
    assert 'Stopping Volume' not in w.facts['וקטור']
    assert source.calls.count(('fetch', SYMBOL, '1h', 30)) == 2
    news = source.calls.index(('calendar', 'news-desk/data/ff_calendar.json'))
    assert source.calls[news - 1] == ('clock',) and source.calls[news + 1] == ('clock',)
    if variant == 'strict':
        assert 'כולל פיבוטים ו-M' in w.facts['רמות']
    plan = reader.trade_from_walk(w)
    from trading_system.tree_replay._vendor.pricing import Plan
    assert isinstance(plan, Plan) and plan.tradeable
    assert plan.entry == 110. and plan.direction == 'לונג' and plan.style == 'intraday'
    assert plan.stop == pytest.approx(99.7)
    assert plan.targets[0][1] == 125.
    assert plan.not_drawn == w.missing and plan.not_drawn is not w.missing
    assert w.refused is None


@pytest.mark.parametrize('calendar', [[], '{', OSError('missing'),
    [{'dateline': NOW.timestamp() - 86400, 'impact': 'Low'}]])
def test_unusable_calendar_stops_at_session(calendar):
    source = full_source()
    source.calendar = json.dumps(calendar) if isinstance(calendar, list) else calendar
    w = api().TreeReader(source).walk(SYMBOL)
    assert not w.complete and w.reached == 'SESSION'
    assert w.passed == ['DATA', 'CONTEXT', 'LEVELS']
    assert w.stopped_because.startswith('לוח החדשות לא שמיש')
    assert ('fetch', SYMBOL, '5m', 5) not in source.calls


@pytest.mark.parametrize('offset,want_stop', [(-901, False), (-900, True), (900, True), (901, False)])
def test_calendar_blackout_inclusive_fifteen_minutes(offset, want_stop):
    events = [{'dateline': NOW.timestamp() + offset, 'impact': 'High', 'title': 'event'},
              {'dateline': NOW.timestamp() + 86400, 'impact': 'Low'}]
    result = api('tree_core')._news_stop(events, NOW.timestamp())
    assert (result is not None) is want_stop
    if want_stop:
        assert result.startswith('חלון חדשות: event')


def test_calendar_missing_impact_inside_window_is_error():
    with pytest.raises(ValueError, match='has no impact'):
        api('tree_core')._news_stop([{'dateline': NOW.timestamp() + 10}], NOW.timestamp())


@pytest.mark.parametrize('short', [False, True])
def test_first_vector_reads_completed_break_not_forming_noise(short):
    df = frame(120, '5min', False)
    df['open'] = 128.
    df['high'] = 129.
    df['low'] = 127.
    df.iloc[-2, df.columns.get_loc('close')] = 116. if short else 140.
    df.iloc[-2, df.columns.get_loc('high')] = 129. if short else 141.
    df.iloc[-2, df.columns.get_loc('low')] = 115. if short else 127.
    df.iloc[-2, df.columns.get_loc('volume')] = 250.
    source = RawSource({('5m', 5): (df, correction())})
    result = api().TreeReader(source).first_vector_above_50(SYMBOL)
    assert result['direction'] == ('שורט' if short else 'לונג')
    assert result['vector'] == ('red' if short else 'green')
    assert result['close'] == (116. if short else 140.)
    df.iloc[-1, df.columns.get_loc('close')] = 10000.
    assert api().TreeReader(source).first_vector_above_50(SYMBOL) == result


def test_strict_pivots_do_not_replace_failed_base_map():
    source = full_source()
    del source.frames[('1d', 400)]
    reader = api().TreeReader(source)
    # Source map returns empty on daily fetch failure; strict still adds pivots.
    # A thrown malformed daily frame invalidates the whole universe instead.
    source.frames[('1d', 400)] = (frame(0), correction())
    assert reader._variant_levels(SYMBOL, 'strict') is None
    assert ('fetch', SYMBOL, '1d', 30) not in source.calls


def test_builder_stops_on_drift_before_map_rebuild():
    source = full_source()
    core = api('tree_core')
    w = core.Walk(SYMBOL, 'TARGET', direction='לונג', passed=list(STAGES), decided_close=100.)
    assert api().TreeReader(source).trade_from_walk(w) is None
    assert w.facts['נדחה'].startswith('המחיר זז')
    assert source.calls == [('fetch', SYMBOL, '15m', 10)]


def test_builder_keeps_refused_plan_when_band_crosses_invalidation():
    source = RawSource({
        ('15m', 10): (frame(100, rising=False, close=110, width=10), correction()),
        ('1d', 400): (frame(220, '1D', False, close=1000, width=20), correction()),
    })
    core = api('tree_core')
    w = core.Walk(SYMBOL, 'TARGET', direction='לונג', passed=list(STAGES), zones=[(80., 'green', 0)])
    assert api().TreeReader(source).trade_from_walk(w) is None
    assert w.refused is not None and w.refused.entry == 110.
    assert w.refused.stop > 80.
    assert 'לפני נקודת הביטול' in w.facts['נדחה']


def falling(df):
    out = df.copy()
    out['open'], out['close'] = 220 - df['open'], 220 - df['close']
    out['high'], out['low'] = 220 - df['low'], 220 - df['high']
    return out


@pytest.mark.parametrize('conflicting_high_pair,want,tf', [(False, 'שורט', '4h'), (True, 'לונג', '30m')])
def test_real_ladder_uses_combined_ranges_and_selected_read(conflicting_high_pair, want, tf):
    source = full_source()
    for key in [('4h', 60)] + ([] if conflicting_high_pair else [('1h', 30)]):
        df, c = source.frames[key]
        source.frames[key] = (falling(df), c)
    w = api().TreeReader(source).walk(SYMBOL)
    assert w.complete and w.direction == want
    assert w.facts['מסגרת הכיוון'].endswith('נקרא מ-' + tf)
    assert 'הקשר ' + tf in w.facts
    assert ('פער מגמות' in w.facts) is (not conflicting_high_pair)


def test_all_neutral_reads_stop_after_memory_without_directional_geometry():
    source = full_source()
    for key in [('4h', 60), ('1h', 30), ('30m', 30), ('15m', 30), ('5m', 30)]:
        source.frames[key] = (frame(rising=False), correction())
    w = api().TreeReader(source).walk(SYMBOL)
    assert not w.complete and w.direction is None and w.reached == 'MEMORY'
    assert w.passed == STAGES[:10]
    assert 'אין כיוון' in w.stopped_because
    assert 'commitment' not in w.facts and 'רמות לפנים' not in w.facts


def test_missing_stretch_is_unknown_not_a_positive_regime():
    source = full_source()
    # Stretch's first daily read fails; the later map read still succeeds.
    daily = source.frames[('1d', 400)]
    source.frames[('1d', 400)] = [LookupError('stretch daily unavailable'), daily]
    w = api().TreeReader(source).walk(SYMBOL)
    assert w.complete and 'UNKNOWN' in w.facts['הקשר 4h']
    assert 'לא מתוח' not in w.facts['וקטור']
    assert source.calls.count(('fetch', SYMBOL, '1d', 400)) == 2


def test_none_initial_corrections_are_not_an_invented_veto():
    source = full_source()
    for key in [('15m', 10), ('4h', 60)]:
        source.frames[key] = (source.frames[key][0], None)
    assert api().TreeReader(source).walk(SYMBOL).complete


def test_news_gate_uses_clock_before_calendar_read_not_after():
    class AdvancingCalendar(RawSource):
        def calendar_text(self, path):
            result = super().calendar_text(path)
            self.now = NOW + pd.Timedelta(seconds=2)
            return result
    source = AdvancingCalendar(full_source().frames)
    source.calendar = json.dumps([{'dateline': NOW.timestamp() + 901, 'impact': 'High'},
                                  {'dateline': NOW.timestamp() + 86400, 'impact': 'Low'}])
    w = api().TreeReader(source).walk(SYMBOL)
    assert w.complete  # 901 seconds at the captured clock; 899 only after IO.
    at = source.calls.index(('calendar', 'news-desk/data/ff_calendar.json'))
    assert source.calls[at - 1] == ('clock',) and source.calls[at + 1] == ('clock',)


def test_actual_hourly_w_pattern_is_consumed_without_secondary_scan():
    anchors = {0: 100., 5: 103., 10: 90., 17: 110., 25: 91., 35: 115., 39: 115.}
    closes = pd.Series(anchors).reindex(range(40)).interpolate()
    df = frame(40, '1h', False)
    df['close'], df['open'] = closes.to_numpy(), closes.to_numpy()
    df['high'], df['low'] = closes.to_numpy() + 1, closes.to_numpy() - 1
    source = full_source()
    source.frames[('1h', 10)] = (df, correction())
    w = api().TreeReader(source).walk(SYMBOL)
    assert w.complete and w.facts['תבנית'] == 'W מאושרת'
    # DATA, pools and run: three reads. The slow run stops before its own
    # pool reread; a redundant WM fallback would introduce a fourth read.
    assert source.calls.count(('fetch', SYMBOL, '15m', 10)) == 3


@pytest.mark.parametrize('fault', ['short', 'missing_volume', 'zero_volume'])
def test_stopping_volume_missing_or_short_tape_is_not_confirmation(fault):
    df = frame(11 if fault == 'short' else 12, rising=False)
    if fault == 'missing_volume':
        df = df.drop(columns='volume')
    elif fault == 'zero_volume':
        df['volume'] = 0.
    assert api('tree_core')._stopping_volume(df) is False


@pytest.mark.parametrize('fault', ['short', 'no_cloud_history', 'ordinary', 'unverified', 'prior_break', 'missing_volume'])
def test_first_vector_absence_is_not_fabricated(fault):
    df = frame(59 if fault == 'short' else 60 if fault == 'no_cloud_history' else 120, '5min', False)
    df['open'] = 128.
    if fault != 'ordinary':
        df.iloc[-2, df.columns.get_loc('close')] = 140.
        df.iloc[-2, df.columns.get_loc('high')] = 141.
        df.iloc[-2, df.columns.get_loc('volume')] = 250.
    if fault == 'prior_break':
        df.iloc[-3, df.columns.get_loc('close')] = 150.
        df.iloc[-3, df.columns.get_loc('high')] = 151.
    if fault == 'missing_volume':
        df = df.drop(columns='volume')
    c = correction('none', 'unknown') if fault == 'unverified' else correction()
    assert api().TreeReader(RawSource({('5m', 5): (df, c)})).first_vector_above_50(SYMBOL) is None


def assert_named_ladder(actual, expected):
    # The flat100 SMA-seeded EMAs can differ by floating-point roundoff.
    # That affects the order of coincident names, not their membership or rung.
    assert [sorted(n.split('/')) for n, _ in actual] == [
        sorted(n.split('/')) for n, _ in expected]
    assert [p for _, p in actual] == pytest.approx([p for _, p in expected])


def check_geometry(reader_type, short):
    source = full_source()
    core = api('tree_core')
    side = 'שורט' if short else 'לונג'
    w = core.Walk(SYMBOL, 'TARGET', direction=side, passed=list(STAGES), decided_close=110.,
                  missing=['missing observation'], facts={'fixture': 'literal'})
    reader = reader_type(source)
    # Daily range20: ADR/RD=115/95. Weekly/monthly current H/L=115/90,
    # so their low rails also equal95; open100 +/- range/2 gives110/90.
    # Prior daily/weekly lows90 merge with the three from-open low rails.
    # Entry zone108..112 excludes110. MIN_RR=1.2 makes95 pay on risk9.5;
    # 107/103/100 do not. Long risk10.3 makes115 an obstacle,125 a target.
    stop = 119.5 if short else 99.7
    targets = [
        ('ADR-LO/AWR-LO/RW-LO/AMR-LO/RD-LO', 95.),
        ('ADR50-LO/AWR50-LO/AMR50-LO/YDAY-LO/D2-LO/D3-LO/D4-LO/LWEEK-LO', 90.),
        ('Q-QUARTER', 75.),
    ] if short else [('Q-QUARTER', 125.), ('Q-HALF', 150.)]
    obstacles = [
        ('NY-OPEN', 107.), ('LONDON-OPEN', 103.),
        ('YDAY-CLOSE/DAY-OPEN/WEEK-OPEN/EMA200-1h/EMA800-1h/CLOUD50-4h/EMA200-4h/Q-WHOLE', 100.),
    ] if short else [('ADR-HI/RD-HI', 115.)]
    plan = reader.trade_from_walk(w)
    assert plan is not None and plan.tradeable and plan.stop == pytest.approx(stop)
    assert_named_ladder(plan.targets, targets)
    assert_named_ladder(plan.obstacles, obstacles)
    assert plan.not_drawn == ['missing observation']
    geometry = reader.levels_to_trade(SYMBOL, 110., side, 2.)
    assert geometry is not None and geometry[0] == pytest.approx(stop)
    assert_named_ladder(geometry[1], targets)


@pytest.mark.parametrize('short', [False, True])
def test_both_geometry_consumers_use_original_prices(short):
    check_geometry(api().TreeReader, short)


@pytest.mark.parametrize('decided,present', [(109.34, True), (109.33999, False)])
def test_builder_drift_boundary_is_strict_greater_than(decided, present):
    source = full_source()
    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג', decided_close=decided, passed=list(STAGES))
    result = api().TreeReader(source).trade_from_walk(w)
    assert (result is not None) is present
    assert (('fetch', SYMBOL, '1d', 400) in source.calls) is present


def test_builder_and_geometry_classify_map_outage_without_economic_verdict():
    source = full_source()
    source.frames[('1d', 400)] = (frame(0), correction())
    core = api('tree_core')
    w = core.Walk(SYMBOL, 'TARGET', direction='לונג')
    reader = api().TreeReader(source)
    assert reader.trade_from_walk(w) is None and w.refused is None
    assert w.facts['בניית עסקה'] == 'מפת הרמות לא נקראה מחדש — אין מסקנת R:R'
    with pytest.raises(core.LevelsUnavailable):
        reader.levels_to_trade(SYMBOL, 110., 'לונג', 2.)


def test_trap_reason_changes_plan_family_and_is_retained():
    source = full_source()
    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג', passed=list(STAGES),
                              facts={'מלכודת': 'היערך ללונג'})
    plan = api().TreeReader(source).trade_from_walk(w)
    assert plan is not None and plan.kind == 'reversal'
    assert 'עסקת מלכודת' in plan.warnings[-1]
    assert any('היערך ללונג' in reason for reason in plan.reasons)


def test_strict_appends_all_thirteen_previous_day_pivots_in_source_order():
    reader = api().TreeReader(full_source())
    house = reader._variant_levels(SYMBOL, 'house')
    strict = reader._variant_levels(SYMBOL, 'strict')
    # Previous H/L/C = 110/90/100; forming day 115/95/110 must not enter pivots.
    assert strict == house + [('PP', 100.), ('R1', 110.), ('R2', 120.),
        ('R3', 130.), ('S1', 90.), ('S2', 80.), ('S3', 70.),
        ('M0', 75.), ('M1', 85.), ('M2', 95.), ('M3', 105.),
        ('M4', 115.), ('M5', 125.)]


def test_strict_pivot_read_failure_invalidates_successful_base_universe():
    source = full_source()
    source.frames[('1d', 30)] = OSError('daily pivot read unavailable')
    w = api().TreeReader(source).walk(SYMBOL, 'strict')
    assert not w.complete and w.reached == 'LEVELS'
    assert 'פיבוט' in w.stopped_because
    assert ('calendar', 'news-desk/data/ff_calendar.json') not in source.calls


@pytest.mark.parametrize('inverse,name', [(False, 'RVC'), (True, 'GVC')])
def test_actual_recovered_vector_pair_enters_pattern_and_context(inverse, name):
    df = frame(33, rising=False, close=100.)
    df['open'], df['volume'] = 100., 1.
    for i, values in [(30, (102., 103., 99., 100., 3.)),
                      (31, (100., 103., 99., 102., 10.)),
                      (32, (102., 103., 99., 100., 100.))]:
        for field, value in zip(('open', 'high', 'low', 'close', 'volume'), values):
            df.iloc[i, df.columns.get_loc(field)] = value
    if inverse:
        df = falling(df)
    source = full_source()
    source.frames[('15m', 5)] = (df, correction())
    w = api().TreeReader(source).walk(SYMBOL)
    assert w.complete and w.facts['תבנית'] == name + ' — התבנית היחידה כרגע'
    assert name in w.facts['RVC/GVC']
    assert 'תבנית (' + name + ')' in w.facts['וקטור']


def test_actual_brinks_box_and_checklist_replace_the_first_box_annotation():
    source = full_source()
    source.now = pd.Timestamp('2026-09-09T15:00Z')
    box = frame(12, '5min', False, close=100.)
    box.index = pd.date_range('2026-09-09T14:00Z', periods=12, freq='5min')
    source.frames[('5m', 2)] = (box, correction())
    w = api().TreeReader(source).walk(SYMBOL)
    assert w.complete and '99.00' in w.facts['ברינקס'] and '101.00' in w.facts['ברינקס']
    # Two independent real consumers; second performs vector and Asia reads.
    assert source.calls.count(('fetch', SYMBOL, '5m', 2)) == 2
    assert ('fetch', SYMBOL, '5m', 10) in source.calls
    assert ('fetch', SYMBOL, '15m', 3) in source.calls


@pytest.mark.parametrize('mid,included', [(60., True), (59.999, False)])
def test_vector_anchor_five_atr_boundary_changes_refusal_geometry(mid, included):
    source = RawSource({
        ('15m', 10): (frame(100, rising=False, close=110., width=10.), correction()),
        ('1d', 400): (frame(220, '1D', False, close=1000., width=20.), correction()),
    })
    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג',
                              zones=[(mid, 'green', 0)])
    assert api().TreeReader(source).trade_from_walk(w) is None
    if included:
        assert w.refused is not None and w.refused.stop == pytest.approx(97.5)
        assert 'VZ50-green' in w.facts['נדחה']
    else:
        assert w.refused is None and 'אין רמה מאחור' in w.facts['נדחה']


def test_both_geometry_consumers_refuse_a_clamp_in_front_of_actual_map_anchor():
    source = RawSource({
        ('15m', 10): (frame(100, rising=False, close=110., width=10.), correction()),
        ('1d', 400): (frame(220, '1D', False, close=1000., width=20.), correction()),
        ('1h', 240): (frame(1600, '1h', False, close=80.), correction()),
    })
    reader = api().TreeReader(source)
    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג')
    assert reader.trade_from_walk(w) is None and w.refused is not None
    assert w.refused.stop == pytest.approx(97.5)
    assert 'לפני נקודת הביטול' in w.facts['נדחה']
    assert reader.levels_to_trade(SYMBOL, 110., 'לונג', 10.) is None


@pytest.mark.parametrize('reached,direction', [('MEMORY', 'לונג'), ('TARGET', None)])
def test_builder_does_not_fetch_for_an_incomplete_or_directionless_walk(reached, direction):
    source = RawSource()
    w = api('tree_core').Walk(SYMBOL, reached, direction=direction)
    assert api().TreeReader(source).trade_from_walk(w) is None
    assert source.calls == [] and w.refused is None


def test_builder_raw_price_reread_failure_is_not_an_economic_refusal():
    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג')
    source = RawSource()
    assert api().TreeReader(source).trade_from_walk(w) is None
    assert w.refused is None
    assert w.facts['בניית עסקה'] == 'טייפ 15m לא נקרא מחדש — אין מסקנת R:R'


def memory_tape(cleared=False):
    # Ten warmup bars: spread2 * volume100 = 200; no classified vectors yet.
    # Row10 green body100..102, volume300 >= 2*100, spread-volume1200.
    # Row11 departs above it. Row12 red body104..108, volume1000 >= 2*120.
    # Row13 returns to green (one touch), while departing below red.
    # Row14 either stays above red, or returns through it (one touch).
    rows = [(100., 101., 99., 100., 100.)] * 10 + [
        (100., 103., 99., 102., 300.),
        (104., 105., 103., 104., 100.),
        (108., 109., 103., 104., 1000.),
        (100., 102., 99., 101., 100.),
        (104., 109., 103., 108., 100.) if cleared else (110., 111., 109., 110., 100.),
    ]
    return pd.DataFrame(rows, columns=['open', 'high', 'low', 'close', 'volume'],
                        index=pd.date_range(end=NOW, periods=15, freq='15min'))


def check_memory(reader_type, cleared):
    source = full_source()
    df = memory_tape(cleared)
    source.frames[('15m', 10)] = (df, correction())
    # Exercise the real default PVSRA and vector-zone reader, not supplied zones.
    zones = api('tree_signals').vector_zones(df)
    assert list(zones.index) == [df.index[10], df.index[12]]
    assert list(zones[['bottom', 'top', 'kind', 'open', 'touches']].itertuples(index=False, name=None)) == [
        (100., 102., 'green', False, 1),
        (104., 108., 'red', not cleared, 1 if cleared else 0),
    ]
    w = reader_type(source).walk(SYMBOL)
    assert w.complete and w.passed == STAGES
    assert w.zones == ([] if cleared else [(106., 'red', 0)])
    if cleared:
        assert w.facts['זיכרון וקטור'] == 'אין אזור פתוח'
    else:
        # ATR starts2; last five true ranges4,3,6,5,10, Wilder alpha1/14.
        # ATR=53449/16807=3.180163...; distance4/ATR=1.25779... rounds1.3.
        assert w.facts['זיכרון וקטור'] == (
            '1 אזורים פתוחים (0 מעל · 1 מתחת) · הקרוב red '
            '104.00-108.00 מתחת, 1.3 ATR, לא נבחן')
    assert w.missing.count('אין אזורי וקטור פתוחים') == int(cleared)
    assert w.facts['מגנט נזילות (EQH/EQL)'] == 'אין מגנט בטווח'


@pytest.mark.parametrize('cleared', [False, True])
def test_raw_vector_memory_handoff_and_observed_empty_classification(cleared):
    check_memory(api().TreeReader, cleared)


def check_first_vector_window(reader_type, short, offset):
    df = frame(120, '5min', False)
    df['open'] = 128.
    # i=118. Prior close at112 (=i-6) is included;111 (=i-7) excluded.
    # At the prior break EMA=128 +/-22*2/51, cloud width=22*sqrt(.0099)/4:
    # 150/106 clears the corresponding edge; intervening128 closes are inside.
    for index, close, volume in [(118 - offset, 106. if short else 150., 100.),
                                  (118, 116. if short else 140., 250.)]:
        df.iloc[index, df.columns.get_loc('close')] = close
        df.iloc[index, df.columns.get_loc('high')] = max(129., close + 1)
        df.iloc[index, df.columns.get_loc('low')] = min(127., close - 1)
        df.iloc[index, df.columns.get_loc('volume')] = volume
    source = RawSource({('5m', 5): (df, correction())})
    result = reader_type(source).first_vector_above_50(SYMBOL)
    if offset == 6:
        assert result is None
    else:
        assert result is not None
        assert result['direction'] == ('שורט' if short else 'לונג')
        assert result['vector'] == ('red' if short else 'green')
        assert result['close'] == (116. if short else 140.)
    assert source.calls == [('fetch', SYMBOL, '5m', 5)]


@pytest.mark.parametrize('short', [False, True])
@pytest.mark.parametrize('offset', [6, 7])
def test_first_vector_six_prior_closes_inclusion_boundary(short, offset):
    check_first_vector_window(api().TreeReader, short, offset)


def check_full_trace(reader_type, variant):
    source = full_source()
    reader = reader_type(source)
    assert source.calls == []
    assert reader.walk(SYMBOL, variant).complete
    # Literal source call order: DATA; ladder; options; stretch; map; optional
    # strict pivots; news; session/Brinks/PSY clocks; patterns; MTF; memory.
    assert source.calls == [
        ('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '4h', 60),
        ('fetch', SYMBOL, '1h', 30), ('fetch', SYMBOL, '30m', 30),
        ('fetch', SYMBOL, '15m', 30), ('fetch', SYMBOL, '5m', 30),
        ('options-list',),
        ('fetch', SYMBOL, '1d', 400), ('fetch', SYMBOL, '15m', 20),
        ('fetch', SYMBOL, '1h', 60), ('fetch', SYMBOL, '4h', 240),
        ('fetch', SYMBOL, '1d', 400), ('fetch', SYMBOL, '5m', 3), ('clock',),
        ('fetch', SYMBOL, '1h', 20),
        ('fetch', SYMBOL, '1h', 240), ('fetch', SYMBOL, '4h', 240),
        *([('fetch', SYMBOL, '1d', 30)] if variant == 'strict' else []),
        ('clock',), ('calendar', 'news-desk/data/ff_calendar.json'),
        ('clock',), ('clock',), ('clock',),
        ('fetch', SYMBOL, '1h', 10), ('fetch', SYMBOL, '15m', 10),
        ('fetch', SYMBOL, '5m', 5), ('fetch', SYMBOL, '15m', 5),
        ('fetch', SYMBOL, '1h', 30), ('clock',),
        ('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '15m', 10),
    ]


@pytest.mark.parametrize('variant', ['house', 'strict'])
def test_successful_full_walk_has_exact_ordered_raw_trace(variant):
    check_full_trace(api().TreeReader, variant)


@pytest.mark.parametrize('method,path,call', [
    ('read_report', 'synthetic-report.json', 'options-read'),
    ('read_tv_csv', 'synthetic-tape.csv', 'tv-read'),
])
def test_raw_artifact_failure_records_attempt_before_raising(method, path, call):
    source = RawSource()
    with pytest.raises(FileNotFoundError):
        getattr(source, method)(path)
    assert source.calls == [(call, path)]


def local_candidate(before, after):
    """Compile only this repository's candidate class; never retained originals."""
    module = api()
    text = Path(module.__file__).read_text(encoding='utf-8')
    assert text.count(before) == 1, 'Mutation must bind one exact candidate site'
    parsed = ast.parse(text.replace(before, after))
    cls = next(node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name == 'TreeReader')
    namespace = dict(vars(module))
    exec(compile(ast.Module(body=[cls], type_ignores=[]), '<local-tree-candidate>', 'exec'), namespace)
    return namespace['TreeReader']


@pytest.mark.parametrize('before,after,probe', [
    ("w.zones = [(float(m), str(k), int(tc)) for m, k, tc in zip(mid, open_z['kind'], open_z['touches'])]",
     'w.zones = []', 'memory'),
    ("mid = (open_z['top'] + open_z['bottom']) / 2.0", "mid = open_z['top']", 'memory'),
    ('(float(m), str(k), int(tc))', "(float(m), 'green', int(tc))", 'memory'),
    ('(float(m), str(k), int(tc))', '(float(m), str(k), int(tc) + 1)', 'memory'),
    ("w.missing.append('אין אזורי וקטור פתוחים')", 'pass', 'empty-memory'),
    ('obstacles=obstacles, refusal=refusal)', 'obstacles=[], refusal=refusal)', 'geometry'),
    ('targets=targets, atr=atr', 'targets=targets[:1], atr=atr', 'geometry'),
    ('return (stop, targets)', 'return (stop, targets[:1])', 'geometry'),
    ('for tf in TREND_LADDER[1:]:', 'for tf in reversed(TREND_LADDER[1:]):', 'trace'),
    ('look = df.iloc[max(0, i - 6):i]', 'look = df.iloc[max(0, i - 5):i]', 'window-six'),
    ('look = df.iloc[max(0, i - 6):i]', 'look = df.iloc[max(0, i - 7):i]', 'window-seven'),
], ids=['drop-zone-handoff', 'zone-top-not-midpoint', 'wrong-zone-kind', 'wrong-touch-count',
        'erase-observed-empty', 'drop-plan-obstacles', 'truncate-plan-targets',
        'truncate-geometry-targets', 'reverse-ladder-reads', 'exclude-sixth-close', 'include-seventh-close'])
def test_new_assertions_reject_local_runtime_mutations(before, after, probe):
    # Mutate the aligned price/cloud slices together for a real behavior defect,
    # avoiding a pandas alignment exception as a substitute for detection.
    if probe.startswith('window-'):
        count = 5 if probe == 'window-six' else 7
        module = api()
        text = Path(module.__file__).read_text(encoding='utf-8')
        start = text.index('        look = df.iloc[max(0, i - 6):i]')
        end = text.index('        if not prev_in_or_below:', start)
        before = text[start:end]
        after = before.replace('i - 6', f'i - {count}')
    candidate = local_candidate(before, after)
    with pytest.raises(AssertionError):
        if probe in ('memory', 'empty-memory'):
            check_memory(candidate, probe == 'empty-memory')
        elif probe == 'geometry':
            check_geometry(candidate, False)
        elif probe == 'trace':
            check_full_trace(candidate, 'house')
        else:
            check_first_vector_window(candidate, False, 6 if probe == 'window-six' else 7)
