"""Pending revalidation consumes actual raw matrix and tree calculations."""
from contextlib import contextmanager
from copy import deepcopy
import importlib
import importlib.util
import io
import json

import pandas as pd
import pytest

# Reuse only raw tape recipes, never expected outputs or finished reader replies.
from test_tree_walk import RawSource, full_source, frame, falling, correction, SYMBOL, NOW


def api():
    name = 'trading_system.tree_replay.tree_revalidation'
    assert importlib.util.find_spec(name) is not None, 'tree binding missing'
    return importlib.import_module(name)


class Inputs(RawSource):
    def __init__(self):
        super().__init__(full_source().frames)
        for tf, days in [('15m', 3), ('1h', 3), ('4h', 3), ('15m', 20),
                         ('1h', 60), ('1h', 2000), ('15m', 2000), ('4h', 400), ('15m', 60)]:
            self.frames[(tf, days)] = (frame(1600, rising=False), correction())
        self.shadow_lines = []
        self.deep = False

    def read_symbol(self, *args, **kwargs):
        raise AssertionError('provider-final matrix must not be used')

    def tree_walk(self, *args, **kwargs):
        raise AssertionError('provider-final tree must not be used')

    def broker_shape_ok(self, *args, **kwargs):
        raise AssertionError('provider-final shape verdict must not be used')

    def now_epoch(self):
        self.calls.append(('epoch',))
        return self.now.timestamp()

    def now_timestamp(self, *, tz):
        self.calls.append(('timestamp', str(tz)))
        return self.now.tz_convert(tz)

    def deep_exists(self, key):
        self.calls.append(('deep_exists', key))
        return self.deep

    def deep_bytes(self, key):
        self.calls.append(('deep_bytes', key))
        raise OSError('raw deep unavailable')

    def calendar_exists(self, path):
        self.calls.append(('calendar_exists', path))
        return True

    def ensure_shadow_parent(self, *, parents, exist_ok):
        self.calls.append(('shadow_parent', parents, exist_ok))

    @contextmanager
    def shadow_open(self, mode, encoding):
        self.calls.append(('shadow_open', mode, encoding))
        owner = self
        class Buffer(io.StringIO):
            def write(self, value):
                owner.calls.append(('shadow_write',))
                return super().write(value)
        buffer = Buffer()
        try:
            yield buffer
        finally:
            self.shadow_lines.extend(buffer.getvalue().splitlines())
            buffer.close()
            self.calls.append(('shadow_close',))


def pending(*, age=7200., direction='לונג'):
    return dict(symbol=SYMBOL, direction=direction, entry=110., stop=99.7,
                ts=NOW.timestamp() - age, bias_at_send={'4h': 0., '1h': 0.})


def opposite_tree(source):
    for key in [('4h', 60), ('1h', 30)]:
        df, corr = source.frames[key]
        source.frames[key] = (falling(df), corr)


def test_actual_failed_tree_is_bound_and_constructor_is_inert():
    source = RawSource()
    bound = api().TreeRevalidation(source)
    assert source.calls == []
    assert bound.checks._tree_agrees(SYMBOL, 'לונג') == (
        True, 'העץ נעצר ב-DATA: אין נתונים (LookupError)')
    assert source.calls == [('fetch', SYMBOL, '15m', 10)]


@pytest.mark.parametrize('inverse,side', [(False, 1), (True, -1)])
def test_actual_matrix_reader_uses_original_requests_and_entire_delivered_frame(inverse, side):
    source = RawSource()
    df = falling(frame()) if inverse else frame()
    for tf, lookback in [('5m', 55), ('30m', 90), ('1h', 240)]:
        source.frames[(tf, lookback)] = (df, correction())
    bound = api().TreeRevalidation(source)
    result = bound.read_symbol(SYMBOL, tfs=('5m', '30m', '1h'))
    assert list(result) == ['5m', '30m', '1h']
    assert source.calls == [('fetch', SYMBOL, '5m', 55), ('fetch', SYMBOL, '30m', 90),
                            ('fetch', SYMBOL, '1h', 240)]
    for tf, view in result.items():
        assert view.tf == tf and view.close == 110. and view.bar_ts == NOW.timestamp()
        assert view.atr == pytest.approx(2.) and view.basis_note is None
        assert view.reads[0].tool == 'tr' and view.reads[0].direction == side
        assert [r.tool for r in view.reads] == ['tr', 'supertrend', 'vwap', 'structure']


@pytest.mark.parametrize('fault', ['none_correction', 'missing_frame', 'unknown_tf'])
def test_matrix_preserves_source_errors_instead_of_inventing_empty_views(fault):
    source = RawSource({('1h', 240): (frame(), None if fault == 'none_correction' else correction())})
    if fault == 'missing_frame':
        source.frames.clear()
    error = {'none_correction': AttributeError, 'missing_frame': LookupError, 'unknown_tf': KeyError}[fault]
    with pytest.raises(error):
        api().TreeRevalidation(source).read_symbol(SYMBOL, tfs=('bad' if fault == 'unknown_tf' else '1h',))


def test_matrix_retains_actual_visible_correction_note():
    source = RawSource({('1h', 240): (frame(), correction('mt5_broker'))})
    view = api().TreeRevalidation(source).read_symbol(SYMBOL, tfs=('1h',))['1h']
    assert view.basis_note == '✅ OANDA:XAUUSD: synthetic'


def test_matrix_history_before_requested_lookback_still_contributes_to_atr():
    # LOOKBACK[5m]=55 identifies the fetch, not a delivered-row limit. A range
    # of30 just before the final55rows raises Wilder ATR by28/14, which then
    # decays55times. Trimming to55rows incorrectly returns exactly2.
    df = frame(1001, rising=False)
    df.iloc[-56, df.columns.get_loc('high')] = 157.
    source = RawSource({('5m', 55): (df, correction())})
    view = api().TreeRevalidation(source).read_symbol(SYMBOL, tfs=('5m',))['5m']
    assert view.atr == pytest.approx(2. + 2. * (13. / 14.) ** 55)
    assert view.atr > 2.01


@pytest.mark.parametrize('opposite', [False, True])
def test_aged_pending_consumes_actual_tree_without_provider_final_verdicts(opposite):
    source = Inputs()
    if opposite:
        opposite_tree(source)
    t = pending()
    before = deepcopy(t)
    bound = api().TreeRevalidation(source)
    assert source.calls == []
    ok, reason, verified = bound.revalidate_pending(t, now=NOW.timestamp())
    assert ok is (not opposite) and verified is True
    assert ('העץ מצביע לכיוון ההפוך (שורט)' if opposite else 'העץ מאשר') in reason
    assert t == before and ('fetch', SYMBOL, '15m', 10) in source.calls
    shadows = [json.loads(line) for line in source.shadow_lines]
    assert shadows and all(row['symbol'] == SYMBOL and row['ts'] == NOW.timestamp() for row in shadows)
    assert {'session', 'news_window', 'stop_distance'} <= {row['check'] for row in shadows}
    first_open = source.calls.index(('shadow_open', 'a', 'utf-8'))
    assert source.calls[first_open-1:first_open+4] == [
        ('shadow_parent', True, True), ('shadow_open', 'a', 'utf-8'),
        ('epoch',), ('shadow_write',), ('shadow_close',)]


@pytest.mark.parametrize('age,consulted', [(7199.999, False), (7200., True)])
def test_two_hour_boundary_controls_real_tree_reads(age, consulted):
    source = Inputs()
    opposite_tree(source)
    ok, reason, verified = api().TreeRevalidation(source).revalidate_pending(pending(age=age), now=NOW.timestamp())
    assert ok is (not consulted) and verified
    assert (('fetch', SYMBOL, '15m', 10) in source.calls) is consulted
    assert ('העץ מצביע' in reason) is consulted


@pytest.mark.parametrize('failure,stage', [('data', 'DATA'), ('news', 'SESSION'), ('map', 'LEVELS')])
def test_actual_tree_unavailable_paths_allow_only_unverified(failure, stage):
    source = Inputs()
    if failure == 'data':
        source.frames[('15m', 10)] = LookupError('tree tape unavailable')
    elif failure == 'news':
        source.calendar = json.dumps([{'dateline': NOW.timestamp() + 300, 'impact': 'High', 'title': 'event'},
                                      {'dateline': NOW.timestamp() + 86400, 'impact': 'Low'}])
    else:
        daily = source.frames[('1d', 400)]
        source.frames[('1d', 400)] = [daily, daily, (frame(0), correction())]
    ok, reason, verified = api().TreeRevalidation(source).revalidate_pending(pending(), now=NOW.timestamp())
    assert ok and not verified and 'העץ נעצר ב-' + stage in reason


def test_opposite_direction_precedes_later_tree_target_failure():
    source = Inputs()
    opposite_tree(source)
    df, corr = source.frames[('15m', 10)]
    # Completed evidence remains midrange/short; the forming gap places price
    # below every positive source-map level, so the later short TARGET fails.
    for col, value in [('open', 1.), ('close', 1.), ('high', 2.), ('low', 0.)]:
        df.iloc[-1, df.columns.get_loc(col)] = value
    bound = api().TreeRevalidation(source)
    walk = bound.tree_walk(SYMBOL)
    assert walk.direction == 'שורט' and walk.reached == 'TARGET'
    assert walk.stopped_because == 'אין רמה בכיוון העסקה לשמש יעד'
    ok, reason, verified = bound.revalidate_pending(pending(), now=NOW.timestamp())
    assert not ok and verified and 'העץ מצביע לכיוון ההפוך (שורט)' in reason


def test_early_freshness_veto_skips_tree_and_preserves_unverified():
    source = Inputs()
    df, corr = source.frames[('15m', 3)]
    df.index = df.index - pd.Timedelta(minutes=121)
    ok, reason, verified = api().TreeRevalidation(source).revalidate_pending(pending(), now=NOW.timestamp())
    assert not ok and not verified and 'אין נתונים לאימות מחדש' in reason
    assert ('fetch', SYMBOL, '15m', 10) not in source.calls


def test_clean_tree_cannot_upgrade_unknown_freshness():
    source = Inputs()
    source.frames[('15m', 3)] = OSError('age unavailable')
    ok, reason, verified = api().TreeRevalidation(source).revalidate_pending(pending(), now=NOW.timestamp())
    assert ok and not verified and 'העץ מאשר' in reason


def test_default_age_clock_is_extra_operation_after_still_valid():
    explicit, implicit = Inputs(), Inputs()
    first = api().TreeRevalidation(explicit).revalidate_pending(pending(), now=NOW.timestamp())
    second = api().TreeRevalidation(implicit).revalidate_pending(pending())
    assert first == second and first[0] and first[2]
    at = implicit.calls.index(('fetch', SYMBOL, '15m', 10))
    assert implicit.calls[at - 1] == ('epoch',)
    assert implicit.calls[:at - 1] + implicit.calls[at:] == explicit.calls


def test_still_valid_entrypoint_runs_actual_checks_without_tree():
    source = Inputs()
    ok, _, verified = api().TreeRevalidation(source).still_valid(pending())
    assert ok and verified and source.shadow_lines
    assert ('fetch', SYMBOL, '15m', 10) not in source.calls


def test_original_higher_bias_flip_vetoes_before_stretch_and_tree():
    source = Inputs()
    df = frame()
    prices = [5000. - i for i in range(len(df))]
    df['close'], df['open'] = prices, [p + .005 for p in prices]
    df['high'], df['low'] = [p + 1 for p in prices], [p - 1 for p in prices]
    for key in [('4h', 240), ('1h', 240)]:
        source.frames[key] = (df, correction())
    t = pending()
    t['bias_at_send'] = {'4h': 1., '1h': 1.}
    ok, reason, verified = api().TreeRevalidation(source).revalidate_pending(t)
    assert not ok and verified and reason.startswith('ההטיה הגבוהה התהפכה מאז השליחה')
    assert source.calls == [('fetch', SYMBOL, '4h', 240), ('fetch', SYMBOL, '1h', 240)]
    assert not source.shadow_lines


@pytest.mark.parametrize('span,verified', [(20 * 86400, True), (20 * 86400 - 1, False)])
def test_real_shape_gate_uses_operation_clock_not_provider_verdict(span, verified):
    source = Inputs()
    daily, _ = source.frames[('1d', 400)]
    corr = correction('tv_spliced')
    corr.tv_from = NOW - pd.Timedelta(seconds=span)
    source.frames[('1d', 400)] = (daily, corr)
    ok, _, actual_verified = api().TreeRevalidation(source).still_valid(pending())
    assert ok and actual_verified is verified
    at = source.calls.index(('fetch', SYMBOL, '1d', 400))
    assert source.calls[at + 1] == ('clock',)
    assert any(json.loads(row)['check'] == 'stretch' for row in source.shadow_lines) is (not verified)


def test_raw_deep_read_failure_keeps_original_optional_fallback():
    source = Inputs()
    source.deep = True
    ok, _, verified = api().TreeRevalidation(source).still_valid(pending())
    assert ok and verified
    for key in ['deep/XAUUSD_H1.csv', 'deep/XAUUSD_M15.csv']:
        at = source.calls.index(('deep_exists', key))
        assert source.calls[at + 1] == ('deep_bytes', key)
    checks = {json.loads(row)['check'] for row in source.shadow_lines}
    assert {'ema50_1h', 'ema50_15m'} <= checks


def test_pending_metadata_does_not_change_original_house_default():
    source = Inputs()
    source.frames[('1d', 30)] = OSError('strict pivot unavailable')
    t = pending()
    t['variant'] = 'strict'
    ok, why, verified = api().TreeRevalidation(source).revalidate_pending(t, now=NOW.timestamp())
    assert ok and verified and 'העץ מאשר' in why
    assert ('fetch', SYMBOL, '1d', 30) not in source.calls


@pytest.mark.parametrize('stamp', [None, 'invalid'])
def test_invalid_pending_send_time_does_not_invent_a_clean_tree_approval(stamp):
    source = Inputs()
    t = pending()
    t['ts'] = stamp
    ok, reason, verified = api().TreeRevalidation(source).revalidate_pending(t, now=NOW.timestamp())
    assert ok and not verified and 'העץ מאשר' not in reason
    assert ('fetch', SYMBOL, '15m', 10) not in source.calls
