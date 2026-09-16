# Task1 test-only fix round1

Reviewed snapshot191914Z ->currentfix, no commits. Runtime/usageunchanged.

--- reviewed/test_tree_walk.py
+++ current/test_tree_walk.py
@@ -1,15 +1,17 @@
 """Actual original tree decisions from raw synthetic tapes, not final read mocks."""
 
+import ast
 import importlib
 import importlib.util
 import json
+from pathlib import Path
 
 import pandas as pd
 import pytest
 
 from trading_system.tree_replay._vendor.correction import Correction
 
 SYMBOL = 'OANDA:XAUUSD'
 NOW = pd.Timestamp('2026-09-09T14:00Z')
 STAGES = ['DATA', 'CONTEXT', 'LEVELS', 'SESSION', 'PATTERN', 'LOCATION',
           'VECTOR', 'MTF', 'TRAP', 'MEMORY', 'TRIGGER', 'TARGET']
@@ -59,23 +61,25 @@
         assert path == 'news-desk/data/ff_calendar.json'
         if isinstance(self.calendar, Exception):
             raise self.calendar
         return self.calendar
 
     def list_reports(self):
         self.calls.append(('options-list',))
         return []
 
     def read_report(self, path):
+        self.calls.append(('options-read', path))
         raise FileNotFoundError(path)
 
     def read_tv_csv(self, filename):
+        self.calls.append(('tv-read', filename))
         raise FileNotFoundError(filename)
 
 
 def full_source():
     c = correction()
     frames = {('15m', 10): (frame(), c), ('4h', 60): (frame(freq='4h'), c)}
     for tf in ('1h', '30m', '15m', '5m'):
         frames[(tf, 30)] = (frame(freq={'1h': '1h', '30m': '30min', '15m': '15min', '5m': '5min'}[tf]), c)
     daily = frame(220, '1D', False, close=100, width=20)
     daily.index = pd.date_range(end='2026-09-09T00:00Z', periods=220, freq='1D')
@@ -96,20 +100,29 @@
 
 def test_data_fetch_failure_is_structured_stop_without_downstream_reads():
     source = RawSource()
     w = api().TreeReader(source).walk(SYMBOL)
     assert w.reached == 'DATA' and not w.complete
     assert w.stopped_because == '��� ������ (LookupError)'
     assert w.passed == []
     assert source.calls == [('fetch', SYMBOL, '15m', 10)]
 
 
+def test_data_four_hour_exception_after_successful_fifteen_minute_read():
+    source = full_source()
+    source.frames[('4h', 60)] = OSError('raw four-hour failure')
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert not w.complete and w.reached == 'DATA' and w.passed == []
+    assert w.stopped_because == '��� ������ (OSError)'
+    assert source.calls == [('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '4h', 60)]
+
+
 @pytest.mark.parametrize('key', [('15m', 10), ('4h', 60)])
 @pytest.mark.parametrize('fault', ['unverified', 'stale', 'short'])
 def test_both_initial_frames_are_gated(key, fault):
     source = full_source()
     df, c = source.frames[key]
     if fault == 'unverified':
         c = correction('none', 'unknown')
     elif fault == 'stale':
         c = correction('tv_stale')
     else:
@@ -119,21 +132,23 @@
     assert not w.complete and w.reached == 'DATA' and w.stopped_because
     assert source.calls == [('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '4h', 60)]
 
 
 @pytest.mark.parametrize('high,low,kind,sv,trend,want,verdict', [
     (True, False, 'green', False, None, '����', 'trap'),
     (True, False, 'blue', False, '����', '����', 'trap'),
     (False, True, 'red', False, None, '����', 'trap'),
     (False, True, 'violet', False, '����', '����', 'trap'),
     (False, True, 'green', False, '����', '����', 'committed'),
+    (False, True, 'blue', False, '����', '����', 'committed'),
     (True, False, 'red', False, '����', '����', 'committed'),
+    (True, False, 'violet', False, '����', '����', 'committed'),
     (True, False, None, True, '����', '����', 'trap'),
     (False, True, None, True, '����', '����', 'trap'),
     (False, False, 'green', True, '����', '����', 'trend'),
     (False, False, None, False, None, None, 'trend'),
 ])
 def test_trap_follows_vector_side_and_completed_edge(high, low, kind, sv, trend, want, verdict):
     assert api('tree_core').trap_direction(high, low, kind, sv, trend) == (want, verdict)
 
 
 @pytest.mark.parametrize('row,vol,want', [
@@ -356,34 +371,63 @@
         df.iloc[-2, df.columns.get_loc('volume')] = 250.
     if fault == 'prior_break':
         df.iloc[-3, df.columns.get_loc('close')] = 150.
         df.iloc[-3, df.columns.get_loc('high')] = 151.
     if fault == 'missing_volume':
         df = df.drop(columns='volume')
     c = correction('none', 'unknown') if fault == 'unverified' else correction()
     assert api().TreeReader(RawSource({('5m', 5): (df, c)})).first_vector_above_50(SYMBOL) is None
 
 
-@pytest.mark.parametrize('short,stop,first', [(False, 99.7, 125.), (True, 119.5, 95.)])
-def test_both_geometry_consumers_use_original_prices(short, stop, first):
+def assert_named_ladder(actual, expected):
+    # The flat100 SMA-seeded EMAs can differ by floating-point roundoff.
+    # That affects the order of coincident names, not their membership or rung.
+    assert [sorted(n.split('/')) for n, _ in actual] == [
+        sorted(n.split('/')) for n, _ in expected]
+    assert [p for _, p in actual] == pytest.approx([p for _, p in expected])
+
+
+def check_geometry(reader_type, short):
     source = full_source()
     core = api('tree_core')
     side = '����' if short else '����'
     w = core.Walk(SYMBOL, 'TARGET', direction=side, passed=list(STAGES), decided_close=110.,
                   missing=['missing observation'], facts={'fixture': 'literal'})
-    reader = api().TreeReader(source)
+    reader = reader_type(source)
+    # Daily range20: ADR/RD=115/95. Weekly/monthly current H/L=115/90,
+    # so their low rails also equal95; open100 +/- range/2 gives110/90.
+    # Prior daily/weekly lows90 merge with the three from-open low rails.
+    # Entry zone108..112 excludes110. MIN_RR=1.2 makes95 pay on risk9.5;
+    # 107/103/100 do not. Long risk10.3 makes115 an obstacle,125 a target.
+    stop = 119.5 if short else 99.7
+    targets = [
+        ('ADR-LO/AWR-LO/RW-LO/AMR-LO/RD-LO', 95.),
+        ('ADR50-LO/AWR50-LO/AMR50-LO/YDAY-LO/D2-LO/D3-LO/D4-LO/LWEEK-LO', 90.),
+        ('Q-QUARTER', 75.),
+    ] if short else [('Q-QUARTER', 125.), ('Q-HALF', 150.)]
+    obstacles = [
+        ('NY-OPEN', 107.), ('LONDON-OPEN', 103.),
+        ('YDAY-CLOSE/DAY-OPEN/WEEK-OPEN/EMA200-1h/EMA800-1h/CLOUD50-4h/EMA200-4h/Q-WHOLE', 100.),
+    ] if short else [('ADR-HI/RD-HI', 115.)]
     plan = reader.trade_from_walk(w)
     assert plan is not None and plan.tradeable and plan.stop == pytest.approx(stop)
-    assert plan.targets[0][1] == first and plan.not_drawn == ['missing observation']
+    assert_named_ladder(plan.targets, targets)
+    assert_named_ladder(plan.obstacles, obstacles)
+    assert plan.not_drawn == ['missing observation']
     geometry = reader.levels_to_trade(SYMBOL, 110., side, 2.)
     assert geometry is not None and geometry[0] == pytest.approx(stop)
-    assert geometry[1][0][1] == first
+    assert_named_ladder(geometry[1], targets)
+
+
+@pytest.mark.parametrize('short', [False, True])
+def test_both_geometry_consumers_use_original_prices(short):
+    check_geometry(api().TreeReader, short)
 
 
 @pytest.mark.parametrize('decided,present', [(109.34, True), (109.33999, False)])
 def test_builder_drift_boundary_is_strict_greater_than(decided, present):
     source = full_source()
     w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='����', decided_close=decided, passed=list(STAGES))
     result = api().TreeReader(source).trade_from_walk(w)
     assert (result is not None) is present
     assert (('fetch', SYMBOL, '1d', 400) in source.calls) is present
 
@@ -500,10 +544,182 @@
     assert api().TreeReader(source).trade_from_walk(w) is None
     assert source.calls == [] and w.refused is None
 
 
 def test_builder_raw_price_reread_failure_is_not_an_economic_refusal():
     w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='����')
     source = RawSource()
     assert api().TreeReader(source).trade_from_walk(w) is None
     assert w.refused is None
     assert w.facts['����� ����'] == '���� 15m �� ���� ���� � ��� ����� R:R'
+
+
+def memory_tape(cleared=False):
+    # Ten warmup bars: spread2 * volume100 = 200; no classified vectors yet.
+    # Row10 green body100..102, volume300 >= 2*100, spread-volume1200.
+    # Row11 departs above it. Row12 red body104..108, volume1000 >= 2*120.
+    # Row13 returns to green (one touch), while departing below red.
+    # Row14 either stays above red, or returns through it (one touch).
+    rows = [(100., 101., 99., 100., 100.)] * 10 + [
+        (100., 103., 99., 102., 300.),
+        (104., 105., 103., 104., 100.),
+        (108., 109., 103., 104., 1000.),
+        (100., 102., 99., 101., 100.),
+        (104., 109., 103., 108., 100.) if cleared else (110., 111., 109., 110., 100.),
+    ]
+    return pd.DataFrame(rows, columns=['open', 'high', 'low', 'close', 'volume'],
+                        index=pd.date_range(end=NOW, periods=15, freq='15min'))
+
+
+def check_memory(reader_type, cleared):
+    source = full_source()
+    df = memory_tape(cleared)
+    source.frames[('15m', 10)] = (df, correction())
+    # Exercise the real default PVSRA and vector-zone reader, not supplied zones.
+    zones = api('tree_signals').vector_zones(df)
+    assert list(zones.index) == [df.index[10], df.index[12]]
+    assert list(zones[['bottom', 'top', 'kind', 'open', 'touches']].itertuples(index=False, name=None)) == [
+        (100., 102., 'green', False, 1),
+        (104., 108., 'red', not cleared, 1 if cleared else 0),
+    ]
+    w = reader_type(source).walk(SYMBOL)
+    assert w.complete and w.passed == STAGES
+    assert w.zones == ([] if cleared else [(106., 'red', 0)])
+    if cleared:
+        assert w.facts['������ �����'] == '��� ���� ����'
+    else:
+        # ATR starts2; last five true ranges4,3,6,5,10, Wilder alpha1/14.
+        # ATR=53449/16807=3.180163...; distance4/ATR=1.25779... rounds1.3.
+        assert w.facts['������ �����'] == (
+            '1 ������ ������ (0 ��� � 1 ����) � ����� red '
+            '104.00-108.00 ����, 1.3 ATR, �� ����')
+    assert w.missing.count('��� ����� ����� ������') == int(cleared)
+    assert w.facts['���� ������ (EQH/EQL)'] == '��� ���� �����'
+
+
+@pytest.mark.parametrize('cleared', [False, True])
+def test_raw_vector_memory_handoff_and_observed_empty_classification(cleared):
+    check_memory(api().TreeReader, cleared)
+
+
+def check_first_vector_window(reader_type, short, offset):
+    df = frame(120, '5min', False)
+    df['open'] = 128.
+    # i=118. Prior close at112 (=i-6) is included;111 (=i-7) excluded.
+    # At the prior break EMA=128 +/-22*2/51, cloud width=22*sqrt(.0099)/4:
+    # 150/106 clears the corresponding edge; intervening128 closes are inside.
+    for index, close, volume in [(118 - offset, 106. if short else 150., 100.),
+                                  (118, 116. if short else 140., 250.)]:
+        df.iloc[index, df.columns.get_loc('close')] = close
+        df.iloc[index, df.columns.get_loc('high')] = max(129., close + 1)
+        df.iloc[index, df.columns.get_loc('low')] = min(127., close - 1)
+        df.iloc[index, df.columns.get_loc('volume')] = volume
+    source = RawSource({('5m', 5): (df, correction())})
+    result = reader_type(source).first_vector_above_50(SYMBOL)
+    if offset == 6:
+        assert result is None
+    else:
+        assert result is not None
+        assert result['direction'] == ('����' if short else '����')
+        assert result['vector'] == ('red' if short else 'green')
+        assert result['close'] == (116. if short else 140.)
+    assert source.calls == [('fetch', SYMBOL, '5m', 5)]
+
+
+@pytest.mark.parametrize('short', [False, True])
+@pytest.mark.parametrize('offset', [6, 7])
+def test_first_vector_six_prior_closes_inclusion_boundary(short, offset):
+    check_first_vector_window(api().TreeReader, short, offset)
+
+
+def check_full_trace(reader_type, variant):
+    source = full_source()
+    reader = reader_type(source)
+    assert source.calls == []
+    assert reader.walk(SYMBOL, variant).complete
+    # Literal source call order: DATA; ladder; options; stretch; map; optional
+    # strict pivots; news; session/Brinks/PSY clocks; patterns; MTF; memory.
+    assert source.calls == [
+        ('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '4h', 60),
+        ('fetch', SYMBOL, '1h', 30), ('fetch', SYMBOL, '30m', 30),
+        ('fetch', SYMBOL, '15m', 30), ('fetch', SYMBOL, '5m', 30),
+        ('options-list',),
+        ('fetch', SYMBOL, '1d', 400), ('fetch', SYMBOL, '15m', 20),
+        ('fetch', SYMBOL, '1h', 60), ('fetch', SYMBOL, '4h', 240),
+        ('fetch', SYMBOL, '1d', 400), ('fetch', SYMBOL, '5m', 3), ('clock',),
+        ('fetch', SYMBOL, '1h', 20),
+        ('fetch', SYMBOL, '1h', 240), ('fetch', SYMBOL, '4h', 240),
+        *([('fetch', SYMBOL, '1d', 30)] if variant == 'strict' else []),
+        ('clock',), ('calendar', 'news-desk/data/ff_calendar.json'),
+        ('clock',), ('clock',), ('clock',),
+        ('fetch', SYMBOL, '1h', 10), ('fetch', SYMBOL, '15m', 10),
+        ('fetch', SYMBOL, '5m', 5), ('fetch', SYMBOL, '15m', 5),
+        ('fetch', SYMBOL, '1h', 30), ('clock',),
+        ('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '15m', 10),
+    ]
+
+
+@pytest.mark.parametrize('variant', ['house', 'strict'])
+def test_successful_full_walk_has_exact_ordered_raw_trace(variant):
+    check_full_trace(api().TreeReader, variant)
+
+
+@pytest.mark.parametrize('method,path,call', [
+    ('read_report', 'synthetic-report.json', 'options-read'),
+    ('read_tv_csv', 'synthetic-tape.csv', 'tv-read'),
+])
+def test_raw_artifact_failure_records_attempt_before_raising(method, path, call):
+    source = RawSource()
+    with pytest.raises(FileNotFoundError):
+        getattr(source, method)(path)
+    assert source.calls == [(call, path)]
+
+
+def local_candidate(before, after):
+    """Compile only this repository's candidate class; never retained originals."""
+    module = api()
+    text = Path(module.__file__).read_text(encoding='utf-8')
+    assert text.count(before) == 1, 'Mutation must bind one exact candidate site'
+    parsed = ast.parse(text.replace(before, after))
+    cls = next(node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name == 'TreeReader')
+    namespace = dict(vars(module))
+    exec(compile(ast.Module(body=[cls], type_ignores=[]), '<local-tree-candidate>', 'exec'), namespace)
+    return namespace['TreeReader']
+
+
+@pytest.mark.parametrize('before,after,probe', [
+    ("w.zones = [(float(m), str(k), int(tc)) for m, k, tc in zip(mid, open_z['kind'], open_z['touches'])]",
+     'w.zones = []', 'memory'),
+    ("mid = (open_z['top'] + open_z['bottom']) / 2.0", "mid = open_z['top']", 'memory'),
+    ('(float(m), str(k), int(tc))', "(float(m), 'green', int(tc))", 'memory'),
+    ('(float(m), str(k), int(tc))', '(float(m), str(k), int(tc) + 1)', 'memory'),
+    ("w.missing.append('��� ����� ����� ������')", 'pass', 'empty-memory'),
+    ('obstacles=obstacles, refusal=refusal)', 'obstacles=[], refusal=refusal)', 'geometry'),
+    ('targets=targets, atr=atr', 'targets=targets[:1], atr=atr', 'geometry'),
+    ('return (stop, targets)', 'return (stop, targets[:1])', 'geometry'),
+    ('for tf in TREND_LADDER[1:]:', 'for tf in reversed(TREND_LADDER[1:]):', 'trace'),
+    ('look = df.iloc[max(0, i - 6):i]', 'look = df.iloc[max(0, i - 5):i]', 'window-six'),
+    ('look = df.iloc[max(0, i - 6):i]', 'look = df.iloc[max(0, i - 7):i]', 'window-seven'),
+], ids=['drop-zone-handoff', 'zone-top-not-midpoint', 'wrong-zone-kind', 'wrong-touch-count',
+        'erase-observed-empty', 'drop-plan-obstacles', 'truncate-plan-targets',
+        'truncate-geometry-targets', 'reverse-ladder-reads', 'exclude-sixth-close', 'include-seventh-close'])
+def test_new_assertions_reject_local_runtime_mutations(before, after, probe):
+    # Mutate the aligned price/cloud slices together for a real behavior defect,
+    # avoiding a pandas alignment exception as a substitute for detection.
+    if probe.startswith('window-'):
+        count = 5 if probe == 'window-six' else 7
+        module = api()
+        text = Path(module.__file__).read_text(encoding='utf-8')
+        start = text.index('        look = df.iloc[max(0, i - 6):i]')
+        end = text.index('        if not prev_in_or_below:', start)
+        before = text[start:end]
+        after = before.replace('i - 6', f'i - {count}')
+    candidate = local_candidate(before, after)
+    with pytest.raises(AssertionError):
+        if probe in ('memory', 'empty-memory'):
+            check_memory(candidate, probe == 'empty-memory')
+        elif probe == 'geometry':
+            check_geometry(candidate, False)
+        elif probe == 'trace':
+            check_full_trace(candidate, 'house')
+        else:
+            check_first_vector_window(candidate, False, 6 if probe == 'window-six' else 7)
