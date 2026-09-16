# Whole options reader component review

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49. Six full additions, no commits.

warning: in the working copy of 'trading_system/tree_replay/_vendor/optionswall.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/optionswall.py b/trading_system/tree_replay/_vendor/optionswall.py
new file mode 100644
index 0000000..5cded1e
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/optionswall.py
@@ -0,0 +1,177 @@
+"""Options positioning bridge with an explicit freshness and mapping contract.
+
+The options desk works in ETF strikes (GLD/QQQ/IBIT), while subscribers trade
+XAUUSD/NAS100USD/BTCUSDT. A wall is context, never an executable price. The
+conversion ratio is frozen from the report ETF spot and the underlying's
+TradingView close at the same market timestamp. It must not be recomputed from
+the current spot: doing that made every wall move with price and made a crossing
+mathematically impossible.
+
+Fail closed: missing quote timestamps, delayed/historical entitlements, stale
+quotes, expired front expiries or an unsynchronised TradingView anchor all
+produce None. Options are an optional prior and never block the TR tree.
+"""
+from __future__ import annotations
+import datetime as dt
+import json
+import math
+from dataclasses import dataclass
+from zoneinfo import ZoneInfo
+import pandas as pd
+from io import StringIO
+MAX_QUOTE_AGE_MIN = 45.0
+MAX_ANCHOR_GAP_MIN = 75.0
+ETF_OF = {'OANDA:XAUUSD': 'GLD', 'OANDA:NAS100USD': 'QQQ', 'BINANCE:BTCUSDT': 'IBIT'}
+TV_FILE_OF = {'OANDA:XAUUSD': 'XAUUSD_M15.csv', 'OANDA:NAS100USD': 'NAS100_M15.csv', 'BINANCE:BTCUSDT': 'BTCUSD_M15.csv'}
+
+@dataclass(frozen=True)
+class Walls:
+    symbol: str
+    etf: str
+    regime: str
+    flip: float
+    call_wall: float
+    put_wall: float
+    max_pain: float | None
+    positive_gamma: float | None
+    negative_gamma: float | None
+    ratio: float
+    mapped_at: str
+    market_asof: str
+    age_h: float
+    stale: bool = False
+    level_source: str = 'open_interest'
+    mapping_quality: str = 'approximate_etf_to_underlying'
+
+    def regime_he(self) -> str:
+        if self.regime == 'long_gamma':
+            return 'גמא ארוכה — הדילרים מרסנים תנועות (טווח/פין)'
+        if self.regime == 'short_gamma':
+            return 'גמא קצרה — הדילרים מגבירים תנועות (מגמות רצות)'
+        return self.regime
+
+    def line(self) -> str:
+        value = f'אופציות ({self.etf}, מיפוי מקורב): {self.regime_he()} · קיר OI קולים ~{self.call_wall:,.0f} · קיר OI פוטים ~{self.put_wall:,.0f}'
+        if self.flip:
+            value += f' · פליפ גמא ~{self.flip:,.0f}'
+        return value
+
+@dataclass(frozen=True)
+class OptionsStatus:
+    usable: bool
+    reason: str
+    walls: Walls | None = None
+
+def _timestamp(value) -> pd.Timestamp | None:
+    if not value:
+        return None
+    try:
+        out = pd.Timestamp(value)
+        if out.tzinfo is None:
+            return None
+        return out.tz_convert('UTC')
+    except Exception:
+        return None
+
+def _finite(value) -> float | None:
+    try:
+        result = float(value)
+        return result if math.isfinite(result) else None
+    except (TypeError, ValueError):
+        return None
+
+def _front_expiry(entry: dict, market_asof: pd.Timestamp) -> dict | None:
+    market_day = market_asof.tz_convert(ZoneInfo('America/New_York')).date()
+    for expiry in entry.get('expiries') or []:
+        try:
+            if dt.date.fromisoformat(str(expiry.get('expiry'))) >= market_day:
+                return expiry
+        except (TypeError, ValueError):
+            continue
+    return None
+
+class OptionsWallReader:
+
+    def __init__(self, source):
+        self.source = source
+
+    def _anchor(self, symbol: str, market_asof: pd.Timestamp) -> tuple[float, pd.Timestamp] | None:
+        path = TV_FILE_OF[symbol]
+        try:
+            frame = pd.read_csv(StringIO(self.source.read_tv_csv(path)))
+            idx = pd.to_datetime(frame['time'], utc=True, errors='coerce')
+            src = frame.get('src')
+            mask = idx.notna() & (idx <= market_asof)
+            if src is not None:
+                mask &= src.fillna('').astype(str).eq(symbol)
+            usable = frame.loc[mask].copy()
+            if usable.empty:
+                return None
+            usable['_ts'] = idx[mask]
+            row = usable.sort_values('_ts').iloc[-1]
+            stamp = pd.Timestamp(row['_ts'])
+            gap = (market_asof - stamp).total_seconds() / 60.0
+            price = _finite(row.get('close'))
+            if price is None or gap < 0 or gap > MAX_ANCHOR_GAP_MIN:
+                return None
+            return (price, stamp)
+        except (OSError, KeyError, ValueError, pd.errors.ParserError):
+            return None
+
+    def status(self, symbol: str, _current_spot: float | None=None, *, now: pd.Timestamp | None=None) -> OptionsStatus:
+        """Return a usable prior or a precise fail-closed reason.
+
+    _current_spot is accepted for compatibility but is never used in mapping.
+    This is the invariant that lets price cross a fixed wall.
+    """
+        etf = ETF_OF.get(symbol)
+        if not etf:
+            return OptionsStatus(False, 'unsupported_symbol')
+        files = sorted(self.source.list_reports())
+        if not files:
+            return OptionsStatus(False, 'no_report')
+        try:
+            report = json.loads(self.source.read_report(files[-1]))
+        except (json.JSONDecodeError, OSError):
+            return OptionsStatus(False, 'invalid_report')
+        entry = next((item for item in report.get('symbols', []) if item.get('symbol') == etf and (not item.get('degraded'))), None)
+        if not entry:
+            return OptionsStatus(False, 'missing_or_degraded_symbol')
+        market_asof = _timestamp(entry.get('data_asof'))
+        if market_asof is None:
+            return OptionsStatus(False, 'missing_market_asof')
+        permission = str(entry.get('quote_permission') or '')
+        if permission != 'realtime_permission':
+            return OptionsStatus(False, f"non_realtime_permission:{permission or 'unknown'}")
+        clock = pd.Timestamp(self.source.now_utc()) if now is None else pd.Timestamp(now)
+        clock = clock.tz_localize('UTC') if clock.tzinfo is None else clock.tz_convert('UTC')
+        age_min = (clock - market_asof).total_seconds() / 60.0
+        if age_min < -2 or age_min > MAX_QUOTE_AGE_MIN:
+            return OptionsStatus(False, f'stale_market_data:{age_min:.1f}m')
+        etf_spot = _finite(entry.get('spot'))
+        anchor = self._anchor(symbol, market_asof)
+        if etf_spot is None or etf_spot <= 0 or anchor is None:
+            return OptionsStatus(False, 'missing_synchronised_mapping_anchor')
+        under_spot, mapped_at = anchor
+        ratio = under_spot / etf_spot
+        front = _front_expiry(entry, market_asof)
+        if front is None:
+            return OptionsStatus(False, 'no_live_expiry')
+        oi = front.get('walls') or {}
+        calls, puts = (oi.get('call_walls') or [], oi.get('put_walls') or [])
+        call = _finite(calls[0].get('strike') if calls else None)
+        put = _finite(puts[0].get('strike') if puts else None)
+        if call is None or put is None:
+            return OptionsStatus(False, 'missing_oi_walls')
+        gex = entry.get('gex') or {}
+        flip = _finite(gex.get('flip_level'))
+        positive = _finite((gex.get('largest_positive') or {}).get('strike'))
+        negative = _finite((gex.get('largest_negative') or {}).get('strike'))
+        max_pain = _finite(front.get('max_pain'))
+        walls = Walls(symbol=symbol, etf=etf, regime=str(gex.get('regime') or 'unknown'), flip=(flip or 0.0) * ratio, call_wall=call * ratio, put_wall=put * ratio, max_pain=max_pain * ratio if max_pain is not None else None, positive_gamma=positive * ratio if positive is not None else None, negative_gamma=negative * ratio if negative is not None else None, ratio=ratio, mapped_at=mapped_at.isoformat(), market_asof=market_asof.isoformat(), age_h=age_min / 60.0)
+        return OptionsStatus(True, 'ok', walls)
+
+    def load(self, symbol: str, spot: float) -> Walls | None:
+        """Compatibility API used by the tree and trade plan."""
+        return self.status(symbol, spot).walls
+

warning: in the working copy of 'tests/tree_replay/test_optionswall.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_optionswall.py b/tests/tree_replay/test_optionswall.py
new file mode 100644
index 0000000..523d800
--- /dev/null
+++ b/tests/tree_replay/test_optionswall.py
@@ -0,0 +1,194 @@
+"""Original options mapping from raw JSON/CSV with literal economic geometry."""
+import importlib
+import importlib.util
+import json
+
+import pandas as pd
+import pytest
+
+
+SYMBOL='OANDA:XAUUSD'
+
+
+def api():
+    name='trading_system.tree_replay._vendor.optionswall'
+    assert importlib.util.find_spec(name) is not None,'options wall reader missing'
+    return importlib.import_module(name)
+
+
+def entry():
+    return dict(symbol='GLD',data_asof='2026-09-09T15:00:00Z',
+        quote_permission='realtime_permission',spot=200,
+        expiries=[dict(expiry='2026-09-09',walls=dict(
+            call_walls=[dict(strike=210)],put_walls=[dict(strike=190)]),max_pain=205)],
+        gex=dict(regime='long_gamma',flip_level=201,
+            largest_positive=dict(strike=215),largest_negative=dict(strike=185)))
+
+
+class Artifacts:
+    def __init__(self,item=None,now='2026-09-09T15:30:00Z'):
+        self.ids=['report-b.json','report-a.json']
+        self.reports={'report-b.json':json.dumps({'symbols':[entry() if item is None else item]}),
+            'report-a.json':'invalid older report'}
+        self.csv='time,close,src\n2026-09-09T14:45:00Z,2000,OANDA:XAUUSD\n'
+        self.now=pd.Timestamp(now)
+        self.calls=[]
+    def list_reports(self):
+        self.calls.append(('list',))
+        if isinstance(self.ids,Exception): raise self.ids
+        return list(self.ids)
+    def read_report(self,path):
+        self.calls.append(('report',path))
+        value=self.reports[path]
+        if isinstance(value,Exception): raise value
+        return value
+    def read_tv_csv(self,filename):
+        self.calls.append(('csv',filename))
+        if isinstance(self.csv,Exception): raise self.csv
+        return self.csv
+    def now_utc(self):
+        self.calls.append(('clock',))
+        return self.now
+
+
+def test_raw_mapping_is_fixed_not_current_spot_and_port_order():
+    source=Artifacts(); reader=api().OptionsWallReader(source)
+    for current in [1.,99999.,None]:
+        r=reader.status(SYMBOL,current)
+        assert r.usable and r.reason=='ok'
+        w=r.walls
+        assert (w.ratio,w.call_wall,w.put_wall,w.flip,w.max_pain,w.positive_gamma,w.negative_gamma)==(10.,2100.,1900.,2010.,2050.,2150.,1850.)
+        assert (w.mapped_at,w.market_asof,w.age_h)==('2026-09-09T14:45:00+00:00','2026-09-09T15:00:00+00:00',.5)
+        assert not w.stale and w.level_source=='open_interest'
+    assert source.calls==[('list',),('report','report-b.json'),('clock',),('csv','XAUUSD_M15.csv')]*3
+    assert reader.load(SYMBOL,9000).call_wall==2100.
+
+
+@pytest.mark.parametrize('symbol',['GC','GC.v.0','XAUUSD','UNKNOWN'])
+def test_unsupported_symbol_does_not_access_artifacts(symbol):
+    p=Artifacts(); r=api().OptionsWallReader(p).status(symbol)
+    assert not r.usable and r.reason=='unsupported_symbol' and r.walls is None
+    assert p.calls==[]
+
+
+@pytest.mark.parametrize('symbol,etf,filename',[
+    ('OANDA:XAUUSD','GLD','XAUUSD_M15.csv'),('OANDA:NAS100USD','QQQ','NAS100_M15.csv'),
+    ('BINANCE:BTCUSDT','IBIT','BTCUSD_M15.csv')])
+def test_literal_supported_mapping(symbol,etf,filename):
+    e=entry(); e['symbol']=etf; p=Artifacts(e)
+    p.csv='time,close,src\n2026-09-09T14:45:00Z,2000,'+symbol+'\n'
+    w=api().OptionsWallReader(p).status(symbol).walls
+    assert w.etf==etf and w.call_wall==2100. and p.calls[-1]==('csv',filename)
+
+
+@pytest.mark.parametrize('fault,reason',[
+    ('empty','no_report'),('json','invalid_report'),('io','invalid_report'),
+    ('degraded','missing_or_degraded_symbol'),('missing_time','missing_market_asof'),
+    ('naive_time','missing_market_asof'),('permission','non_realtime_permission:delayed'),
+    ('bad_spot','missing_synchronised_mapping_anchor'),('expiry','no_live_expiry'),
+    ('walls','missing_oi_walls')])
+def test_original_failure_reasons(fault,reason):
+    e=entry()
+    if fault=='degraded': e['degraded']=True
+    elif fault=='missing_time': e.pop('data_asof')
+    elif fault=='naive_time': e['data_asof']='2026-09-09T15:00:00'
+    elif fault=='permission': e['quote_permission']='delayed'
+    elif fault=='bad_spot': e['spot']=0
+    elif fault=='expiry': e['expiries'][0]['expiry']='2026-09-08'
+    elif fault=='walls': e['expiries'][0]['walls']['call_walls']=[]
+    p=Artifacts(e)
+    if fault=='empty': p.ids=[]
+    elif fault=='json': p.reports['report-b.json']='bad'
+    elif fault=='io': p.reports['report-b.json']=OSError('missing')
+    r=api().OptionsWallReader(p).status(SYMBOL)
+    assert not r.usable and r.reason==reason and r.walls is None
+    assert ('report','report-a.json') not in p.calls
+    if fault in ['missing_time','naive_time','permission']: assert ('clock',) not in p.calls
+
+
+@pytest.mark.parametrize('now,usable',[
+    ('2026-09-09T14:58:00Z',True),('2026-09-09T14:57:59Z',False),
+    ('2026-09-09T15:45:00Z',True),('2026-09-09T15:45:01Z',False)])
+def test_age_boundaries(now,usable):
+    r=api().OptionsWallReader(Artifacts(now=now)).status(SYMBOL)
+    assert r.usable==usable
+    if not usable: assert r.reason.startswith('stale_market_data:')
+
+
+def test_explicit_naive_clock_is_utc_and_skips_clock_port():
+    p=Artifacts(now='2030-01-01T00:00Z')
+    r=api().OptionsWallReader(p).status(SYMBOL,now=pd.Timestamp('2026-09-09T15:30:00'))
+    assert r.usable and r.walls.age_h==.5 and ('clock',) not in p.calls
+
+
+@pytest.mark.parametrize('stamp,usable',[('13:45:00',True),('13:44:59',False),('15:00:01',False)])
+def test_anchor_age_and_future_boundary(stamp,usable):
+    p=Artifacts(); p.csv='time,close\n2026-09-09T'+stamp+'Z,2000\n'
+    r=api().OptionsWallReader(p).status(SYMBOL)
+    assert r.usable==usable
+    if usable: assert r.walls.ratio==10.
+    else: assert r.reason=='missing_synchronised_mapping_anchor'
+
+
+def test_anchor_filters_wrong_source_and_future_rows_before_selecting():
+    p=Artifacts()
+    p.csv+='2026-09-09T14:59:00Z,9000,WRONG\n2026-09-09T15:01:00Z,8000,OANDA:XAUUSD\n'
+    assert api().OptionsWallReader(p).status(SYMBOL).walls.ratio==10.
+
+
+@pytest.mark.parametrize('value',['bad','nan','inf'])
+def test_latest_bad_anchor_does_not_fallback(value):
+    p=Artifacts(); p.csv+='2026-09-09T15:00:00Z,'+value+',OANDA:XAUUSD\n'
+    r=api().OptionsWallReader(p).status(SYMBOL)
+    assert r.reason=='missing_synchronised_mapping_anchor' and not r.usable
+
+
+@pytest.mark.parametrize('underlying,ratio',[(0.,0.),(-2000.,-10.)])
+def test_finite_nonpositive_underlying_anchor_is_preserved(underlying,ratio):
+    p=Artifacts(); p.csv='time,close\n2026-09-09T14:45Z,'+str(underlying)+'\n'
+    r=api().OptionsWallReader(p).status(SYMBOL)
+    assert r.usable and r.walls.ratio==ratio
+
+
+def test_first_undegraded_etf_and_first_unexpired_entry_not_sorted():
+    e=entry(); e['expiries'][0]['expiry']='2026-10-01'
+    earlier=entry()['expiries'][0]; earlier['walls']['call_walls'][0]['strike']=999
+    e['expiries'].append(earlier)
+    bad=entry(); bad['degraded']=True; bad['spot']=1
+    later=entry(); later['spot']=1
+    p=Artifacts(); p.reports['report-b.json']=json.dumps({'symbols':[bad,e,later]})
+    assert api().OptionsWallReader(p).status(SYMBOL).walls.call_wall==2100.
+
+
+def test_expiry_day_is_new_york_not_utc_date():
+    e=entry(); e['data_asof']='2026-09-10T00:00:00Z'
+    p=Artifacts(e,now='2026-09-10T00:00:00Z')
+    p.csv='time,close\n2026-09-09T23:45:00Z,2000\n'
+    assert api().OptionsWallReader(p).status(SYMBOL).usable
+
+
+def test_first_wall_nonfinite_does_not_fallback_and_optional_zero_is_retained():
+    e=entry(); e['expiries'][0]['walls']['call_walls']=[dict(strike='inf'),dict(strike=210)]
+    assert api().OptionsWallReader(Artifacts(e)).status(SYMBOL).reason=='missing_oi_walls'
+    e=entry(); e['gex']={'flip_level':None,'largest_positive':{'strike':0},'largest_negative':{'strike':'nan'}}
+    e['expiries'][0]['max_pain']=0
+    w=api().OptionsWallReader(Artifacts(e)).status(SYMBOL).walls
+    assert (w.flip,w.positive_gamma,w.negative_gamma,w.max_pain,w.regime)==(0.,0.,None,0.,'unknown')
+
+
+@pytest.mark.parametrize('bad',[OSError('missing'), 'time,other\n2026-09-09T14:45Z,1\n'])
+def test_csv_failure_is_missing_anchor(bad):
+    p=Artifacts(); p.csv=bad
+    assert api().OptionsWallReader(p).status(SYMBOL).reason=='missing_synchronised_mapping_anchor'
+
+
+def test_decoded_wrong_report_shape_retains_original_uncaught_error():
+    p=Artifacts(); p.reports['report-b.json']='[]'
+    with pytest.raises(AttributeError): api().OptionsWallReader(p).status(SYMBOL)
+
+
+def test_listing_failure_propagates_before_later_ports():
+    p=Artifacts(); p.ids=OSError('listing unavailable')
+    with pytest.raises(OSError,match='listing unavailable'):
+        api().OptionsWallReader(p).status(SYMBOL)
+    assert p.calls==[('list',)]

warning: in the working copy of 'docs/architecture/OPTIONS-WALL-READER-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/OPTIONS-WALL-READER-USAGE.md b/docs/architecture/OPTIONS-WALL-READER-USAGE.md
new file mode 100644
index 0000000..9bfa8cf
--- /dev/null
+++ b/docs/architecture/OPTIONS-WALL-READER-USAGE.md
@@ -0,0 +1,32 @@
+# Options context from raw offline artifacts
+
+Private API: trading_system.tree_replay._vendor.optionswall.OptionsWallReader.
+Construct with a source implementing list_reports(), read_report(report_id),
+read_tv_csv(filename), now_utc(). First returns logical report IDs; next two
+return raw text; clock returns an aware UTC datetime/pandas timestamp.
+
+status(symbol,_current_spot=None,*,now=None) returns original OptionsStatus
+with precise reason and optional Walls. load(symbol,spot) calls actual status
+and returns only Walls or None. No default source, disk access or process clock.
+This is implemented, not yet accepted; source audit and independent reviews
+are required under 2026-09-10-options-wall-reader.md.
+
+The reader sorts report IDs and reads only the lexically latest; it never
+silently falls back to an older usable report. Actual json.loads and pandas
+CSV parsing remain. Reports must carry an aware data_asof, exact realtime
+permission and original age bounds. CSV anchors are filtered at market_asof,
+not current time; optional src is matched exactly to the underlying symbol.
+The first valid input-order expiry uses the New York market date. Report order,
+first-wall selection and original exception scopes are unchanged.
+
+Mapping is historical underlying anchor / report ETF spot. Changing the current
+spot does not move the walls. Source accepts finite zero/negative underlying
+anchor values; these raw results are not a new endorsement of input quality.
+Walls are approximate context, not executable targets. Only original GLD/XAU,
+QQQ/NAS and IBIT/BTC mappings exist; GC futures are not aliased to OANDA spot.
+
+These interfaces do not prove artifact availability at an historical instant.
+The later causal provider must establish identity, provenance and publication
+at each operation. No report download, vendor permission, market labels, model
+training, broker execution or live promotion is enabled. Raw source catches
+and reasons are evidence for later features, not guaranteed measured negatives.

warning: in the working copy of 'trading_system/tree_spec/optionswall_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/optionswall_source.py b/trading_system/tree_spec/optionswall_source.py
new file mode 100644
index 0000000..ba78387
--- /dev/null
+++ b/trading_system/tree_spec/optionswall_source.py
@@ -0,0 +1,123 @@
+"""Inert full-source audit of options artifacts, fixed mapping and clock ports."""
+import ast
+import hashlib
+from pathlib import Path
+
+from .tracker_admission_source import INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _without_doc
+
+ROOT=Path(__file__).resolve().parents[2]
+RUNTIME=ROOT/'trading_system/tree_replay/_vendor/optionswall.py'
+COMMIT='68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9'
+BLOB='c7d27ca396c162f6997b2a72bbd035ed6477e05b'
+SOURCE_IMPORTS='''from __future__ import annotations
+import datetime as dt
+import glob
+import json
+import math
+from dataclasses import dataclass
+from pathlib import Path
+from zoneinfo import ZoneInfo
+import pandas as pd
+from .workspace import repo'''
+IMPORTS='''from __future__ import annotations
+import datetime as dt
+import json
+import math
+from dataclasses import dataclass
+from zoneinfo import ZoneInfo
+import pandas as pd
+from io import StringIO'''
+PHYSICAL_GLOBALS='''REPORTS = str(repo("options-desk") / "out" / "report-*.json")
+TV_DIR = Path(__file__).resolve().parent.parent / "data" / "tv"'''
+INVENTORY=['REPORTS','TV_DIR','MAX_QUOTE_AGE_MIN','MAX_ANCHOR_GAP_MIN','ETF_OF','TV_FILE_OF',
+    'Walls','OptionsStatus','_timestamp','_finite','_anchor','_front_expiry','status','load']
+SIGNATURES='''def _anchor(symbol: str, market_asof: pd.Timestamp) -> tuple[float, pd.Timestamp] | None: pass
+def status(symbol: str, _current_spot: float | None=None, *, now: pd.Timestamp | None=None) -> OptionsStatus: pass
+def load(symbol: str, spot: float) -> Walls | None: pass'''
+REPLACEMENTS={
+    '_anchor':[
+        ('TV_DIR / TV_FILE_OF[symbol]','TV_FILE_OF[symbol]'),
+        ('pd.read_csv(path)','pd.read_csv(StringIO(self.source.read_tv_csv(path)))')],
+    'status':[
+        ('glob.glob(REPORTS)','self.source.list_reports()'),
+        ("Path(files[-1]).read_text(encoding='utf-8')",'self.source.read_report(files[-1])'),
+        ("pd.Timestamp.now(tz='UTC')",'pd.Timestamp(self.source.now_utc())'),
+        ('_anchor(symbol, market_asof)','self._anchor(symbol, market_asof)')],
+    'load':[('status(symbol, spot)','self.status(symbol, spot)')],
+}
+
+
+def _name(node):
+    if isinstance(node,(ast.ClassDef,ast.FunctionDef)):
+        return node.name
+    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
+        return node.targets[0].id
+    raise ValueError('UNEXPECTED_SOURCE_NODE')
+
+
+def _projection(text):
+    nodes=_without_doc(ast.parse(text))
+    imports=ast.parse(SOURCE_IMPORTS).body
+    if [_dump(n) for n in nodes[:len(imports)]]!=[_dump(n) for n in imports]:
+        raise ValueError('SOURCE_IMPORT_MISMATCH')
+    nodes=nodes[len(imports):]
+    if [_name(n) for n in nodes]!=INVENTORY:
+        raise ValueError('SOURCE_INVENTORY_MISMATCH')
+    if [_dump(n) for n in nodes[:2]]!=[_dump(n) for n in ast.parse(PHYSICAL_GLOBALS).body]:
+        raise ValueError('SOURCE_PHYSICAL_GLOBAL_MISMATCH')
+    signatures={n.name:n for n in ast.parse(SIGNATURES).body}
+    pure,methods=[],[]
+    for node in nodes[2:]:
+        if not isinstance(node,ast.FunctionDef) or node.name not in signatures:
+            pure.append(node)
+            continue
+        sig=signatures[node.name]
+        if node.decorator_list or _dump(node.args)!=_dump(sig.args) or _dump(node.returns)!=_dump(sig.returns):
+            raise ValueError('SOURCE_SIGNATURE_MISMATCH:'+node.name)
+        node.args.args.insert(0,ast.arg(arg='self'))
+        for old,new in REPLACEMENTS[node.name]:
+            _replace_exact(node,old,new)
+        methods.append(node)
+    if [n.name for n in methods]!=list(signatures):
+        raise ValueError('SOURCE_METHOD_ORDER')
+    ctor=ast.parse('def __init__(self, source):\n    self.source = source').body
+    reader=ast.ClassDef(name='OptionsWallReader',bases=[],keywords=[],body=ctor+methods,decorator_list=[])
+    return ast.parse(IMPORTS).body+pure+[reader]
+
+
+def audit_optionswall_source(source_root):
+    """Certify projection only; no historical artifact or feed readiness claim."""
+    blockers,checked=[],[]
+    report=dict(status='BLOCKED',source_subset_verified=False,blockers=blockers,
+        checked_projections=checked,source_commits={'chart-desk':COMMIT},
+        ready_for_replay=False,ready_for_training=False)
+    try:
+        root=Path(source_root)/'chart-desk'
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_ROOT_INVALID:'+type(exc).__name__)
+        return report
+    try:
+        if Path(_git(root,'--show-toplevel')).resolve()!=root.resolve(): blockers.append('NOT_REPOSITORY_ROOT')
+        if _git(root,'HEAD')!=COMMIT: blockers.append('SOURCE_COMMIT_MISMATCH')
+        baseline=_read_json(ROOT/'configs/trees/existing-alerts-baseline.json')
+        if [r.get('commit') for r in baseline['repositories'] if r.get('name')=='chart-desk']!=[COMMIT]:
+            blockers.append('BASELINE_COMMIT_MISMATCH')
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_IDENTITY_UNREADABLE:'+type(exc).__name__)
+    try:
+        text=(root/'chartdesk/optionswall.py').read_text(encoding='utf-8')
+        raw=text.encode('utf-8')
+        if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=BLOB:
+            blockers.append('SOURCE_BLOB_MISMATCH')
+        expected=_projection(text)
+    except INPUT_ERRORS as exc:
+        blockers.append('SOURCE_PROJECTION_UNREADABLE:'+type(exc).__name__)
+    else:
+        try:
+            actual=_without_doc(ast.parse(RUNTIME.read_text(encoding='utf-8')))
+            if [_dump(n) for n in actual]!=[_dump(n) for n in expected]: blockers.append('VENDOR_AST_MISMATCH')
+            else: checked.append('optionswall')
+        except INPUT_ERRORS as exc:
+            blockers.append('VENDOR_UNREADABLE:'+type(exc).__name__)
+    if not blockers: report.update(status='VERIFIED',source_subset_verified=True)
+    return report

warning: in the working copy of 'tests/tree_spec/test_optionswall_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_optionswall_source.py b/tests/tree_spec/test_optionswall_source.py
new file mode 100644
index 0000000..1483c27
--- /dev/null
+++ b/tests/tree_spec/test_optionswall_source.py
@@ -0,0 +1,123 @@
+"""Original options-wall projection must fail closed on source/candidate drift."""
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
+ROOT=Path(__file__).resolve().parents[2]
+SOURCE=Path(os.environ.get('TR_TREE_SOURCE_ROOT','C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'))
+RUNTIME=ROOT/'trading_system/tree_replay/_vendor/optionswall.py'
+
+
+def api():
+    name='trading_system.tree_spec.optionswall_source'
+    assert importlib.util.find_spec(name) is not None,'options auditor missing'
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch,path,transform):
+    original=Path.read_text
+    def read(p,*a,**kw):
+        s=original(p,*a,**kw)
+        return transform(s) if p.resolve()==path.resolve() else s
+    monkeypatch.setattr(Path,'read_text',read)
+
+
+def test_original_module_verified_with_false_readiness():
+    r=api().audit_optionswall_source(SOURCE)
+    assert r['source_subset_verified'] and r['status']=='VERIFIED' and r['blockers']==[]
+    assert r['checked_projections']==['optionswall']
+    assert not r['ready_for_replay'] and not r['ready_for_training']
+
+
+@pytest.mark.parametrize('old,new',[
+    ('from io import StringIO','from io import StringIO\nimport urllib.request'),
+    ('MAX_QUOTE_AGE_MIN = 45.0','MAX_QUOTE_AGE_MIN = 60.0'),
+    ('MAX_ANCHOR_GAP_MIN = 75.0','MAX_ANCHOR_GAP_MIN = 90.0'),
+    ("'OANDA:XAUUSD': 'GLD'","'GC': 'GLD'"),
+    ('@dataclass(frozen=True)','@dataclass(frozen=False)'),
+    ('math.isfinite(result)','True'),
+    ('self.source = source','self.source = None'),
+    ("spot: float)","spot: int)"),
+    ('files = sorted(self.source.list_reports())','files = list(self.source.list_reports())'),
+    ('self.source.read_report(files[-1])','self.source.read_report(files[0])'),
+    ("permission != 'realtime_permission'","permission != 'delayed'"),
+    ('pd.Timestamp(self.source.now_utc())',"pd.Timestamp.now(tz='UTC')"),
+    ('age_min < -2','age_min <= -2'),
+    ('age_min > MAX_QUOTE_AGE_MIN','age_min >= MAX_QUOTE_AGE_MIN'),
+    ('idx <= market_asof','idx < market_asof'),
+    ("src.fillna('').astype(str).eq(symbol)",'True'),
+    ("usable.sort_values('_ts').iloc[-1]","usable.sort_values('_ts').iloc[0]"),
+    ('gap > MAX_ANCHOR_GAP_MIN','gap >= MAX_ANCHOR_GAP_MIN'),
+    ('ratio = under_spot / etf_spot','ratio = _current_spot / etf_spot'),
+    ('>= market_day','> market_day'),
+    ("ZoneInfo('America/New_York')","ZoneInfo('UTC')"),
+    ("calls[0].get('strike')","calls[-1].get('strike')"),
+    ('except (json.JSONDecodeError, OSError):','except Exception:'),
+    ('self.status(symbol, spot).walls','None'),
+])
+def test_candidate_semantic_changes_block(monkeypatch,old,new):
+    m=api(); assert old in RUNTIME.read_text(encoding='utf-8')
+    intercept(monkeypatch,RUNTIME,lambda s:s.replace(old,new))
+    r=m.audit_optionswall_source(SOURCE)
+    assert not r['source_subset_verified'] and 'VENDOR_AST_MISMATCH' in r['blockers']
+
+
+@pytest.mark.parametrize('fault',['head','root','baseline','blob'])
+def test_identity_not_redefined_by_candidate(monkeypatch,fault):
+    m=api()
+    if fault=='blob':
+        intercept(monkeypatch,SOURCE/'chart-desk/chartdesk/optionswall.py',lambda s:s+'\n# drift\n')
+        want='SOURCE_BLOB_MISMATCH'
+    elif fault=='baseline':
+        intercept(monkeypatch,ROOT/'configs/trees/existing-alerts-baseline.json',lambda s:s.replace('68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9','0'*40))
+        want='BASELINE_COMMIT_MISMATCH'
+    else:
+        arg,value,want=('HEAD','0'*40,'SOURCE_COMMIT_MISMATCH') if fault=='head' else ('--show-toplevel',str(SOURCE),'NOT_REPOSITORY_ROOT')
+        original=m._git
+        monkeypatch.setattr(m,'_git',lambda p,*a:value if a==(arg,) else original(p,*a))
+    r=m.audit_optionswall_source(SOURCE)
+    assert not r['source_subset_verified'] and want in r['blockers']
+
+
+@pytest.mark.parametrize('fault',['global','import','signature','duplicate','order','substitution','syntax'])
+def test_projection_has_literal_source_contract(fault):
+    m=api(); text=(SOURCE/'chart-desk/chartdesk/optionswall.py').read_text(encoding='utf-8')
+    if fault=='global': text=text.replace('report-*.json','different-*.json')
+    elif fault=='import': text=text.replace('import glob','import glob as changed')
+    elif fault=='signature': text=text.replace('spot: float)', 'spot: int)')
+    elif fault=='duplicate': text+='\ndef load(symbol, spot): pass\n'
+    elif fault=='order': text=text.replace('MAX_QUOTE_AGE_MIN = 45.0','EXTRA = 1\nMAX_QUOTE_AGE_MIN = 45.0')
+    elif fault=='substitution': text=text.replace('glob.glob(REPORTS)','glob.glob(OTHER)')
+    else: text+='\ndef syntax error'
+    with pytest.raises((ValueError,SyntaxError)): m._projection(text)
+
+
+def test_missing_source_and_candidate_block(tmp_path,monkeypatch):
+    m=api()
+    for root in [None,tmp_path]:
+        r=m.audit_optionswall_source(root)
+        assert not r['source_subset_verified'] and r['blockers']
+    monkeypatch.setattr(m,'RUNTIME',tmp_path/'missing.py')
+    assert 'VENDOR_UNREADABLE:FileNotFoundError' in m.audit_optionswall_source(SOURCE)['blockers']
+
+
+def test_cli_and_forbidden_imports(tmp_path):
+    api()
+    for root,code in [(SOURCE,0),(tmp_path,2)]:
+        p=subprocess.run([sys.executable,'-B',str(ROOT/'tools/check_optionswall_source_parity.py'),'--source-root',str(root)],cwd=tmp_path,capture_output=True,text=True,timeout=45)
+        assert p.returncode==code,p.stderr
+        r=json.loads(p.stdout)
+        assert r['source_subset_verified']==(code==0)
+        assert not r['ready_for_replay'] and not r['ready_for_training']
+    code='\n'.join(['import sys','class Guard:','    def find_spec(self,fullname,*a):',
+        "        if fullname.startswith(('chartdesk','floor','trading_system.tree_replay')): raise AssertionError(fullname)",
+        'sys.meta_path.insert(0,Guard())','from trading_system.tree_spec.optionswall_source import audit_optionswall_source',
+        "assert audit_optionswall_source(sys.argv[1])['source_subset_verified']"])
+    p=subprocess.run([sys.executable,'-B','-c',code,str(SOURCE)],cwd=ROOT,capture_output=True,text=True,timeout=45)
+    assert p.returncode==0,p.stderr

warning: in the working copy of 'tools/check_optionswall_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_optionswall_source_parity.py b/tools/check_optionswall_source_parity.py
new file mode 100644
index 0000000..33e6bba
--- /dev/null
+++ b/tools/check_optionswall_source_parity.py
@@ -0,0 +1,23 @@
+"""Read-only full options context source projection audit."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None,''):
+    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.optionswall_source import audit_optionswall_source
+
+
+def main():
+    parser=argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--source-root',type=Path,required=True)
+    args=parser.parse_args()
+    result=audit_optionswall_source(args.source_root)
+    print(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2))
+    return 0 if result['source_subset_verified'] else 2
+
+
+if __name__=='__main__':
+    raise SystemExit(main())

