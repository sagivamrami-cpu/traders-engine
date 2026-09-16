"""Reject reader, dependency or pinned source drift without executing source."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(os.environ.get('TR_TREE_SOURCE_ROOT',Path(__file__).resolve().parents[2] / ".source-checkouts"))
VENDOR=ROOT/'trading_system/tree_replay/_vendor'


def api():
    name='trading_system.tree_spec.pattern_readers_source'
    assert importlib.util.find_spec(name) is not None,'pattern source auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch,path,transform):
    original=Path.read_text
    def read(p,*a,**kw):
        text=original(p,*a,**kw)
        return transform(text) if p.resolve()==path.resolve() else text
    monkeypatch.setattr(Path,'read_text',read)


def test_real_source_graph_verified_not_replay_or_training():
    r=api().audit_pattern_readers_source(SOURCE)
    assert r['status']=='VERIFIED' and r['source_subset_verified'] and r['blockers']==[]
    assert r['checked_projections']==['wm','liquidity','brinks','checklists','pattern_tr']
    assert set(r['dependencies'])=={'tree_tr','pvsra'}
    assert all(d['source_subset_verified'] for d in r['dependencies'].values())
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('module,old,new',[
    ('wm','SWING_K = 3','SWING_K = 2'),
    ('wm','MAX_AGE_BARS = 40','MAX_AGE_BARS = 41'),
    ('wm','self.source = source','self.source = None'),
    ('wm',"timeframe: str='15m'","timeframe: str='5m'"),
    ('wm','m.bars_since_leg2 < best.bars_since_leg2','m.bars_since_leg2 <= best.bars_since_leg2'),
    ('wm','confirmed=close > neck','confirmed=close >= neck'),
    ('wm','elif hi[i]','if hi[i]'),
    ('wm','except Exception:','except OSError:'),
    ('liquidity','LOOKBACK = 120','LOOKBACK = 121'),
    ('liquidity','EQ_TOL_ATR = 0.25','EQ_TOL_ATR = 0.5'),
    ('liquidity','RUN_BARS = 4','RUN_BARS = 5'),
    ('liquidity','self.pools(symbol, timeframe)','[]'),
    ('liquidity','newest + 1:','newest:'),
    ('liquidity','abs(jpx - px) <= tol','abs(jpx - px) < tol'),
    ('brinks','BOX_START_H, BOX_END_H = (14, 15)','BOX_START_H, BOX_END_H = (13, 15)'),
    ('brinks','self.source.now_utc()','datetime.now(timezone.utc)'),
    ('brinks','len(seg) < 8','len(seg) < 12'),
    ('brinks',"tr.vector_zones(seg, pv)",'tr.vector_zones(seg)'),
    ('checklists','self.brinks = BrinksReader(source)','self.brinks = source'),
    ('checklists',"timeframe, 5)","timeframe, 10)"),
    ('checklists','i = len(df) - 2','i = len(df) - 1'),
    ('checklists','c2 >= max(o1, c1)','c2 > max(o1, c1)'),
    ('checklists','hi_w <= WICK_SYMMETRY_MAX','hi_w < WICK_SYMMETRY_MAX'),
    ('checklists','if q ==','if False and q =='),
    ('checklists','lo <= mid <= hi','lo < mid < hi'),
    ('checklists',"self.source.fetch_corrected(symbol, '15m', 3)","self.source.fetch_corrected(symbol, '15m', 5)"),
    ('pattern_tr','from .tree_tr import vector_zones','from .tree_tr import daily_pivots as vector_zones'),
])
def test_candidate_mutations_block(monkeypatch,module,old,new):
    m=api(); path=VENDOR/(module+'.py')
    assert old in path.read_text(encoding='utf-8')
    intercept(monkeypatch,path,lambda s:s.replace(old,new))
    r=m.audit_pattern_readers_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH:'+module in r['blockers']


@pytest.mark.parametrize('module',['wm','liquidity','brinks','checklists','pattern_tr'])
def test_extra_executable_or_import_blocks(monkeypatch,module):
    m=api(); intercept(monkeypatch,VENDOR/(module+'.py'),lambda s:s+'\nimport urllib.request\n')
    r=m.audit_pattern_readers_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH:'+module in r['blockers']


@pytest.mark.parametrize('module',['tree_tr','pvsra'])
def test_actual_dependency_drift_blocks(monkeypatch,module):
    m=api(); intercept(monkeypatch,VENDOR/(module+'.py'),lambda s:s+'\nDRIFT=True\n')
    r=m.audit_pattern_readers_source(SOURCE)
    assert not r['source_subset_verified'] and any(b.startswith('DEPENDENCY:') for b in r['blockers'])


@pytest.mark.parametrize('dependency',['tree_tr','pvsra'])
@pytest.mark.parametrize('fault',['false_empty','exception','true_blocked'])
def test_dependency_failures_block(monkeypatch,dependency,fault):
    m=api(); attr='audit_'+dependency; original=getattr(m,attr)
    def damaged(root):
        r=original(root)
        assert r['source_subset_verified'] and not r['blockers']
        if fault=='exception': raise OSError('read failed')
        if fault=='false_empty': r['source_subset_verified']=False
        else: r['blockers']=['TEST_BLOCKER']
        return r
    monkeypatch.setattr(m,attr,damaged)
    r=m.audit_pattern_readers_source(SOURCE)
    suffix={'false_empty':'NOT_VERIFIED','exception':'UNREADABLE:OSError','true_blocked':'TEST_BLOCKER'}[fault]
    assert 'DEPENDENCY:'+dependency+':'+suffix in r['blockers']
    assert not r['source_subset_verified'] and not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('module',['wm','liquidity','brinks','checklists'])
def test_each_source_blob_is_pinned(monkeypatch,module):
    m=api(); intercept(monkeypatch,SOURCE/'chart-desk/chartdesk'/(module+'.py'),lambda s:s+'\n# drift\n')
    r=m.audit_pattern_readers_source(SOURCE)
    assert 'SOURCE_BLOB_MISMATCH:'+module in r['blockers'] and not r['source_subset_verified']


@pytest.mark.parametrize('fault',['head','root','baseline'])
def test_source_identity_blocks(monkeypatch,fault):
    m=api()
    if fault=='baseline':
        intercept(monkeypatch,ROOT/'configs/trees/existing-alerts-baseline.json',lambda s:s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9','0'*40))
        want='BASELINE_COMMIT_MISMATCH'
    else:
        arg,value,want=('HEAD','0'*40,'SOURCE_COMMIT_MISMATCH') if fault=='head' else ('--show-toplevel',str(SOURCE),'NOT_REPOSITORY_ROOT')
        original=m._git
        monkeypatch.setattr(m,'_git',lambda p,*a:value if a==(arg,) else original(p,*a))
    r=m.audit_pattern_readers_source(SOURCE)
    assert want in r['blockers'] and not r['source_subset_verified']


@pytest.mark.parametrize('fault',['duplicate','order','signature','substitution','import','syntax'])
def test_projection_rejects_unexpected_source_shape(fault):
    m=api(); text=(SOURCE/'chart-desk/chartdesk/wm.py').read_text(encoding='utf-8')
    if fault=='duplicate': text+='\ndef detect(symbol): pass\n'
    elif fault=='order': text=text.replace('SWING_K = 3','EXTRA = 3\nSWING_K = 3')
    elif fault=='signature': text=text.replace('timeframe: str = "15m"','timeframe: str = "5m"')
    elif fault=='substitution': text=text.replace('basis.fetch_corrected(symbol, timeframe, 10)','basis.fetch_corrected(symbol, timeframe, 9)')
    elif fault=='import': text=text.replace('from . import basis, tr','from . import basis')
    else: text+='\ndef syntax error'
    with pytest.raises((ValueError,SyntaxError)): m._projection('wm',text)


def test_missing_source_and_candidate_block(tmp_path,monkeypatch):
    m=api()
    for root in [None,tmp_path]:
        r=m.audit_pattern_readers_source(root)
        assert not r['source_subset_verified'] and r['blockers']
    monkeypatch.setattr(m,'VENDOR',tmp_path)
    r=m.audit_pattern_readers_source(SOURCE)
    assert 'VENDOR_UNREADABLE:wm:FileNotFoundError' in r['blockers']


def test_cli_and_import_guard(tmp_path):
    api()
    for root,exitcode in [(SOURCE,0),(tmp_path,2)]:
        p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/check_pattern_readers_source_parity.py'),'--source-root',str(root)],cwd=tmp_path,capture_output=True,text=True,timeout=60)
        assert p.returncode==exitcode,p.stderr
        r=json.loads(p.stdout)
        assert r['source_subset_verified']==(exitcode==0)
        assert not r['ready_for_training'] and not r['ready_for_replay']
    code='\n'.join(['import sys','class Guard:','    def find_spec(self,fullname,*args):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
        'sys.meta_path.insert(0,Guard())','from trading_system.tree_spec.pattern_readers_source import audit_pattern_readers_source',
        "assert audit_pattern_readers_source(sys.argv[1])['source_subset_verified']"])
    p=subprocess.run([sys.executable,'-B','-c',code,str(SOURCE)],cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert p.returncode==0,p.stderr
