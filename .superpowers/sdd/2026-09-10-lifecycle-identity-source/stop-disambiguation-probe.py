"""Local in-memory stop-branch mutation; run from repository root."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'tests/tree_replay'))
import test_lifecycle_identity as tests
import trading_system.tree_replay._vendor.lifecycle_identity as runtime

source = Path(runtime.__file__).read_text(encoding='utf-8')
old = "if trade.get('stop') is not None and _text_has_price(text, float(trade['stop'])):\n        return True"
assert source.count(old) == 1
candidate = dict(vars(runtime))
exec(compile(source.replace(old, old.replace('return True', 'return False')),
             '<local-stop-mutant>', 'exec'), candidate)
test = tests.test_same_entry_uses_named_stop_to_identify_actual_trade
test()
namespace = dict(test.__globals__)
namespace['api'] = lambda: types.SimpleNamespace(_match_trade_for_text=candidate['_match_trade_for_text'])
try:
    types.FunctionType(test.__code__, namespace)()
except AssertionError:
    print('PASS actual stop disambiguates; local stop-disabled mutant rejected')
else:
    raise AssertionError('stop-disabled mutant survived')
