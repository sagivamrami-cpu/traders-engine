"""Independent source-proof contract for lifecycle gate/park/retry."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

RETAINED = Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts"))


def api():
    name = 'trading_system.tree_spec.lifecycle_gate_park_source'
    assert importlib.util.find_spec(name) is not None, 'lifecycle gate/park source auditor missing'
    return importlib.import_module(name)


def test_actual_gate_park_projection_and_real_children_are_verified():
    result = api().audit_lifecycle_gate_park_source(RETAINED)
    assert result['status'] == 'VERIFIED'
    assert result['source_subset_verified'] and result['blockers'] == []
    assert set(result['dependencies']) == {'claim_verifier', 'outbox_journal', 'lifecycle_identity'}
    assert not result['ready_for_replay'] and not result['ready_for_training']


def test_missing_retained_root_fails_closed_without_claiming_readiness(tmp_path):
    result = api().audit_lifecycle_gate_park_source(tmp_path / 'missing')
    assert result['status'] == 'BLOCKED'
    assert result['blockers'] and not result['source_subset_verified']
    assert not result['ready_for_replay'] and not result['ready_for_training']


def test_cli_works_from_unrelated_directory_with_explicit_source_root(tmp_path):
    cli = Path(__file__).resolve().parents[2] / 'tools/check_lifecycle_gate_park_source_parity.py'
    run = subprocess.run([sys.executable, '-B', str(cli), '--source-root', str(RETAINED)],
                         cwd=tmp_path, text=True, capture_output=True, check=False)
    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report['status'] == 'VERIFIED' and report['blockers'] == []


def test_audit_rejects_vendor_verifier_dispatch_drift(tmp_path, monkeypatch):
    module = api()
    original = Path(__file__).resolve().parents[2] / 'trading_system/tree_replay/_vendor/lifecycle_gate.py'
    mutated = tmp_path / 'lifecycle_gate.py'
    mutated.write_text(original.read_text(encoding='utf-8').replace(
        'self.verifier.check_message(text, tr)', 'self.source.check_message(text, tr)', 1),
        encoding='utf-8')
    monkeypatch.setattr(module, 'VENDOR', str(mutated))
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'VENDOR_AST_MISMATCH:lifecycle_gate' in result['blockers']


def test_audit_propagates_an_actual_child_failure(monkeypatch):
    module = api()
    original = module._child_audit
    def child(name, root):
        if name == 'claim_verifier':
            return {'source_subset_verified': False, 'blockers': ['CHILD_DRIFT']}
        return original(name, root)
    monkeypatch.setattr(module, '_child_audit', child)
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'DEPENDENCY:claim_verifier:CHILD_DRIFT' in result['blockers']
    assert not result['source_subset_verified']


def test_audit_turns_missing_or_raised_child_audit_into_a_blocker(monkeypatch):
    module = api()
    def child(name, _root):
        if name == 'claim_verifier':
            raise RuntimeError('child unavailable')
        return {'source_subset_verified': True, 'blockers': []}
    monkeypatch.setattr(module, '_child_audit', child)
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'DEPENDENCY:claim_verifier:UNREADABLE:RuntimeError' in result['blockers']
    assert not result['source_subset_verified']


def test_audit_turns_unimportable_child_module_into_a_blocker(monkeypatch):
    module = api()
    original = module.importlib.import_module
    def load(name):
        if name == 'trading_system.tree_spec.claim_verifier_source':
            raise ModuleNotFoundError(name)
        return original(name)
    monkeypatch.setattr(module.importlib, 'import_module', load)
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'DEPENDENCY:claim_verifier:UNREADABLE:ModuleNotFoundError' in result['blockers']
    assert not result['source_subset_verified']


@pytest.mark.parametrize('report', [
    {'source_subset_verified': 'yes', 'blockers': []},
    {'source_subset_verified': True, 'blockers': ()},
    {'source_subset_verified': True, 'blockers': [object()]},
])
def test_audit_turns_malformed_child_report_fields_into_a_blocker(monkeypatch, report):
    module = api()
    def child(name, _root):
        if name == 'claim_verifier':
            return report
        return {'source_subset_verified': True, 'blockers': []}
    monkeypatch.setattr(module, '_child_audit', child)
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'DEPENDENCY:claim_verifier:UNREADABLE:TypeError' in result['blockers']
    assert not result['source_subset_verified']


def test_audit_rejects_strict_park_expiry_boundary_drift(tmp_path, monkeypatch):
    module = api()
    original = Path(__file__).resolve().parents[2] / 'trading_system/tree_replay/_vendor/lifecycle_gate.py'
    mutated = tmp_path / 'lifecycle_gate.py'
    mutated.write_text(original.read_text(encoding='utf-8').replace(
        '> PARK_MAX_AGE_S:', '>= PARK_MAX_AGE_S:', 1), encoding='utf-8')
    monkeypatch.setattr(module, 'VENDOR', str(mutated))
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'VENDOR_AST_MISMATCH:lifecycle_gate' in result['blockers']


def test_cli_returns_blocked_exit_code_for_missing_explicit_root(tmp_path):
    cli = Path(__file__).resolve().parents[2] / 'tools/check_lifecycle_gate_park_source_parity.py'
    run = subprocess.run([sys.executable, '-B', str(cli), '--source-root', str(tmp_path / 'missing')],
                         cwd=tmp_path, text=True, capture_output=True, check=False)
    assert run.returncode == 2
    assert json.loads(run.stdout)['status'] == 'BLOCKED'


def test_cli_turns_unexpected_audit_error_into_blocked_json(monkeypatch, capsys):
    cli_path = Path(__file__).resolve().parents[2] / 'tools/check_lifecycle_gate_park_source_parity.py'
    spec = importlib.util.spec_from_file_location('gate_parity_cli', cli_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    def broken(_root):
        raise RuntimeError('unexpected child import')
    monkeypatch.setattr(cli, 'audit_lifecycle_gate_park_source', broken)
    assert cli.main(['--source-root', str(RETAINED)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report['status'] == 'BLOCKED'
    assert report['blockers'] == ['AUDIT_UNREADABLE:RuntimeError']


@pytest.mark.parametrize('old,new', [
    ('self.threads = self.outbox.threads', 'self.threads = None'),
    ("str(why).startswith('STALE:')", 'False'),
    ('if k not in d:', 'if True:'),
    ('self.source.atomic_mkdir', 'self.source.mkdir'),
    ('self.source.atomic_mkstemp', 'self.source.mkstemp'),
    ('self.source.atomic_fdopen', 'self.source.fdopen'),
    ('self.source.atomic_fsync', 'self.source.fsync'),
    ('self.source.atomic_replace', 'self.source.replace'),
    ('self.source.atomic_unlink', 'self.source.unlink'),
])
def test_audit_rejects_constructor_persistence_park_and_atomic_rewrite_mutations(tmp_path, monkeypatch, old, new):
    module = api()
    monkeypatch.setattr(module, '_child_audit',
                        lambda _name, _root: {'source_subset_verified': True, 'blockers': []})
    original = Path(__file__).resolve().parents[2] / 'trading_system/tree_replay/_vendor/lifecycle_gate.py'
    mutated = tmp_path / 'lifecycle_gate.py'
    text = original.read_text(encoding='utf-8')
    assert old in text
    mutated.write_text(text.replace(old, new, 1), encoding='utf-8')
    monkeypatch.setattr(module, 'VENDOR', str(mutated))
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'VENDOR_AST_MISMATCH:lifecycle_gate' in result['blockers']


def test_audit_rejects_source_symbol_order_and_signature_or_decorator_contract_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, '_child_audit',
                        lambda _name, _root: {'source_subset_verified': True, 'blockers': []})
    monkeypatch.setattr(module, 'SYMBOLS', tuple(reversed(module.SYMBOLS)))
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert any(row.startswith('SOURCE_PROJECTION_UNREADABLE:lifecycle_gate:ValueError:SOURCE_SYMBOL_ORDER')
               for row in result['blockers'])
    monkeypatch.undo()
    monkeypatch.setattr(module, 'SIGNATURES', ('@contextmanager\ndef gate(msgs: list, state: dict | None = None) -> tuple[list, list]: pass',))
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert any('SOURCE_DECORATOR_MISMATCH:gate' in row for row in result['blockers'])


def test_audit_rejects_authority_pin_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, 'COMMIT', '0' * 40)
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'BASELINE_COMMIT_MISMATCH' in result['blockers']
    assert 'SOURCE_COMMIT_MISMATCH' in result['blockers']


def test_audit_rejects_tracker_blob_pin_and_ordinary_signature_drift(monkeypatch):
    module = api()
    monkeypatch.setattr(module, 'BLOB', '0' * 40)
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'SOURCE_BLOB_MISMATCH:tracker.py' in result['blockers']
    monkeypatch.undo()
    monkeypatch.setattr(module, '_child_audit',
                        lambda _name, _root: {'source_subset_verified': True, 'blockers': []})
    signatures = list(module.SIGNATURES)
    signatures[2] = 'def _park_key(tr: dict, text: int) -> str: pass'
    monkeypatch.setattr(module, 'SIGNATURES', tuple(signatures))
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert any('SOURCE_SIGNATURE_MISMATCH:_park_key' in row for row in result['blockers'])


@pytest.mark.parametrize('old,new', [
    ('if ambiguous_matches:', 'if tr is None:'),
    ("getattr(v, 'stale', False)", 'False'),
    ("blocked.append((text, v.reason))", "blocked.append((text, f'STALE: {v.reason}'))"),
])
def test_audit_rejects_gate_decision_order_and_stale_contradiction_branch_mutations(tmp_path, monkeypatch, old, new):
    module = api()
    monkeypatch.setattr(module, '_child_audit',
                        lambda _name, _root: {'source_subset_verified': True, 'blockers': []})
    original = Path(__file__).resolve().parents[2] / 'trading_system/tree_replay/_vendor/lifecycle_gate.py'
    mutated = tmp_path / 'lifecycle_gate.py'
    text = original.read_text(encoding='utf-8')
    assert old in text
    mutated.write_text(text.replace(old, new, 1), encoding='utf-8')
    monkeypatch.setattr(module, 'VENDOR', str(mutated))
    result = module.audit_lifecycle_gate_park_source(RETAINED)
    assert 'VENDOR_AST_MISMATCH:lifecycle_gate' in result['blockers']
