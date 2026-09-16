"""An audit accepts only the pinned complete EMA reader and actual dependency."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get('TR_TREE_SOURCE_ROOT',
    Path(__file__).resolve().parents[2] / ".source-checkouts"))
RUNTIME = ROOT / 'trading_system/tree_replay/_vendor/ema_windows.py'


def api():
    name = 'trading_system.tree_spec.ema_windows_source'
    assert importlib.util.find_spec(name) is not None, 'EMA windows auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch, path, transform):
    original = Path.read_text
    def read(p, *args, **kwargs):
        value = original(p, *args, **kwargs)
        return transform(value) if p.resolve() == path.resolve() else value
    monkeypatch.setattr(Path, 'read_text', read)


def test_complete_reader_and_real_seeded_ema_verify_without_readiness():
    r = api().audit_ema_windows_source(SOURCE)
    assert r['status'] == 'VERIFIED' and r['source_subset_verified']
    assert r['checked_projections'] == ['ema_windows'] and r['blockers'] == []
    assert r['dependencies']['ema']['source_subset_verified']
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('old,new', [
    ('from . import indicators as I', 'from . import indicators as I\nimport urllib.request'),
    ('from pathlib import PurePosixPath', 'from pathlib import Path as PurePosixPath'),
    ("'BINANCE:BTCUSDT': 'BTCUSD'", "'BINANCE:BTCUSDT': 'BTCUSDT'"),
    ('LENGTHS = (5, 7, 13, 50, 200, 800)', 'LENGTHS = (5, 13, 50, 200, 800)'),
    ('SLOPE_BARS = 3', 'SLOPE_BARS = 5'),
    ('OPEN_ATR = 0.75', 'OPEN_ATR = 0.7'),
    ('GLUED_ATR = 0.2', 'GLUED_ATR = 0.3'),
    ('self.distance > 0', 'self.distance > 1e-10'),
    ('abs(self.atr_distance) >= OPEN_ATR', 'abs(self.atr_distance) > OPEN_ATR'),
    ('w.distance < 0', 'w.distance <= 0'),
    ('deepest = max(self.lost)', 'deepest = min(self.lost)'),
    ('min(opens, key=', 'max(opens, key='),
    ('sum(vals) / total', 'sum(vals) / len(vals)'),
    ('/ len(LENGTHS)', '/ len(self.windows)'),
    ('if w.slope_atr is not None', 'if w.slope_atr'),
    ('fast_length: int=5', 'fast_length: int=7'),
    ('order[i] > order[i + 1]', 'order[i] >= order[i + 1]'),
    ('adjust=False', 'adjust=True'),
    ('len(df) < 2 * n and deep is not None', 'deep is not None'),
    ('deep.index < df.index[0]', 'deep.index <= df.index[0]'),
    ('pd.concat([head, df])', 'head'),
    ("keep='last'", "keep='first'"),
    ('if len(src) < 2 * n:', 'if len(src) < n:'),
    ('I.ema(src[\'close\'], n)', 'I.ema(df[\'close\'], n)'),
    ('if val != val:', 'if False:'),
    ('series.iloc[-1 - SLOPE_BARS]', 'series.iloc[-1]'),
    ('src.tail(2 * SLOPE_BARS + 14)', 'src'),
    ('if len(src) > 20 else atr', 'if len(src) > 200 else atr'),
    ('Window(n, val, close - val, atr,', 'Window(n, val, close - val, span_atr,'),
    ('self.source = source', 'self.source = None'),
    ('class EmaReader:', 'class EmaReader:\n    extra = True'),
    ('lookback: int | None=None', 'lookback=None'),
    ("'1d': 2200", "'1d': 2000"),
    ('lookback = lookback or', 'lookback = 2000 or'),
    ("PurePosixPath('.')", "PurePosixPath('other')"),
    ("'15m': 'M15'", "'15m': 'M5'"),
    ("_dp.name.startswith('_') is False", 'True'),
    ('self.source.deep_exists(_dp.as_posix())', 'True'),
    ('BytesIO(self.source.deep_bytes(_dp.as_posix()))', '_dp'),
    ('utc=True', 'utc=False'),
    ("_d.set_index('time').sort_index()", "_d.set_index('time')"),
    ('except Exception:', 'except OSError:'),
    ("source=corr.source if corr else ''", "source=''"),
    ('for tf in timeframes:', 'for tf in set(timeframes):'),
    ('out[tf] = self.read(symbol, tf)', 'out[tf] = None'),
])
def test_real_candidate_drift_is_blocked(monkeypatch, old, new):
    m = api()
    assert old in RUNTIME.read_text(encoding='utf-8'), old
    intercept(monkeypatch, RUNTIME, lambda s: s.replace(old, new))
    r = m.audit_ema_windows_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']


@pytest.mark.parametrize('filename', ['emawin.py', 'basis.py'])
def test_each_source_blob_is_independently_pinned(monkeypatch, filename):
    m = api()
    intercept(monkeypatch, SOURCE / 'chart-desk/chartdesk' / filename, lambda s: s+'\n# drift\n')
    r = m.audit_ema_windows_source(SOURCE)
    assert not r['source_subset_verified']
    assert 'SOURCE_BLOB_MISMATCH:'+filename in r['blockers']


def test_actual_indicator_dependency_drift_blocks_verification(monkeypatch):
    m = api()
    p = RUNTIME.parent / 'indicators.py'
    assert 'prev = alpha * v[i]' in p.read_text(encoding='utf-8')
    intercept(monkeypatch, p, lambda s: s.replace('prev = alpha * v[i]', 'prev = 0 * v[i]'))
    r = m.audit_ema_windows_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('DEPENDENCY:ema:') and 'indicators.py' in b for b in r['blockers'])


@pytest.mark.parametrize('fault', ['head', 'root', 'baseline'])
def test_source_identity_cannot_be_redefined(monkeypatch, fault):
    m = api()
    if fault == 'baseline':
        intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json',
            lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0'*40))
        want = 'BASELINE_COMMIT_MISMATCH'
    else:
        arg, value, want = ('HEAD', '0'*40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else (
            '--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
        original = m._git
        monkeypatch.setattr(m, '_git', lambda p, *args: value if args == (arg,) else original(p, *args))
    r = m.audit_ema_windows_source(SOURCE)
    assert want in r['blockers'] and not r['source_subset_verified']


def test_missing_source_candidate_and_invalid_root_block(tmp_path, monkeypatch):
    m = api()
    for root in [tmp_path, None]:
        r = m.audit_ema_windows_source(root)
        assert r['blockers'] and not r['source_subset_verified']
    monkeypatch.setattr(m, 'RUNTIME', tmp_path / 'absent.py')
    r = m.audit_ema_windows_source(SOURCE)
    assert any(b.startswith('VENDOR_UNREADABLE:') for b in r['blockers'])
    assert not r['source_subset_verified']


@pytest.mark.parametrize('fault', ['count', 'order', 'duplicate', 'map_collision'])
def test_projection_rejects_missing_substitution_or_symbol_collisions(fault):
    m = api()
    source = (SOURCE / 'chart-desk/chartdesk/emawin.py').read_text(encoding='utf-8')
    basis = (SOURCE / 'chart-desk/chartdesk/basis.py').read_text(encoding='utf-8')
    if fault == 'count': source = source.replace('_dp.exists()', 'True')
    elif fault == 'order': source = source.replace('FAST =', '_swap =').replace('SLOW =', 'FAST =').replace('_swap =', 'SLOW =')
    elif fault == 'duplicate': source += '\ndef read(symbol, timeframe): return None\n'
    else: basis += '\nMT5_SYMBOL_MAP = {}\n'
    with pytest.raises(ValueError):
        m._projection(source, basis)


def test_cli_unrelated_cwd_and_import_guard(tmp_path):
    api()
    command = [sys.executable, '-B', str(ROOT/'tools/check_ema_windows_source_parity.py'), '--source-root']
    for root, code, status in [(SOURCE, 0, 'VERIFIED'), (tmp_path, 2, 'BLOCKED')]:
        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=45)
        assert p.returncode == code, p.stderr
        r = json.loads(p.stdout)
        assert r['status'] == status and not r['ready_for_replay'] and not r['ready_for_training']
    script = '\n'.join([
        'import sys', 'class Guard:', '    def find_spec(self, fullname, *args):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')):",
        "            raise AssertionError('forbidden import: '+fullname)",
        'sys.meta_path.insert(0,Guard())',
        'from trading_system.tree_spec.ema_windows_source import audit_ema_windows_source',
        "assert audit_ema_windows_source(sys.argv[1])['source_subset_verified']",
    ])
    p = subprocess.run([sys.executable, '-B', '-c', script, str(SOURCE)], cwd=ROOT,
        capture_output=True, text=True, timeout=45)
    assert p.returncode == 0, p.stderr
