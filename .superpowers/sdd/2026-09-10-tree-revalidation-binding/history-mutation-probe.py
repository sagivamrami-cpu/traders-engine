"""Run from repo root: python -B <this path>. Only local in-memory candidates."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'tests/tree_replay'))
import test_tree_revalidation as tests
import trading_system.tree_replay.tree_revalidation as binding
import trading_system.tree_replay._vendor.matrix_reader as matrix

source = Path(matrix.__file__).read_text(encoding='utf-8')
needle = 'note = corr.render() if corr.show else None'
assert source.count(needle) == 1
namespace = dict(vars(matrix))
exec(compile(source.replace(needle, 'df = df.tail(matrix.LOOKBACK[tf])\n        ' + needle),
             '<local-trim-mutant>', 'exec'), namespace)
facade = dict(vars(binding))
exec(compile(Path(binding.__file__).read_text(encoding='utf-8'), '<local-binding>', 'exec'), facade)
facade['MatrixReader'] = namespace['MatrixReader']
check = tests.test_matrix_history_before_requested_lookback_still_contributes_to_atr
check()
check_globals = dict(check.__globals__)
check_globals['api'] = lambda: types.SimpleNamespace(TreeRevalidation=facade['TreeRevalidation'])
try:
    types.FunctionType(check.__code__, check_globals)()
except AssertionError:
    print('PASS real history preserved; local tail(LOOKBACK) mutant rejected')
else:
    raise AssertionError('history trim mutant survived')
