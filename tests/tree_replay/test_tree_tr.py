"""Behavioral oracles for original TR vector-zone memory and daily pivots."""
import importlib
import importlib.util

import pandas as pd
import pytest


def api():
    name = 'trading_system.tree_replay._vendor.tree_tr'
    assert importlib.util.find_spec(name) is not None, 'tree TR memory missing'
    return importlib.import_module(name)


def tape(rows):
    return pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'],
        index=pd.date_range('2026-09-01', periods=len(rows), freq='5min', tz='UTC'))


def evidence(df, *, climax=(0,)):
    return pd.DataFrame({'available': True, 'kind': 'green',
        'climax': [i in climax for i in range(len(df))]}, index=df.index)


@pytest.mark.parametrize('tail,opened,touches', [
    ([], True, 0), ([(12,13,11,12)], True, 0),
    ([(12,13,11,12),(14,15,13,14)], True, 0),
    ([(14,15,13,14),(12,13,12,12)], False, 1),
    ([(14,15,13,14),(12,13,12,12),(11,12,10,11)], False, 2),
    ([(12,13,11,12),(11,12,10,11)], True, 0),
])
def test_departure_must_precede_returns_and_each_overlap_counts(tail,opened,touches):
    df = tape([(10,13,9,12)]+tail)
    zones = api().vector_zones(df, evidence(df))
    assert list(zones.index) == [df.index[0]] and zones.index.name == 'time'
    row = zones.iloc[0]
    assert (row['top'],row['bottom'],bool(row['open']),row['touches'],row['kind']) == (
        12.,10.,opened,touches,'green')


@pytest.mark.parametrize('zone_from,cleared_by,top,bottom,opened', [
    ('body','wick',12.,10.,False), ('body','body',12.,10.,True),
    ('wick','wick',13.,9.,False), ('wick','body',13.,9.,True),
])
def test_zone_and_return_geometry_are_independent(zone_from,cleared_by,top,bottom,opened):
    df=tape([(10,13,9,12),(15,16,14,15),(15,16,11,15)])
    z=api().vector_zones(df,evidence(df),zone_from=zone_from,cleared_by=cleared_by).iloc[0]
    assert (z['top'],z['bottom'],bool(z['open'])) == (top,bottom,opened)


@pytest.mark.parametrize('limit,want', [(1,[2]),(2,[1,2]),(0,[0,1,2]),(-1,[1,2])])
def test_zone_cap_retains_raw_source_slice_semantics(limit,want):
    df=tape([(10,13,9,12),(14,17,13,16),(18,21,17,20)])
    zones=api().vector_zones(df,evidence(df,climax=(0,1,2)),max_zones=limit)
    assert list(zones.index)==[df.index[i] for i in want]


@pytest.mark.parametrize('fault', ['first_unavailable','missing_available','no_climax'])
def test_unavailable_or_nonclimax_evidence_has_original_empty_schema(fault):
    df=tape([(10,13,9,12),(14,17,13,16)])
    pv=evidence(df)
    if fault=='first_unavailable': pv.iloc[0,pv.columns.get_loc('available')]=False
    elif fault=='missing_available': pv=pv.drop(columns='available')
    else: pv['climax']=False; pv['kind']='blue'
    z=api().vector_zones(df,pv)
    assert z.empty and list(z.columns)==['top','bottom','kind','open','touches','time']


def test_raw_empty_available_series_is_not_fabricated_as_absence():
    df=tape([])
    with pytest.raises(IndexError): api().vector_zones(df,evidence(df))


def test_returns_are_selected_by_timestamp_not_position():
    df=tape([(10,13,9,12),(14,15,13,14),(11,12,10,11)])
    df.index=[df.index[1],df.index[0],df.index[2]]
    z=api().vector_zones(df,evidence(df)).iloc[0]
    # Positional row1 is a departure, but occurred BEFORE the zone's timestamp.
    assert bool(z['open']) and z['touches']==0


def test_actual_pvsra_composition_generates_the_climax_zone_and_return():
    df=tape([(10,11,9,10)]*10+[(10,13,9,12),(14,15,13,14),(11,12,10,11)])
    df['volume']=[1.]*10+[3.,1.,1.]
    z=api().vector_zones(df)
    assert list(z.index)==[df.index[10]]
    assert z.iloc[0]['kind']=='green' and z.iloc[0]['top']==12.
    assert z.iloc[0]['bottom']==10. and not bool(z.iloc[0]['open'])
    assert z.iloc[0]['touches']==1


@pytest.mark.parametrize('volume', [None,0.])
def test_actual_pvsra_missing_or_zero_volume_yields_no_zones(volume):
    df=tape([(10,13,9,12)]*15)
    if volume is not None: df['volume']=volume
    assert api().vector_zones(df).empty


def test_daily_pivots_use_previous_bar_and_exact_named_ladder():
    df=tape([(10,12,8,10),(999,1000,998,999)])
    assert api().daily_pivots(df)=={'PP':10.,'R1':12.,'R2':14.,'R3':16.,
        'S1':8.,'S2':6.,'S3':4.,'M0':5.,'M1':7.,'M2':9.,'M3':11.,'M4':13.,'M5':15.}
    assert list(api().daily_pivots(df,include_m=False))==['PP','R1','R2','R3','S1','S2','S3']


@pytest.mark.parametrize('rows',[[],[(10,12,8,10)]])
def test_daily_pivots_need_a_previous_row(rows):
    assert api().daily_pivots(tape(rows))=={}
