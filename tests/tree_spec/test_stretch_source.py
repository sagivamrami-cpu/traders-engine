"""Audit drift must fail without importing or executing source/runtime modules."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(os.environ.get('TR_TREE_SOURCE_ROOT',
    Path(__file__).resolve().parents[2] / ".source-checkouts"))
RUNTIME=ROOT/'trading_system/tree_replay/_vendor/stretch.py'


def api():
    name='trading_system.tree_spec.stretch_source'
    assert importlib.util.find_spec(name) is not None, 'stretch auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch,path,transform):
    original=Path.read_text
    def read(p,*args,**kwargs):
        text=original(p,*args,**kwargs)
        return transform(text) if p.resolve()==path.resolve() else text
    monkeypatch.setattr(Path,'read_text',read)


def test_complete_runtime_and_actual_dependencies_verify_without_readiness():
    r=api().audit_stretch_source(SOURCE)
    assert r['status']=='VERIFIED' and r['source_subset_verified']
    assert r['checked_projections']==['stretch'] and r['blockers']==[]
    assert r['dependencies']['range']['source_subset_verified']
    assert r['dependencies']['ema']['source_subset_verified']
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('old,new',[
    ('BUDGET_MIN = 1.25','BUDGET_MIN = 1.0'),
    ('self.budget_used >= BUDGET_MIN','self.budget_used > BUDGET_MIN'),
    ('self.beyond > BEYOND_MIN','self.beyond >= BEYOND_MIN'),
    ('BEYOND_EXTREME = 0.5','BEYOND_EXTREME = 0.25'),
    ('DEV_STRETCHED = 3.0','DEV_STRETCHED = 2.0'),
    ('direction == self.direction','direction != self.direction'),
    ('abs(v) for v','v for v'),
    ("self.side == 'up'","self.side == 'down'"),
    ('rng.ewm(alpha=1 / n, adjust=False)','rng.ewm(alpha=1 / n, adjust=True)'),
    ('len(df) < 60','len(df) < 59'),
    ("e['ema50']","e['ema13']"),
    ('if not atr:','if atr:'),
    ("self.source.fetch_corrected(symbol, '1d', 400)","self.source.fetch_corrected(symbol, '1d', 20)"),
    ('self.source.broker_shape_ok(dcorr, 20)','self.source.broker_shape_ok(dcorr, 14)'),
    ('daily.empty or not self.source.broker_shape_ok','not self.source.broker_shape_ok'),
    ('ranges.weekly_from_daily(daily)','None'),
    ('broker_bars=True','broker_bars=False'),
    ("af.get('verified')","True"),
    ("('15m', 20), ('1h', 60), ('4h', 240)","('4h', 240), ('1h', 60), ('15m', 20)"),
    ('self._dev_from_cloud(symbol, tf, days)','None'),
    ('if d is not None:','if d:'),
    ('from . import tr, ranges','from . import tr, ranges\nimport urllib.request'),
    ('self.source = source','self.source = None'),
    ('class StretchReader:','class StretchReader:\n    extra = True'),
    ('def state(self, symbol: str)','def state(self, symbol)'),
])
def test_real_candidate_mutations_are_rejected(monkeypatch,old,new):
    api()
    assert old in RUNTIME.read_text(encoding='utf-8')
    intercept(monkeypatch,RUNTIME,lambda s:s.replace(old,new))
    r=api().audit_stretch_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']


@pytest.mark.parametrize('file', ['stretch.py','rails.py'])
def test_both_source_files_have_independent_blob_pins(monkeypatch,file):
    api()
    intercept(monkeypatch,SOURCE/'chart-desk/chartdesk'/file,lambda s:s+'\n# drift\n')
    r=api().audit_stretch_source(SOURCE)
    assert not r['source_subset_verified']
    assert f'SOURCE_BLOB_MISMATCH:{file}' in r['blockers']


@pytest.mark.parametrize('file,old,new',[
    ('ranges.py','o + ar / 2.0','o + ar'),
    ('tr.py','def emas','def changed_emas'),
    ('indicators.py','prev = alpha * v[i]','prev = 0 * v[i]'),
])
def test_actual_range_and_seeded_ema_dependencies_are_audited(monkeypatch,file,old,new):
    api()
    p=RUNTIME.parent/file
    assert old in p.read_text(encoding='utf-8')
    intercept(monkeypatch,p,lambda s:s.replace(old,new))
    r=api().audit_stretch_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('DEPENDENCY:') and file in b for b in r['blockers'])


@pytest.mark.parametrize('fault',['head','root','baseline'])
def test_source_identity_is_not_redefined_by_checkout_or_manifest(monkeypatch,fault):
    m=api()
    if fault=='baseline':
        intercept(monkeypatch,ROOT/'configs/trees/existing-alerts-baseline.json',
            lambda s:s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9','0'*40))
        want='BASELINE_COMMIT_MISMATCH'
    else:
        arg,value,want=('HEAD','0'*40,'SOURCE_COMMIT_MISMATCH') if fault=='head' else (
            '--show-toplevel',str(SOURCE),'NOT_REPOSITORY_ROOT')
        original=m._git
        monkeypatch.setattr(m,'_git',lambda p,*args:value if args==(arg,) else original(p,*args))
    assert want in m.audit_stretch_source(SOURCE)['blockers']


def test_missing_source_and_candidate_are_blocked(tmp_path,monkeypatch):
    m=api()
    assert not m.audit_stretch_source(tmp_path)['source_subset_verified']
    monkeypatch.setattr(m,'RUNTIME',tmp_path/'missing.py')
    r=m.audit_stretch_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('VENDOR_UNREADABLE:') for b in r['blockers'])


@pytest.mark.parametrize('fault',['count','order','duplicate'])
def test_projection_preconditions_reject_wrong_source_shape(fault):
    m=api()
    s=(SOURCE/'chart-desk/chartdesk/stretch.py').read_text(encoding='utf-8')
    rails=(SOURCE/'chart-desk/chartdesk/rails.py').read_text(encoding='utf-8')
    if fault=='count': s=s.replace('basis.fetch_corrected(symbol, tf, days)','None')
    elif fault=='order': s=s.replace('BEYOND_MIN =','_swap =').replace(
        'BEYOND_EXTREME =','BEYOND_MIN =').replace('_swap =','BEYOND_EXTREME =')
    else: s+='\ndef state(symbol): return None\n'
    with pytest.raises(ValueError):
        m._projection(s,rails)


def test_cli_from_unrelated_cwd_and_auditor_prohibits_runtime_import(tmp_path):
    api()
    command=[sys.executable,'-B',str(ROOT/'tools/check_stretch_source_parity.py'),'--source-root']
    for root,code,status in [(SOURCE,0,'VERIFIED'),(tmp_path,2,'BLOCKED')]:
        p=subprocess.run(command+[str(root)],cwd=tmp_path,capture_output=True,text=True,timeout=45)
        assert p.returncode==code,p.stderr
        r=json.loads(p.stdout)
        assert r['status']==status and not r['ready_for_replay'] and not r['ready_for_training']
    script="\n".join([
        'import sys', 'class Guard:', '    def find_spec(self, fullname, *args):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')):",
        "            raise AssertionError('forbidden import: '+fullname)",
        'sys.meta_path.insert(0,Guard())',
        'from trading_system.tree_spec.stretch_source import audit_stretch_source',
        "assert audit_stretch_source(sys.argv[1])['source_subset_verified']",
    ])
    p=subprocess.run([sys.executable,'-B','-c',script,str(SOURCE)],cwd=ROOT,
        capture_output=True,text=True,timeout=45)
    assert p.returncode==0,p.stderr
