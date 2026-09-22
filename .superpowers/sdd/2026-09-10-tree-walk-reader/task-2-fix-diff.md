# Task2 scoped fix

--- reviewed/trading_system/tree_spec/tree_walk_source.py
+++ current/trading_system/tree_spec/tree_walk_source.py
@@ -188,15 +188,17 @@
         ('options', audit_options, parent), ('tree_tr', audit_tree_tr, parent),
         ('stretch', audit_stretch, parent), ('admission', audit_admission, parent),
         ('revalidation', audit_revalidation, parent), ('ema', audit_ema, root),
     ]:
         try:
             result = audit(path)
             dependencies[name] = result
             blockers.extend('DEPENDENCY:' + name + ':' + b for b in result['blockers'])
             if result['source_subset_verified'] is not True and not result['blockers']:
                 blockers.append('DEPENDENCY:' + name + ':NOT_VERIFIED')
-        except INPUT_ERRORS as exc:
+        except INPUT_ERRORS + (StopIteration,) as exc:
+            # The retained EMA auditor uses next() for the baseline pin. A
+            # missing row is unavailable authority, not an unhandled CLI error.
             blockers.append('DEPENDENCY:' + name + ':UNREADABLE:' + type(exc).__name__)
     if not blockers:
         report.update(status='VERIFIED', source_subset_verified=True)
     return report
--- reviewed/tests/tree_spec/test_tree_walk_source.py
+++ current/tests/tree_spec/test_tree_walk_source.py
@@ -96,20 +96,41 @@
                   lambda s: s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9', '0' * 40))
         want = 'BASELINE_COMMIT_MISMATCH'
     else:
         arg, value, want = ('HEAD', '0' * 40, 'SOURCE_COMMIT_MISMATCH') if fault == 'head' else ('--show-toplevel', str(SOURCE), 'NOT_REPOSITORY_ROOT')
         original = m._git
         monkeypatch.setattr(m, '_git', lambda p, *a: value if a == (arg,) else original(p, *a))
     r = m.audit_tree_walk_source(SOURCE)
     assert not r['source_subset_verified'] and want in r['blockers']
 
 
+@pytest.mark.parametrize('via_cli', [False, True])
+def test_missing_baseline_pin_returns_blocked_report_with_actual_ema(monkeypatch, capsys, via_cli):
+    m = api()
+    def missing_pin(text):
+        doc = json.loads(text)
+        doc['repositories'] = [r for r in doc['repositories'] if r['name'] != 'chart-desk']
+        return json.dumps(doc)
+    intercept(monkeypatch, ROOT / 'configs/trees/existing-alerts-baseline.json', missing_pin)
+    if via_cli:
+        cli = importlib.import_module('tools.check_tree_walk_source_parity')
+        monkeypatch.setattr(sys, 'argv', ['check_tree_walk_source_parity.py', '--source-root', str(SOURCE)])
+        assert cli.main() == 2
+        r = json.loads(capsys.readouterr().out)
+    else:
+        r = m.audit_tree_walk_source(SOURCE)
+    assert r['status'] == 'BLOCKED' and not r['source_subset_verified']
+    assert 'BASELINE_COMMIT_MISMATCH' in r['blockers']
+    assert 'DEPENDENCY:ema:UNREADABLE:StopIteration' in r['blockers']
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
 @pytest.mark.parametrize('fault', ['import', 'signature', 'missing', 'duplicate', 'order', 'clock_count', 'clock_site'])
 def test_projection_independently_validates_source_inventory_and_substitution_contract(fault):
     m = api()
     tree = ast.parse(ORIGINAL.read_text(encoding='utf-8'))
     walk = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'walk')
     if fault == 'import':
         tree.body.insert(1, ast.parse('import socket').body[0])
     elif fault == 'signature':
         walk.args.defaults[0] = ast.Constant('different')
     elif fault == 'missing':
