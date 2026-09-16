# Task1 untracked additions against HEAD c1b6071

diff --git a/trading_system/tree_replay/_vendor/revalidation.py b/trading_system/tree_replay/_vendor/revalidation.py
new file mode 100644
index 0000000..1c7cd69
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/revalidation.py
@@ -0,0 +1,281 @@
+"""Original pending-plan checks over offline ports; not full causal replay."""
+from __future__ import annotations
+import json
+import pandas as pd
+from pathlib import PurePosixPath
+from . import lifecycle_voice as voice
+from . import admission_matrix, pvsra, watch_sessions
+from .tracker_admission import TrackerAdmission
+from .stretch import StretchReader
+from .ema_windows import EmaReader
+AGED_PENDING_RECHECK_H = 2.0
+_BIAS_AGAINST_AS_SENT = voice.check('ההטיה הגבוהה נגד העסקה — כך גם בשליחה', False)
+_BIAS_AGAINST_FLAT_AT_SEND = voice.check('ההטיה הגבוהה נגד העסקה — בשליחה הייתה ניטרלית', False)
+_BIAS_AGAINST_UNREAD = voice.check('ההטיה הגבוהה נגד העסקה — בשליחה לא נקראה', False)
+SOFT_STALE_MIN = 20.0
+HARD_STALE_MIN = 120.0
+
+def calendar_event_ts(ev: dict) -> float | None:
+    """Seconds since epoch for a calendar row, or None. ONE implementation.
+
+    THE BLACKOUT NEVER FIRED. Until 2026-09-01 the gate read
+    `e.get("dateline")` -- a field the cached ForexFactory feed does not have.
+    Verified against the live cache: 0 of 112 rows carried it; all 112 carry
+    `date`, ISO with an offset. Every event scored 0, the +/-15 minute test was
+    never true, and the desk traded through every High-impact print while
+    logging that it had checked.
+
+    It lives here, module level, because the first fix put a copy in
+    liveness.py too and the scanner flagged the duplicate within the minute --
+    correctly. Two readers of one feed format is how one gets fixed and the
+    other silently keeps the old shape. `dateline` stays as a fallback in case
+    the upstream feed restores it.
+    """
+    from datetime import datetime as _d
+    raw = ev.get('dateline')
+    if isinstance(raw, (int, float)) and raw and (not isinstance(raw, bool)):
+        return float(raw)
+    txt = ev.get('date')
+    if not txt:
+        return None
+    try:
+        return _d.fromisoformat(str(txt)).timestamp()
+    except (ValueError, TypeError):
+        return None
+
+def calendar_high_impact_in_window(events: list[dict], now_ts: float, window_s: float) -> dict | None:
+    """Return the High-impact row inside ``window_s``, if one exists.
+
+    This is the one firing condition for the cached ForexFactory shape. The
+    trade plan, tree, and revalidation shadow used to each read the feed on
+    their own; one asked for the nonexistent ``dateline`` field and silently
+    stayed false forever. Consumers may choose different windows, but they do
+    not get to invent different field names.
+    """
+    for event in events:
+        ts = calendar_event_ts(event)
+        if ts is None or abs(ts - now_ts) > window_s:
+            continue
+        impact = event.get('impact')
+        if not isinstance(impact, str) or not impact.strip():
+            raise ValueError('calendar event inside blackout window has no impact')
+        if impact.lower().startswith('high'):
+            return event
+    return None
+
+def _bias_against(nets: dict, short: bool) -> bool:
+    """Every higher frame siding against the trade, and with weight.
+
+    A FLIP SHOWS ON EVERY HIGHER TIMEFRAME, NOT IN AN AVERAGE. Summing let
+    one timeframe outvote the other: on 2026-08-31 the BTC short carried 4h
+    +43 and 1h -2, so the sum read +41 and the veto cancelled a filled,
+    profitable position while the 1h agreed with the trade. Two timeframes
+    pointing opposite ways is uncertainty, not a flip, and the tree may not
+    veto on its own uncertainty -- so no higher frame may still side with
+    the trade.
+    """
+    vals = [float(x) for x in (nets or {}).values()]
+    if not vals:
+        return False
+    net = sum(vals)
+    worst = min(vals) if short else max(vals)
+    return net >= 25.0 and short and (worst >= 0.0) or (net <= -25.0 and (not short) and (worst <= 0.0))
+
+class Revalidation:
+
+    def __init__(self, source):
+        self.source = source
+        self.admission = TrackerAdmission(source)
+        self.stretch = StretchReader(source)
+        self.ema = EmaReader(source)
+
+    def _tree_agrees(self, symbol: str, direction: str) -> tuple[bool, str]:
+        """Does the decision tree still reach a trade, on this side, right now?
+
+    Consulted but NOT given a veto on its own: measured over 26-27.08 the
+    tree's verdict split outcomes 39% vs 40%, no demonstrated edge either way,
+    so it reports and the caller decides. When the tree cannot run at all this
+    returns True -- a broken tree must not silently block every revival, which
+    is exactly the shape of failure this repo keeps producing.
+    """
+        try:
+            w = self.source.tree_walk(symbol)
+            if w is None:
+                return (True, 'העץ לא החזיר תשובה')
+            if w.direction and w.direction != direction:
+                return (False, f'העץ מצביע לכיוון ההפוך ({w.direction})')
+            if w.stopped_because:
+                return (True, f'העץ נעצר ב-{w.reached}: {w.stopped_because}')
+            return (True, 'העץ מאשר')
+        except Exception as e:
+            return (True, f'העץ לא זמין ({type(e).__name__})')
+
+    def revalidate_pending(self, t: dict, *, now: float | None=None) -> tuple[bool, str, bool]:
+        """Fill-time recheck; aged plans also need a non-opposing current tree.
+
+    This does not build or send a new trade. It decides whether an old plan
+    may transition PENDING->OPEN when its entry zone is finally reached.
+    """
+        ok, why, verified = self.still_valid(t)
+        if not ok:
+            return (ok, why, verified)
+        now = self.source.now_epoch() if now is None else now
+        try:
+            age_h = max(0.0, (now - float(t['ts'])) / 3600.0)
+        except (KeyError, TypeError, ValueError):
+            return (True, why, False)
+        if age_h < AGED_PENDING_RECHECK_H:
+            return (True, why, verified)
+        tree_ok, tree_note = self._tree_agrees(t['symbol'], t['direction'])
+        if not tree_ok:
+            return (False, f'בדיקה חוזרת אחרי {age_h:.1f} שעות: {tree_note}', True)
+        clean = tree_note == 'העץ מאשר'
+        note = f'בדיקה חוזרת אחרי {age_h:.1f} שעות: {tree_note}'
+        return (True, '\n'.join((x for x in (why, note) if x)), bool(verified and clean))
+
+    def _shadow(self, symbol: str, name: str, fired: bool, detail: str) -> None:
+        """Record what a not-yet-enabled check WOULD have done.
+
+    The four new checks Sagiv asked for have never been measured on this
+    tape. Giving them veto power immediately risks trading one failure
+    (entering on a dead thesis) for a worse one (cancelling everything and
+    publishing nothing). So they run, they write here, and they do not vote
+    until the log says how often they fire.
+    """
+        try:
+            self.source.ensure_shadow_parent(parents=True, exist_ok=True)
+            with self.source.shadow_open('a', encoding='utf-8') as fh:
+                fh.write(json.dumps({'ts': self.source.now_epoch(), 'symbol': symbol, 'check': name, 'would_block': bool(fired), 'detail': detail}, ensure_ascii=False) + '\n')
+        except Exception:
+            pass
+
+    def still_valid(self, t: dict) -> tuple[bool, str, bool]:
+        """Is the thesis behind a PENDING trade still alive at fill time?
+
+    Sagiv, 2026-08-26: *"אם הגיעו יש בחינה מחדש אם היא עדיין רלוונטית?"* --
+    it did not. A trade sent at 09:00 and filled at 20:00 was opened on the
+    09:00 thesis with no re-read, which is how a signal channel ends up long
+    into a tape that turned hours earlier.
+
+    Returns (ok, reason_when_not, verified).
+
+    `verified` is the third value because the honest answer has three states,
+    not two: the thesis holds, the thesis broke, or we could not tell. The
+    first version collapsed the third into the first -- `except: return True`
+    -- so a dead feed produced a confident "still valid" and the caller had no
+    way to know the check had not run. That silence is the project's signature
+    bug, and it was found here again on 2026-08-30 review.
+
+    VETOING checks (measured or mechanical, allowed to cancel a trade):
+      1. Higher-timeframe bias must not have FLIPPED against the trade. Bias
+         decaying to neutral is tolerated -- a retest into a flat tape is
+         still the trade that was sent; a bias that inverted is not.
+      2. The tape must not now be extended in the trade's own direction.
+      3. Evidence must not be older than HARD_STALE_MIN.
+
+    SHADOW checks (run, logged, no vote yet -- see _shadow): EMA stack side,
+    market structure, session/event window, and whether the stop is still a
+    sane distance from the live entry.
+    """
+        symbol = t.get('symbol', '?')
+        short = t['direction'] == 'שורט'
+        verified = True
+        label = ''
+        try:
+            nets = self.admission._higher_bias(symbol)
+            if nets is None:
+                raise RuntimeError('matrix.read_symbol returned nothing')
+            net = sum(nets.values())
+            if _bias_against(nets, short):
+                sent = t.get('bias_at_send') or {}
+                sent_net = sum((float(x) for x in sent.values())) if sent else None
+                with_trade_at_send = sent_net is not None and (sent_net < 0 if short else sent_net > 0)
+                if with_trade_at_send:
+                    return (False, f'ההטיה הגבוהה התהפכה מאז השליחה ({net:+.0f})', True)
+                if not sent:
+                    label = _BIAS_AGAINST_UNREAD
+                elif sent_net == 0:
+                    label = _BIAS_AGAINST_FLAT_AT_SEND
+                else:
+                    label = _BIAS_AGAINST_AS_SENT
+            st = self.stretch.state(symbol)
+            if st is None:
+                verified = False
+                self._shadow(symbol, 'stretch', False, 'stretch.state() returned None')
+            if st and st.is_extended and st.side:
+                if (st.side == 'up') != short:
+                    return (False, f'הטווח היומי כבר נוצל לכיוון העסקה ({st.budget_used * 100:.0f}% מה-ADR) — הכניסה איחרה', True)
+        except Exception as exc:
+            verified = False
+            self._shadow(symbol, 'core', False, f'core checks unavailable: {exc}')
+        age_min = None
+        try:
+            worst_ratio = None
+            for tf, bar_min in (('15m', 15.0), ('1h', 60.0), ('4h', 240.0)):
+                _df, _c = self.source.fetch_corrected(symbol, tf, 3)
+                if _df is None or not len(_df):
+                    continue
+                last = _df.index[-1]
+                a = (self.source.now_timestamp(tz=last.tz) - last).total_seconds() / 60.0
+                ratio = a / (bar_min / 15.0)
+                if worst_ratio is None or ratio > worst_ratio:
+                    worst_ratio, age_min = (ratio, ratio)
+        except Exception:
+            age_min = None
+        if age_min is not None and age_min > HARD_STALE_MIN:
+            return (False, f'אין נתונים לאימות מחדש — הנר האחרון בן {age_min:.0f} דקות. לא נכנסים על תזה שלא ניתן לבדוק.', False)
+        if age_min is None or age_min > SOFT_STALE_MIN:
+            verified = False
+        try:
+            stack = self.ema.read_stack(symbol, timeframes=('1h', '15m'))
+            for tf, es in (stack or {}).items():
+                if es is None:
+                    continue
+                w = es.window(50)
+                if w is None:
+                    continue
+                above = es.close > w.value
+                against = above if short else not above
+                self._shadow(symbol, f'ema50_{tf}', against, f'close {es.close:.2f} vs ema50 {w.value:.2f}, short={short}')
+        except Exception as exc:
+            self._shadow(symbol, 'ema', False, f'unavailable: {exc}')
+        try:
+            cur = watch_sessions.current_session_at(decision_time=self.source.now_timestamp(tz='UTC'))
+            self._shadow(symbol, 'session', not bool(cur), f'sessions={cur}')
+        except Exception as exc:
+            self._shadow(symbol, 'session', False, f'unavailable: {exc}')
+        try:
+            entry, stop = (float(t['entry']), float(t['stop']))
+            risk = abs(entry - stop)
+            self._shadow(symbol, 'stop_distance', risk <= 0, f'entry {entry:.2f} stop {stop:.2f} risk {risk:.2f}')
+        except Exception as exc:
+            self._shadow(symbol, 'stop_distance', False, f'unavailable: {exc}')
+        try:
+            _d4, _ = self.source.fetch_corrected(symbol, '4h', 400)
+            stru = admission_matrix.read_structure(_d4)
+            against = stru.direction != 0 and (stru.direction < 0 if not short else stru.direction > 0)
+            self._shadow(symbol, 'structure_4h', bool(against), f'structure dir {stru.direction}, short={short}')
+        except Exception as exc:
+            self._shadow(symbol, 'structure_4h', False, f'unavailable: {exc}')
+        try:
+            _d15, _ = self.source.fetch_corrected(symbol, '15m', 60)
+            _p = pvsra.pvsra(_d15).tail(12)
+            opp = {'red', 'violet'} if not short else {'green', 'blue'}
+            fired = bool(_p['kind'].isin(opp).any())
+            self._shadow(symbol, 'opposing_vector_15m', fired, f"last12 kinds={list(_p['kind'].tail(4))}")
+        except Exception as exc:
+            self._shadow(symbol, 'opposing_vector_15m', False, f'unavailable: {exc}')
+        try:
+            import json as _json
+            from datetime import datetime as _dt, timezone as _tz, timedelta as _td
+            _cal = PurePosixPath('news-desk') / 'data' / 'ff_calendar.json'
+            if not self.source.calendar_exists(_cal.as_posix()):
+                self._shadow(symbol, 'news_window', False, 'calendar file missing')
+            else:
+                _now = self.source.now_utc()
+                _event = calendar_high_impact_in_window(_json.loads(self.source.calendar_text(_cal.as_posix())), _now.timestamp(), 30 * 60)
+                _title = _event.get('title', '?') if _event is not None else None
+                self._shadow(symbol, 'news_window', _event is not None, f'inside ±30m of: {_title}' if _event is not None else 'clear')
+        except Exception as exc:
+            self._shadow(symbol, 'news_window', False, f'unavailable: {exc}')
+        return (True, label, verified)

diff --git a/tests/tree_replay/test_revalidation.py b/tests/tree_replay/test_revalidation.py
new file mode 100644
index 0000000..e6e7d51
--- /dev/null
+++ b/tests/tree_replay/test_revalidation.py
@@ -0,0 +1,496 @@
+"""Original pending revalidation: raw calendar semantics and real input calculations."""
+from contextlib import contextmanager
+import importlib
+import importlib.util
+import io
+import json
+import math
+from types import SimpleNamespace
+
+import pandas as pd
+import numpy as np
+import pytest
+
+from trading_system.tree_replay._vendor.admission_matrix import read_frame
+from trading_system.tree_replay._vendor.correction import Correction, broker_shape_ok_at
+
+
+NOW = pd.Timestamp('2026-09-09T16:00:00Z')
+SYMBOL = 'OANDA:XAUUSD'
+LONG, SHORT = 'לונג', 'שורט'
+
+
+def api():
+    name = 'trading_system.tree_replay._vendor.revalidation'
+    assert importlib.util.find_spec(name) is not None, 'revalidation missing'
+    return importlib.import_module(name)
+
+
+def bars(n=100, *, step=1., end=NOW):
+    close = [200.+step*i for i in range(n)]
+    return pd.DataFrame({'open':close, 'high':[x+1 for x in close],
+        'low':[x-1 for x in close], 'close':close, 'volume':1.},
+        index=pd.date_range(end=end, periods=n, freq='15min'))
+
+
+def daily():
+    return pd.DataFrame({'open':100., 'high':110., 'low':90., 'close':100., 'volume':1.},
+        index=pd.date_range(end=NOW.normalize(), periods=22, freq='D'))
+
+
+def trade(direction=LONG, age_s=60.):
+    return dict(symbol=SYMBOL, direction=direction, entry=100., stop=95.,
+                ts=NOW.timestamp()-age_s, bias_at_send={'4h':1., '1h':1.})
+
+
+class Ports:
+    """Offline boundary replies; matrix/EMA/stretch/PVSRA/JSON stay real."""
+    def __init__(self):
+        self.frames = {(tf,days): bars() for tf,days in [
+            ('15m',20),('1h',60),('4h',240),('15m',3),('1h',3),('4h',3),
+            ('1h',2000),('15m',2000),('4h',400),('15m',60)]}
+        self.frames['1d',400] = daily()
+        self.bias_frames = {'4h':bars(60), '1h':bars(60)}
+        self.corr = Correction(SYMBOL,0.,'tv_daily','high','synthetic')
+        self.calls = []
+        self.shadow_text = ''
+        self.calendar = '[]'
+        self.walk = SimpleNamespace(direction=LONG, stopped_because='', reached='TARGET')
+        self.now = NOW
+        self.shadow_fault = None
+
+    def fetch_corrected(self,symbol,tf,lookback):
+        self.calls.append(('fetch',symbol,tf,lookback))
+        assert symbol == SYMBOL
+        value = self.frames[tf,lookback]
+        if isinstance(value,Exception): raise value
+        return value,self.corr
+
+    def read_symbol(self,symbol,tfs):
+        self.calls.append(('matrix',symbol,tfs))
+        assert symbol == SYMBOL
+        return {tf:read_frame(self.bias_frames[tf],tf) for tf in tfs if tf in self.bias_frames}
+
+    def broker_shape_ok(self,correction,days):
+        self.calls.append(('shape',days))
+        return broker_shape_ok_at(correction,days,decision_time=self.now)
+
+    def deep_exists(self,key):
+        self.calls.append(('deep_exists',key))
+        return False
+
+    def deep_bytes(self,key):
+        raise AssertionError('absent deep file must not be read')
+
+    def now_epoch(self):
+        self.calls.append(('epoch',))
+        if self.shadow_fault == 'clock': raise OSError('captured clock failure')
+        return self.now.timestamp()
+
+    def now_timestamp(self,*,tz):
+        self.calls.append(('timestamp',str(tz)))
+        return self.now.tz_convert(tz)
+
+    def now_utc(self):
+        self.calls.append(('utc',))
+        return self.now.to_pydatetime()
+
+    def tree_walk(self,symbol):
+        self.calls.append(('walk',symbol))
+        if isinstance(self.walk,Exception): raise self.walk
+        return self.walk
+
+    def ensure_shadow_parent(self,*,parents,exist_ok):
+        self.calls.append(('shadow_parent',parents,exist_ok))
+        if self.shadow_fault == 'parent': raise OSError('captured parent failure')
+
+    @contextmanager
+    def shadow_open(self,mode,encoding):
+        self.calls.append(('shadow_open',mode,encoding))
+        if self.shadow_fault == 'open': raise OSError('captured open failure')
+        owner = self
+        class Buffer(io.StringIO):
+            def write(self,value):
+                if owner.shadow_fault == 'write': raise OSError('captured write failure')
+                return super().write(value)
+        buffer = Buffer()
+        try:
+            yield buffer
+        finally:
+            self.shadow_text += buffer.getvalue()
+            buffer.close()
+            self.calls.append(('shadow_close',))
+            if self.shadow_fault == 'close': raise OSError('captured close failure')
+
+    def calendar_exists(self,key):
+        self.calls.append(('calendar_exists',key))
+        return self.calendar is not None
+
+    def calendar_text(self,key):
+        self.calls.append(('calendar_text',key))
+        if isinstance(self.calendar,Exception): raise self.calendar
+        return self.calendar
+
+    def shadows(self):
+        return [json.loads(line) for line in self.shadow_text.splitlines()]
+
+
+@pytest.mark.parametrize('event,want',[
+    ({'dateline':17,'date':'invalid'},17.),
+    ({'dateline':-3},-3.),
+    ({'dateline':True,'date':'2026-01-01T00:00:00Z'},1767225600.),
+    ({'dateline':0,'date':'2026-01-01T02:00:00+02:00'},1767225600.),
+    ({'dateline':'17','date':'2026-01-01T00:00:00Z'},1767225600.),
+    ({'date':'invalid'},None),({},None),({'dateline':False},None),
+])
+def test_calendar_numeric_precedence_and_original_fallback(event,want):
+    assert api().calendar_event_ts(event) == want
+
+
+def test_calendar_raw_nonfinite_values_are_not_sanitized():
+    m = api()
+    assert math.isnan(m.calendar_event_ts({'dateline':float('nan')}))
+    assert m.calendar_event_ts({'dateline':float('inf')}) == float('inf')
+
+
+def test_news_window_inclusive_first_match_identity_not_nearest_or_sorted():
+    m = api()
+    first = {'dateline':1180,'impact':'HIGH impact','title':'first'}
+    closer = {'dateline':1001,'impact':'High','title':'closer'}
+    assert m.calendar_high_impact_in_window([first,closer],1000.,180.) is first
+    assert m.calendar_high_impact_in_window([first],1000.,179.999) is None
+    assert m.calendar_high_impact_in_window([first],1000.,-1.) is None
+
+
+def test_news_missing_impact_raises_only_inside_and_leading_space_is_not_high():
+    m = api()
+    with pytest.raises(ValueError,match='no impact'):
+        m.calendar_high_impact_in_window([{'dateline':1000}],1000.,180.)
+    assert m.calendar_high_impact_in_window([{'dateline':1}],1000.,180.) is None
+    assert m.calendar_high_impact_in_window([{'dateline':1000,'impact':' High'}],1000.,180.) is None
+
+
+@pytest.mark.parametrize('nets,short,want',[
+    ({'4h':43.,'1h':-2.},True,False),({'4h':25.,'1h':0.},True,True),
+    ({'4h':24.999,'1h':0.},True,False),({'4h':-25.,'1h':0.},False,True),
+    ({'4h':-43.,'1h':2.},False,False),({},True,False),
+])
+def test_bias_requires_magnitude_and_each_frame_against_not_sum_alone(nets,short,want):
+    assert api()._bias_against(nets,short) is want
+
+
+@pytest.mark.parametrize('direction,step',[(LONG,1.),(SHORT,-1.)])
+def test_real_calculations_clean_tape_keeps_all_shadows_observational(direction,step):
+    m = api()
+    p = Ports()
+    p.bias_frames = {'4h':bars(60,step=step),'1h':bars(60,step=step)}
+    t = trade(direction)
+    ok,why,verified = m.Revalidation(p).still_valid(t)
+    assert (ok,why,verified) == (True,'',True)
+    rows = p.shadows()
+    assert [r['check'] for r in rows] == ['ema50_1h','ema50_15m','session',
+        'stop_distance','structure_4h','opposing_vector_15m','news_window']
+    assert all(r['ts'] == NOW.timestamp() and r['symbol'] == SYMBOL for r in rows)
+    assert rows[-1]['detail'] == 'clear' and rows[-1]['would_block'] is False
+    assert ('fetch',SYMBOL,'1d',400) in p.calls and ('shape',20) in p.calls
+    assert ('calendar_text','news-desk/data/ff_calendar.json') in p.calls
+    if direction == SHORT:
+        assert rows[0]['would_block'] is True  # Rising EMA shadow does not veto.
+
+
+def test_actual_higher_bias_flip_cancels_before_stretch_age_and_shadow_reads():
+    m = api()
+    p = Ports()
+    p.bias_frames = {'4h':bars(60,step=-1.),'1h':bars(60,step=-1.)}
+    ok,why,verified = m.Revalidation(p).still_valid(trade())
+    assert not ok and verified and 'התהפכה מאז השליחה' in why
+    assert p.calls == [('matrix',SYMBOL,('4h','1h'))]
+    assert p.shadow_text == ''
+
+
+@pytest.mark.parametrize('sent,label',[
+    ({'4h':-1.,'1h':-1.},'כך גם בשליחה'),
+    ({'4h':1.,'1h':-1.},'בשליחה הייתה ניטרלית'),
+    ({},'בשליחה לא נקראה'),
+])
+def test_against_bias_without_actual_flip_is_a_label_not_cancellation(sent,label):
+    m = api()
+    p = Ports()
+    p.bias_frames = {'4h':bars(60,step=-1.),'1h':bars(60,step=-1.)}
+    t = trade()
+    t['bias_at_send'] = sent
+    ok,why,verified = m.Revalidation(p).still_valid(t)
+    assert ok and verified and label in why and p.shadows()
+
+
+@pytest.mark.parametrize('age_min,ok,verified',[
+    (0.,True,True),(20.,True,True),(20.001,True,False),
+    (120.,True,False),(120.001,False,False),(-1.,True,True),
+])
+def test_freshness_exact_soft_hard_and_future_boundaries(age_min,ok,verified):
+    m = api()
+    p = Ports()
+    p.frames['15m',3] = bars(end=NOW-pd.Timedelta(minutes=age_min))
+    result = m.Revalidation(p).still_valid(trade())
+    assert (result[0],result[2]) == (ok,verified)
+    assert bool(p.shadows()) is ok
+
+
+def test_four_hour_age_is_normalized_to_own_frame_size():
+    m = api()
+    p = Ports()
+    p.frames['4h',3] = bars(end=NOW-pd.Timedelta(minutes=90))
+    assert m.Revalidation(p).still_valid(trade()) == (True,'',True)
+    p.frames['4h',3] = bars(end=NOW-pd.Timedelta(minutes=1921))
+    ok,why,verified = m.Revalidation(p).still_valid(trade())
+    assert not ok and not verified and 'אין נתונים' in why
+
+
+@pytest.mark.parametrize('fault,want',[('one_empty',True),('all_empty',False),('later_error',False)])
+def test_empty_age_is_skipped_but_exception_resets_prior_evidence(fault,want):
+    m = api()
+    p = Ports()
+    if fault == 'one_empty': p.frames['1h',3] = None
+    elif fault == 'all_empty':
+        for tf in ('15m','1h','4h'): p.frames[tf,3] = pd.DataFrame()
+    else: p.frames['4h',3] = OSError('captured')
+    ok,why,verified = m.Revalidation(p).still_valid(trade())
+    assert ok and verified is want
+
+
+@pytest.mark.parametrize('calendar,detail,fired',[
+    (None,'calendar file missing',False),('broken-json','unavailable:',False),
+    (json.dumps([{'dateline':NOW.timestamp(),'impact':'High','title':'CPI'}]),'inside ±30m of: CPI',True),
+    (json.dumps([{'dateline':NOW.timestamp()}]),'unavailable:',False),
+])
+def test_news_fired_or_unavailable_is_shadow_only(calendar,detail,fired):
+    m = api()
+    p = Ports()
+    p.calendar = calendar
+    assert m.Revalidation(p).still_valid(trade()) == (True,'',True)
+    row = p.shadows()[-1]
+    assert row['check'] == 'news_window' and row['would_block'] is fired
+    assert detail in row['detail']
+
+
+@pytest.mark.parametrize('fault',['parent','open','clock','write','close'])
+def test_shadow_writer_failures_remain_best_effort(fault):
+    m = api()
+    p = Ports()
+    p.shadow_fault = fault
+    assert m.Revalidation(p).still_valid(trade()) == (True,'',True)
+
+
+@pytest.mark.parametrize('age,walks',[(7199.,False),(7200.,True),(-1.,False)])
+def test_pending_exact_two_hour_recheck_boundary(age,walks):
+    m = api()
+    p = Ports()
+    ok,why,verified = m.Revalidation(p).revalidate_pending(trade(age_s=age),now=NOW.timestamp())
+    assert ok and verified
+    assert (('walk',SYMBOL) in p.calls) is walks
+    assert ('העץ מאשר' in why) is walks
+
+
+@pytest.mark.parametrize('walk,ok,verified,note',[
+    (None,True,False,'לא החזיר תשובה'),
+    (OSError('captured'),True,False,'לא זמין (OSError)'),
+    (SimpleNamespace(direction=LONG,stopped_because='missing',reached='DATA'),True,False,'נעצר ב-DATA'),
+    (SimpleNamespace(direction=SHORT,stopped_because='missing',reached='DATA'),False,True,'לכיוון ההפוך'),
+])
+def test_pending_tree_boundary_precedence_and_unknown_states(walk,ok,verified,note):
+    m = api()
+    p = Ports()
+    p.walk = walk
+    result = m.Revalidation(p).revalidate_pending(trade(age_s=7200.),now=NOW.timestamp())
+    assert (result[0],result[2]) == (ok,verified) and note in result[1]
+
+
+@pytest.mark.parametrize('stamp',[None,'invalid'])
+def test_invalid_send_time_allows_unverified_without_tree(stamp):
+    m = api()
+    p = Ports()
+    t = trade()
+    t['ts'] = stamp
+    assert m.Revalidation(p).revalidate_pending(t,now=NOW.timestamp()) == (True,'',False)
+    assert ('walk',SYMBOL) not in p.calls
+
+
+@pytest.mark.parametrize('direction,close,high,low,blocked',[
+    (LONG,116.,126.,100.,True),(SHORT,84.,100.,74.,True),
+    (LONG,84.,100.,74.,False),(SHORT,116.,126.,100.,False),
+])
+def test_actual_extension_veto_applies_only_in_trade_direction(direction,close,high,low,blocked):
+    m = api()
+    p = Ports()
+    p.frames['1d',400].iloc[-1] = [100.,high,low,close,1.]
+    p.bias_frames = {'4h':bars(60,step=1. if direction == LONG else -1.),
+                     '1h':bars(60,step=1. if direction == LONG else -1.)}
+    ok,why,verified = m.Revalidation(p).still_valid(trade(direction))
+    assert ok is (not blocked) and verified
+    if blocked:
+        assert '130% מה-ADR' in why
+        assert not p.shadows()
+        assert [c[2:] for c in p.calls if c[0]=='fetch'] == [
+            ('1d',400),('15m',20),('1h',60),('4h',240)]
+    else:
+        assert p.shadows()[-1]['check'] == 'news_window'
+
+
+@pytest.mark.parametrize('fault,check',[('missing_higher','core'),('empty_daily','stretch'),('failed_daily','stretch')])
+def test_unavailable_core_is_logged_and_does_not_claim_verified(fault,check):
+    m = api()
+    p = Ports()
+    if fault == 'missing_higher': del p.bias_frames['1h']
+    elif fault == 'empty_daily': p.frames['1d',400] = pd.DataFrame()
+    else: p.frames['1d',400] = OSError('captured daily failure')
+    assert m.Revalidation(p).still_valid(trade()) == (True,'',False)
+    rows = p.shadows()
+    assert rows[0]['check'] == check and rows[0]['would_block'] is False
+    assert rows[-1]['check'] == 'news_window'
+
+
+def test_missing_direction_raises_before_any_source_operations():
+    m = api()
+    p = Ports()
+    with pytest.raises(KeyError,match='direction'):
+        m.Revalidation(p).still_valid({'symbol':SYMBOL})
+    assert p.calls == []
+
+
+@pytest.mark.parametrize('direction,offset,fired',[
+    (LONG,12,True),(LONG,13,False),(SHORT,12,True),(SHORT,13,False),
+])
+def test_actual_opposing_pvsra_uses_only_last_twelve_bars(direction,offset,fired):
+    m = api()
+    p = Ports()
+    f = bars(60)
+    # Background climax direction agrees; one opposing bar has triple volume.
+    f['open'] = f['close']+(.5 if direction == SHORT else -.5)
+    f.iloc[-offset,f.columns.get_loc('open')] = f['close'].iloc[-offset]+(.5 if direction == LONG else -.5)
+    f.iloc[-offset,f.columns.get_loc('volume')] = 3.
+    p.frames['15m',60] = f
+    assert m.Revalidation(p).still_valid(trade(direction))[0] is True
+    row = next(r for r in p.shadows() if r['check']=='opposing_vector_15m')
+    assert row['would_block'] is fired
+
+
+def test_actual_bearish_structure_and_zero_risk_remain_shadow_only():
+    m = api()
+    p = Ports()
+    prices = np.interp(np.arange(24),[0,3,9,15,20,23],[5,11,2,10,1,5])
+    f = bars(24)
+    f['open']=f['close']=prices
+    f['high'],f['low']=prices+1,prices-1
+    p.frames['4h',400]=f
+    t=trade()
+    t['stop']=t['entry']
+    assert m.Revalidation(p).still_valid(t)==(True,'',True)
+    rows={r['check']:r for r in p.shadows()}
+    assert rows['stop_distance']['would_block'] is True
+    assert rows['structure_4h']['would_block'] is True
+    assert rows['structure_4h']['detail']=='structure dir -1, short=False'
+
+
+def test_shadow_json_uses_operation_clock_and_exact_effect_order():
+    m=api()
+    p=Ports()
+    reader=m.Revalidation(p)
+    reader._shadow(SYMBOL,'בדיקה',1,'פרטים')
+    p.now=NOW+pd.Timedelta(seconds=7)
+    reader._shadow(SYMBOL,'second',0,'detail')
+    assert p.calls==[('shadow_parent',True,True),('shadow_open','a','utf-8'),
+        ('epoch',),('shadow_close',)]*2
+    assert [r['ts'] for r in p.shadows()]==[NOW.timestamp(),NOW.timestamp()+7]
+    assert [r['would_block'] for r in p.shadows()]==[True,False]
+    assert 'בדיקה' in p.shadow_text and p.shadow_text.endswith('\n')
+
+
+def test_pending_default_clock_is_read_after_shadows_and_not_on_initial_veto():
+    m=api()
+    p=Ports()
+    assert m.Revalidation(p).revalidate_pending(trade())==(True,'',True)
+    assert p.calls[-1]==('epoch',)
+    explicit=Ports()
+    m.Revalidation(explicit).revalidate_pending(trade(),now=NOW.timestamp())
+    assert explicit.calls==p.calls[:-1]
+    blocked=Ports()
+    blocked.bias_frames={'4h':bars(60,step=-1.),'1h':bars(60,step=-1.)}
+    assert m.Revalidation(blocked).revalidate_pending(trade(age_s=7200.))[0] is False
+    assert blocked.calls==[('matrix',SYMBOL,('4h','1h'))]
+
+
+def test_pending_missing_timestamp_does_not_become_cancellation():
+    m=api()
+    p=Ports()
+    t=trade()
+    del t['ts']
+    assert m.Revalidation(p).revalidate_pending(t,now=NOW.timestamp())==(True,'',False)
+    assert ('walk',SYMBOL) not in p.calls
+
+
+def test_full_fetch_order_includes_calculation_reads_before_separate_age_reads():
+    m=api()
+    p=Ports()
+    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
+    assert [c[2:] for c in p.calls if c[0]=='fetch']==[
+        ('1d',400),('15m',20),('1h',60),('4h',240),
+        ('15m',3),('1h',3),('4h',3),('1h',2000),('15m',2000),
+        ('4h',400),('15m',60)]
+    assert [c for c in p.calls if c[0]=='timestamp']==[('timestamp','UTC')]*4
+    idx=p.calls.index(('calendar_exists','news-desk/data/ff_calendar.json'))
+    assert p.calls[idx:idx+3]==[('calendar_exists','news-desk/data/ff_calendar.json'),
+        ('utc',),('calendar_text','news-desk/data/ff_calendar.json')]
+
+
+@pytest.mark.parametrize('seconds,fired',[(1800.,True),(1800.001,False),(-1800.,True),(-1800.001,False)])
+def test_actual_news_consumer_uses_iso_date_and_thirty_minute_inclusive_window(seconds,fired):
+    m=api()
+    p=Ports()
+    p.calendar=json.dumps([{'date':(NOW+pd.Timedelta(seconds=seconds)).isoformat(),
+                           'impact':'High','title':'ISO event'}])
+    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
+    row=p.shadows()[-1]
+    assert row['would_block'] is fired
+    assert row['detail']==('inside ±30m of: ISO event' if fired else 'clear')
+
+
+def test_age_probe_corrections_are_not_new_vetoes():
+    m=api()
+    class AgePorts(Ports):
+        def fetch_corrected(self,symbol,tf,lookback):
+            f,c=super().fetch_corrected(symbol,tf,lookback)
+            if lookback==3:
+                c=Correction(symbol,0.,'none','unknown','captured unavailable correction')
+                assert c.unverified
+            return f,c
+    assert m.Revalidation(AgePorts()).still_valid(trade())==(True,'',True)
+
+
+def test_closed_weekend_session_is_shadow_not_veto():
+    m=api()
+    p=Ports()
+    p.now=pd.Timestamp('2026-09-12T16:00:00Z')
+    for (tf,days),f in p.frames.items():
+        if tf!='1d': f.index=f.index+(p.now-NOW)
+    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
+    row=next(r for r in p.shadows() if r['check']=='session')
+    assert row['would_block'] is True and row['detail']=='sessions=[]'
+
+
+@pytest.mark.parametrize('frame_key,check',[(('4h',400),'structure_4h'),(('15m',60),'opposing_vector_15m')])
+def test_shadow_calculation_unavailability_is_logged_not_vetoed(frame_key,check):
+    m=api()
+    p=Ports()
+    p.frames[frame_key]=OSError('captured shadow data failure')
+    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
+    row=next(r for r in p.shadows() if r['check']==check)
+    assert row['would_block'] is False and row['detail'].startswith('unavailable:')
+
+
+def test_real_ema_stack_omits_failed_frame_but_keeps_other_shadows():
+    m=api()
+    p=Ports()
+    p.frames['1h',2000]=OSError('captured EMA data failure')
+    assert m.Revalidation(p).still_valid(trade())==(True,'',True)
+    checks=[r['check'] for r in p.shadows()]
+    assert 'ema50_1h' not in checks and 'ema50_15m' in checks and 'news_window' in checks

diff --git a/docs/architecture/REVALIDATION-SOURCE-USAGE.md b/docs/architecture/REVALIDATION-SOURCE-USAGE.md
new file mode 100644
index 0000000..74982a2
--- /dev/null
+++ b/docs/architecture/REVALIDATION-SOURCE-USAGE.md
@@ -0,0 +1,66 @@
+# Original pending-plan revalidation over offline ports
+
+Private API: trading_system.tree_replay._vendor.revalidation.Revalidation(source).
+Source authority, exact adaptations and remaining boundaries are in
+REVALIDATION-SOURCE-CONTRACT.md. Runtime exists with synthetic behavior tests;
+source audit and independent acceptance are required before component acceptance.
+
+```python
+checks = Revalidation(source)
+ok, reason, verified = checks.still_valid(pending_trade)
+ok, reason, verified = checks.revalidate_pending(pending_trade, now=epoch_seconds)
+```
+
+This does not fill, execute, modify the trade, publish an alert or generate a
+profit/loss label. It reproduces the source's thesis recheck. `ok=True` does not
+mean verified; callers must keep the third value and the original reasons.
+
+The reader composes real TrackerAdmission higher-bias, StretchReader, EmaReader,
+admission_matrix structure, default non-auction PVSRA and source session logic.
+It consumes the existing read_symbol, fetch_corrected, broker_shape_ok and
+deep_exists/deep_bytes ports plus these explicit offline operations:
+
+| Port | Returned evidence / operation |
+| --- | --- |
+| now_epoch() | Captured per-operation epoch seconds |
+| now_timestamp(tz=...) | Captured timestamp expressed in requested timezone |
+| now_utc() | Captured aware UTC datetime |
+| tree_walk(symbol) | Original Walk-like reply, None or captured exception; full walk binding is not implemented here |
+| ensure_shadow_parent(parents=True, exist_ok=True) | Replay-only parent creation operation |
+| shadow_open('a', encoding='utf-8') | Text-writer context manager for logical chart-desk/out/revalidation_shadow.jsonl |
+| calendar_exists(path) | Captured existence for news-desk/data/ff_calendar.json |
+| calendar_text(path) | Captured raw JSON text for that same identity |
+
+No default live/filesystem providers are supplied. Input presence/identity,
+observation/publication times, process timezone and caught failures require
+separate causal trace/provider evidence. Unknown is not an empty successful
+reply. Raw source catches do not certify missing evidence as safe.
+
+The higher bias veto requires a real flip from a send bias favoring the trade;
+flat/unread/already-opposing send bias yields distinct labels. A same-direction
+extended daily range vetoes. Missing stretch marks unverified; daily fetch
+errors are already caught inside StretchReader and reach this reader as absent
+stretch, not necessarily as a propagated core exception.
+
+Freshness separately fetches15m/1h/4h with lookback3 and compares each to its own
+bar duration in15m-equivalent minutes. Values over120 block/unverified; over20
+or unknown allow/unverified. Exact thresholds are inclusive on the allowed
+side. Empty frames are skipped; an exception resets age to unknown. This is
+the original policy, not a guarantee of complete feed coverage.
+
+EMA/session/stop-distance/structure/vector/news are shadow observations, not
+new vetoes. They serialize actual JSON lines with operation timestamps. Writer
+failures remain source best-effort. A news event uses a30minute inclusive window;
+missing/invalid calendar is reported, not asserted clear. Numeric nonzero
+dateline takes precedence except bool; ISO date is the fallback. Raw offset-free
+ISO dates use the host timezone, which is NOT approved historical interpretation.
+Impact leading whitespace and nonfinite inputs retain raw source semantics.
+
+For pending age below2hours, no tree check is requested. At/above2hours, opposite
+direction blocks; unavailable/stopped tree allows but is unverified. Invalid
+or missing send time also allows/unverified after still_valid. Default operation
+clock is read only after that check; explicit now avoids that extra clock read.
+
+Run tests/tree_replay/test_revalidation.py for current synthetic behavior.
+Full tree_walk, causal providers, resolver/caller/effects, economic simulation,
+dataset and model work remain separate required parts of the master plan.

