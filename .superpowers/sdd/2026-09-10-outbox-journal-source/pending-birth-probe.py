"""New raw-journal regression versus a local retained-birth mutant."""
import importlib
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
runtime = importlib.import_module('trading_system.tree_replay._vendor.outbox_journal')
spec = importlib.util.spec_from_file_location(
    'local_outbox_tests', ROOT / 'tests/tree_replay/test_outbox_journal.py')
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
test = tests.test_pending_duplicate_consumes_birth_before_later_new_event
text = Path(runtime.__file__).read_text(encoding='utf-8')
assert text.count('self._BORN.pop(text, None)') == 1
mutant = types.ModuleType('local_outbox_mutant')
mutant.__dict__.update(runtime.__dict__)
exec(compile(text.replace('self._BORN.pop(text, None)', 'self._BORN.get(text)'),
             '<local-outbox-mutation>', 'exec'), mutant.__dict__)
mutant_test = types.FunctionType(test.__code__, dict(test.__globals__, api=lambda: mutant))
for duplicate_time in (120., 180.):
    for upgrade in (False, True):
        test(duplicate_time, upgrade)
        try:
            mutant_test(duplicate_time, upgrade)
        except AssertionError:
            continue
        raise AssertionError('birth retention mutant survived')
print('PASS four actual pending-duplicate regressions; four retained-birth mutants rejected')
