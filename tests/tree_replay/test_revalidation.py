"""Original pending revalidation: raw calendar semantics and real input calculations."""
from contextlib import contextmanager
import importlib
import importlib.util
import io
import json
import math
from types import SimpleNamespace

import pandas as pd
import numpy as np
import pytest

from trading_system.tree_replay._vendor.admission_matrix import read_frame
from trading_system.tree_replay._vendor.correction import Correction, broker_shape_ok_at


NOW = pd.Timestamp('2026-09-09T16:00:00Z')
SYMBOL = 'OANDA:XAUUSD'
LONG, SHORT = 'לונג', 'שורט'


def api():
    name = 'trading_system.tree_replay._vendor.revalidation'
    assert importlib.util.find_spec(name) is not None, 'revalidation missing'
    return importlib.import_module(name)


def bars(n=100, *, step=1., end=NOW):
    close = [200.+step*i for i in range(n)]
    return pd.DataFrame({'open':close, 'high':[x+1 for x in close],
        'low':[x-1 for x in close], 'close':close, 'volume':1.},
        index=pd.date_range(end=end, periods=n, freq='15min'))


def daily():
    return pd.DataFrame({'open':100., 'high':110., 'low':90., 'close':100., 'volume':1.},
        index=pd.date_range(end=NOW.normalize(), periods=22, freq='D'))


def trade(direction=LONG, age_s=60.):
    return dict(symbol=SYMBOL, direction=direction, entry=100., stop=95.,
                ts=NOW.timestamp()-age_s, bias_at_send={'4h':1., '1h':1.})


class Ports:
    """Offline boundary replies; matrix/EMA/stretch/PVSRA/JSON stay real."""
    def __init__(self):
        self.frames = {(tf,days): bars() for tf,days in [
            ('15m',20),('1h',60),('4h',240),('15m',3),('1h',3),('4h',3),
            ('1h',2000),('15m',2000),('4h',400),('15m',60)]}
        self.frames['1d',400] = daily()
        self.bias_frames = {'4h':bars(60), '1h':bars(60)}
        self.corr = Correction(SYMBOL,0.,'tv_daily','high','synthetic')
        self.calls = []
        self.shadow_text = ''
        self.calendar = '[]'
        self.walk = SimpleNamespace(direction=LONG, stopped_because='', reached='TARGET')
        self.now = NOW
        self.shadow_fault = None

    def fetch_corrected(self,symbol,tf,lookback):
        self.calls.append(('fetch',symbol,tf,lookback))
        assert symbol == SYMBOL
        value = self.frames[tf,lookback]
        if isinstance(value,Exception): raise value
        return value,self.corr

    def read_symbol(self,symbol,tfs):
        self.calls.append(('matrix',symbol,tfs))
        assert symbol == SYMBOL
        return {tf:read_frame(self.bias_frames[tf],tf) for tf in tfs if tf in self.bias_frames}

    def broker_shape_ok(self,correction,days):
        self.calls.append(('shape',days))
        return broker_shape_ok_at(correction,days,decision_time=self.now)

    def deep_exists(self,key):
        self.calls.append(('deep_exists',key))
        return False

    def deep_bytes(self,key):
        raise AssertionError('absent deep file must not be read')

    def now_epoch(self):
        self.calls.append(('epoch',))
        if self.shadow_fault == 'clock': raise OSError('captured clock failure')
        return self.now.timestamp()

    def now_timestamp(self,*,tz):
        self.calls.append(('timestamp',str(tz)))
        return self.now.tz_convert(tz)

    def now_utc(self):
        self.calls.append(('utc',))
        return self.now.to_pydatetime()

    def tree_walk(self,symbol):
        self.calls.append(('walk',symbol))
        if isinstance(self.walk,Exception): raise self.walk
        return self.walk

    def ensure_shadow_parent(self,*,parents,exist_ok):
        self.calls.append(('shadow_parent',parents,exist_ok))
        if self.shadow_fault == 'parent': raise OSError('captured parent failure')

    @contextmanager
    def shadow_open(self,mode,encoding):
        self.calls.append(('shadow_open',mode,encoding))
        if self.shadow_fault == 'open': raise OSError('captured open failure')
        owner = self
        class Buffer(io.StringIO):
            def write(self,value):
                if owner.shadow_fault == 'write': raise OSError('captured write failure')
                return super().write(value)
        buffer = Buffer()
        try:
            yield buffer
        finally:
            self.shadow_text += buffer.getvalue()
            buffer.close()
            self.calls.append(('shadow_close',))
            if self.shadow_fault == 'close': raise OSError('captured close failure')

    def calendar_exists(self,key):
        self.calls.append(('calendar_exists',key))
        return self.calendar is not None

    def calendar_text(self,key):
        self.calls.append(('calendar_text',key))
        if isinstance(self.calendar,Exception): raise self.calendar
        return self.calendar

    def shadows(self):
        return [json.loads(line) for line in self.shadow_text.splitlines()]


@pytest.mark.parametrize('event,want',[
    ({'dateline':17,'date':'invalid'},17.),
    ({'dateline':-3},-3.),
    ({'dateline':True,'date':'2026-01-01T00:00:00Z'},1767225600.),
    ({'dateline':0,'date':'2026-01-01T02:00:00+02:00'},1767225600.),
    ({'dateline':'17','date':'2026-01-01T00:00:00Z'},1767225600.),
    ({'date':'invalid'},None),({},None),({'dateline':False},None),
])
def test_calendar_numeric_precedence_and_original_fallback(event,want):
    assert api().calendar_event_ts(event) == want


def test_calendar_raw_nonfinite_values_are_not_sanitized():
    m = api()
    assert math.isnan(m.calendar_event_ts({'dateline':float('nan')}))
    assert m.calendar_event_ts({'dateline':float('inf')}) == float('inf')


def test_news_window_inclusive_first_match_identity_not_nearest_or_sorted():
    m = api()
    first = {'dateline':1180,'impact':'HIGH impact','title':'first'}
    closer = {'dateline':1001,'impact':'High','title':'closer'}
    assert m.calendar_high_impact_in_window([first,closer],1000.,180.) is first
    assert m.calendar_high_impact_in_window([first],1000.,179.999) is None
    assert m.calendar_high_impact_in_window([first],1000.,-1.) is None


def test_news_missing_impact_raises_only_inside_and_leading_space_is_not_high():
    m = api()
    with pytest.raises(ValueError,match='no impact'):
        m.calendar_high_impact_in_window([{'dateline':1000}],1000.,180.)
    assert m.calendar_high_impact_in_window([{'dateline':1}],1000.,180.) is None
    assert m.calendar_high_impact_in_window([{'dateline':1000,'impact':' High'}],1000.,180.) is None


@pytest.mark.parametrize('nets,short,want',[
    ({'4h':43.,'1h':-2.},True,False),({'4h':25.,'1h':0.},True,True),
    ({'4h':24.999,'1h':0.},True,False),({'4h':-25.,'1h':0.},False,True),
    ({'4h':-43.,'1h':2.},False,False),({},True,False),
])
def test_bias_requires_magnitude_and_each_frame_against_not_sum_alone(nets,short,want):
    assert api()._bias_against(nets,short) is want


@pytest.mark.parametrize('direction,step',[(LONG,1.),(SHORT,-1.)])
def test_real_calculations_clean_tape_keeps_all_shadows_observational(direction,step):
    m = api()
    p = Ports()
    p.bias_frames = {'4h':bars(60,step=step),'1h':bars(60,step=step)}
    t = trade(direction)
    ok,why,verified = m.Revalidation(p).still_valid(t)
    assert (ok,why,verified) == (True,'',True)
    rows = p.shadows()
    assert [r['check'] for r in rows] == ['ema50_1h','ema50_15m','session',
        'stop_distance','structure_4h','opposing_vector_15m','news_window']
    assert all(r['ts'] == NOW.timestamp() and r['symbol'] == SYMBOL for r in rows)
    assert rows[-1]['detail'] == 'clear' and rows[-1]['would_block'] is False
    assert ('fetch',SYMBOL,'1d',400) in p.calls and ('shape',20) in p.calls
    assert ('calendar_text','news-desk/data/ff_calendar.json') in p.calls
    if direction == SHORT:
        assert rows[0]['would_block'] is True  # Rising EMA shadow does not veto.


def test_actual_higher_bias_flip_cancels_before_stretch_age_and_shadow_reads():
    m = api()
    p = Ports()
    p.bias_frames = {'4h':bars(60,step=-1.),'1h':bars(60,step=-1.)}
    ok,why,verified = m.Revalidation(p).still_valid(trade())
    assert not ok and verified and 'התהפכה מאז השליחה' in why
    assert p.calls == [('matrix',SYMBOL,('4h','1h'))]
    assert p.shadow_text == ''


@pytest.mark.parametrize('sent,label',[
    ({'4h':-1.,'1h':-1.},'כך גם בשליחה'),
    ({'4h':1.,'1h':-1.},'בשליחה הייתה ניטרלית'),
    ({},'בשליחה לא נקראה'),
])
def test_against_bias_without_actual_flip_is_a_label_not_cancellation(sent,label):
    m = api()
    p = Ports()
    p.bias_frames = {'4h':bars(60,step=-1.),'1h':bars(60,step=-1.)}
    t = trade()
    t['bias_at_send'] = sent
    ok,why,verified = m.Revalidation(p).still_valid(t)
    assert ok and verified and label in why and p.shadows()


@pytest.mark.parametrize('age_min,ok,verified',[
    (0.,True,True),(20.,True,True),(20.001,True,False),
    (120.,True,False),(120.001,False,False),(-1.,True,True),
])
def test_freshness_exact_soft_hard_and_future_boundaries(age_min,ok,verified):
    m = api()
    p = Ports()
    p.frames['15m',3] = bars(end=NOW-pd.Timedelta(minutes=age_min))
    result = m.Revalidation(p).still_valid(trade())
    assert (result[0],result[2]) == (ok,verified)
    assert bool(p.shadows()) is ok


def test_four_hour_age_is_normalized_to_own_frame_size():
    m = api()
    p = Ports()
    p.frames['4h',3] = bars(end=NOW-pd.Timedelta(minutes=90))
    assert m.Revalidation(p).still_valid(trade()) == (True,'',True)
    p.frames['4h',3] = bars(end=NOW-pd.Timedelta(minutes=1921))
    ok,why,verified = m.Revalidation(p).still_valid(trade())
    assert not ok and not verified and 'אין נתונים' in why


@pytest.mark.parametrize('fault,want',[('one_empty',True),('all_empty',False),('later_error',False)])
def test_empty_age_is_skipped_but_exception_resets_prior_evidence(fault,want):
    m = api()
    p = Ports()
    if fault == 'one_empty': p.frames['1h',3] = None
    elif fault == 'all_empty':
        for tf in ('15m','1h','4h'): p.frames[tf,3] = pd.DataFrame()
    else: p.frames['4h',3] = OSError('captured')
    ok,why,verified = m.Revalidation(p).still_valid(trade())
    assert ok and verified is want


@pytest.mark.parametrize('calendar,detail,fired',[
    (None,'calendar file missing',False),('broken-json','unavailable:',False),
    (json.dumps([{'dateline':NOW.timestamp(),'impact':'High','title':'CPI'}]),'inside ±30m of: CPI',True),
    (json.dumps([{'dateline':NOW.timestamp()}]),'unavailable:',False),
])
def test_news_fired_or_unavailable_is_shadow_only(calendar,detail,fired):
    m = api()
    p = Ports()
    p.calendar = calendar
    assert m.Revalidation(p).still_valid(trade()) == (True,'',True)
    row = p.shadows()[-1]
    assert row['check'] == 'news_window' and row['would_block'] is fired
    assert detail in row['detail']


@pytest.mark.parametrize('fault',['parent','open','clock','write','close'])
def test_shadow_writer_failures_remain_best_effort(fault):
    m = api()
    p = Ports()
    p.shadow_fault = fault
    assert m.Revalidation(p).still_valid(trade()) == (True,'',True)


@pytest.mark.parametrize('age,walks',[(7199.,False),(7200.,True),(-1.,False)])
def test_pending_exact_two_hour_recheck_boundary(age,walks):
    m = api()
    p = Ports()
    ok,why,verified = m.Revalidation(p).revalidate_pending(trade(age_s=age),now=NOW.timestamp())
    assert ok and verified
    assert (('walk',SYMBOL) in p.calls) is walks
    assert ('העץ מאשר' in why) is walks


@pytest.mark.parametrize('walk,ok,verified,note',[
    (None,True,False,'לא החזיר תשובה'),
    (OSError('captured'),True,False,'לא זמין (OSError)'),
    (SimpleNamespace(direction=LONG,stopped_because='missing',reached='DATA'),True,False,'נעצר ב-DATA'),
    (SimpleNamespace(direction=SHORT,stopped_because='missing',reached='DATA'),False,True,'לכיוון ההפוך'),
])
def test_pending_tree_boundary_precedence_and_unknown_states(walk,ok,verified,note):
    m = api()
    p = Ports()
    p.walk = walk
    result = m.Revalidation(p).revalidate_pending(trade(age_s=7200.),now=NOW.timestamp())
    assert (result[0],result[2]) == (ok,verified) and note in result[1]


@pytest.mark.parametrize('stamp',[None,'invalid'])
def test_invalid_send_time_allows_unverified_without_tree(stamp):
    m = api()
    p = Ports()
    t = trade()
    t['ts'] = stamp
    assert m.Revalidation(p).revalidate_pending(t,now=NOW.timestamp()) == (True,'',False)
    assert ('walk',SYMBOL) not in p.calls


@pytest.mark.parametrize('direction,close,high,low,blocked',[
    (LONG,116.,126.,100.,True),(SHORT,84.,100.,74.,True),
    (LONG,84.,100.,74.,False),(SHORT,116.,126.,100.,False),
])
def test_actual_extension_veto_applies_only_in_trade_direction(direction,close,high,low,blocked):
    m = api()
    p = Ports()
    p.frames['1d',400].iloc[-1] = [100.,high,low,close,1.]
    p.bias_frames = {'4h':bars(60,step=1. if direction == LONG else -1.),
                     '1h':bars(60,step=1. if direction == LONG else -1.)}
    ok,why,verified = m.Revalidation(p).still_valid(trade(direction))
    assert ok is (not blocked) and verified
    if blocked:
        assert '130% מה-ADR' in why
        assert not p.shadows()
        assert [c[2:] for c in p.calls if c[0]=='fetch'] == [
            ('1d',400),('15m',20),('1h',60),('4h',240)]
    else:
        assert p.shadows()[-1]['check'] == 'news_window'


@pytest.mark.parametrize('fault,check',[('missing_higher','core'),('empty_daily','stretch'),('failed_daily','stretch')])
def test_unavailable_core_is_logged_and_does_not_claim_verified(fault,check):
    m = api()
    p = Ports()
    if fault == 'missing_higher': del p.bias_frames['1h']
    elif fault == 'empty_daily': p.frames['1d',400] = pd.DataFrame()
    else: p.frames['1d',400] = OSError('captured daily failure')
    assert m.Revalidation(p).still_valid(trade()) == (True,'',False)
    rows = p.shadows()
    assert rows[0]['check'] == check and rows[0]['would_block'] is False
    assert rows[-1]['check'] == 'news_window'


def test_missing_direction_raises_before_any_source_operations():
    m = api()
    p = Ports()
    with pytest.raises(KeyError,match='direction'):
        m.Revalidation(p).still_valid({'symbol':SYMBOL})
    assert p.calls == []


@pytest.mark.parametrize('direction,offset,fired',[
    (LONG,12,True),(LONG,13,False),(SHORT,12,True),(SHORT,13,False),
])
def test_actual_opposing_pvsra_uses_only_last_twelve_bars(direction,offset,fired):
    m = api()
    p = Ports()
    f = bars(60)
    # Background climax direction agrees; one opposing bar has triple volume.
    f['open'] = f['close']+(.5 if direction == SHORT else -.5)
    f.iloc[-offset,f.columns.get_loc('open')] = f['close'].iloc[-offset]+(.5 if direction == LONG else -.5)
    f.iloc[-offset,f.columns.get_loc('volume')] = 3.
    p.frames['15m',60] = f
    assert m.Revalidation(p).still_valid(trade(direction))[0] is True
    row = next(r for r in p.shadows() if r['check']=='opposing_vector_15m')
    assert row['would_block'] is fired


def test_actual_bearish_structure_and_zero_risk_remain_shadow_only():
    m = api()
    p = Ports()
    prices = np.interp(np.arange(24),[0,3,9,15,20,23],[5,11,2,10,1,5])
    f = bars(24)
    f['open']=f['close']=prices
    f['high'],f['low']=prices+1,prices-1
    p.frames['4h',400]=f
    t=trade()
    t['stop']=t['entry']
    assert m.Revalidation(p).still_valid(t)==(True,'',True)
    rows={r['check']:r for r in p.shadows()}
    assert rows['stop_distance']['would_block'] is True
    assert rows['structure_4h']['would_block'] is True
    assert rows['structure_4h']['detail']=='structure dir -1, short=False'


def test_shadow_json_uses_operation_clock_and_exact_effect_order():
    m=api()
    p=Ports()
    reader=m.Revalidation(p)
    reader._shadow(SYMBOL,'בדיקה',1,'פרטים')
    p.now=NOW+pd.Timedelta(seconds=7)
    reader._shadow(SYMBOL,'second',0,'detail')
    assert p.calls==[('shadow_parent',True,True),('shadow_open','a','utf-8'),
        ('epoch',),('shadow_close',)]*2
    assert [r['ts'] for r in p.shadows()]==[NOW.timestamp(),NOW.timestamp()+7]
    assert [r['would_block'] for r in p.shadows()]==[True,False]
    assert 'בדיקה' in p.shadow_text and p.shadow_text.endswith('\n')


def test_pending_default_clock_is_read_after_shadows_and_not_on_initial_veto():
    m=api()
    p=Ports()
    assert m.Revalidation(p).revalidate_pending(trade())==(True,'',True)
    assert p.calls[-1]==('epoch',)
    explicit=Ports()
    m.Revalidation(explicit).revalidate_pending(trade(),now=NOW.timestamp())
    assert explicit.calls==p.calls[:-1]
    blocked=Ports()
    blocked.bias_frames={'4h':bars(60,step=-1.),'1h':bars(60,step=-1.)}
    assert m.Revalidation(blocked).revalidate_pending(trade(age_s=7200.))[0] is False
    assert blocked.calls==[('matrix',SYMBOL,('4h','1h'))]


def test_pending_missing_timestamp_does_not_become_cancellation():
    m=api()
    p=Ports()
    t=trade()
    del t['ts']
    assert m.Revalidation(p).revalidate_pending(t,now=NOW.timestamp())==(True,'',False)
    assert ('walk',SYMBOL) not in p.calls


def test_full_fetch_order_includes_calculation_reads_before_separate_age_reads():
    m=api()
    p=Ports()
    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
    assert [c[2:] for c in p.calls if c[0]=='fetch']==[
        ('1d',400),('15m',20),('1h',60),('4h',240),
        ('15m',3),('1h',3),('4h',3),('1h',2000),('15m',2000),
        ('4h',400),('15m',60)]
    assert [c for c in p.calls if c[0]=='timestamp']==[('timestamp','UTC')]*4
    idx=p.calls.index(('calendar_exists','news-desk/data/ff_calendar.json'))
    assert p.calls[idx:idx+3]==[('calendar_exists','news-desk/data/ff_calendar.json'),
        ('utc',),('calendar_text','news-desk/data/ff_calendar.json')]


@pytest.mark.parametrize('seconds,fired',[(1800.,True),(1800.001,False),(-1800.,True),(-1800.001,False)])
def test_actual_news_consumer_uses_iso_date_and_thirty_minute_inclusive_window(seconds,fired):
    m=api()
    p=Ports()
    p.calendar=json.dumps([{'date':(NOW+pd.Timedelta(seconds=seconds)).isoformat(),
                           'impact':'High','title':'ISO event'}])
    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
    row=p.shadows()[-1]
    assert row['would_block'] is fired
    assert row['detail']==('inside ±30m of: ISO event' if fired else 'clear')


def test_age_probe_corrections_are_not_new_vetoes():
    m=api()
    class AgePorts(Ports):
        def fetch_corrected(self,symbol,tf,lookback):
            f,c=super().fetch_corrected(symbol,tf,lookback)
            if lookback==3:
                c=Correction(symbol,0.,'none','unknown','captured unavailable correction')
                assert c.unverified
            return f,c
    assert m.Revalidation(AgePorts()).still_valid(trade())==(True,'',True)


def test_closed_weekend_session_is_shadow_not_veto():
    m=api()
    p=Ports()
    p.now=pd.Timestamp('2026-09-12T16:00:00Z')
    for (tf,days),f in p.frames.items():
        if tf!='1d': f.index=f.index+(p.now-NOW)
    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
    row=next(r for r in p.shadows() if r['check']=='session')
    assert row['would_block'] is True and row['detail']=='sessions=[]'


@pytest.mark.parametrize('frame_key,check',[(('4h',400),'structure_4h'),(('15m',60),'opposing_vector_15m')])
def test_shadow_calculation_unavailability_is_logged_not_vetoed(frame_key,check):
    m=api()
    p=Ports()
    p.frames[frame_key]=OSError('captured shadow data failure')
    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
    row=next(r for r in p.shadows() if r['check']==check)
    assert row['would_block'] is False and row['detail'].startswith('unavailable:')


def test_real_ema_stack_omits_failed_frame_but_keeps_other_shadows():
    m=api()
    p=Ports()
    p.frames['1h',2000]=OSError('captured EMA data failure')
    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
    checks=[r['check'] for r in p.shadows()]
    assert 'ema50_1h' not in checks and 'ema50_15m' in checks and 'news_window' in checks
