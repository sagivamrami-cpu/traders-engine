"""Literal OHLCV fixtures exercise original readers, not final verdict doubles."""
import importlib
import importlib.util
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


def api(module):
    name='trading_system.tree_replay._vendor.'+module
    assert importlib.util.find_spec(name) is not None, 'pattern reader missing: '+module
    return importlib.import_module(name)


def frame(anchors=None,n=40,start='2026-09-09 10:00Z'):
    anchors=anchors or {0:100.,n-1:100.}
    c=np.interp(np.arange(n),list(anchors),list(anchors.values()))
    return pd.DataFrame(dict(open=c,high=c+1,low=c-1,close=c,volume=1.),
        index=pd.date_range(start,periods=n,freq='5min'))


class Frames:
    def __init__(self,mapping,now='2026-09-09 15:00Z',corr=None):
        self.mapping=mapping
        self.now=pd.Timestamp(now).to_pydatetime()
        self.corr=corr
        self.calls=[]
    def fetch_corrected(self,*key):
        self.calls.append(key)
        value=self.mapping[key]
        if isinstance(value,list): value=value.pop(0)
        if isinstance(value,Exception): raise value
        return value.copy(),self.corr
    def now_utc(self):
        self.calls.append(('clock',))
        return self.now


def w_frame():
    return frame({0:100.,5:103.,10:90.,17:110.,25:91.,35:115.,39:115.})


def mirror(f):
    result=f.copy()
    for col in ['open','close']: result[col]=200-f[col]
    result['high'],result['low']=200-f['low'],200-f['high']
    return result


@pytest.mark.parametrize('inverse,kind,legs,neck,direction',[
    (False,'W',(89.,90.),111.,'לונג'),(True,'M',(111.,110.),89.,'שורט')])
def test_wm_geometry_and_actual_local_vector_warmup(inverse,kind,legs,neck,direction):
    f=mirror(w_frame()) if inverse else w_frame()
    f.loc[f.index[25],'volume']=1000
    p=Frames({('X','1h',10):f})
    got=api('wm').WmReader(p).detect('X','1h')
    assert (got.kind,got.leg1,got.leg2,got.neckline)==(kind,*legs,neck)
    assert got.confirmed and got.direction==direction and got.bars_since_leg2==14
    assert not got.vector_at_leg2  # original five-row PVSRA has no baseline
    assert p.calls==[('X','1h',10)]


@pytest.mark.parametrize('close,confirmed',[(111.,False),(111.01,True),(110.99,False)])
def test_wm_neckline_needs_strict_close(close,confirmed):
    f=w_frame(); f.iloc[-1,f.columns.get_loc('close')]=close
    got=api('wm').WmReader(Frames({('X','15m',10):f})).detect('X')
    assert got.kind=='W' and got.confirmed==confirmed


def test_swing_priority_and_plateau_policy_are_not_interchangeable():
    f=frame(n=10)
    assert api('wm')._swings(f)==([],[(6,99.)])
    assert api('liquidity')._swings(f)==([(3,101.),(4,101.),(5,101.),(6,101.)],[])
    assert api('wm')._dedup_pivots([(1,10.),(4,10.),(8,10.),(9,11.)],3)==[(4,10.),(8,10.),(9,11.)]


@pytest.mark.parametrize('n,present',[(66,True),(67,False)])
def test_wm_age_boundary_without_new_pivots(n,present):
    f=frame({0:100.,5:103.,10:90.,17:110.,25:91.,n-1:115.},n)
    got=api('wm').WmReader(Frames({('X','15m',10):f})).detect('X')
    assert (got is not None)==present
    if present: assert got.bars_since_leg2==40


@pytest.mark.parametrize('leg,present',[(89.5,True),(80.,False)])
def test_wm_second_leg_undercut_tolerance(leg,present):
    f=frame({0:100.,10:90.,17:110.,25:leg,39:115.})
    got=api('wm').WmReader(Frames({('X','15m',10):f})).detect('X')
    assert (got is not None)==present


def test_wm_newer_m_takes_precedence_over_valid_w():
    f=frame({0:100.,5:90.,10:110.,18:91.,25:109.,39:95.})
    got=api('wm').WmReader(Frames({('X','15m',10):f})).detect('X')
    assert (got.kind,got.leg1,got.leg2,got.neckline,got.bars_since_leg2)==('M',111.,110.,90.,14)


@pytest.mark.parametrize('module,method,lookback,minimum,empty',[
    ('wm','detect',10,30,None),('liquidity','pools',10,40,[]),
    ('liquidity','run',10,40,False),('checklists','rvc_gvc',5,30,None),
    ('checklists','blocks',10,40,[])])
@pytest.mark.parametrize('fault',['short','correction','error'])
def test_reader_initial_unavailability_preserves_original_result(module,method,lookback,minimum,empty,fault):
    f=OSError('missing') if fault=='error' else frame(n=minimum-1 if fault=='short' else 60)
    p=Frames({('X','15m',lookback):f},corr=SimpleNamespace(unverified=True) if fault=='correction' else None)
    cls={'wm':'WmReader','liquidity':'LiquidityReader','checklists':'ChecklistReader'}[module]
    got=getattr(getattr(api(module),cls)(p),method)('X')
    assert (got.detected if method=='run' else got)==empty
    assert p.calls==[('X','15m',lookback)]


def pool_frame(sweep=False):
    f=frame({0:100.,10:110.,17:100.,25:110.,35:100.,39:101.})
    if sweep: f.iloc[-1,f.columns.get_loc('high')]=115.
    return f


@pytest.mark.parametrize('sweep',[False,True])
def test_equal_highs_pool_geometry_and_newest_touch(sweep):
    p=Frames({('X','15m',10):pool_frame(sweep)})
    pools=api('liquidity').LiquidityReader(p).pools('X')
    highs=[x for x in pools if x.side=='high']
    assert len(highs)==1
    h=highs[0]
    assert (h.price,h.touches,h.bars_ago,h.swept)==(111.,2,14,sweep)


def test_pool_groups_against_first_price_not_chained_centroid():
    f=frame(n=60)
    f['high']=np.linspace(101.,102.,60); f['low']=np.linspace(90.,91.,60)
    f.iloc[10,f.columns.get_loc('high')]=110.
    f.iloc[25,f.columns.get_loc('high')]=112.
    f.iloc[40,f.columns.get_loc('high')]=114.
    got=api('liquidity').LiquidityReader(Frames({('X','15m',10):f})).pools('X')
    assert [(p.side,p.price,p.touches,p.bars_ago,p.swept) for p in got]==[('high',111.,2,34,True)]


def test_pool_lookback_excludes_old_extremes():
    f=frame({0:100.,10:150.,20:100.,30:150.,40:100.,159:110.},160)
    assert api('liquidity').LiquidityReader(Frames({('X','15m',10):f})).pools('X')==[]


@pytest.mark.parametrize('swept,direction',[(True,'לונג'),(False,None)])
def test_run_needs_actual_swept_pool_from_second_read(swept,direction):
    speed=frame()
    speed.iloc[35:39,speed.columns.get_loc('low')]=95.
    speed.iloc[35:39,speed.columns.get_loc('high')]=115.
    speed.iloc[38,speed.columns.get_loc('close')]=112.
    p=Frames({('X','15m',10):[speed,pool_frame(swept)]})
    got=api('liquidity').LiquidityReader(p).run('X')
    assert got.detected==swept and got.direction==direction
    if swept: assert got.pool.price==111. and got.bars==4
    assert p.calls==[('X','15m',10),('X','15m',10)]


def test_slow_run_does_not_request_pool_and_forming_spike_is_not_completed_speed():
    f=frame(); f.iloc[-1,f.columns.get_loc('high')]=1000.
    p=Frames({('X','15m',10):f})
    assert not api('liquidity').LiquidityReader(p).run('X').detected
    assert p.calls==[('X','15m',10)]


@pytest.mark.parametrize('close',[99.,100.])
def test_run_equal_or_lower_close_is_short_even_with_high_side_pool(close):
    f=frame(); f.loc[f.index[35:39],'high']=115.; f.loc[f.index[35:39],'low']=95.
    f.iloc[38,f.columns.get_loc('close')]=close
    p=Frames({('X','15m',10):[f,pool_frame(True)]})
    r=api('liquidity').LiquidityReader(p).run('X')
    assert r.detected and r.direction=='שורט' and r.pool.side=='high'


@pytest.mark.parametrize('now,formed',[
    ('2026-09-09 14:59:59Z',False),('2026-09-09 15:00Z',True),
    ('2026-09-09 19:59:59Z',True),('2026-09-09 20:00Z',False),
    ('2026-09-12 15:00Z',False)])
def test_brinks_utc_window_and_clock_order(now,formed):
    p=Frames({('X','5m',2):frame(n=8,start='2026-09-09 14:00Z')},now)
    got=api('brinks').BrinksReader(p).today_box('X')
    assert (got is not None)==formed
    assert p.calls==[('clock',)]+([('X','5m',2)] if formed else [])
    if formed:
        assert (got.hi,got.lo,got.mid,got.side)==(101.,99.,100.,'על האמצע')
        assert got.formed_at=='2026-09-09 14:00-15:00 GMT'


@pytest.mark.parametrize('count',[7,8])
def test_brinks_minimum_and_explicit_clock(count):
    f=frame(n=count,start='2026-09-09 14:00Z')
    f.loc[pd.Timestamp('2026-09-09 15:00Z')]=[120.,130.,110.,125.,1.]
    p=Frames({('X','5m',2):f})
    b=api('brinks').BrinksReader(p).today_box('X',now=p.now)
    assert p.calls==[('X','5m',2)]
    if count==7: assert b is None
    else: assert (b.hi,b.lo,b.close,b.open_vectors_inside)==(101.,99.,125.,0)


def test_brinks_counts_actual_unrecovered_vector_inside_hour():
    f=frame(n=12,start='2026-09-09 14:00Z')
    f.iloc[10]=[100.,103.,99.,102.,3.]
    p=Frames({('X','5m',2):f})
    assert api('brinks').BrinksReader(p).today_box('X').open_vectors_inside==1


def test_brinks_vector_input_error_is_unknown_not_zero():
    f=frame(n=8,start='2026-09-09 14:00Z')
    f['volume']='bad'
    p=Frames({('X','5m',2):f})
    box=api('brinks').BrinksReader(p).today_box('X')
    assert box is not None and (box.hi,box.lo,box.close)==(101.,99.,100.)
    assert box.open_vectors_inside is None
    assert p.calls==[('clock',),('X','5m',2)]


def rvc_frame(inverse=False,close=102.,upper=1.,lower=1.):
    f=frame(n=33)
    f.iloc[30]=[102.,103.,99.,100.,3.]
    f.iloc[31]=[100.,max(100.,close)+upper,100.-lower,close,10.]
    f.iloc[32]=[102.,103.,99.,100.,100.]  # opposite forming vector is ignored
    return mirror(f) if inverse else f


@pytest.mark.parametrize('inverse,name,direction',[(False,'RVC','לונג'),(True,'GVC','שורט')])
@pytest.mark.parametrize('close,upper,lower,recovered,wick_ok',[
    (102.,1.,1.,True,True),(101.9,1.,1.,False,True),
    (102.,2.,1.,True,True),(102.,2.1,1.,True,False),(102.,0.,1.,True,False)])
def test_rvc_completed_real_vectors_recovery_and_wicks(inverse,name,direction,close,upper,lower,recovered,wick_ok):
    p=Frames({('X','15m',5):rvc_frame(inverse,close,upper,lower)})
    r=api('checklists').ChecklistReader(p).rvc_gvc('X')
    assert r is not None
    assert (r.name,r.direction,r.recovered,r.wick_ok,r.bars_ago)==(name,direction,recovered,wick_ok,1)
    assert (r.first_kind,r.second_kind)==(('green','red') if inverse else ('red','green'))


def test_rvc_requires_second_completed_vector_not_just_opposite_color():
    f=rvc_frame(); f.iloc[31,f.columns.get_loc('volume')]=0.1
    assert api('checklists').ChecklistReader(Frames({('X','15m',5):f})).rvc_gvc('X') is None


@pytest.mark.parametrize('inverse',[False,True])
def test_rvc_accepts_real_rising_tier_vectors(inverse):
    f=rvc_frame()
    # A prior wide candle keeps spread-volume below climax while volumes rise.
    f.iloc[25]=[100.,120.,80.,100.,1.]
    f.iloc[30,f.columns.get_loc('volume')]=1.6
    f.iloc[31,f.columns.get_loc('volume')]=1.7
    if inverse: f=mirror(f)
    r=api('checklists').ChecklistReader(Frames({('X','15m',5):f})).rvc_gvc('X')
    assert (r.first_kind,r.second_kind)==(('blue','violet') if inverse else ('violet','blue'))
    assert r.recovered and r.wick_ok


@pytest.mark.parametrize('body,atr,quality',[(6.,10.,'טוב'),(6.,10.1,'גבולי'),(4.5,10.,'גבולי'),(4.49,10.,'גרוע')])
def test_block_literal_quality_boundaries(body,atr,quality):
    f=pd.DataFrame([dict(open=0.,close=body,low=0.,high=10.)])
    q,pct,ratio=api('checklists').block_quality(f,0,atr)
    assert q==quality and pct==body/10. and ratio==10./atr


def test_blocks_actual_vectors_newest_order_and_forming_exclusion():
    f=frame(n=43)
    f.iloc[40]=[100.,110.,100.,108.,3.]
    f.iloc[41]=[108.,110.,100.,100.,10.]
    f.iloc[42]=[100.,110.,100.,110.,100.]
    p=Frames({('X','15m',10):f})
    got=api('checklists').ChecklistReader(p).blocks('X')
    assert [(b.direction,b.price_hi,b.price_lo,b.quality,b.bars_ago) for b in got]==[
        ('שורט',110.,100.,'טוב',1),('לונג',110.,100.,'טוב',2)]


def test_blocks_suppress_poor_vector_body_and_apply_lookback():
    f=frame(n=43)
    f.iloc[40]=[100.,110.,100.,108.,3.]
    f.iloc[41]=[100.,110.,100.,102.,10.]
    reader=api('checklists').ChecklistReader(Frames({('X','15m',10):f}))
    assert [b.bars_ago for b in reader.blocks('X')]==[2]
    assert reader.blocks('X',lookback=2)==[]


@pytest.mark.parametrize('inverse',[False,True])
def test_blocks_accept_actual_rising_tier_and_full_frame_atr(inverse):
    f=frame(n=42)
    f.iloc[35]=[100.,120.,80.,100.,1.]
    f.iloc[40]=[100.,110.,100.,108.,1.6]
    if inverse: f=mirror(f)
    p=Frames({('X','15m',10):f})
    got=api('checklists').ChecklistReader(p).blocks('X',lookback=2)
    assert len(got)==1 and got[0].direction==('שורט' if inverse else 'לונג')
    assert got[0].quality=='טוב'
    # The forming row cannot be emitted but does contribute to original ATR.
    f.iloc[-1,f.columns.get_loc('high')]=1000.
    got=api('checklists').ChecklistReader(Frames({('X','15m',10):f})).blocks('X',lookback=2)
    assert len(got)==1 and got[0].quality=='גבולי'


@pytest.mark.parametrize('broken',[False,True])
def test_brinks_checklist_composes_real_box_and_raw_timestamp_failure(broken):
    box=frame(n=12,start='2026-09-09 14:00Z')
    zones=frame(n=12)
    zones.iloc[10]=[100.,102.,99.,102.,3.]
    zones.iloc[11]=[102.,103.,99.,101.,1.]
    p=Frames({('X','5m',2):box,('X','5m',10):OSError('missing zones') if broken else zones,
        ('X','15m',3):frame(n=10,start='2026-09-09 00:00Z')})
    got=api('checklists').ChecklistReader(p).brinks_read('X')
    assert got.formed and (got.box_hi,got.box_lo)==(101.,99.) and got.swept_asia is None
    if broken: assert got.internal_vectors is None and got.external_vectors is None
    else:
        assert got.internal_vectors==[dict(price=101.,kind='green',top=102.,bottom=100.)]
        assert got.external_vectors==[]
    assert p.calls==[('clock',),('X','5m',2),('X','5m',10),('X','15m',3)]
