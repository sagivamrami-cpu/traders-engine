"""Original options-wall projection must fail closed on source/candidate drift."""
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
RUNTIME=ROOT/'trading_system/tree_replay/_vendor/optionswall.py'


def api():
    name='trading_system.tree_spec.optionswall_source'
    assert importlib.util.find_spec(name) is not None,'options auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch,path,transform):
    original=Path.read_text
    def read(p,*a,**kw):
        s=original(p,*a,**kw)
        return transform(s) if p.resolve()==path.resolve() else s
    monkeypatch.setattr(Path,'read_text',read)


def test_original_module_verified_with_false_readiness():
    r=api().audit_optionswall_source(SOURCE)
    assert r['source_subset_verified'] and r['status']=='VERIFIED' and r['blockers']==[]
    assert r['checked_projections']==['optionswall']
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('old,new',[
    ('from io import StringIO','from io import StringIO\nimport urllib.request'),
    ('MAX_QUOTE_AGE_MIN = 45.0','MAX_QUOTE_AGE_MIN = 60.0'),
    ('MAX_ANCHOR_GAP_MIN = 75.0','MAX_ANCHOR_GAP_MIN = 90.0'),
    ("'OANDA:XAUUSD': 'GLD'","'GC': 'GLD'"),
    ('@dataclass(frozen=True)','@dataclass(frozen=False)'),
    ('math.isfinite(result)','True'),
    ('self.source = source','self.source = None'),
    ("spot: float)","spot: int)"),
    ('files = sorted(self.source.list_reports())','files = list(self.source.list_reports())'),
    ('self.source.read_report(files[-1])','self.source.read_report(files[0])'),
    ("permission != 'realtime_permission'","permission != 'delayed'"),
    ('pd.Timestamp(self.source.now_utc())',"pd.Timestamp.now(tz='UTC')"),
    ('age_min < -2','age_min <= -2'),
    ('age_min > MAX_QUOTE_AGE_MIN','age_min >= MAX_QUOTE_AGE_MIN'),
    ('idx <= market_asof','idx < market_asof'),
    ("src.fillna('').astype(str).eq(symbol)",'True'),
    ("usable.sort_values('_ts').iloc[-1]","usable.sort_values('_ts').iloc[0]"),
    ('gap > MAX_ANCHOR_GAP_MIN','gap >= MAX_ANCHOR_GAP_MIN'),
    ('ratio = under_spot / etf_spot','ratio = _current_spot / etf_spot'),
    ('>= market_day','> market_day'),
    ("ZoneInfo('America/New_York')","ZoneInfo('UTC')"),
    ("calls[0].get('strike')","calls[-1].get('strike')"),
    ('except (json.JSONDecodeError, OSError):','except Exception:'),
    ('self.status(symbol, spot).walls','None'),
])
def test_candidate_semantic_changes_block(monkeypatch,old,new):
    m=api(); assert old in RUNTIME.read_text(encoding='utf-8')
    intercept(monkeypatch,RUNTIME,lambda s:s.replace(old,new))
    r=m.audit_optionswall_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']


@pytest.mark.parametrize('fault',['head','root','baseline','blob'])
def test_identity_not_redefined_by_candidate(monkeypatch,fault):
    m=api()
    if fault=='blob':
        intercept(monkeypatch,SOURCE/'chart-desk/chartdesk/optionswall.py',lambda s:s+'\n# drift\n')
        want='SOURCE_BLOB_MISMATCH'
    elif fault=='baseline':
        intercept(monkeypatch,ROOT/'configs/trees/existing-alerts-baseline.json',lambda s:s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9','0'*40))
        want='BASELINE_COMMIT_MISMATCH'
    else:
        arg,value,want=('HEAD','0'*40,'SOURCE_COMMIT_MISMATCH') if fault=='head' else ('--show-toplevel',str(SOURCE),'NOT_REPOSITORY_ROOT')
        original=m._git
        monkeypatch.setattr(m,'_git',lambda p,*a:value if a==(arg,) else original(p,*a))
    r=m.audit_optionswall_source(SOURCE)
    assert not r['source_subset_verified'] and want in r['blockers']


@pytest.mark.parametrize('fault',['global','import','signature','duplicate','order','substitution','syntax'])
def test_projection_has_literal_source_contract(fault):
    m=api(); text=(SOURCE/'chart-desk/chartdesk/optionswall.py').read_text(encoding='utf-8')
    if fault=='global': text=text.replace('report-*.json','different-*.json')
    elif fault=='import': text=text.replace('import glob','import glob as changed')
    elif fault=='signature': text=text.replace('spot: float)', 'spot: int)')
    elif fault=='duplicate': text+='\ndef load(symbol, spot): pass\n'
    elif fault=='order': text=text.replace('MAX_QUOTE_AGE_MIN = 45.0','EXTRA = 1\nMAX_QUOTE_AGE_MIN = 45.0')
    elif fault=='substitution': text=text.replace('glob.glob(REPORTS)','glob.glob(OTHER)')
    else: text+='\ndef syntax error'
    with pytest.raises((ValueError,SyntaxError)): m._projection(text)


def test_missing_source_and_candidate_block(tmp_path,monkeypatch):
    m=api()
    for root in [None,tmp_path]:
        r=m.audit_optionswall_source(root)
        assert not r['source_subset_verified'] and r['blockers']
    monkeypatch.setattr(m,'RUNTIME',tmp_path/'missing.py')
    assert 'VENDOR_UNREADABLE:FileNotFoundError' in m.audit_optionswall_source(SOURCE)['blockers']


def test_cli_and_forbidden_imports(tmp_path):
    api()
    for root,code in [(SOURCE,0),(tmp_path,2)]:
        p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/check_optionswall_source_parity.py'),'--source-root',str(root)],cwd=tmp_path,capture_output=True,text=True,timeout=45)
        assert p.returncode==code,p.stderr
        r=json.loads(p.stdout)
        assert r['source_subset_verified']==(code==0)
        assert not r['ready_for_replay'] and not r['ready_for_training']
    code='\n'.join(['import sys','class Guard:','    def find_spec(self,fullname,*a):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
        'sys.meta_path.insert(0,Guard())','from trading_system.tree_spec.optionswall_source import audit_optionswall_source',
        "assert audit_optionswall_source(sys.argv[1])['source_subset_verified']"])
    p=subprocess.run([sys.executable,'-B','-c',code,str(SOURCE)],cwd=ROOT,capture_output=True,text=True,timeout=45)
    assert p.returncode==0,p.stderr
