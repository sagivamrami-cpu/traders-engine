# Options reader Task1

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; three full untracked additions.

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
index 0000000..68131b3
--- /dev/null
+++ b/tests/tree_replay/test_optionswall.py
@@ -0,0 +1,186 @@
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

