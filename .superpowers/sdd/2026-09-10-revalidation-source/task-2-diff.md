# Task2 untracked additions against HEAD c1b6071

diff --git a/trading_system/tree_spec/revalidation_source.py b/trading_system/tree_spec/revalidation_source.py
new file mode 100644
index 0000000..f990bb8
--- /dev/null
+++ b/trading_system/tree_spec/revalidation_source.py
@@ -0,0 +1,156 @@
+"""Inert audit of original pending checks and all consumed calculation readers."""
+import ast
+import hashlib
+from pathlib import Path
+
+from tools.check_reversal_source_parity import check_source_parity as audit_pvsra
+from .admission_source import audit_admission_source, _replace_exact as _replace_counted
+from .ema_windows_source import audit_ema_windows_source
+from .lifecycle_primitives_source import audit_lifecycle_primitives_source
+from .stretch_source import audit_stretch_source
+from .tracker_admission_source import (
+    INPUT_ERRORS, _dump, _git, _name, _read_json, _replace_exact, _selected,
+    _without_doc, audit_tracker_admission_source,
+)
+from .watch_io_source import audit_watch_io_source
+
+ROOT = Path(__file__).resolve().parents[2]
+RUNTIME = ROOT / 'trading_system/tree_replay/_vendor/revalidation.py'
+COMMIT = '68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
+BLOBS = {'tracker.py': 'b616b34022e436545d8c1daf85eced51614fd74e',
+         'tradeplan.py': 'd09e9be39ce8dadf1674029e0c03751c70502135'}
+CONSTANTS = ['AGED_PENDING_RECHECK_H', '_BIAS_AGAINST_AS_SENT',
+    '_BIAS_AGAINST_FLAT_AT_SEND', '_BIAS_AGAINST_UNREAD', 'SOFT_STALE_MIN', 'HARD_STALE_MIN']
+METHODS = ['_tree_agrees', 'revalidate_pending', '_shadow', 'still_valid']
+TRACKER_ORDER = CONSTANTS[:4] + METHODS[:2] + CONSTANTS[4:] + METHODS[2:] + ['_bias_against']
+IMPORTS = '''from __future__ import annotations
+import json
+import pandas as pd
+from pathlib import PurePosixPath
+from . import lifecycle_voice as voice
+from . import admission_matrix, pvsra, watch_sessions
+from .tracker_admission import TrackerAdmission
+from .stretch import StretchReader
+from .ema_windows import EmaReader'''
+REMOVE_IMPORTS = {
+    '_tree_agrees': ['from . import tree'],
+    'still_valid': ['from . import stretch', 'from . import basis',
+        'from . import emawin', 'from . import sessions',
+        'from . import basis as _b, matrix as _mx',
+        'from . import basis as _b2, tr as _tr',
+        'from .workspace import repo as _repo',
+        'from .tradeplan import calendar_high_impact_in_window'],
+}
+EXPRESSIONS = {
+    '_tree_agrees': [('tree.walk(symbol)', 'self.source.tree_walk(symbol)')],
+    'revalidate_pending': [('still_valid(t)', 'self.still_valid(t)'),
+        ('time.time()', 'self.source.now_epoch()'),
+        ("_tree_agrees(t['symbol'], t['direction'])", "self._tree_agrees(t['symbol'], t['direction'])")],
+    '_shadow': [('SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)',
+                 'self.source.ensure_shadow_parent(parents=True, exist_ok=True)'),
+        ("SHADOW_LOG.open('a', encoding='utf-8')", "self.source.shadow_open('a', encoding='utf-8')"),
+        ('time.time()', 'self.source.now_epoch()')],
+    'still_valid': [('_higher_bias(symbol)', 'self.admission._higher_bias(symbol)'),
+        ('stretch.state(symbol)', 'self.stretch.state(symbol)'),
+        ('basis.fetch_corrected(symbol, tf, 3)', 'self.source.fetch_corrected(symbol, tf, 3)'),
+        ('pd.Timestamp.now(tz=last.tz)', 'self.source.now_timestamp(tz=last.tz)'),
+        ("emawin.read_stack(symbol, timeframes=('1h', '15m'))", "self.ema.read_stack(symbol, timeframes=('1h', '15m'))"),
+        ('sessions.current_session()', "watch_sessions.current_session_at(decision_time=self.source.now_timestamp(tz='UTC'))"),
+        ("_b.fetch_corrected(symbol, '4h', 400)", "self.source.fetch_corrected(symbol, '4h', 400)"),
+        ('_mx.read_structure(_d4)', 'admission_matrix.read_structure(_d4)'),
+        ("_b2.fetch_corrected(symbol, '15m', 60)", "self.source.fetch_corrected(symbol, '15m', 60)"),
+        ('_tr.pvsra(_d15)', 'pvsra.pvsra(_d15)'),
+        ("_repo('news-desk')", "PurePosixPath('news-desk')"),
+        ('_cal.exists()', 'self.source.calendar_exists(_cal.as_posix())'),
+        ('_dt.now(_tz.utc)', 'self.source.now_utc()'),
+        ('_cal.read_text()', 'self.source.calendar_text(_cal.as_posix())')],
+}
+
+
+def _projection(tracker_text, tradeplan_text):
+    nodes = {_name(n): n for n in _selected(tracker_text, TRACKER_ORDER)}
+    calendar = _selected(tradeplan_text, ['calendar_event_ts', 'calendar_high_impact_in_window'])
+    cls = ast.parse('''class Revalidation:
+    def __init__(self, source):
+        self.source = source
+        self.admission = TrackerAdmission(source)
+        self.stretch = StretchReader(source)
+        self.ema = EmaReader(source)''').body[0]
+    for name in METHODS:
+        node = nodes[name]
+        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(
+                arg.arg == 'self' for arg in node.args.args):
+            raise ValueError('METHOD_SHAPE_MISMATCH:' + name)
+        for statement in REMOVE_IMPORTS.get(name, []):
+            _replace_exact(node, statement, None, statement=True)
+        for old, new in EXPRESSIONS[name]:
+            _replace_exact(node, old, new)
+        if name == 'still_valid':
+            _replace_counted(node, '_shadow', 'self._shadow', 15)
+        node.args.args.insert(0, ast.arg(arg='self'))
+        cls.body.append(node)
+    return ast.parse(IMPORTS).body + [nodes[n] for n in CONSTANTS] + calendar + [nodes['_bias_against'], cls]
+
+
+def audit_revalidation_source(source_root):
+    """Verify source identity and whole projection; no execution or readiness grant."""
+    blockers, checked, dependencies = [], [], {}
+    report = dict(status='BLOCKED', source_subset_verified=False, blockers=blockers,
+        checked_projections=checked, dependencies=dependencies,
+        source_commits={'chart-desk': COMMIT}, ready_for_replay=False, ready_for_training=False)
+    try:
+        parent = Path(source_root)
+        root = parent / 'chart-desk'
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_ROOT_INVALID:' + type(exc).__name__)
+        return report
+    try:
+        if Path(_git(root, '--show-toplevel')).resolve() != root.resolve():
+            blockers.append('NOT_REPOSITORY_ROOT')
+        if _git(root, 'HEAD') != COMMIT:
+            blockers.append('SOURCE_COMMIT_MISMATCH')
+        baseline = _read_json(ROOT / 'configs/trees/existing-alerts-baseline.json')
+        if [r.get('commit') for r in baseline['repositories'] if r.get('name') == 'chart-desk'] != [COMMIT]:
+            blockers.append('BASELINE_COMMIT_MISMATCH')
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_IDENTITY_UNREADABLE:' + type(exc).__name__)
+    texts = {}
+    for filename, pin in BLOBS.items():
+        try:
+            text = (root / 'chartdesk' / filename).read_text(encoding='utf-8')
+            raw = text.encode('utf-8')
+            if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != pin:
+                blockers.append('SOURCE_BLOB_MISMATCH:' + filename)
+            texts[filename] = text
+        except INPUT_ERRORS as exc:
+            blockers.append(f'SOURCE_UNREADABLE:{filename}:{type(exc).__name__}')
+    if len(texts) == len(BLOBS):
+        try:
+            expected = _projection(texts['tracker.py'], texts['tradeplan.py'])
+        except INPUT_ERRORS as exc:
+            blockers.append(f'SOURCE_PROJECTION_UNREADABLE:{type(exc).__name__}:{exc}')
+        else:
+            try:
+                actual = _without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
+                if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
+                    blockers.append('VENDOR_AST_MISMATCH')
+                else:
+                    checked.append('revalidation')
+            except INPUT_ERRORS as exc:
+                blockers.append('VENDOR_UNREADABLE:' + type(exc).__name__)
+    audits = [('tracker_admission', audit_tracker_admission_source, parent),
+        ('stretch', audit_stretch_source, parent), ('ema_windows', audit_ema_windows_source, parent),
+        ('admission', audit_admission_source, parent), ('watch_io', audit_watch_io_source, parent),
+        ('lifecycle_primitives', audit_lifecycle_primitives_source, parent), ('pvsra', audit_pvsra, root)]
+    for name, audit, path in audits:
+        try:
+            result = audit(path)
+            dependencies[name] = result
+            blockers.extend('DEPENDENCY:' + name + ':' + b for b in result['blockers'])
+            if not result['source_subset_verified'] and not result['blockers']:
+                blockers.append('DEPENDENCY:' + name + ':NOT_VERIFIED')
+        except INPUT_ERRORS as exc:
+            blockers.append('DEPENDENCY:' + name + ':UNREADABLE:' + type(exc).__name__)
+    if not blockers:
+        report.update(status='VERIFIED', source_subset_verified=True)
+    return report

diff --git a/tests/tree_spec/test_revalidation_source.py b/tests/tree_spec/test_revalidation_source.py
new file mode 100644
index 0000000..a6dd971
--- /dev/null
+++ b/tests/tree_spec/test_revalidation_source.py
@@ -0,0 +1,201 @@
+"""Reject policy/dependency drift without executing the retained source."""
+import importlib
+import importlib.util
+import json
+import os
+from pathlib import Path
+import subprocess
+import sys
+
+import pytest
+
+ROOT = Path(__file__).resolve().parents[2]
+SOURCE = Path(os.environ.get('TR_TREE_SOURCE_ROOT',
+    'C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'))
+RUNTIME = ROOT / 'trading_system/tree_replay/_vendor/revalidation.py'
+
+
+def api():
+    name = 'trading_system.tree_spec.revalidation_source'
+    assert importlib.util.find_spec(name) is not None, 'revalidation auditor missing'
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch, path, transform):
+    original = Path.read_text
+    def read(p, *args, **kwargs):
+        text = original(p, *args, **kwargs)
+        return transform(text) if p.resolve() == path.resolve() else text
+    monkeypatch.setattr(Path, 'read_text', read)
+
+
+def test_complete_policy_and_real_dependencies_verify_without_readiness():
+    r = api().audit_revalidation_source(SOURCE)
+    assert r['status'] == 'VERIFIED' and r['source_subset_verified']
+    assert r['blockers'] == [] and r['checked_projections'] == ['revalidation']
+    assert set(r['dependencies']) == {'tracker_admission', 'stretch', 'ema_windows',
+        'admission', 'watch_io', 'lifecycle_primitives', 'pvsra'}
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('old,new', [
+    ('import json\n', 'import json\nimport urllib.request\n'),
+    ('from pathlib import PurePosixPath', 'from pathlib import Path as PurePosixPath'),
+    ('AGED_PENDING_RECHECK_H = 2.0', 'AGED_PENDING_RECHECK_H = 3.0'),
+    ('SOFT_STALE_MIN = 20.0', 'SOFT_STALE_MIN = 30.0'),
+    ('HARD_STALE_MIN = 120.0', 'HARD_STALE_MIN = 121.0'),
+    ('self.admission = TrackerAdmission(source)', 'self.admission = None'),
+    ('self.stretch = StretchReader(source)', 'self.stretch = source'),
+    ('self.ema = EmaReader(source)', 'self.ema = source'),
+    ('net >= 25.0', 'net > 25.0'),
+    ('worst >= 0.0', 'True'),
+    ('sent_net < 0 if short else sent_net > 0', 'sent_net > 0 if short else sent_net < 0'),
+    ('if with_trade_at_send:', 'if True:'),
+    ("(st.side == 'up') != short", "(st.side == 'up') == short"),
+    ('if _df is None or not len(_df):', 'if _df is None:'),
+    ('ratio = a / (bar_min / 15.0)', 'ratio = a'),
+    ('ratio > worst_ratio', 'ratio < worst_ratio'),
+    ('age_min > HARD_STALE_MIN', 'age_min >= HARD_STALE_MIN'),
+    ('age_min > SOFT_STALE_MIN', 'age_min >= SOFT_STALE_MIN'),
+    ('except Exception:\n            age_min = None', 'except Exception:\n            age_min = 0'),
+    ('except Exception as exc:', 'except OSError as exc:'),
+    ("self.source.fetch_corrected(symbol, '4h', 400)", "self.source.fetch_corrected(symbol, '4h', 3)"),
+    ('self._shadow(symbol,', 'self.source.shadow(symbol,'),
+    ('bool(fired)', 'False'),
+    ('ensure_ascii=False', 'ensure_ascii=True'),
+    ('self.source.now_epoch() if now is None else now', 'self.source.now_epoch()'),
+    ('age_h < AGED_PENDING_RECHECK_H', 'age_h <= AGED_PENDING_RECHECK_H'),
+    ('bool(verified and clean)', 'bool(clean)'),
+    ('w.direction and w.direction != direction', 'False'),
+    ('self.source.tree_walk(symbol)', 'None'),
+    ('abs(ts - now_ts) > window_s', 'abs(ts - now_ts) >= window_s'),
+    ('for event in events:', 'for event in reversed(events):'),
+    ("impact.lower().startswith('high')", "impact.strip().lower().startswith('high')"),
+    ('not isinstance(raw, bool)', 'True'),
+    ('return float(raw)', 'return abs(float(raw))'),
+    ('_now.timestamp(), 30 * 60', '_now.timestamp(), 15 * 60'),
+    ("pvsra.pvsra(_d15).tail(12)", "pvsra.pvsra(_d15).tail(13)"),
+    ('now: float | None=None', 'now=None'),
+    ('return (True, label, verified)', 'return (True, label, True)'),
+])
+def test_candidate_policy_drift_blocks(monkeypatch, old, new):
+    m = api()
+    assert old in RUNTIME.read_text(encoding='utf-8'), old
+    intercept(monkeypatch, RUNTIME, lambda s: s.replace(old, new))
+    r = m.audit_revalidation_source(SOURCE)
+    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']
+
+
+@pytest.mark.parametrize('filename', ['tracker.py', 'tradeplan.py'])
+def test_each_source_blob_is_pinned(monkeypatch, filename):
+    m = api()
+    intercept(monkeypatch, SOURCE/'chart-desk/chartdesk'/filename, lambda s: s+'\n# drift\n')
+    r = m.audit_revalidation_source(SOURCE)
+    assert not r['source_subset_verified'] and 'SOURCE_BLOB_MISMATCH:'+filename in r['blockers']
+
+
+@pytest.mark.parametrize('filename,dependency', [
+    ('tracker_admission.py', 'tracker_admission'), ('stretch.py', 'stretch'),
+    ('ema_windows.py', 'ema_windows'), ('admission_matrix.py', 'admission'),
+    ('watch_sessions.py', 'watch_io'), ('lifecycle_voice.py', 'lifecycle_primitives'),
+    ('pvsra.py', 'pvsra'),
+])
+def test_actual_consumed_dependency_drift_blocks(monkeypatch, filename, dependency):
+    m = api()
+    intercept(monkeypatch, RUNTIME.parent/filename, lambda s: s+'\nUNAPPROVED_EXECUTION = True\n')
+    r = m.audit_revalidation_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert any(b.startswith('DEPENDENCY:'+dependency+':') for b in r['blockers']), r['blockers']
+
+
+@pytest.mark.parametrize('fault', ['head', 'root', 'baseline'])
+def test_identity_cannot_be_redefined(monkeypatch, fault):
+    m = api()
+    if fault == 'baseline':
+        intercept(monkeypatch, ROOT/'configs/trees/existing-alerts-baseline.json',
+            lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0'*40))
+        want = 'BASELINE_COMMIT_MISMATCH'
+    else:
+        arg, value, want = ('HEAD', '0'*40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else (
+            '--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
+        original = m._git
+        monkeypatch.setattr(m, '_git', lambda p, *a: value if a == (arg,) else original(p, *a))
+    r = m.audit_revalidation_source(SOURCE)
+    assert not r['source_subset_verified'] and want in r['blockers']
+
+
+def test_missing_source_candidate_and_invalid_root_block(tmp_path, monkeypatch):
+    m = api()
+    for root in [tmp_path, None]:
+        r = m.audit_revalidation_source(root)
+        assert r['blockers'] and not r['source_subset_verified']
+    monkeypatch.setattr(m, 'RUNTIME', tmp_path/'absent.py')
+    r = m.audit_revalidation_source(SOURCE)
+    assert not r['source_subset_verified']
+    assert any(b.startswith('VENDOR_UNREADABLE:') for b in r['blockers'])
+
+
+@pytest.mark.parametrize('fault', ['count', 'shadow_count', 'order', 'duplicate', 'missing', 'calendar_duplicate'])
+def test_projection_requires_literal_counts_and_selected_node_identity(fault):
+    m = api()
+    tracker = (SOURCE/'chart-desk/chartdesk/tracker.py').read_text(encoding='utf-8')
+    calendar = (SOURCE/'chart-desk/chartdesk/tradeplan.py').read_text(encoding='utf-8')
+    if fault == 'count': tracker = tracker.replace('tree.walk(symbol)', 'None')
+    elif fault == 'shadow_count': tracker = tracker.replace('_shadow(symbol,', '_other_shadow(symbol,', 1)
+    elif fault == 'order': tracker = tracker.replace('SOFT_STALE_MIN =', '_swap =').replace('HARD_STALE_MIN =', 'SOFT_STALE_MIN =').replace('_swap =', 'HARD_STALE_MIN =')
+    elif fault == 'duplicate': tracker += '\ndef still_valid(t): return None\n'
+    elif fault == 'missing': tracker = tracker.replace('def _bias_against(', 'def other_bias(')
+    else: calendar += '\ndef calendar_event_ts(ev): return None\n'
+    with pytest.raises(ValueError): m._projection(tracker, calendar)
+
+
+@pytest.mark.parametrize('fault', ['false_empty', 'raised', 'true_with_blocker'])
+def test_dependency_failure_cannot_be_hidden_by_verification_flag(monkeypatch, fault):
+    m = api()
+    original = m.audit_watch_io_source
+    def damaged_report(root):
+        result = original(root)
+        assert result['source_subset_verified'] and not result['blockers']
+        if fault == 'raised':
+            raise OSError('captured audit input failure')
+        if fault == 'false_empty':
+            result['source_subset_verified'] = False
+        else:
+            result['blockers'] = ['INCONSISTENT_DEPENDENCY_REPORT']
+        return result
+    monkeypatch.setattr(m, 'audit_watch_io_source', damaged_report)
+    r = m.audit_revalidation_source(SOURCE)
+    want = {'false_empty': 'NOT_VERIFIED', 'raised': 'UNREADABLE:OSError',
+            'true_with_blocker': 'INCONSISTENT_DEPENDENCY_REPORT'}[fault]
+    assert not r['source_subset_verified']
+    assert 'DEPENDENCY:watch_io:' + want in r['blockers']
+
+
+def test_candidate_top_level_order_is_part_of_the_contract(monkeypatch):
+    m = api()
+    def reorder(text):
+        first, second = 'SOFT_STALE_MIN = 20.0', 'HARD_STALE_MIN = 120.0'
+        assert first+'\n'+second in text
+        return text.replace(first+'\n'+second, second+'\n'+first)
+    intercept(monkeypatch, RUNTIME, reorder)
+    r = m.audit_revalidation_source(SOURCE)
+    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']
+
+
+def test_cli_unrelated_cwd_and_fresh_process_import_guard(tmp_path):
+    api()
+    command = [sys.executable, '-B', str(ROOT/'tools/check_revalidation_source_parity.py'), '--source-root']
+    for root, code, status in [(SOURCE, 0, 'VERIFIED'), (tmp_path, 2, 'BLOCKED')]:
+        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True, text=True, timeout=90)
+        assert p.returncode == code, p.stderr
+        r = json.loads(p.stdout)
+        assert r['status'] == status and not r['ready_for_replay'] and not r['ready_for_training']
+    script = '\n'.join(['import sys', 'class Guard:', '    def find_spec(self, fullname, *args):',
+        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')):",
+        "            raise AssertionError('forbidden import: '+fullname)",
+        'sys.meta_path.insert(0,Guard())',
+        'from trading_system.tree_spec.revalidation_source import audit_revalidation_source',
+        "assert audit_revalidation_source(sys.argv[1])['source_subset_verified']"])
+    p = subprocess.run([sys.executable, '-B', '-c', script, str(SOURCE)], cwd=ROOT,
+        capture_output=True, text=True, timeout=90)
+    assert p.returncode == 0, p.stderr

diff --git a/tools/check_revalidation_source_parity.py b/tools/check_revalidation_source_parity.py
new file mode 100644
index 0000000..7a2c72d
--- /dev/null
+++ b/tools/check_revalidation_source_parity.py
@@ -0,0 +1,23 @@
+"""Audit pending-plan checks and real dependencies without importing the runtime."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ''):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.revalidation_source import audit_revalidation_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--source-root', type=Path, required=True,
+                        help='Explicit parent of retained source checkouts')
+    report = audit_revalidation_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report['source_subset_verified'] else 2
+
+
+if __name__ == '__main__':
+    raise SystemExit(main())

