"""Original options mapping from raw JSON/CSV with literal economic geometry."""
import importlib
import importlib.util
import json

import pandas as pd
import pytest


SYMBOL='OANDA:XAUUSD'


def api():
    name='trading_system.tree_replay._vendor.optionswall'
    assert importlib.util.find_spec(name) is not None,'options wall reader missing'
    return importlib.import_module(name)


def entry():
    return dict(symbol='GLD',data_asof='2026-09-09T15:00:00Z',
        quote_permission='realtime_permission',spot=200,
        expiries=[dict(expiry='2026-09-09',walls=dict(
            call_walls=[dict(strike=210)],put_walls=[dict(strike=190)]),max_pain=205)],
        gex=dict(regime='long_gamma',flip_level=201,
            largest_positive=dict(strike=215),largest_negative=dict(strike=185)))


class Artifacts:
    def __init__(self,item=None,now='2026-09-09T15:30:00Z'):
        self.ids=['report-b.json','report-a.json']
        self.reports={'report-b.json':json.dumps({'symbols':[entry() if item is None else item]}),
            'report-a.json':'invalid older report'}
        self.csv='time,close,src\n2026-09-09T14:45:00Z,2000,OANDA:XAUUSD\n'
        self.now=pd.Timestamp(now)
        self.calls=[]
    def list_reports(self):
        self.calls.append(('list',))
        if isinstance(self.ids,Exception): raise self.ids
        return list(self.ids)
    def read_report(self,path):
        self.calls.append(('report',path))
        value=self.reports[path]
        if isinstance(value,Exception): raise value
        return value
    def read_tv_csv(self,filename):
        self.calls.append(('csv',filename))
        if isinstance(self.csv,Exception): raise self.csv
        return self.csv
    def now_utc(self):
        self.calls.append(('clock',))
        return self.now


def test_raw_mapping_is_fixed_not_current_spot_and_port_order():
    source=Artifacts(); reader=api().OptionsWallReader(source)
    for current in [1.,99999.,None]:
        r=reader.status(SYMBOL,current)
        assert r.usable and r.reason=='ok'
        w=r.walls
        assert (w.ratio,w.call_wall,w.put_wall,w.flip,w.max_pain,w.positive_gamma,w.negative_gamma)==(10.,2100.,1900.,2010.,2050.,2150.,1850.)
        assert (w.mapped_at,w.market_asof,w.age_h)==('2026-09-09T14:45:00+00:00','2026-09-09T15:00:00+00:00',.5)
        assert not w.stale and w.level_source=='open_interest'
    assert source.calls==[('list',),('report','report-b.json'),('clock',),('csv','XAUUSD_M15.csv')]*3
    assert reader.load(SYMBOL,9000).call_wall==2100.


@pytest.mark.parametrize('symbol',['GC','GC.v.0','XAUUSD','UNKNOWN'])
def test_unsupported_symbol_does_not_access_artifacts(symbol):
    p=Artifacts(); r=api().OptionsWallReader(p).status(symbol)
    assert not r.usable and r.reason=='unsupported_symbol' and r.walls is None
    assert p.calls==[]


@pytest.mark.parametrize('symbol,etf,filename',[
    ('OANDA:XAUUSD','GLD','XAUUSD_M15.csv'),('OANDA:NAS100USD','QQQ','NAS100_M15.csv'),
    ('BINANCE:BTCUSDT','IBIT','BTCUSD_M15.csv')])
def test_literal_supported_mapping(symbol,etf,filename):
    e=entry(); e['symbol']=etf; p=Artifacts(e)
    p.csv='time,close,src\n2026-09-09T14:45:00Z,2000,'+symbol+'\n'
    w=api().OptionsWallReader(p).status(symbol).walls
    assert w.etf==etf and w.call_wall==2100. and p.calls[-1]==('csv',filename)


@pytest.mark.parametrize('fault,reason',[
    ('empty','no_report'),('json','invalid_report'),('io','invalid_report'),
    ('degraded','missing_or_degraded_symbol'),('missing_time','missing_market_asof'),
    ('naive_time','missing_market_asof'),('permission','non_realtime_permission:delayed'),
    ('bad_spot','missing_synchronised_mapping_anchor'),('expiry','no_live_expiry'),
    ('walls','missing_oi_walls')])
def test_original_failure_reasons(fault,reason):
    e=entry()
    if fault=='degraded': e['degraded']=True
    elif fault=='missing_time': e.pop('data_asof')
    elif fault=='naive_time': e['data_asof']='2026-09-09T15:00:00'
    elif fault=='permission': e['quote_permission']='delayed'
    elif fault=='bad_spot': e['spot']=0
    elif fault=='expiry': e['expiries'][0]['expiry']='2026-09-08'
    elif fault=='walls': e['expiries'][0]['walls']['call_walls']=[]
    p=Artifacts(e)
    if fault=='empty': p.ids=[]
    elif fault=='json': p.reports['report-b.json']='bad'
    elif fault=='io': p.reports['report-b.json']=OSError('missing')
    r=api().OptionsWallReader(p).status(SYMBOL)
    assert not r.usable and r.reason==reason and r.walls is None
    assert ('report','report-a.json') not in p.calls
    if fault in ['missing_time','naive_time','permission']: assert ('clock',) not in p.calls


@pytest.mark.parametrize('now,usable',[
    ('2026-09-09T14:58:00Z',True),('2026-09-09T14:57:59Z',False),
    ('2026-09-09T15:45:00Z',True),('2026-09-09T15:45:01Z',False)])
def test_age_boundaries(now,usable):
    r=api().OptionsWallReader(Artifacts(now=now)).status(SYMBOL)
    assert r.usable==usable
    if not usable: assert r.reason.startswith('stale_market_data:')


def test_explicit_naive_clock_is_utc_and_skips_clock_port():
    p=Artifacts(now='2030-01-01T00:00Z')
    r=api().OptionsWallReader(p).status(SYMBOL,now=pd.Timestamp('2026-09-09T15:30:00'))
    assert r.usable and r.walls.age_h==.5 and ('clock',) not in p.calls


@pytest.mark.parametrize('stamp,usable',[('13:45:00',True),('13:44:59',False),('15:00:01',False)])
def test_anchor_age_and_future_boundary(stamp,usable):
    p=Artifacts(); p.csv='time,close\n2026-09-09T'+stamp+'Z,2000\n'
    r=api().OptionsWallReader(p).status(SYMBOL)
    assert r.usable==usable
    if usable: assert r.walls.ratio==10.
    else: assert r.reason=='missing_synchronised_mapping_anchor'


def test_anchor_filters_wrong_source_and_future_rows_before_selecting():
    p=Artifacts()
    p.csv+='2026-09-09T14:59:00Z,9000,WRONG\n2026-09-09T15:01:00Z,8000,OANDA:XAUUSD\n'
    assert api().OptionsWallReader(p).status(SYMBOL).walls.ratio==10.


@pytest.mark.parametrize('value',['bad','nan','inf'])
def test_latest_bad_anchor_does_not_fallback(value):
    p=Artifacts(); p.csv+='2026-09-09T15:00:00Z,'+value+',OANDA:XAUUSD\n'
    r=api().OptionsWallReader(p).status(SYMBOL)
    assert r.reason=='missing_synchronised_mapping_anchor' and not r.usable


@pytest.mark.parametrize('underlying,ratio',[(0.,0.),(-2000.,-10.)])
def test_finite_nonpositive_underlying_anchor_is_preserved(underlying,ratio):
    p=Artifacts(); p.csv='time,close\n2026-09-09T14:45Z,'+str(underlying)+'\n'
    r=api().OptionsWallReader(p).status(SYMBOL)
    assert r.usable and r.walls.ratio==ratio


def test_first_undegraded_etf_and_first_unexpired_entry_not_sorted():
    e=entry(); e['expiries'][0]['expiry']='2026-10-01'
    earlier=entry()['expiries'][0]; earlier['walls']['call_walls'][0]['strike']=999
    e['expiries'].append(earlier)
    bad=entry(); bad['degraded']=True; bad['spot']=1
    later=entry(); later['spot']=1
    p=Artifacts(); p.reports['report-b.json']=json.dumps({'symbols':[bad,e,later]})
    assert api().OptionsWallReader(p).status(SYMBOL).walls.call_wall==2100.


def test_expiry_day_is_new_york_not_utc_date():
    e=entry(); e['data_asof']='2026-09-10T00:00:00Z'
    p=Artifacts(e,now='2026-09-10T00:00:00Z')
    p.csv='time,close\n2026-09-09T23:45:00Z,2000\n'
    assert api().OptionsWallReader(p).status(SYMBOL).usable


def test_first_wall_nonfinite_does_not_fallback_and_optional_zero_is_retained():
    e=entry(); e['expiries'][0]['walls']['call_walls']=[dict(strike='inf'),dict(strike=210)]
    assert api().OptionsWallReader(Artifacts(e)).status(SYMBOL).reason=='missing_oi_walls'
    e=entry(); e['gex']={'flip_level':None,'largest_positive':{'strike':0},'largest_negative':{'strike':'nan'}}
    e['expiries'][0]['max_pain']=0
    w=api().OptionsWallReader(Artifacts(e)).status(SYMBOL).walls
    assert (w.flip,w.positive_gamma,w.negative_gamma,w.max_pain,w.regime)==(0.,0.,None,0.,'unknown')


@pytest.mark.parametrize('bad',[OSError('missing'), 'time,other\n2026-09-09T14:45Z,1\n'])
def test_csv_failure_is_missing_anchor(bad):
    p=Artifacts(); p.csv=bad
    assert api().OptionsWallReader(p).status(SYMBOL).reason=='missing_synchronised_mapping_anchor'


def test_decoded_wrong_report_shape_retains_original_uncaught_error():
    p=Artifacts(); p.reports['report-b.json']='[]'
    with pytest.raises(AttributeError): api().OptionsWallReader(p).status(SYMBOL)


def test_listing_failure_propagates_before_later_ports():
    p=Artifacts(); p.ids=OSError('listing unavailable')
    with pytest.raises(OSError,match='listing unavailable'):
        api().OptionsWallReader(p).status(SYMBOL)
    assert p.calls==[('list',)]
