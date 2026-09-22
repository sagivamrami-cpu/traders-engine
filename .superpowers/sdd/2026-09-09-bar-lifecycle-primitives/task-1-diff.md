# Task1 full new-file package

```diff
diff --git a/trading_system/tree_replay/_vendor/lifecycle_bars.py b/trading_system/tree_replay/_vendor/lifecycle_bars.py
new file mode 100644
index 0000000..b1cad63
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/lifecycle_bars.py
@@ -0,0 +1,111 @@
+"""Pinned chart-desk position geometry; caller owns tape causality. Private source projection."""
+import pandas as pd
+
+def _fill_on_tape(df, t: dict):
+    """The first bar whose range touched the entry zone, or None.
+
+    One implementation, used by both resolvers. A second copy is a second
+    convention, and this bug has already come back three times because two
+    code paths disagreed about when a trade became a position.
+    """
+    try:
+        import pandas as _pd
+        idx = _pd.to_datetime(df.index, utc=True)
+        after = df[[x.timestamp() > float(t['ts']) for x in idx]]
+        if after.empty:
+            return None
+        zlo, zhi = _entry_band(t)
+        short = t['direction'] == 'שורט'
+        hit = after['high'] >= zlo if short else after['low'] <= zhi
+        return hit.idxmax() if hit.any() else None
+    except Exception:
+        return None
+
+def _position_extremes(window, t: dict, *, fill_bar_first: bool) -> tuple[float, float]:
+    """(hi, lo) the POSITION saw, from a window that begins at the fill.
+
+    One implementation for the bar resolver and the live path; the convention
+    they share is the pessimistic one:
+
+    * The fill bar counts AGAINST the position and never FOR it. Within one
+      bar the order of the two extremes is unknown, and on a retest entry the
+      pre-fill part of that bar sits on the target side by construction --
+      price came from there into the entry. 2026-09-02 17:10: gold short
+      4,396.52 filled at 17:09:25; the 17:00 bar's low of 4,378.9 (printed
+      before the fill) became "📈 +40 / +79 / +119 פיפס" in the group while
+      the position was ten points old.
+    * With nothing after the fill bar, the favourable side is the entry
+      itself: nothing has been earned yet.
+
+    `fill_bar_first` says whether window.iloc[0] IS the fill bar (located on
+    the tape) or the window already starts after the fill stamp.
+    """
+    short = t['direction'] == 'שורט'
+    e = float(t['entry'])
+    adverse = float(window['high'].max()) if short else float(window['low'].min())
+    fav_bars = window.iloc[1:] if fill_bar_first else window
+    if fav_bars.empty:
+        fav = e
+    else:
+        fav = float(fav_bars['low'].min()) if short else float(fav_bars['high'].max())
+    return (adverse, fav) if short else (fav, adverse)
+
+def position_bars(since, t: dict, *, include_fill_bar: bool=False):
+    """(bars, fill_bar_first) for the window the POSITION owns. None = no fill.
+
+    The one place that decides where a position's excursion begins. The bar
+    resolver reads it every pass through _open_extremes; trade_admin reopen
+    reads it to revive a trade the resolver closed on a false excursion, and
+    trade_admin settle walks it bar by bar to close a row the tape
+    contradicts -- one convention, so no repair can disagree with the next
+    pass.
+
+    Using a wall-clock filled_ts alone does not work: within a single pass the
+    trade transitions PENDING->OPEN and is resolved immediately after, and
+    "bars after now" is empty. The fill is a property of the tape, so it is
+    located on the tape.
+
+    `include_fill_bar` keeps the bar the fill happened IN even when later
+    bars exist. The excursion readers do not want it (its pre-fill half sits
+    on the target side by construction), but a walk over a position's whole
+    life must see it: a stop printed on the fill bar ended the trade, and
+    skipping that bar settles a stopped position as a winner (Codex,
+    2026-09-04). The flag never affects what the fill bar may PAY -- that is
+    fill_bar_first's job, and it stays True whenever the bar is included.
+    """
+    if t['state'] == 'OPEN' and t.get('filled_ts') and (not include_fill_bar):
+        _fts = float(t['filled_ts'])
+        _sts = [ts.timestamp() for ts in pd.to_datetime(since.index, utc=True)]
+        _mask = [x >= _fts for x in _sts]
+        if any(_mask):
+            return (since[_mask], False)
+        _i = max((i for i, x in enumerate(_sts) if x <= _fts))
+        return (since.iloc[_i:], True)
+    if include_fill_bar and t.get('filled_ts'):
+        _fts = float(t['filled_ts'])
+        _sts = [ts.timestamp() for ts in pd.to_datetime(since.index, utc=True)]
+        _at = [i for i, x in enumerate(_sts) if x <= _fts]
+        if not _at:
+            return None
+        return (since.iloc[max(_at):], True)
+    _fi = _fill_on_tape(since, t)
+    if _fi is None:
+        return None
+    return (since.loc[_fi:], True)
+
+def _open_extremes(since, t: dict) -> tuple[float, float] | None:
+    """(hi, lo) the position has seen, from the bars since the SEND. None = no fill."""
+    sel = position_bars(since, t)
+    if sel is None:
+        return None
+    bars, fill_bar_first = sel
+    return _position_extremes(bars, t, fill_bar_first=fill_bar_first)
+
+def _entry_band(t: dict) -> tuple[float, float]:
+    """The price band that fills this trade. Falls back to the exact level."""
+    try:
+        from .pricing import entry_zone
+        return entry_zone(t['symbol'], float(t['entry']))
+    except Exception:
+        e = float(t['entry'])
+        return (e, e)

```

```diff
diff --git a/trading_system/tree_replay/_vendor/lifecycle_voice.py b/trading_system/tree_replay/_vendor/lifecycle_voice.py
new file mode 100644
index 0000000..46fc691
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/lifecycle_voice.py
@@ -0,0 +1,126 @@
+"""The client voice of TR-Trade: one vocabulary for every message the desk sends.
+
+2026-09-02, after the first full client-visible trade (gold SELL 4,373.35:
+entry, +39/+79 pips, a break-even option, eight thesis flip/return alerts in
+95 minutes, stop), Sagiv chose direction א of the message redesign -- keep the
+flow the clients already know, make each message identity-first, one marker
+one meaning, one unit per instrument -- and asked for the signal's detail
+block as a checklist, "עץ ההחלטות ✅ · הסטופ הורחב ❗️", one item per line.
+
+Rules this module carries so that no renderer re-derives them:
+
+IDENTITY. Every lifecycle message opens `{marker} {NAME} {SIDE} {entry}`.
+The tracker gate matches a message to its trade by the symbol name, the side
+word and the entry price it finds in the text (tracker._match_trade_for_text)
+and the outbox reads the FIRST price-looking token to catch a stale message
+(outbox._stale_price). Both parse the identity line, so it stays first and
+the entry stays the first price.
+
+UNITS. Gold is counted in pips (a point is ten pips -- his convention);
+the Nasdaq and BTC in points. One unit per instrument, in every message: the
+📈 ladder said "פיפס" while the ⚠️ warning said "נק'" for the same trade.
+
+MARKERS. One meaning each, never reused:
+    🔴 🟢  new trade (SELL / BUY)      👀  approaching the entry
+    ▶️  entry reached                   📈  progress in the trade's favour
+    🔒  protection can be taken         ✅  target reached
+    ⚠️  thesis weakened (a warning)     🔄  back in the trade's direction
+    🛑  stop reached                    🏁  closed at entry / trailed stop
+    ✖️  cancelled or expired before entry   ⏳  time in position
+    🔧  correction
+
+FOOTER. The desk reports direction and never closes a trade (Sagiv,
+2026-08-31: BE is "רשות, לא חובה"). The footer says so in one sentence.
+
+Everything here is pure: strings in, strings out. Telegram receives plain
+text (floor/notify.py sends no parse_mode), so the design is carried by
+structure -- identity line, one fact per line, a checklist -- not by markup.
+"""
+from __future__ import annotations
+
+import re
+
+FOOTER = "הדסק לא סוגר עסקאות. המצב לפניכם, ההחלטה שלכם."
+OPTIONAL = "רשות, לא חובה."
+TARGETS_NOTE = "היעדים הם רמות דיווח · מימוש וניהול לפי החלטת הסוחר"
+
+OK, MISSING = "✅", "❗️"
+
+
+def name(symbol: str) -> str:
+    return str(symbol).split(":")[-1]
+
+
+def side(direction: str | None) -> str:
+    return "SELL" if direction == "שורט" else "BUY"
+
+
+def dot(direction: str | None) -> str:
+    return "🔴" if direction == "שורט" else "🟢"
+
+
+def is_gold(symbol: str) -> bool:
+    return "XAU" in str(symbol).upper()
+
+
+def unit(symbol: str) -> str:
+    return "פיפס" if is_gold(symbol) else "נק'"
+
+
+def _scale(symbol: str) -> float:
+    return 10.0 if is_gold(symbol) else 1.0
+
+
+def move(symbol: str, points: float) -> str:
+    """A signed distance in the instrument's own unit: '+79 פיפס', '-660 נק''."""
+    return f"{points * _scale(symbol):+,.0f} {unit(symbol)}"
+
+
+def dist(symbol: str, points: float) -> str:
+    """An unsigned distance: '42 פיפס', '25 נק''."""
+    return f"{abs(points) * _scale(symbol):,.0f} {unit(symbol)}"
+
+
+def price(x: float) -> str:
+    return f"{float(x):,.2f}"
+
+
+def head(marker: str, symbol: str, direction: str | None, entry: float,
+         what: str = "") -> str:
+    """The identity line: `📈 XAUUSD SELL 4,373.35 · +79 פיפס`."""
+    line = f"{marker} {name(symbol)} {side(direction)} {price(entry)}"
+    return f"{line} · {what}" if what else line
+
+
+def check(text: str, ok: bool) -> str:
+    """One checklist line: `עץ ההחלטות ✅` or `וקטור — חסר ❗️`."""
+    return f"{text} {OK if ok else MISSING}"
+
+
+def moved_from_entry(symbol: str, direction: str | None, entry: float,
+                     px: float) -> str:
+    """Where price stands relative to the entry, signed by the trade's side."""
+    d = (float(entry) - float(px)) if direction == "שורט" else (float(px) - float(entry))
+    return move(symbol, d) if abs(d) >= 0.5 / _scale(symbol) else "בכניסה"
+
+
+def rung_points(entry: float, pct: float, step: int) -> float:
+    """Distance of progress rung `step` from the entry, in points."""
+    return float(entry) * (float(pct) / 100.0) * int(step)
+
+
+_RESOLUTION_WIDEN = re.compile(r"הורחב ל-([\d,]+(?:\.\d+)?)")
+
+
+def widen_line(symbol: str, warning: str) -> str | None:
+    """`הסטופ הורחב ל-8 מקצה טווח הכניסה — …` → `הסטופ הורחב ל-80 פיפס מקצה האזור`.
+
+    The engine writes the widening in points. A gold reader counts pips, and
+    "8" on a gold signal read as eight pips (Sagiv, 2026-09-02) when it meant
+    eighty.
+    """
+    m = _RESOLUTION_WIDEN.search(warning)
+    if not m:
+        return None
+    pts = float(m.group(1).replace(",", ""))
+    return f"הסטופ הורחב ל-{dist(symbol, pts)} מקצה האזור"

```

```diff
diff --git a/trading_system/tree_replay/_vendor/desk_success.py b/trading_system/tree_replay/_vendor/desk_success.py
new file mode 100644
index 0000000..6d47d9b
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/desk_success.py
@@ -0,0 +1,108 @@
+"""Pinned movement proof over explicit clocks; not economic success or feed certification."""
+from __future__ import annotations
+import math
+import pandas as pd
+from . import lifecycle_voice as voice
+VERSION = 'desk-minimum-2026-09-07'
+FLOOR = {'OANDA:XAUUSD': ('פיפס', 40.0, 10.0, '{:,.0f} פיפס'), 'OANDA:NAS100USD': ('נק׳', 70.0, 1.0, '{:,.0f} נק׳'), 'BINANCE:BTCUSDT': ('דולר', 200.0, 1.0, '${:,.0f}')}
+
+def minimum(symbol):
+    from .basis_symbols import canonical_symbol
+    row = FLOOR.get(canonical_symbol(symbol))
+    return row[1] / row[2] if row else None
+
+class DeskSuccess:
+
+    def __init__(self, source):
+        self.source = source
+
+    def reached(self, t, *, as_of=None):
+        """Only this version's identity-bound, chronological proof is sticky."""
+        p = t.get('minimum_success') or {}
+        try:
+            return p['version'] == VERSION and p['trade_id'] == t['trade_id'] and (p['trade_ts'] == float(t['ts'])) and (p['symbol'] == t['symbol']) and (p['minimum_points'] == minimum(t['symbol'])) and (p['source'] in ('verified_post_fill_bars', 'exact_venue_quote')) and (float(t['ts']) <= p['observed_ts'] <= (as_of or self.source.now_epoch())) and (not t.get('resolved_ts') or p['observed_ts'] <= t['resolved_ts']) and math.isfinite(p['price']) and (p['price'] > 0) and ((float(t['entry']) - p['price'] if t['direction'] == 'שורט' else p['price'] - float(t['entry'])) + 1e-09 >= p['minimum_points'])
+        except (KeyError, TypeError, ValueError):
+            return False
+
+    def observe(self, t, price, observed_ts, source):
+        """Caller certifies post-fill ordering and venue; no financial state changes."""
+        floor = minimum(t['symbol'])
+        if self.reached(t) or floor is None or (not t.get('trade_id')) or (t.get('state') != 'OPEN'):
+            return None
+        if not all((math.isfinite(float(v)) for v in (price, observed_ts))):
+            return None
+        moved = float(t['entry']) - price if t['direction'] == 'שורט' else price - float(t['entry'])
+        if price <= 0 or moved + 1e-09 < floor:
+            return None
+        if t.get('targets'):
+            final = float(t['targets'][-1][1])
+            final_gain = float(t['entry']) - final if t['direction'] == 'שורט' else final - float(t['entry'])
+            if final_gain < floor:
+                return None
+        level = float(t['entry']) + (-floor if t['direction'] == 'שורט' else floor)
+        proof = dict(version=VERSION, trade_id=t['trade_id'], trade_ts=float(t['ts']), symbol=t['symbol'], minimum_points=floor, price=level, observed_price=float(price), observed_ts=float(observed_ts), detected_ts=self.source.now_epoch(), source=source)
+        candidate = {**t, 'minimum_success': proof}
+        if not self.reached(candidate):
+            return None
+        t['minimum_success'] = proof
+        return voice.head('📈', t['symbol'], t['direction'], t['entry'], 'הושג הסף המינימלי · ' + voice.move(t['symbol'], floor)) + f'\n\nרמת הסף: {level:,.2f}\nהעסקה עמדה בסף ההצלחה של הדסק.' + '\n\nקידום סטופ לכניסה וניהול העסקה לשיקולכם.' + '\nהסטופ המקורי והיעדים נשארים במעקב.'
+
+    def observe_bars(self, t, df):
+        """Verified caller tape: exclude fill bar and everything from first stop."""
+        from . import lifecycle_bars as tracker
+        if self.reached(t) or df is None or df.empty:
+            return None
+        got = tracker.position_bars(df, t, include_fill_bar=True)
+        if got is None:
+            return None
+        bars, first = got
+        bars = bars[bars.index <= pd.Timestamp(self.source.now_utc())]
+        paying = bars.iloc[1:] if first else bars
+        short = t['direction'] == 'שורט'
+        stopped = bars['high'] >= float(t['stop']) if short else bars['low'] <= float(t['stop'])
+        if stopped.any():
+            paying = paying[paying.index < stopped[stopped].index[0]]
+        floor = minimum(t['symbol'])
+        if floor is None or paying.empty:
+            return None
+        if t.get('targets'):
+            final = float(t['targets'][-1][1])
+            final_gain = float(t['entry']) - final if short else final - float(t['entry'])
+            if final_gain < floor:
+                return None
+        column = 'low' if short else 'high'
+        gain = float(t['entry']) - paying[column] if short else paying[column] - float(t['entry'])
+        hits = paying[gain + 1e-09 >= floor]
+        if hits.empty:
+            return None
+        at = hits.index[0]
+        return self.observe(t, float(hits.loc[at, column]), self.source.now_epoch(), 'verified_post_fill_bars')
+
+    def classification(self, t, measurement=None):
+        """success / loss / unknown / open / not_entered / other."""
+        if self.reached(t):
+            return 'success'
+        m = measurement or {}
+        floor = minimum(t.get('symbol', t.get('canon', '')))
+        peak = m.get('peak')
+        if floor is not None and peak is not None and math.isfinite(peak):
+            if peak + 1e-09 >= floor:
+                return 'success'
+            if m.get('threshold_ambiguous'):
+                return 'unknown'
+            if str(t.get('result') or t.get('terminal_result', '')).startswith(('stopped', 'published_stop')) or t.get('state') == 'STOPPED':
+                return 'loss'
+            if t.get('state') in ('DONE', 'BE', 'CLOSED'):
+                return 'below_floor'
+        elif t.get('state') in ('STOPPED', 'DONE', 'BE'):
+            return 'unknown'
+        if t.get('state') == 'OPEN':
+            return 'open'
+        if t.get('state') in ('PENDING', 'CANCELLED', 'לא נכנסה'):
+            return 'not_entered'
+        return 'other'
+
+    def stop_note(self, t):
+        if not self.reached(t):
+            return ''
+        return f"\nניתן היה לקדם סטופ לכניסה לאחר {voice.dist(t['symbol'], minimum(t['symbol']))}."

```

```diff
diff --git a/tests/tree_replay/test_lifecycle_bars.py b/tests/tree_replay/test_lifecycle_bars.py
new file mode 100644
index 0000000..5e63812
--- /dev/null
+++ b/tests/tree_replay/test_lifecycle_bars.py
@@ -0,0 +1,110 @@
+"""Original position-window semantics, exercised on literal synthetic OHLC."""
+from datetime import datetime, timedelta, timezone
+import importlib
+import importlib.util
+
+import pandas as pd
+import pytest
+
+
+T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
+
+
+def api():
+    name = "trading_system.tree_replay._vendor.lifecycle_bars"
+    assert importlib.util.find_spec(name) is not None, "lifecycle geometry missing"
+    return importlib.import_module(name)
+
+
+def tape(rows):
+    # (minutes since T, high, low): close/open are inside each literal range.
+    return pd.DataFrame([dict(open=lo, high=hi, low=lo, close=hi) for _, hi, lo in rows],
+        index=pd.DatetimeIndex([T+timedelta(minutes=m) for m, _, _ in rows]))
+
+
+def trade(**changes):
+    return dict(symbol="OANDA:XAUUSD", direction="לונג", entry=100.,
+                state="PENDING", ts=T.timestamp()) | changes
+
+
+@pytest.mark.parametrize("side,rows,want", [
+    ("לונג", [(15, 120, 99), (30, 106, 100)], (106., 99.)),
+    ("שורט", [(15, 101, 80), (30, 100, 94)], (101., 94.)),
+    ("לונג", [(15, 120, 99)], (100., 99.)),
+    ("שורט", [(15, 101, 80)], (101., 100.)),
+])
+def test_fill_bar_counts_adversely_but_never_as_earned_movement(side, rows, want):
+    assert api()._open_extremes(tape(rows), trade(direction=side)) == want
+
+
+@pytest.mark.parametrize("side,rows,minute", [
+    ("לונג", [(-15, 120, 99), (0, 120, 99), (15, 110, 103), (30, 110, 102)], 30),
+    ("שורט", [(-15, 101, 80), (0, 101, 80), (15, 97, 90), (30, 98, 90)], 30),
+])
+def test_touch_uses_source_zone_edges_and_strictly_after_send(side, rows, minute):
+    assert api()._fill_on_tape(tape(rows), trade(direction=side)) == pd.Timestamp(T+timedelta(minutes=minute))
+
+
+@pytest.mark.parametrize("side,rows", [
+    ("לונג", [(0, 120, 99), (15, 110, 102.01)]),
+    ("שורט", [(0, 101, 80), (15, 97.99, 90)]),
+])
+def test_no_postsend_touch_returns_none_not_a_position(side, rows):
+    b, t = api(), trade(direction=side)
+    assert b._fill_on_tape(tape(rows), t) is None
+    assert b.position_bars(tape(rows), t) is None
+    assert b._open_extremes(tape(rows), t) is None
+
+
+@pytest.mark.parametrize("include,fill_minute,want_start,first", [
+    (False, 15, 15, False), (False, 16, 30, False),
+    (True, 15, 15, True), (True, 16, 15, True),
+])
+def test_open_fill_stamp_and_include_fill_bar_select_distinct_windows(include, fill_minute, want_start, first):
+    df = tape([(0, 150, 50), (15, 101, 99), (30, 106, 100)])
+    t = trade(state="OPEN", filled_ts=(T+timedelta(minutes=fill_minute)).timestamp())
+    got, flag = api().position_bars(df, t, include_fill_bar=include)
+    assert got.index[0] == pd.Timestamp(T+timedelta(minutes=want_start)) and flag is first
+    assert got.index[-1] == pd.Timestamp(T+timedelta(minutes=30))
+
+
+def test_open_fill_inside_last_bar_never_falls_back_to_send_extremes():
+    t = trade(state="OPEN", filled_ts=(T+timedelta(minutes=16)).timestamp())
+    df = tape([(0, 150, 50), (15, 105, 98)])
+    got, first = api().position_bars(df, t)
+    assert list(got.index) == [pd.Timestamp(T+timedelta(minutes=15))] and first
+    assert api()._open_extremes(df, t) == (100., 98.)
+
+
+def test_open_without_fill_stamp_uses_actual_first_tape_touch():
+    df = tape([(15, 110, 103), (30, 109, 101), (45, 108, 102)])
+    got, first = api().position_bars(df, trade(state="OPEN"))
+    assert got.index[0] == pd.Timestamp(T+timedelta(minutes=30)) and first
+    assert api()._open_extremes(df, trade(state="OPEN")) == (108., 101.)
+
+
+def test_full_life_mode_without_containing_fill_bar_has_no_window():
+    df = tape([(15, 109, 100)])
+    t = trade(state="OPEN", filled_ts=(T+timedelta(minutes=10)).timestamp())
+    assert api().position_bars(df, t, include_fill_bar=True) is None
+
+
+@pytest.mark.parametrize("side,want", [("לונג", (120., 99.)), ("שורט", (120., 99.))])
+def test_window_already_after_fill_earns_its_first_bar(side, want):
+    assert api()._position_extremes(tape([(15, 120, 99)]), trade(direction=side), fill_bar_first=False) == want
+
+
+def test_source_fill_error_catch_and_empty_window_remain_distinct():
+    b = api()
+    assert b._fill_on_tape(pd.DataFrame(), trade()) is None
+    assert b._fill_on_tape(tape([(15, 110, 99)]), {"entry": 100.}) is None
+    assert b.position_bars(pd.DataFrame(), trade()) is None
+    with pytest.raises(ValueError, match="max"):
+        b.position_bars(tape([]), trade(state="OPEN", filled_ts=T.timestamp()))
+
+
+def test_explicit_source_band_and_unknown_symbol_point_fallback():
+    b = api()
+    assert b._entry_band(trade()) == (98., 102.)
+    assert b._entry_band(trade(symbol="UNKNOWN")) == (100., 100.)
+    assert b._entry_band({"entry": "123.5"}) == (123.5, 123.5)

```

```diff
diff --git a/tests/tree_replay/test_desk_success.py b/tests/tree_replay/test_desk_success.py
new file mode 100644
index 0000000..24e8d46
--- /dev/null
+++ b/tests/tree_replay/test_desk_success.py
@@ -0,0 +1,204 @@
+"""Original movement proof is identity-bound and never changes economic state."""
+from copy import deepcopy
+from datetime import datetime, timedelta, timezone
+import importlib
+import importlib.util
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay.clock import ReplayClock
+
+
+T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
+NOW = T+timedelta(minutes=45)
+
+
+def api():
+    name = "trading_system.tree_replay._vendor.desk_success"
+    assert importlib.util.find_spec(name) is not None, "desk movement source missing"
+    return importlib.import_module(name)
+
+
+class ClockPorts:
+    def __init__(self, at=NOW):
+        self.clock = ReplayClock(at)
+
+    def now_epoch(self):
+        return self.clock.now.timestamp()
+
+    def now_utc(self):
+        return self.clock.now
+
+
+def engine(at=NOW):
+    return api().DeskSuccess(ClockPorts(at))
+
+
+def trade(**changes):
+    return dict(symbol="OANDA:XAUUSD", direction="לונג", trade_id="trade-one",
+        ts=T.timestamp(), entry=100., stop=90., targets=[("TP1", 120.)],
+        state="OPEN", filled_ts=(T+timedelta(minutes=15)).timestamp()) | changes
+
+
+def tape(rows):
+    return pd.DataFrame([dict(open=lo, high=hi, low=lo, close=hi) for _, hi, lo in rows],
+        index=pd.DatetimeIndex([T+timedelta(minutes=m) for m, _, _ in rows]))
+
+
+def proof(**changes):
+    return dict(version="desk-minimum-2026-09-07", trade_id="trade-one",
+        trade_ts=T.timestamp(), symbol="OANDA:XAUUSD", minimum_points=4., price=104.,
+        observed_price=105., observed_ts=NOW.timestamp(), detected_ts=NOW.timestamp(),
+        source="exact_venue_quote") | changes
+
+
+@pytest.mark.parametrize("symbol,entry,price,stop,target,points,firstline", [
+    ("OANDA:XAUUSD", 100., 104., 90., 120., 4., "📈 XAUUSD BUY 100.00 · הושג הסף המינימלי · +40 פיפס"),
+    ("OANDA:NAS100USD", 1000., 1070., 900., 1200., 70., "📈 NAS100USD BUY 1,000.00 · הושג הסף המינימלי · +70 נק'"),
+    ("BINANCE:BTCUSDT", 1000., 1200., 500., 1500., 200., "📈 BTCUSDT BUY 1,000.00 · הושג הסף המינימלי · +200 נק'"),
+])
+def test_literal_instrument_floors_and_original_identity_first_units(symbol, entry, price, stop, target, points, firstline):
+    t = trade(symbol=symbol, entry=entry, stop=stop, targets=[("TP1", target)])
+    prior = deepcopy(t)
+    e = engine()
+    message = e.observe(t, price, NOW.timestamp(), "exact_venue_quote")
+    assert message.splitlines()[0] == firstline
+    assert t["minimum_success"]["minimum_points"] == points
+    assert t["minimum_success"]["price"] == price
+    assert {k: v for k, v in t.items() if k != "minimum_success"} == prior
+    assert e.reached(t) and e.classification(t) == "success"
+
+
+def test_mirror_short_records_threshold_not_best_price_and_remains_open():
+    e, t = engine(), trade(direction="שורט", stop=110., targets=[("TP1", 80.)])
+    message = e.observe(t, 95., NOW.timestamp(), "exact_venue_quote")
+    assert message.startswith("📈 XAUUSD SELL 100.00 · הושג הסף המינימלי · +40 פיפס")
+    assert t["minimum_success"]["price"] == 96. and t["minimum_success"]["observed_price"] == 95.
+    assert t["state"] == "OPEN" and t["stop"] == 110.
+
+
+@pytest.mark.parametrize("field,value", [
+    ("version", "old"), ("trade_id", "different"), ("trade_ts", T.timestamp()-1),
+    ("symbol", "GC"), ("minimum_points", 5.), ("source", "unverified_quote"),
+    ("observed_ts", T.timestamp()-1), ("observed_ts", NOW.timestamp()+1),
+    ("price", float("nan")), ("price", float("inf")), ("price", 0.), ("price", 103.99),
+])
+def test_proof_identity_chronology_source_and_actual_movement_are_checked(field, value):
+    assert engine().reached(trade(minimum_success=proof(**{field: value}))) is False
+
+
+def test_proof_time_boundaries_explicit_asof_and_resolved_horizon():
+    e = engine()
+    t = trade(minimum_success=proof(observed_ts=T.timestamp()))
+    assert e.reached(t, as_of=T.timestamp())
+    t["minimum_success"] = proof()
+    assert not e.reached(t, as_of=NOW.timestamp()-1)
+    assert e.reached(t, as_of=NOW.timestamp())
+    t["resolved_ts"] = NOW.timestamp()-1
+    assert not e.reached(t)
+    t["resolved_ts"] = NOW.timestamp()
+    assert e.reached(t)
+
+
+@pytest.mark.parametrize("change,price,observed,source", [
+    (dict(symbol="GC"), 104., NOW.timestamp(), "exact_venue_quote"),
+    (dict(trade_id=""), 104., NOW.timestamp(), "exact_venue_quote"),
+    (dict(state="PENDING"), 104., NOW.timestamp(), "exact_venue_quote"),
+    (dict(targets=[("TP1", 103.)]), 104., NOW.timestamp(), "exact_venue_quote"),
+    ({}, 103.99, NOW.timestamp(), "exact_venue_quote"),
+    ({}, 104., NOW.timestamp()+1, "exact_venue_quote"),
+    ({}, 104., T.timestamp()-1, "exact_venue_quote"),
+    ({}, 104., NOW.timestamp(), "invented_source"),
+    ({}, float("inf"), NOW.timestamp(), "exact_venue_quote"),
+    ({}, 104., float("nan"), "exact_venue_quote"),
+])
+def test_invalid_new_observation_cannot_mutate_trade(change, price, observed, source):
+    e, t = engine(), trade(**change)
+    prior = deepcopy(t)
+    assert e.observe(t, price, observed, source) is None
+    assert t == prior
+
+
+def test_sticky_valid_proof_survives_later_stop_but_does_not_reemit_success():
+    e, t = engine(), trade(minimum_success=proof())
+    prior = deepcopy(t["minimum_success"])
+    assert e.observe(t, 110., NOW.timestamp(), "exact_venue_quote") is None
+    assert t["minimum_success"] == prior
+    t.update(state="STOPPED", resolved_ts=NOW.timestamp()+1)
+    assert e.classification(t) == "success"
+    assert e.stop_note(t) == "\nניתן היה לקדם סטופ לכניסה לאחר 40 פיפס."
+    assert t["stop"] == 90.  # Source note is advice, not an economic stop update.
+
+
+@pytest.mark.parametrize("rows,want", [
+    ([(15, 120, 99)], False),
+    ([(15, 120, 99), (30, 103.99, 100)], False),
+    ([(15, 120, 99), (30, 104, 100)], True),
+    ([(15, 120, 90), (30, 104, 100)], False),
+    ([(15, 120, 99), (30, 104, 90)], False),
+    ([(15, 120, 99), (30, 103, 90), (45, 104, 100)], False),
+    ([(15, 120, 99), (30, 104, 100), (45, 105, 90)], True),
+    ([(15, 120, 99), (60, 104, 100)], False),
+])
+def test_real_bar_consumer_excludes_fill_bar_stop_bar_and_future_rows(rows, want):
+    e, t = engine(), trade()
+    message = e.observe_bars(t, tape(rows))
+    assert bool(message) is want
+    assert ("minimum_success" in t) is want
+    if want:
+        assert t["minimum_success"] == proof(source="verified_post_fill_bars", observed_price=104.)
+        assert t["minimum_success"]["observed_ts"] == NOW.timestamp()  # not the 16:30 bar stamp.
+    assert t["state"] == "OPEN" and t["stop"] == 90.
+
+
+def test_short_bar_threshold_and_stop_order_are_mirrored():
+    e = engine()
+    t = trade(direction="שורט", stop=110., targets=[("TP1", 80.)])
+    assert e.observe_bars(t, tape([(15, 101, 80), (30, 100, 96)]))
+    assert t["minimum_success"]["price"] == 96.
+    fresh = trade(direction="שורט", stop=110., targets=[("TP1", 80.)])
+    assert e.observe_bars(fresh, tape([(15, 101, 80), (30, 110, 96)])) is None
+
+
+def test_future_row_cutoff_uses_exact_datetime_not_float_rounded_epoch():
+    at = NOW.replace(microsecond=123456)
+    df = tape([(15, 120, 99), (30, 104, 100)])
+    df.index = pd.DatetimeIndex([T+timedelta(minutes=15), at+timedelta(microseconds=1)])
+    e, t = engine(at), trade()
+    assert e.observe_bars(t, df) is None
+    e.source.clock.advance_to(at+timedelta(microseconds=1))
+    assert e.observe_bars(t, df)
+
+
+@pytest.mark.parametrize("state,measurement,want", [
+    ("OPEN", None, "open"), ("PENDING", None, "not_entered"), ("CANCELLED", None, "not_entered"),
+    ("STOPPED", None, "unknown"), ("DONE", None, "unknown"), ("OTHER", None, "other"),
+    ("STOPPED", {"peak": 3.}, "loss"), ("DONE", {"peak": 3.}, "below_floor"),
+    ("STOPPED", {"peak": 4.}, "success"),
+    ("STOPPED", {"peak": 3., "threshold_ambiguous": True}, "unknown"),
+])
+def test_classification_is_source_movement_status_not_automatic_profit_label(state, measurement, want):
+    assert engine().classification(trade(state=state), measurement) == want
+
+
+def test_missing_or_empty_tape_does_not_create_proof_or_advice():
+    e, t = engine(), trade()
+    assert e.observe_bars(t, None) is None
+    assert e.observe_bars(t, pd.DataFrame()) is None
+    assert e.stop_note(t) == "" and not e.reached(t)
+
+
+@pytest.mark.parametrize("method,args,want", [
+    ("head", ("▶️", "OANDA:XAUUSD", "שורט", 4373.35, "נכנסה"), "▶️ XAUUSD SELL 4,373.35 · נכנסה"),
+    ("moved_from_entry", ("OANDA:XAUUSD", "שורט", 100., 99.), "+10 פיפס"),
+    ("moved_from_entry", ("OANDA:XAUUSD", "לונג", 100., 100.01), "בכניסה"),
+    ("widen_line", ("OANDA:XAUUSD", "הורחב ל-8 מקצה הטווח"), "הסטופ הורחב ל-80 פיפס מקצה האזור"),
+    ("widen_line", ("OANDA:XAUUSD", "ללא הרחבה"), None),
+    ("rung_points", (100., .2, 3), .6),
+])
+def test_real_voice_identity_units_and_management_geometry(method, args, want):
+    name = "trading_system.tree_replay._vendor.lifecycle_voice"
+    assert importlib.util.find_spec(name) is not None, "lifecycle voice missing"
+    got = getattr(importlib.import_module(name), method)(*args)
+    assert got == (pytest.approx(want) if type(want) is float else want)

```

```diff
diff --git a/docs/architecture/BAR-LIFECYCLE-PRIMITIVES-USAGE.md b/docs/architecture/BAR-LIFECYCLE-PRIMITIVES-USAGE.md
new file mode 100644
index 0000000..cfcec91
--- /dev/null
+++ b/docs/architecture/BAR-LIFECYCLE-PRIMITIVES-USAGE.md
@@ -0,0 +1,57 @@
+# Original bar geometry and movement proof
+
+Private offline projections of chart-desk at commit
+68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9. Contract:
+BAR-LIFECYCLE-PRIMITIVES-CONTRACT.md. These are source primitives, not a public
+historical replay engine, execution simulator or training-data generator.
+
+`_vendor.lifecycle_bars` exposes the five original position-window functions.
+The supplied frame and source trade row remain caller-owned. Pending touch is
+strictly after send; OPEN/filled_ts selection and include_fill_bar differ as in
+the source. A included fill bar contributes adverse but not favourable extremes.
+Do not apply these raw helpers to unvalidated or future tape and infer causality.
+Original exception handling remains: for example an empty OPEN frame with a
+filled timestamp can raise ValueError in position_bars, while _fill_on_tape
+catches invalid input and returns None.
+
+`_vendor.desk_success.DeskSuccess(source)` requires explicit clock ports:
+
+```python
+class ClockPorts:
+    def __init__(self, replay_clock):
+        self.clock = replay_clock
+    def now_epoch(self):
+        return self.clock.now.timestamp()
+    def now_utc(self):
+        return self.clock.now
+```
+
+Both must refer to the same operation clock; now_utc returns an aware UTC
+datetime. There is no wall-clock fallback or implicit integration with the
+admission context. The source's as_of truthiness and numeric behavior are kept.
+
+Methods: reached, observe, observe_bars, classification, stop_note. The module
+retains minimum(symbol), VERSION and FLOOR. observe requires caller-certified
+post-fill ordering and venue; it does not establish either from an arbitrary
+price. observe_bars uses actual position_bars(include_fill_bar=True), excludes
+future timestamps, the fill bar from favourable movement, and the first stop
+bar and all later bars. The proof's observed/detected times are operation times,
+not inferred intrabar crossings. Explicit now_utc avoids a rounded epoch cutoff.
+
+Only minimum_success is added to an eligible trade by observe. Proof identity,
+symbol, minimum distance, allowed evidence tag and source/resolved chronology
+must validate. A valid proof stays sticky even if the trade later stops; it is
+not a profitable-trade label. Original stop, targets and advisory state remain
+unchanged. Advice to move a stop does not execute a move. Source classification
+can use a caller measurement, which is not independently certified history.
+
+The complete original pure lifecycle_voice preserves identity-first messages
+and instrument units needed by later message parsers. No notifications are sent.
+audited_classification and its external historical-report dependencies are not
+included. Inherited pricing/canonical-symbol calculations remain original.
+
+Verification uses hand-derived real pandas/ReplayClock cases, source AST audit
+and independent review. Current scope leaves causal lifecycle feed binding,
+revalidation, independent claim verification, stateful resolver/caller and
+economic outcomes/dataset/model work open. Component acceptance is recorded in
+agent-exchange/status, never inferred from this usage file or green tests alone.

```
