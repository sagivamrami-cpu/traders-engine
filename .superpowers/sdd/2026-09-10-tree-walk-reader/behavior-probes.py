"""Reproducible local-candidate mutation evidence; retained originals stay inert."""
import ast
import runpy
import sys
import types
from pathlib import Path

from trading_system.tree_replay._vendor import tree_core, tree_walk
from trading_system.tree_spec.tree_walk_source import _projection, _dump


def candidate(name, before, after):
    text = Path('trading_system/tree_replay/_vendor/' + name + '.py').read_text(encoding='utf-8')
    assert text.count(before) == 1
    module = types.ModuleType('trading_system.tree_replay._vendor._probe_' + name)
    module.__package__ = 'trading_system.tree_replay._vendor'
    sys.modules[module.__name__] = module
    exec(compile(text.replace(before, after), '<local candidate mutation>', 'exec'), module.__dict__)
    return module


trap = candidate('tree_core', "return ('שורט', 'trap')", "return ('לונג', 'trap')")
assert tree_core.trap_direction(True, False, 'green', False, None) == ('שורט', 'trap')
assert trap.trap_direction(True, False, 'green', False, None) != ('שורט', 'trap')
news = candidate('tree_core', 'now_ts, 15 * 60', 'now_ts, 30 * 60')
events = [{'dateline': 1900000901, 'impact': 'High', 'title': 'probe'}]
assert tree_core._news_stop(events, 1900000000) is None
assert news._news_stop(events, 1900000000) is not None

fixture = runpy.run_path('tests/tree_replay/test_tree_walk.py')
df = fixture['frame'](120, '5min', False)
df['open'], df['high'], df['low'] = 128., 129., 127.
df.iloc[-2, df.columns.get_loc('close')] = 140.
df.iloc[-2, df.columns.get_loc('high')] = 141.
df.iloc[-2, df.columns.get_loc('volume')] = 250.
source = fixture['RawSource']({('5m', 5): (df, fixture['correction']())})
forming = candidate('tree_walk', 'i = n - 2', 'i = n - 1')
assert tree_walk.TreeReader(source).first_vector_above_50(fixture['SYMBOL'])['close'] == 140.
assert forming.TreeReader(source).first_vector_above_50(fixture['SYMBOL']) is None

# Only parse the retained original for the separate ordered-AST check.
original = Path(sys.argv[1]) / 'chart-desk/chartdesk/tree.py'
expected = _projection(original.read_text(encoding='utf-8'))['tree_walk']
local = ast.parse(Path('trading_system/tree_replay/_vendor/tree_walk.py').read_text(encoding='utf-8'))
cls = next(n for n in local.body if isinstance(n, ast.ClassDef))
walk = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'walk')
def is_clock_assignment(n):
    return isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'now_ts' for t in n.targets)
block = next(n for n in walk.body if isinstance(n, ast.Try) and any(is_clock_assignment(x) for x in n.body))
i = next(i for i, n in enumerate(block.body) if is_clock_assignment(n))
block.body[i], block.body[i + 1] = block.body[i + 1], block.body[i]
assert [_dump(n) for n in local.body] != [_dump(n) for n in expected]
print('PASS: trap side, news15min, completed row and ordered news-clock probes; retained original never executed')
