# Task1 full new-file package

```diff
diff --git a/trading_system/tree_replay/_vendor/claim_verifier.py b/trading_system/tree_replay/_vendor/claim_verifier.py
new file mode 100644
index 0000000..683aa8c
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/claim_verifier.py
@@ -0,0 +1,253 @@
+"""Pinned independent verifier over explicit offline ports; no transport or economic fills."""
+from __future__ import annotations
+import re
+from dataclasses import dataclass
+import pandas as pd
+from .desk_success import DeskSuccess
+TOL = {'XAU': 0.5, 'NAS': 3.0, 'BTC': 15.0}
+
+@dataclass
+class Verdict:
+    ok: bool
+    reason: str = ''
+    claim: str = ''
+    stale: bool = False
+
+    def __bool__(self) -> bool:
+        return self.ok
+
+def _tol(symbol: str) -> float:
+    u = symbol.upper()
+    for k, v in TOL.items():
+        if k in u:
+            return v
+    return 1.0
+
+def _covers(df, when: float | None) -> bool:
+    """Does this tape extend past `when`? Unknown times count as covered."""
+    if when is None or df is None or df.empty:
+        return True
+    try:
+        last = pd.to_datetime(df.index, utc=True)[-1].timestamp()
+    except Exception:
+        return True
+    return last + 900 >= float(when)
+
+def _fill_index(df, trade: dict):
+    """The first bar that touched the entry, located independently.
+
+    Re-derived rather than read from `trade["filled_ts"]`, because a wrong
+    fill time is exactly one of the bugs this gate exists to catch.
+    """
+    try:
+        from .pricing import entry_zone
+        zlo, zhi = entry_zone(trade['symbol'], float(trade['entry']))
+    except Exception:
+        e = float(trade['entry'])
+        zlo = zhi = e
+    idx = pd.to_datetime(df.index, utc=True)
+    bar_s = 900.0
+    try:
+        if len(idx) >= 2:
+            bar_s = float((idx[1] - idx[0]).total_seconds()) or 900.0
+    except Exception:
+        pass
+    after = df[[t.timestamp() > float(trade['ts']) - bar_s for t in idx]]
+    if after.empty:
+        return None
+    short = trade['direction'] == 'שורט'
+    hit = after['high'] >= zlo if short else after['low'] <= zhi
+    return hit.idxmax() if hit.any() else None
+_NOT_YET = 'הטייפ עוד לא מכסה את רגע הטענה — ממתין'
+
+def _closed_past(df, when: float) -> bool:
+    """Has a bar STAMPED at or after `when` been printed?
+
+    Stricter than _covers on purpose: a contradiction needs the bar that
+    contains the moment to be closed, and the only proof of that is the
+    next bar. _covers' one-bar slack is right for "has the tape reached the
+    fill" and wrong here -- it would call a bar still forming "seen".
+    """
+    try:
+        last = pd.to_datetime(df.index, utc=True)[-1].timestamp()
+    except Exception:
+        return True
+    return last >= float(when)
+
+def _fill_unseen(df, trade: dict) -> bool:
+    """No fill on the tape -- but could the tape have shown it yet?
+
+    Codex (2026-09-03): a fill at 04:00:15 and its stop seconds later both
+    live in the 04:00 bar. With that bar still forming, _covers says the
+    tape reaches the fill (04:00 + 15 min) while the bar has not printed the
+    touch -- and the missing fill became a firm "no". The fill bar has to be
+    closed before its absence means anything.
+    """
+    f_ts = trade.get('filled_ts')
+    if not _covers(df, f_ts):
+        return True
+    return bool(f_ts) and (not _closed_past(df, float(f_ts)))
+
+def _frame(df, fill, when: float):
+    """Bars from the fill up to the bar that contains `when`, inclusive.
+
+    Codex (2026-09-03): a claim scanned from the fill to the END of the tape,
+    so a false 10:00 claim parked as stale was released at 10:20 by a real
+    touch that happened twenty minutes after the desk announced it. The
+    claim is about a moment; bars opened after that moment cannot have
+    caused it.
+    """
+    aft = df.loc[fill:]
+    idx = pd.to_datetime(aft.index, utc=True)
+    return aft[[t.timestamp() <= float(when) for t in idx]]
+
+def _extreme(frame, col: str) -> float | None:
+    """min of `low` / max of `high` over the frame; None when it is empty."""
+    if frame is None or frame.empty:
+        return None
+    v = float(frame[col].min() if col == 'low' else frame[col].max())
+    return None if v != v else v
+
+class ClaimVerifier:
+
+    def __init__(self, source):
+        self.source = source
+        self.movement = DeskSuccess(source)
+
+    def _bars(self, symbol: str, days: int=3):
+        """A fresh, independent fetch. Never the caller's frame.
+
+    VENUE FALLBACK for Binance symbols, added 2026-08-31 after a real
+    incident: subscribers got a BTC BUY at 00:22, it filled at 02:28 and
+    stopped at 02:36 — and the stop message was BLOCKED here with "הכניסה לא
+    מומשה", because the local bar files were gappy (the collector was in a
+    reconnect loop dropping short batches) and this verifier saw a tape on
+    which the zone was never touched. The gate did exactly what it promises —
+    fail closed — but it stayed closed for hours because its ONLY evidence
+    source was the broken one. For BINANCE:* the exchange itself publishes
+    the identical series (measured 0.00 diff on 1,124 overlapping bars), so
+    when the local tape does not cover the claim window, the verifier asks
+    the venue directly instead of blocking a true message on our own gap.
+    """
+        if symbol.upper().startswith('BINANCE:'):
+            venue = self._binance_bars(symbol, days)
+            if venue is not None:
+                return venue
+        df, corr = self.source.fetch_corrected(symbol, '15m', days)
+        if corr is not None and getattr(corr, 'unverified', False):
+            return None
+        return df
+
+    def _binance_bars(self, symbol: str, days: int):
+        """15m klines straight from the venue — same series as the chart."""
+        try:
+            sym = symbol.split(':')[-1]
+            start = int((pd.Timestamp(self.source.now_utc()) - pd.Timedelta(days=days)).timestamp() * 1000)
+            url = f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=15m&startTime={start}&limit=1000'
+            rows = self.source.fetch_json(url, timeout=15)
+            if not rows:
+                return None
+            df = pd.DataFrame([[r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4])] for r in rows], columns=['t', 'open', 'high', 'low', 'close'])
+            df.index = pd.to_datetime(df['t'], unit='ms', utc=True)
+            return df.drop(columns=['t'])
+        except Exception:
+            return None
+
+    def target(self, trade: dict, price: float) -> Verdict:
+        """Did price actually trade through `price` AFTER the entry filled?"""
+        claim = f'TP @ {price:,.2f}'
+        df = self._bars(trade['symbol'])
+        if df is None or df.empty:
+            return Verdict(False, 'אין נתונים לאימות', claim)
+        fill = _fill_index(df, trade)
+        if fill is None:
+            if _fill_unseen(df, trade):
+                return Verdict(False, 'הטייפ טרם מגיע לרגע המילוי — אי אפשר לאמת עדיין', claim, stale=True)
+            return Verdict(False, 'הכניסה לא מומשה בטייפ — לא ייתכן יעד', claim)
+        when = self._claim_clock(trade, 'claim_ts')
+        aft = _frame(df, fill, when)
+        short = trade['direction'] == 'שורט'
+        t = _tol(trade['symbol'])
+        best = _extreme(aft, 'low' if short else 'high')
+        reached = best is not None and (best <= price + t if short else best >= price - t)
+        if not reached:
+            if not _closed_past(df, when):
+                return Verdict(False, _NOT_YET, claim, stale=True)
+            seen = f'הקיצון היה {best:,.2f}' if best is not None else 'אין נר'
+            return Verdict(False, f'המחיר לא הגיע ל-{price:,.2f} אחרי המילוי ({fill:%H:%M}) — {seen}', claim)
+        return Verdict(True, claim=claim)
+
+    def _claim_clock(self, trade: dict, *keys: str) -> float:
+        """The moment a claim is about: the first stamped key, else now."""
+        for k in keys:
+            try:
+                v = float(trade.get(k) or 0)
+            except (TypeError, ValueError):
+                v = 0.0
+            if v:
+                return v
+        return pd.Timestamp(self.source.now_utc()).timestamp()
+
+    def fill(self, trade: dict) -> Verdict:
+        """Did price actually reach the entry since the trade was sent?"""
+        claim = f"fill @ {float(trade['entry']):,.2f}"
+        df = self._bars(trade['symbol'])
+        if df is None or df.empty:
+            return Verdict(False, 'אין נתונים לאימות', claim)
+        if _fill_index(df, trade) is None:
+            if not _covers(df, trade.get('filled_ts')):
+                last = pd.to_datetime(df.index, utc=True)[-1]
+                return Verdict(False, f'הטייפ מסתיים ב-{last:%H:%M} — לפני רגע המילוי. אי אפשר לאמת עדיין', claim, stale=True)
+            f_ts = float(trade.get('filled_ts') or trade.get('ts') or 0)
+            if f_ts and pd.Timestamp(self.source.now_utc()).timestamp() - f_ts < 45 * 60:
+                return Verdict(False, 'הטייפ עוד לא מראה את הנגיעה — ממתין', claim, stale=True)
+            return Verdict(False, 'המחיר לא נגע בטווח הכניסה', claim)
+        return Verdict(True, claim=claim)
+
+    def stop(self, trade: dict) -> Verdict:
+        """Did price actually reach the stop after the fill?"""
+        claim = f"stop @ {float(trade['stop']):,.2f}"
+        df = self._bars(trade['symbol'])
+        if df is None or df.empty:
+            return Verdict(False, 'אין נתונים לאימות', claim)
+        fill_i = _fill_index(df, trade)
+        if fill_i is None:
+            if _fill_unseen(df, trade):
+                return Verdict(False, 'הטייפ טרם מגיע לרגע המילוי — אי אפשר לאמת עדיין', claim, stale=True)
+            return Verdict(False, 'הכניסה לא מומשה — לא ייתכן סטופ', claim)
+        when = self._claim_clock(trade, 'resolved_ts', 'claim_ts')
+        aft = _frame(df, fill_i, when)
+        s = float(trade['stop'])
+        short = trade['direction'] == 'שורט'
+        t = _tol(trade['symbol'])
+        worst = _extreme(aft, 'high' if short else 'low')
+        reached = worst is not None and (worst >= s - t if short else worst <= s + t)
+        if not reached:
+            if not _closed_past(df, when):
+                return Verdict(False, _NOT_YET, claim, stale=True)
+            return Verdict(False, f'המחיר לא הגיע לסטופ {s:,.2f} אחרי המילוי', claim)
+        return Verdict(True, claim=claim)
+
+    def check_message(self, text: str, trade: dict) -> Verdict:
+        """Verify an outgoing outcome message against the tape. Never raises.
+
+    Returns ok=True for messages that make no factual claim about a price
+    being reached -- a proximity alert or a break-even note describes a state,
+    not an event, and there is nothing on the tape to disagree with.
+    """
+        try:
+            t = text.strip()
+            if t.startswith('📈') and '· הושג הסף המינימלי ·' in t.splitlines()[0]:
+                return Verdict(self.movement.reached(trade), 'minimum requires a valid identity-bound proof')
+            if t.startswith('✅'):
+                m = re.search('הושג @ ([\\d,]+\\.?\\d*)', t)
+                if not m:
+                    return Verdict(False, 'טענת יעד ללא מחיר — לא ניתן לאמת')
+                return self.target(trade, float(m.group(1).replace(',', '')))
+            if t.startswith('▶️'):
+                return self.fill(trade)
+            if t.startswith('🛑'):
+                return self.stop(trade)
+            return Verdict(True, 'no factual claim')
+        except Exception as e:
+            return Verdict(False, f'האימות נכשל: {type(e).__name__}')

```

```diff
diff --git a/tests/tree_replay/test_claim_verifier.py b/tests/tree_replay/test_claim_verifier.py
new file mode 100644
index 0000000..2c497d2
--- /dev/null
+++ b/tests/tree_replay/test_claim_verifier.py
@@ -0,0 +1,273 @@
+"""Actual independent source claim routing, venue decoder and chronological boundaries."""
+from copy import deepcopy
+from datetime import datetime, timedelta, timezone
+import importlib
+import importlib.util
+from types import SimpleNamespace
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay.clock import ReplayClock
+from trading_system.tree_replay._vendor.desk_success import DeskSuccess
+from trading_system.tree_replay._vendor import lifecycle_bars
+
+
+T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
+NOW = T + timedelta(minutes=45)
+
+
+def api():
+    name = "trading_system.tree_replay._vendor.claim_verifier"
+    assert importlib.util.find_spec(name) is not None, "claim verifier missing"
+    return importlib.import_module(name)
+
+
+def tape(rows):
+    return pd.DataFrame([dict(open=lo, high=hi, low=lo, close=hi) for _, hi, lo in rows],
+        index=pd.DatetimeIndex([T+timedelta(minutes=m) for m, _, _ in rows]))
+
+
+def trade(**changes):
+    return dict(symbol="OANDA:XAUUSD", direction="לונג", trade_id="claim-one",
+        ts=T.timestamp(), filled_ts=(T+timedelta(minutes=15)).timestamp(),
+        entry=100., stop=90., targets=[("TP1", 120.)], state="OPEN") | changes
+
+
+class Ports:
+    def __init__(self, frame=None, *, now=NOW, correction=None, rows=None,
+                 symbol="OANDA:XAUUSD", days=3):
+        self.clock = ReplayClock(now)
+        self.frame, self.correction, self.rows = frame, correction, rows
+        self.symbol, self.days = symbol, days
+        self.calls = []
+
+    def now_utc(self):
+        self.calls.append(("utc", self.clock.now))
+        return self.clock.now
+
+    def now_epoch(self):
+        self.calls.append(("epoch", self.clock.now))
+        return self.clock.now.timestamp()
+
+    def fetch_corrected(self, symbol, timeframe, days):
+        self.calls.append(("local", symbol, timeframe, days))
+        assert (symbol, timeframe, days) == (self.symbol, "15m", self.days)
+        if isinstance(self.frame, Exception):
+            raise self.frame
+        return self.frame, self.correction
+
+    def fetch_json(self, url, *, timeout):
+        self.calls.append(("json", url, timeout))
+        if isinstance(self.rows, Exception):
+            raise self.rows
+        return self.rows
+
+
+def engine(frame=None, **options):
+    return api().ClaimVerifier(Ports(frame, **options))
+
+
+@pytest.mark.parametrize("direction,hi,lo,target", [("לונג", 120., 99., 110.), ("שורט", 101., 80., 90.)])
+def test_independent_fill_slack_and_fill_bar_target_differ_from_resolver(direction, hi, lo, target):
+    df = tape([(0, hi, lo)])
+    t = trade(direction=direction, state="PENDING", filled_ts=None)
+    before = deepcopy(t)
+    e = engine(df)
+    assert lifecycle_bars._fill_on_tape(df, t) is None
+    assert api()._fill_index(df, t) == pd.Timestamp(T)
+    result = e.target(t, target)
+    assert result.ok and not result.stale and result.claim == f"TP @ {target:,.2f}"
+    assert t == before
+    pd.testing.assert_frame_equal(df, tape([(0, hi, lo)]))
+
+
+@pytest.mark.parametrize("send_minutes,spacing,want", [(14., 15., 0), (15., 15., 15), (29., 30., 0), (30., 30., 30)])
+def test_fill_slack_uses_actual_spacing_and_strict_lower_boundary(send_minutes, spacing, want):
+    api()
+    df = tape([(0, 101., 99.), (spacing, 101., 99.)])
+    got = api()._fill_index(df, trade(ts=(T+timedelta(minutes=send_minutes)).timestamp()))
+    assert got == pd.Timestamp(T+timedelta(minutes=want))
+
+
+def test_target_claim_cannot_be_repaired_by_later_touch():
+    df = tape([(0, 101., 99.), (15, 103., 100.), (30, 120., 100.)])
+    e = engine(df)
+    t = trade(claim_ts=(T+timedelta(minutes=15)).timestamp())
+    r = e.target(t, 110.)
+    assert not r and not r.stale and "המחיר לא הגיע" in r.reason
+    t["claim_ts"] = (T+timedelta(minutes=30)).timestamp()
+    assert e.target(t, 110.)
+
+
+def test_stop_uses_resolved_clock_before_claim_clock():
+    df = tape([(0, 101., 99.), (15, 103., 98.), (30, 103., 89.)])
+    t = trade(resolved_ts=(T+timedelta(minutes=15)).timestamp(), claim_ts=(T+timedelta(minutes=30)).timestamp())
+    e = engine(df)
+    r = e.stop(t)
+    assert not r and not r.stale
+    del t["resolved_ts"]
+    assert e.stop(t)
+
+
+@pytest.mark.parametrize("method", ["target", "stop"])
+def test_nonreach_stale_is_distinct_from_closed_tape_contradiction(method):
+    e = engine(tape([(0, 101., 99.), (15, 103., 98.)]))
+    t = trade(claim_ts=NOW.timestamp(), resolved_ts=NOW.timestamp())
+    args = (t, 110.) if method == "target" else (t,)
+    r = getattr(e, method)(*args)
+    assert not r and r.stale and r.reason == "הטייפ עוד לא מכסה את רגע הטענה — ממתין"
+    e.source.frame = tape([(0, 101., 99.), (45, 103., 98.)])
+    r = getattr(e, method)(*args)
+    assert not r and not r.stale
+
+
+@pytest.mark.parametrize("method", ["target", "stop"])
+def test_missing_fill_distinguishes_unseen_from_contradicted(method):
+    e = engine(tape([(0, 120., 110.), (15, 120., 110.)]))
+    t = trade(filled_ts=(T+timedelta(minutes=20)).timestamp())
+    args = (t, 130.) if method == "target" else (t,)
+    r = getattr(e, method)(*args)
+    assert not r and r.stale
+    e.source.frame = tape([(0, 120., 110.), (30, 120., 110.)])
+    r = getattr(e, method)(*args)
+    assert not r and not r.stale
+
+
+@pytest.mark.parametrize("age_seconds,want_stale", [(2699., True), (2700., False), (2701., False)])
+def test_fill_grace_is_strictly_less_than_45_minutes(age_seconds, want_stale):
+    e = engine(tape([(0, 120., 110.), (45, 120., 110.)]))
+    t = trade(filled_ts=NOW.timestamp()-age_seconds)
+    r = e.fill(t)
+    assert not r and r.stale is want_stale
+
+
+def test_fill_stale_when_tape_does_not_reach_filled_stamp_even_after_grace():
+    e = engine(tape([(0, 120., 110.)]), now=NOW+timedelta(hours=2))
+    r = e.fill(trade(filled_ts=(T+timedelta(minutes=30)).timestamp()))
+    assert not r and r.stale and "לפני רגע המילוי" in r.reason
+
+
+@pytest.mark.parametrize("method", ["target", "stop", "fill"])
+@pytest.mark.parametrize("frame", [None, pd.DataFrame()])
+def test_missing_tape_blocks_claims(method, frame):
+    e = engine(frame)
+    r = e.target(trade(), 110.) if method == "target" else getattr(e, method)(trade())
+    assert not r and not r.stale and r.reason == "אין נתונים לאימות"
+
+
+@pytest.mark.parametrize("symbol,tolerance", [("OANDA:XAUUSD", .5), ("OANDA:NAS100USD", 3.), ("BINANCE:BTCUSDT", 15.), ("OTHER", 1.)])
+@pytest.mark.parametrize("short", [False, True])
+def test_real_target_and_stop_comparisons_use_literal_instrument_tolerances(symbol, tolerance, short):
+    # Venue decoding is real for BTC; no replacement of _bars or _fill_index.
+    direction = "שורט" if short else "לונג"
+    entry, target, stop = 1000., (800. if short else 1200.), (1200. if short else 800.)
+    def evaluate(extra):
+        hi = stop-tolerance-extra if short else target-tolerance-extra
+        lo = target+tolerance+extra if short else stop+tolerance+extra
+        df = tape([(0, 1001., 999.), (30, hi, lo)])
+        rows = [[int(i.timestamp()*1000), r.open, r.high, r.low, r.close] for i, r in df.iterrows()]
+        e = engine(df, symbol=symbol, rows=rows)
+        t = trade(symbol=symbol, direction=direction, entry=entry, stop=stop, claim_ts=(T+timedelta(minutes=30)).timestamp())
+        return e.target(t, target), e.stop(t)
+    target_ok, stop_ok = evaluate(0.)
+    assert target_ok and stop_ok
+    target_miss, stop_miss = evaluate(.01)
+    assert not target_miss and not target_miss.stale
+    assert not stop_miss and not stop_miss.stale
+
+
+def test_binance_venue_first_real_decode_exact_request_and_no_local_read():
+    rows = [[1788969600000, "100", "105", "99", "104", "999"]]
+    before = deepcopy(rows)
+    e = engine(RuntimeError("local must not be used"), symbol="BINANCE:BTCUSDT", rows=rows)
+    df = e._bars("BINANCE:BTCUSDT")
+    expected = tape([(0, 105., 99.)])
+    expected["open"], expected["close"] = 100., 104.
+    expected.index.name = "t"
+    pd.testing.assert_frame_equal(df, expected, check_dtype=False)
+    assert rows == before and len(e.source.calls) == 2
+    assert e.source.calls[1] == ("json", "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=15m&startTime=1788713100000&limit=1000", 15)
+
+
+@pytest.mark.parametrize("rows", [None, [], ValueError("transport"), [[0, "bad", "2", "1", "2"]], [[0]]])
+def test_failed_or_empty_venue_falls_back_to_original_local_fetch(rows):
+    df = tape([(0, 101., 99.)])
+    e = engine(df, symbol="BINANCE:BTCUSDT", rows=rows)
+    assert e._bars("BINANCE:BTCUSDT") is df
+    assert [c[0] for c in e.source.calls] == ["utc", "json", "local"]
+    assert e.source.calls[-1] == ("local", "BINANCE:BTCUSDT", "15m", 3)
+
+
+def test_custom_days_propagate_to_venue_request_and_fallback():
+    e = engine(tape([(0, 101., 99.)]), symbol="BINANCE:BTCUSDT", days=2, rows=[])
+    e._bars("BINANCE:BTCUSDT", 2)
+    assert "startTime=1788799500000&limit=1000" in e.source.calls[1][1]
+    assert e.source.calls[-1] == ("local", "BINANCE:BTCUSDT", "15m", 2)
+
+
+@pytest.mark.parametrize("correction,blocked", [(None, False), (SimpleNamespace(unverified=True), True), (SimpleNamespace(unverified=False, source="tv_stale"), False)])
+def test_local_path_preserves_only_original_unverified_veto(correction, blocked):
+    df = tape([(0, 101., 99.)])
+    e = engine(df, correction=correction)
+    got = e._bars("OANDA:XAUUSD")
+    assert (got is None) if blocked else (got is df)
+    assert e.source.calls == [("local", "OANDA:XAUUSD", "15m", 3)]
+
+
+@pytest.mark.parametrize("text,ok,claim", [
+    ("✅ XAUUSD BUY 100.00 · הושג @ 110.00", True, "TP @ 110.00"),
+    ("✅ XAUUSD BUY 100.00 · הושג @ 130.00", False, "TP @ 130.00"),
+    ("✅ XAUUSD BUY 100.00", False, ""),
+    ("▶️ XAUUSD BUY 100.00 · נכנסה", True, "fill @ 100.00"),
+    ("🛑 XAUUSD BUY 100.00", True, "stop @ 90.00"),
+    ("🔒 XAUUSD BUY 100.00 · רשות", True, ""),
+    ("📈 XAUUSD BUY 100.00 · +40 פיפס", True, ""),
+])
+def test_actual_message_router_runs_real_claim_comparisons(text, ok, claim):
+    e = engine(tape([(0, 101., 99.), (45, 120., 89.)]))
+    t = trade()
+    before = deepcopy(t)
+    r = e.check_message("  "+text+"  ", t)
+    assert bool(r) is ok and r.claim == claim
+    assert t == before
+    if claim:
+        assert e.source.calls[0] == ("local", "OANDA:XAUUSD", "15m", 3)
+
+
+def test_minimum_message_uses_actual_proof_dependency_and_no_tape_fetch():
+    e = engine(RuntimeError("not used"))
+    t = trade()
+    message = DeskSuccess(e.source).observe(t, 105., NOW.timestamp(), "exact_venue_quote")
+    e.source.calls.clear()
+    assert e.check_message(message, t)
+    assert [c[0] for c in e.source.calls] == ["epoch"]
+    t["trade_id"] = "different"
+    assert not e.check_message(message, t)
+
+
+@pytest.mark.parametrize("text,frame", [("▶️ XAUUSD", RuntimeError("offline read")), ("🛑 XAUUSD", tape([(0, 101., 99.)])), (None, None)])
+def test_router_contains_exceptions_instead_of_blessing_claim(text, frame):
+    e = engine(frame)
+    t = trade()
+    if text and text.startswith("🛑"):
+        del t["stop"]
+    r = e.check_message(text, t)
+    assert not r and r.reason.startswith("האימות נכשל:")
+
+
+@pytest.mark.parametrize("row,want", [({"resolved_ts": 123., "claim_ts": 456.}, 123.), ({"resolved_ts": "bad", "claim_ts": 456.}, 456.), ({"resolved_ts": 0, "claim_ts": None}, NOW.timestamp())])
+def test_claim_clock_first_usable_key_and_explicit_operation_fallback(row, want):
+    assert engine()._claim_clock(row, "resolved_ts", "claim_ts") == want
+
+
+def test_internal_coverage_predicates_do_not_certify_missing_data():
+    m = api()
+    df = tape([(0, 101., 99.)])
+    assert m._covers(df, (T+timedelta(minutes=15)).timestamp())
+    assert not m._covers(df, (T+timedelta(minutes=15, microseconds=1)).timestamp())
+    assert not m._closed_past(df, (T+timedelta(microseconds=1)).timestamp())
+    assert m._closed_past(df, T.timestamp())
+    assert m._covers(None, NOW.timestamp()) and m._covers(pd.DataFrame(), NOW.timestamp())
+    assert m._extreme(pd.DataFrame(), "high") is None
+    assert m._extreme(pd.DataFrame({"high": [float("nan")]}), "high") is None

```

```diff
diff --git a/docs/architecture/INDEPENDENT-CLAIM-VERIFIER-USAGE.md b/docs/architecture/INDEPENDENT-CLAIM-VERIFIER-USAGE.md
new file mode 100644
index 0000000..f028f85
--- /dev/null
+++ b/docs/architecture/INDEPENDENT-CLAIM-VERIFIER-USAGE.md
@@ -0,0 +1,67 @@
+# Original independent claim verifier
+
+Private source projection: `trading_system.tree_replay._vendor.claim_verifier`.
+Authority and exact substitutions are in INDEPENDENT-CLAIM-VERIFIER-CONTRACT.md.
+This component supplies the original checker, not the full tracker gate or a
+historical feed provider. It performs no network, delivery, trade-state or outbox
+operation. The source checkout is inspected, never executed by extraction/audit.
+
+Construct `ClaimVerifier(source)` with these explicit local ports:
+
+```python
+class Ports:
+    def __init__(self, clock, frame_source, json_source):
+        self.clock = clock
+        self.frame_source = frame_source
+        self.json_source = json_source
+    def now_utc(self):
+        return self.clock.now
+    def now_epoch(self):
+        return self.clock.now.timestamp()
+    def fetch_corrected(self, symbol, timeframe, days):
+        return self.frame_source.read(symbol, timeframe, days)
+    def fetch_json(self, url, *, timeout):
+        return self.json_source.read(url, timeout=timeout)
+```
+
+The frame_source/json_source above are caller-supplied offline evidence readers,
+not provided public adapters. They must not access live APIs. The URL is request
+identity, including original symbol,15m,lookback-derived milliseconds,limit1000
+and timeout15. now_utc must be aware UTC; both ports refer to one operation clock.
+No system-time default is used. Real causal readers and their traces remain work.
+
+`check_message(text, trade)` returns original Verdict(ok, reason, claim, stale),
+whose truthiness is ok. It routes minimum-movement, target, fill and stop messages
+through their original calculations; other messages pass as no factual claim.
+It catches exceptions into a failed verdict. Direct target/fill/stop methods
+retain narrower original exception boundaries and may raise on malformed inputs.
+
+Important limits and preserved differences:
+
+- The caller must already match the message to the correct trade. This checker
+  is not the tracker text-to-trade matcher, park/retry, delivery receipt or gate.
+- BINANCE reads the independently supplied venue response first, runs the real
+  OHLC decoder, and falls back to supplied corrected local bars on None/failure.
+  Other symbols use local15m/3 directly. Only original unverified veto is kept;
+  successful reads and source tags do not prove historical coverage or quality.
+- Its independent fill locator has one-bar send slack and target extrema include
+  the fill bar. This intentionally differs from resolver geometry. Neither is
+  economic proof of an executable intrabar trade. No resolver helper is reused.
+- Target claim_ts and stop resolved_ts-before-claim_ts cap the frame by opening
+  timestamps. This alone cannot certify the historical OHLC of the containing
+  bar; late publication/partial-bar semantics require the later causal provider.
+- Missing data, tape not yet reaching a claim, and an actual contradiction have
+  distinct original verdicts. The45min fill grace is not a generic freshness rule.
+  Internal _covers accepts some missing/error cases by design; public methods
+  still check missing/empty frames. Raw predicates are not coverage certification.
+- Minimum messages call the actual DeskSuccess identity proof using the same
+  supplied clock. A valid movement proof is not economic profit or model target.
+
+No input trade is intentionally mutated by verification. Source tolerances,
+numeric behavior and message parsing are unchanged. Use audit CLI with an
+explicit retained source root; its VERIFIED result certifies projection fidelity
+only and leaves ready_for_replay/ready_for_training false.
+
+Remaining: causal verifier/lifecycle feeds, full revalidation and effects,
+stateful resolver/caller, other producer paths, economic outcomes/dataset/model.
+Component acceptance lives in agent-exchange/status, not in this usage note.

```
