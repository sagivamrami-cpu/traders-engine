"""Reject policy/dependency drift without executing the retained source."""
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
RUNTIME = ROOT / 'trading_system/tree_replay/_vendor/revalidation.py'


def api():
    name = 'trading_system.tree_spec.revalidation_source'
    assert importlib.util.find_spec(name) is not None, 'revalidation auditor missing'
    return importlib.import_module(name)


def intercept(monkeypatch, path, transform):
    original = Path.read_text
    def read(p, *args, **kwargs):
        text = original(p, *args, **kwargs)
        return transform(text) if p.resolve() == path.resolve() else text
    monkeypatch.setattr(Path, 'read_text', read)


def test_complete_policy_and_real_dependencies_verify_without_readiness():
    r = api().audit_revalidation_source(SOURCE)
    assert r['status'] == 'VERIFIED' and r['source_subset_verified']
    assert r['blockers'] == [] and r['checked_projections'] == ['revalidation']
    assert set(r['dependencies']) == {'tracker_admission', 'stretch', 'ema_windows',
        'admission', 'watch_io', 'lifecycle_primitives', 'pvsra'}
    assert not r['ready_for_replay'] and not r['ready_for_training']


@pytest.mark.parametrize('old,new', [
    ('import json\n', 'import json\nimport urllib.request\n'),
    ('from pathlib import PurePosixPath', 'from pathlib import Path as PurePosixPath'),
    ('AGED_PENDING_RECHECK_H = 2.0', 'AGED_PENDING_RECHECK_H = 3.0'),
    ('SOFT_STALE_MIN = 20.0', 'SOFT_STALE_MIN = 30.0'),
    ('HARD_STALE_MIN = 120.0', 'HARD_STALE_MIN = 121.0'),
    ('self.admission = TrackerAdmission(source)', 'self.admission = None'),
    ('self.stretch = StretchReader(source)', 'self.stretch = source'),
    ('self.ema = EmaReader(source)', 'self.ema = source'),
    ('net >= 25.0', 'net > 25.0'),
    ('worst >= 0.0', 'True'),
    ('sent_net < 0 if short else sent_net > 0', 'sent_net > 0 if short else sent_net < 0'),
    ('if with_trade_at_send:', 'if True:'),
    ("(st.side == 'up') != short", "(st.side == 'up') == short"),
    ('if _df is None or not len(_df):', 'if _df is None:'),
    ('ratio = a / (bar_min / 15.0)', 'ratio = a'),
    ('ratio > worst_ratio', 'ratio < worst_ratio'),
    ('age_min > HARD_STALE_MIN', 'age_min >= HARD_STALE_MIN'),
    ('age_min > SOFT_STALE_MIN', 'age_min >= SOFT_STALE_MIN'),
    ('except Exception:\n            age_min = None', 'except Exception:\n            age_min = 0'),
    ('except Exception as exc:', 'except OSError as exc:'),
    ("self.source.fetch_corrected(symbol, '4h', 400)", "self.source.fetch_corrected(symbol, '4h', 3)"),
    ('self._shadow(symbol,', 'self.source.shadow(symbol,'),
    ('bool(fired)', 'False'),
    ('ensure_ascii=False', 'ensure_ascii=True'),
    ('self.source.now_epoch() if now is None else now', 'self.source.now_epoch()'),
    ('age_h < AGED_PENDING_RECHECK_H', 'age_h <= AGED_PENDING_RECHECK_H'),
    ('bool(verified and clean)', 'bool(clean)'),
    ('w.direction and w.direction != direction', 'False'),
    ('self.source.tree_walk(symbol)', 'None'),
    ('abs(ts - now_ts) > window_s', 'abs(ts - now_ts) >= window_s'),
    ('for event in events:', 'for event in reversed(events):'),
    ("impact.lower().startswith('high')", "impact.strip().lower().startswith('high')"),
    ('not isinstance(raw, bool)', 'True'),
    ('return float(raw)', 'return abs(float(raw))'),
    ('_now.timestamp(), 30 * 60', '_now.timestamp(), 15 * 60'),
    ("pvsra.pvsra(_d15).tail(12)", "pvsra.pvsra(_d15).tail(13)"),
    ('now: float | None=None', 'now=None'),
    ('return (True, label, verified)', 'return (True, label, True)'),
])
def test_candidate_policy_drift_blocks(monkeypatch, old, new):
    m = api()
    assert old in RUNTIME.read_text(encoding='utf-8'), old
    intercept(monkeypatch, RUNTIME, lambda s: s.replace(old, new))
    r = m.audit_revalidation_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']


@pytest.mark.parametrize('filename', ['tracker.py', 'tradeplan.py'])
def test_each_source_blob_is_pinned(monkeypatch, filename):
    m = api()
    intercept(monkeypatch, SOURCE/'chart-desk/chartdesk'/filename, lambda s: s+'\n# drift\n')
    r = m.audit_revalidation_source(SOURCE)
    assert not r['source_subset_verified'] and 'SOURCE_BLOB_MISMATCH:'+filename in r['blockers']


@pytest.mark.parametrize('filename,dependency', [
    ('tracker_admission.py', 'tracker_admission'), ('stretch.py', 'stretch'),
    ('ema_windows.py', 'ema_windows'), ('admission_matrix.py', 'admission'),
    ('watch_sessions.py', 'watch_io'), ('lifecycle_voice.py', 'lifecycle_primitives'),
    ('pvsra.py', 'pvsra'),
])
def test_actual_consumed_dependency_drift_blocks(monkeypatch, filename, dependency):
    m = api()
    intercept(monkeypatch, RUNTIME.parent/filename, lambda s: s+'\nUNAPPROVED_EXECUTION = True\n')
    r = m.audit_revalidation_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('DEPENDENCY:'+dependency+':') for b in r['blockers']), r['blockers']


@pytest.mark.parametrize('fault', ['head', 'root', 'baseline'])
def test_identity_cannot_be_redefined(monkeypatch, fault):
    m = api()
    if fault == 'baseline':
        intercept(monkeypatch, ROOT/'configs/trees/existing-alerts-baseline.json',
            lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0'*40))
        want = 'BASELINE_COMMIT_MISMATCH'
    else:
        arg, value, want = ('HEAD', '0'*40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else (
            '--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
        original = m._git
        monkeypatch.setattr(m, '_git', lambda p, *a: value if a == (arg,) else original(p, *a))
    r = m.audit_revalidation_source(SOURCE)
    assert not r['source_subset_verified'] and want in r['blockers']


def test_missing_source_candidate_and_invalid_root_block(tmp_path, monkeypatch):
    m = api()
    for root in [tmp_path, None]:
        r = m.audit_revalidation_source(root)
        assert r['blockers'] and not r['source_subset_verified']
    monkeypatch.setattr(m, 'RUNTIME', tmp_path/'absent.py')
    r = m.audit_revalidation_source(SOURCE)
    assert not r['source_subset_verified']
    assert any(b.startswith('VENDOR_UNREADABLE:') for b in r['blockers'])


@pytest.mark.parametrize('fault', ['count', 'shadow_count', 'order', 'duplicate', 'missing', 'calendar_duplicate'])
def test_projection_requires_literal_counts_and_selected_node_identity(fault):
    m = api()
    tracker = (SOURCE/'chart-desk/chartdesk/tracker.py').read_text(encoding='utf-8')
    calendar = (SOURCE/'chart-desk/chartdesk/tradeplan.py').read_text(encoding='utf-8')
    if fault == 'count': tracker = tracker.replace('tree.walk(symbol)', 'None')
    elif fault == 'shadow_count': tracker = tracker.replace('_shadow(symbol,', '_other_shadow(symbol,', 1)
    elif fault == 'order': tracker = tracker.replace('SOFT_STALE_MIN =', '_swap =').replace('HARD_STALE_MIN =', 'SOFT_STALE_MIN =').replace('_swap =', 'HARD_STALE_MIN =')
    elif fault == 'duplicate': tracker += '\ndef still_valid(t): return None\n'
    elif fault == 'missing': tracker = tracker.replace('def _bias_against(', 'def other_bias(')
    else: calendar += '\ndef calendar_event_ts(ev): return None\n'
    with pytest.raises(ValueError): m._projection(tracker, calendar)


@pytest.mark.parametrize('fault', ['false_empty', 'raised', 'true_with_blocker'])
def test_dependency_failure_cannot_be_hidden_by_verification_flag(monkeypatch, fault):
    m = api()
    original = m.audit_watch_io_source
    def damaged_report(root):
        result = original(root)
        assert result['source_subset_verified'] and not result['blockers']
        if fault == 'raised':
            raise OSError('captured audit input failure')
        if fault == 'false_empty':
            result['source_subset_verified'] = False
        else:
            result['blockers'] = ['INCONSISTENT_DEPENDENCY_REPORT']
        return result
    monkeypatch.setattr(m, 'audit_watch_io_source', damaged_report)
    r = m.audit_revalidation_source(SOURCE)
    want = {'false_empty': 'NOT_VERIFIED', 'raised': 'UNREADABLE:OSError',
            'true_with_blocker': 'INCONSISTENT_DEPENDENCY_REPORT'}[fault]
    assert not r['source_subset_verified']
    assert 'DEPENDENCY:watch_io:' + want in r['blockers']


def test_candidate_top_level_order_is_part_of_the_contract(monkeypatch):
    m = api()
    def reorder(text):
        first, second = 'SOFT_STALE_MIN = 20.0', 'HARD_STALE_MIN = 120.0'
        assert first+'\n'+second in text
        return text.replace(first+'\n'+second, second+'\n'+first)
    intercept(monkeypatch, RUNTIME, reorder)
    r = m.audit_revalidation_source(SOURCE)
    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']


def test_cli_unrelated_cwd_and_fresh_process_import_guard(tmp_path):
    api()
    command = [sys.executable, '-B', str(ROOT/'tools/check_revalidation_source_parity.py'), '--source-root']
    for root, code, status in [(SOURCE, 0, 'VERIFIED'), (tmp_path, 2, 'BLOCKED')]:
        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=90)
        assert p.returncode == code, p.stderr
        r = json.loads(p.stdout)
        assert r['status'] == status and not r['ready_for_replay'] and not r['ready_for_training']
    script = '\n'.join(['import sys', 'class Guard:', '    def find_spec(self, fullname, *args):',
        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')):",
        "            raise AssertionError('forbidden import: '+fullname)",
        'sys.meta_path.insert(0,Guard())',
        'from trading_system.tree_spec.revalidation_source import audit_revalidation_source',
        "assert audit_revalidation_source(sys.argv[1])['source_subset_verified']"])
    p = subprocess.run([sys.executable, '-B', '-c', script, str(SOURCE)], cwd=ROOT,
        capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stderr
