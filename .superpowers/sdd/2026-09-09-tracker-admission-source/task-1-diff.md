# Task 1 review package

BASE/HEAD: c1b6071633c55376c64f0a98ece843706f420f49; no commits. All eight files are new/untracked; full new-file diffs against NUL below. Only current renamed test path is used. Source runtime/auditor hashes unchanged by rename (see report addendum).

```diff
warning: in the working copy of 'trading_system/tree_replay/_vendor/tracker_admission.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/tracker_admission.py b/trading_system/tree_replay/_vendor/tracker_admission.py
new file mode 100644
index 0000000..190bcd4
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tracker_admission.py
@@ -0,0 +1,550 @@
+"""Private pinned tracker decisions on explicit offline ports. No lifecycle or readiness."""
+from __future__ import annotations
+import json
+import hashlib
+import math
+from io import BytesIO
+import pandas as pd
+from . import basis_symbols as basis
+from .pricing import entry_zone
+MAX_STOP_BLOCK_H = 4.0
+QUOTE_MAX_AGE_S = 420.0
+LEVEL_COOLDOWN_S = 2 * 3600.0
+WEAK_GATE = 25.0
+THESIS_RECOVER = 0.0
+
+
+def _trade_identity(symbol: str, direction: str, entry: float, stop: float, targets: list, style: str) -> tuple[str, str]:
+    """Stable (state key, receipt id) for one exact trade geometry."""
+    canonical = basis.canonical_symbol(symbol)
+    geometry = {
+        'symbol': canonical,
+        'direction': direction,
+        'entry': round(float(entry), 8),
+        'stop': round(float(stop), 8),
+        'targets': [round(float(px), 8) for _name, px in targets or []],
+        'style': (style or 'intraday').lower(),
+    }
+    digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]
+    key = f"{canonical}:{direction}:{round(float(entry), 2)}:{geometry['style']}:{digest}"
+    return (key, digest)
+
+
+def _anchor_names(reasons) -> set[str] | None:
+    """See entry_quality.anchor_names — ONE parser, imported, not restated."""
+    from .admission_quality import anchor_names
+    return anchor_names(reasons)
+
+
+def _tail_reader(open_reader, window: int=400000, cap: int=8000000) -> bytes | None:
+    """The last `window` bytes of a JSONL file, whole lines only.
+
+    This was `read_bytes()[-window:]`, which loaded all 10 MB of watch_events
+    twice per plan AND — Codex's catch — silently returned NOTHING whenever
+    the final line was longer than the window: the slice began inside that
+    line, the leading partial was dropped, and every earlier rejection
+    disappeared with no error. Seek from the end, and widen until a line
+    boundary is actually inside the window rather than assuming one is.
+    """
+    try:
+        with open_reader() as fh:
+            fh.seek(0, 2)
+            size = fh.tell()
+            while True:
+                start = max(0, size - window)
+                fh.seek(start)
+                raw = fh.read()
+                if start == 0:
+                    return raw
+                cut = raw.find(b'\n')
+                if cut != -1 and cut + 1 < len(raw):
+                    return raw[cut + 1:]
+                if window >= cap:
+                    fh.seek(0)
+                    return fh.read()
+                window *= 4
+    except Exception:
+        return None
+
+
+def _tail_bytes(raw, window: int=400000, cap: int=8000000) -> bytes | None:
+    if raw is None:
+        return None
+    return _tail_reader(lambda: BytesIO(raw), window, cap)
+
+
+def born_in_zone(symbol: str, entry: float, close: float | None) -> bool:
+    """Was the plan built with price already inside its entry band?
+
+    Such a trade is active the moment it is sent; a ▶️ "המחיר הגיע לאזור"
+    ten seconds later tells the client nothing they did not just read
+    (three of the night's four fills, 2026-09-04). The signal says it
+    instead, and the tracker records the trade OPEN.
+    """
+    if not close:
+        return False
+    zlo, zhi = entry_zone(symbol, float(entry))
+    return zlo <= float(close) <= zhi
+
+
+def thesis_verdict(lo: float, direction: str) -> str | None:
+    """Classify a lower-net reading for a trade: 'broken', 'held', or None.
+
+    HYSTERESIS (2026-09-04). One threshold, WEAK_GATE, was both the break
+    and the recovery line, and gold sat ON it all night: -25, -29, -25, -30
+    against a gate of 25 gave five ⚠️/🔄 flips in an hour, none of which
+    was a change of anything. Break at -WEAK_GATE; recover only at
+    THESIS_RECOVER; in between the trade KEEPS whatever state it has, and
+    this returns None so the caller cannot mistake the deadband for either.
+    The desk reports direction, the client decides -- this is a reading,
+    never an instruction.
+    """
+    signed = lo * (1 if direction == 'לונג' else -1)
+    if signed <= -WEAK_GATE:
+        return 'broken'
+    if signed >= THESIS_RECOVER:
+        return 'held'
+    return None
+
+
+class TrackerAdmission:
+
+    def __init__(self, source):
+        self.source = source
+
+    def record(self, plan, *, variant: str='engine', to_group: bool=False) -> bool:
+        """Register a trade for outcome tracking.
+
+    Failures intentionally propagate. A caller must never publish or queue an
+    entry after tracking failed; swallowing this error is how a shipped trade
+    becomes invisible for its entire move.
+    """
+        if not getattr(plan, 'entry', None) or not getattr(plan, 'stop', None):
+            return False
+        sym = basis.canonical_symbol(plan.symbol)
+        bias_at_send = self._higher_bias(sym)
+        thesis = self._thesis_baseline(sym, plan.direction)
+        born = self._born_in_zone(plan, sym)
+        try:
+            plan.born_open = born
+        except Exception:
+            pass
+        with self.source.locked():
+            return self._record_locked(plan, variant, to_group, bias_at_send, thesis, born)
+
+    def _born_in_zone(self, plan, sym: str) -> bool:
+        """Is this trade active from the send? The build's close must sit inside
+    the entry band AND the live tap must say the band has been reached.
+
+    The build's close alone is the state of the tape when the plan was
+    made; build_all() makes every symbol and style before market_watch
+    records any of them, so by record() the price can have left the band
+    (Codex, 2026-09-04). A fresh quote that disagrees means PENDING and the
+    fill machinery takes over -- an extra ▶️ is a true message, a wrong
+    "פעילה" is not. A stale or missing quote defers to the build.
+
+    "Reached" is check_live's own one-sided fill test (a short fills at or
+    above the band's floor, a long at or below its ceiling), not "inside
+    the band": a short built at 4,600 with the tap at 4,603 would otherwise
+    be recorded PENDING here and filled by the very next pass -- a ▶️ under
+    a signal that already said the trade is active (Codex, second pass).
+    """
+        try:
+            if not born_in_zone(plan.symbol, plan.entry, getattr(plan, 'close', None)):
+                return False
+            spot = self._live_prices().get(sym)
+            if spot is None:
+                return True
+            zlo, zhi = self._entry_band({'symbol': plan.symbol, 'entry': plan.entry})
+            return spot >= zlo if plan.direction == 'שורט' else spot <= zhi
+        except Exception:
+            return False
+
+    def _record_locked(self, plan, variant: str, to_group: bool, bias_at_send: dict | None=None, thesis: str='held', born: bool=False) -> bool:
+        d = self.source.load()
+        if self.has_open(basis.canonical_symbol(plan.symbol), plan.direction, state=d):
+            return False
+        _style = getattr(plan, 'style', 'intraday')
+        key, trade_id = _trade_identity(plan.symbol, plan.direction, plan.entry, plan.stop, plan.targets, _style)
+        prev = d.get(key)
+        if prev is not None:
+            if prev.get('state') in ('PENDING', 'OPEN'):
+                return False
+            d[f"{key}@{int(prev.get('ts', 0))}"] = prev
+        if True:
+            d[key] = {
+                'symbol': basis.canonical_symbol(plan.symbol),
+                'direction': plan.direction,
+                'entry': float(plan.entry), 'stop': float(plan.stop),
+                'targets': [[n, float(p)] for n, p in plan.targets],
+                'obstacles': [[n, float(p)] for n, p in getattr(plan, 'obstacles', None) or []],
+                'reasons': [str(r) for r in getattr(plan, 'reasons', None) or []],
+                'variant': variant, 'to_group': bool(to_group),
+                'style': getattr(plan, 'style', 'intraday'),
+                'trade_id': trade_id, 'kind': getattr(plan, 'kind', 'trend'),
+                'state': 'PENDING', 'hit': [], 'ts': self.source.now_epoch(),
+                'thesis_state': thesis, 'thesis_warned': False,
+            }
+            if born:
+                d[key]['state'] = 'OPEN'
+                d[key]['born_in_zone'] = True
+                d[key]['revalidation_verified'] = False
+                d[key]['fill_verification_reason'] = 'born_open_not_broker_verified'
+                d[key]['filled_ts'] = d[key]['progress_ts'] = d[key]['ts']
+            if bias_at_send:
+                d[key]['bias_at_send'] = bias_at_send
+            self.source.save(d)
+            return True
+
+    def _entry_band(self, t: dict) -> tuple[float, float]:
+        """The price band that fills this trade. Falls back to the exact level."""
+        try:
+            from .pricing import entry_zone
+            return entry_zone(t['symbol'], float(t['entry']))
+        except Exception:
+            e = float(t['entry'])
+            return (e, e)
+
+    def has_open(self, symbol: str, direction: str | None=None, *, state: dict | None=None) -> bool:
+        """Does an actually filled position occupy this symbol/side?
+
+    A PENDING retest is a plan, not exposure. Sagiv's 2026-09-07 ruling:
+    pending scalp/intraday/swing plans may coexist and must not suppress a
+    fresh valid plan. Exact duplicate geometry is still refused by record();
+    once one plan fills, OPEN owns the direction slot.
+
+    Corrupt or unreadable state fails closed because it cannot prove there is
+    no open position. A row explicitly known to be PENDING never blocks.
+    """
+        try:
+            trades = state if state is not None else self.source.load()
+        except Exception:
+            return True
+        if not isinstance(trades, dict):
+            return True
+        for t_ in trades.values():
+            if not isinstance(t_, dict) or 'state' not in t_:
+                return True
+            if t_['state'] != 'OPEN':
+                continue
+            if 'symbol' not in t_:
+                return True
+            if t_['symbol'] != symbol:
+                continue
+            if direction is None:
+                return True
+            if 'direction' not in t_:
+                return True
+            if t_['direction'] == direction:
+                return True
+        return False
+
+    def _higher_bias(self, symbol: str) -> dict[str, float] | None:
+        """The higher-timeframe reading, {tf: net} for 4h and 1h. None = unread.
+
+    TFView exposes `net`, not `score` (a wrong name caught by reading the
+    source before deploying). One reader for the send and the fill, so the
+    two values still_valid compares were taken the same way.
+
+    Both frames or nothing. _bias_against needs every higher frame to side
+    against the trade; a reading with one frame missing would let the other
+    frame veto alone -- the 08-31 BTC sum-vote in a new shape.
+    """
+        tfs = ('4h', '1h')
+        try:
+            v = self.source.read_symbol(symbol, tfs=tfs)
+            nets = {tf: float(x.net) for tf, x in v.items() if x is not None}
+            return nets if all((tf in nets for tf in tfs)) else None
+        except Exception:
+            return None
+
+    def _live_prices(self) -> dict:
+        """Spot from HIS TradingView tap, only while genuinely fresh."""
+        out = {}
+        try:
+            d = self.source.quote_payload()
+        except Exception:
+            return out
+        now = self.source.now_epoch()
+        for sym, q in d.items():
+            try:
+                price = float(q.get('lp', 0))
+                age = now - float(q.get('ts', 0))
+                if math.isfinite(price) and price > 0 and (0 <= age <= QUOTE_MAX_AGE_S):
+                    out[sym] = price
+            except Exception:
+                continue
+        return out
+
+    def _thesis_baseline(self, symbol: str, direction: str) -> str:
+        """The thesis state a trade is BORN with, read at record time.
+
+    Not at the first post-fill read: a trade sent aligned that fills an
+    hour later, after the short frames reversed, would have its reversal
+    swallowed as the baseline. A trap reversal is born with the short
+    frames against it by construction -- that is stored as 'broken' and
+    never warned about (it was the setup), and when they join the trade
+    the client hears that they joined, not that something 'recovered'.
+    Unreadable tape defaults to 'held': the conservative side is a warning
+    the client can weigh, not a silence.
+    """
+        try:
+            now = self.thesis_now(symbol)
+            if now is None:
+                return 'held'
+            return thesis_verdict(now[1], direction) or 'held'
+        except Exception:
+            return 'held'
+
+    def _recent_rejection(self, symbol: str, direction: str, stopped_ts: float, asof_ts: float, entry: float, max_age_s: float=20 * 60, require_overlap: bool=True, max_distance: float | None=None) -> dict | None:
+        """The newest logged rejection that could have informed this entry.
+
+    CAUSAL, not retrospective: only rows already written when the plan was
+    built count. On 2026-09-04 the 10:07 rejection at 4,461.69–4,462.54
+    supports the 10:07–10:19 longs and says nothing about the 10:01 one --
+    it did not exist yet -- which is exactly why the release rule below does
+    not depend on it.
+
+    Two callers, two geometries. A rejection that AGREES with a trade has to
+    be where the trade is (`require_overlap`) -- support you are buying. A
+    rejection that argues AGAINST it does not: the cluster the 10:25 short
+    sold into sat five points below its entry and outside its zone, and that
+    is precisely the distance that made it dangerous. `max_distance` bounds
+    how far away "against this trade" still reaches.
+    """
+        raw = _tail_reader(self.source.event_log_reader)
+        if raw is None:
+            return None
+        zlo, zhi = (0.0, 0.0)
+        try:
+            from .pricing import entry_zone
+            zlo, zhi = entry_zone(symbol, float(entry))
+        except Exception:
+            pass
+        canon = basis.canonical_symbol(symbol)
+        best, best_gap = (None, 0.0)
+        for line in raw.decode('utf-8', 'ignore').splitlines():
+            if '"rejection"' not in line:
+                continue
+            try:
+                r = json.loads(line)
+            except Exception:
+                continue
+            if r.get('kind') != 'rejection' or r.get('direction') != direction:
+                continue
+            if basis.canonical_symbol(str(r.get('symbol', ''))) != canon:
+                continue
+            ts = float(r.get('ts', 0.0))
+            if not stopped_ts <= ts <= asof_ts or asof_ts - ts > max_age_s:
+                continue
+            lo, hi = (r.get('zone_lo'), r.get('zone_hi'))
+            gap = 0.0
+            if zhi > zlo and isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
+                gap = max(zlo - float(hi), float(lo) - zhi, 0.0)
+                if gap > 0:
+                    if require_overlap:
+                        continue
+                    if max_distance is not None and gap > float(max_distance):
+                        continue
+            if best is None or ts > float(best.get('ts', 0.0)):
+                best, best_gap = (r, gap)
+        if best is None:
+            return None
+        out = {k: best.get(k) for k in ('ts', 'direction', 'zone_lo', 'zone_hi', 'levels', 'close', 'wick_atr')}
+        out['age_s'] = round(asof_ts - float(best.get('ts', asof_ts)), 1)
+        out['gap'] = round(best_gap, 4)
+        return out
+
+    def _cooldown_release(self, symbol: str, direction: str, plan, last: dict, stopped_ts: float, hours: float, asof: float | None=None) -> dict | None:
+        """Is this plan a NEW setup rather than the stopped one, re-priced?
+
+    Codex, leading the 2026-09-04 gold post-mortem, ruled the boundary is the
+    stop that rejected us. The morning supplies both cases: after the 4,475.01
+    long stopped at 4,465.51, the 08:23 rebuild at 4,471.56 sat ABOVE that
+    stop -- the same thesis at a better price, and the day low at 4,460.155
+    would have taken it out too. The 10:01 rebuild at 4,463.24 sat BELOW it:
+    price had traded through the invalidation, made a new low, and come back.
+    That is not a re-entry, it is a different trade at a different level.
+
+    The anchor and the rejection are recorded as telemetry so the exception
+    can be scored later. Neither may veto: requiring a logged rejection would
+    have released nothing before 10:07, and by 10:07 the target economics had
+    already moved the trade out of reach.
+    """
+        if plan is None:
+            return None
+        entry = getattr(plan, 'entry', None)
+        stop = getattr(plan, 'stop', None)
+        if entry is None:
+            return None
+        try:
+            entry = float(entry)
+            old_stop = float(last['stop'])
+        except (TypeError, ValueError, KeyError):
+            return None
+        if entry != entry or entry in (float('inf'), float('-inf')):
+            return None
+        if getattr(plan, 'direction', direction) != direction:
+            return None
+        try:
+            if basis.canonical_symbol(getattr(plan, 'symbol', symbol)) != basis.canonical_symbol(symbol):
+                return None
+        except Exception:
+            pass
+        try:
+            from . import tracker_symbols as _sym
+            pip = float(_sym.resolve(symbol).pip)
+        except Exception:
+            pip = 0.0
+        if direction == 'שורט':
+            crossed = entry >= old_stop + pip
+        else:
+            crossed = entry <= old_stop - pip
+        if not crossed:
+            return None
+        new_anchor = _anchor_names(getattr(plan, 'reasons', None))
+        old_anchor = _anchor_names(last.get('reasons'))
+        changed = None
+        if new_anchor is not None and old_anchor is not None:
+            changed = new_anchor != old_anchor
+        return {
+            'plan_entry': entry, 'plan_stop': None if stop is None else float(stop),
+            'stopped_trade_id': last.get('trade_id'), 'stopped_entry': last.get('entry'),
+            'stopped_stop': old_stop, 'stopped_resolved_ts': stopped_ts,
+            'hours_since_stop': round(hours, 2),
+            'boundary_margin': round(abs(entry - old_stop), 4),
+            'release_rule': 'entry_beyond_stopped_stop',
+            'new_anchor': sorted(new_anchor) if new_anchor else None,
+            'stopped_anchor': sorted(old_anchor) if old_anchor else None,
+            'anchor_changed': changed,
+            'recent_rejection': self._recent_rejection(
+                symbol, direction, stopped_ts,
+                self.source.now_epoch() if asof is None else float(asof), entry),
+        }
+
+    def blocked_after_stop(self, symbol: str, direction: str, plan=None) -> str | None:
+        """Refuse a re-entry on the same thesis until the STRUCTURE changes.
+
+    Sagiv, 2026-08-27, choosing between a fixed cooldown and a structural one:
+    *"צינון עד שהמבנה משתנה"*. The night before, a gold short stopped at 01:06
+    and an identical gold short went out at 01:12 -- same direction, same
+    reasoning, six minutes later, entry re-priced 30 points away. The slot
+    guard stops PARALLEL trades; it says nothing about a SEQUENCE.
+
+    A clock-based cooldown would have been the easy version and the wrong one:
+    an hour is arbitrary, and if the market genuinely turns in twenty minutes
+    the block is pure cost. What actually invalidates "the market already told
+    us no" is the market saying something new. So the block lifts on one of:
+
+      1. a NEW confirmed 15m swing has formed beyond the stopped trade's stop
+         -- structure has moved past the level that rejected us; or
+      2. the higher-timeframe bias has FLIPPED -- the thesis itself changed; or
+      3. MAX_STOP_BLOCK_H has elapsed, so a quiet tape cannot freeze the
+         instrument forever; or
+      4. the plan's own ENTRY lies beyond the stop that rejected us -- see
+         _cooldown_release. Added 2026-09-04, after the block refused three
+         gold longs at 4,462-4,463 (TP1 = DAY-OPEN, 1.35-1.47R) built on the
+         cluster London then opened on, and price ran to 4,490.9.
+
+    Returns a reason string while blocked, None when clear.
+    """
+        from . import admission_swing as zones
+        try:
+            last = None
+            for t in self.source.load().values():
+                if t['symbol'] == symbol and t['direction'] == direction and (t.get('state') == 'STOPPED'):
+                    if last is None or float(t.get('resolved_ts', t['ts'])) > float(last.get('resolved_ts', last['ts'])):
+                        last = t
+            if last is None:
+                return None
+            stopped_ts = float(last.get('resolved_ts', last['ts']))
+            hours = (self.source.now_epoch() - stopped_ts) / 3600.0
+            if hours >= MAX_STOP_BLOCK_H:
+                return None
+            short = direction == 'שורט'
+            try:
+                v = self.source.read_symbol(symbol, tfs=('4h', '1h'))
+                net = sum((x.net for x in v.values() if x is not None))
+                if net >= 25.0 and short or (net <= -25.0 and (not short)):
+                    return None
+            except Exception:
+                pass
+            try:
+                df, _c = self.source.fetch_corrected(symbol, '15m', 5)
+                idx = pd.to_datetime(df.index, utc=True)
+                after = df[[ts.timestamp() > stopped_ts for ts in idx]]
+                if len(after) >= 8:
+                    sw = zones._last_swing(after, up=short)
+                    if sw is not None:
+                        lvl = float(sw[0])
+                        moved = lvl > last['stop'] if short else lvl < last['stop']
+                        if moved:
+                            return None
+            except Exception:
+                pass
+            try:
+                rel = self._cooldown_release(symbol, direction, plan, last, stopped_ts, hours)
+            except Exception:
+                rel = None
+            if rel is not None:
+                try:
+                    plan.cooldown_release = rel
+                except Exception:
+                    pass
+                return None
+            return f'סטופ לפני {hours:.1f} שעות באותו כיוון — ממתינים לשינוי מבנה או להיפוך הטיה'
+        except Exception:
+            return None
+
+    def blocked_same_level(self, symbol: str, direction: str, entry: float) -> str | None:
+        """Refuse a plan whose entry sits inside the zone of a trade on the same
+    symbol+direction that finished (DONE / CANCELLED) within LEVEL_COOLDOWN_S.
+
+    Returns a reason string while blocked, None when clear. STOPPED is
+    blocked_after_stop's business; PENDING/OPEN is has_active's.
+    """
+        try:
+            from .pricing import entry_zone
+            now = self.source.now_epoch()
+            for t in self.source.load().values():
+                if not isinstance(t, dict) or t.get('symbol') != symbol:
+                    continue
+                if t.get('direction') != direction:
+                    continue
+                if t.get('state') not in ('DONE', 'CANCELLED'):
+                    continue
+                ended = float(t.get('resolved_ts') or 0.0)
+                if not ended or now - ended >= LEVEL_COOLDOWN_S:
+                    continue
+                lo, hi = entry_zone(symbol, float(t['entry']))
+                if lo <= float(entry) <= hi:
+                    mins = max(1, int((now - ended) // 60))
+                    return f"אותה רמה נסחרה זה עתה: {float(t['entry']):,.2f} סיימה לפני {mins} דק׳"
+            return None
+        except Exception:
+            return None
+
+    def thesis_now(self, symbol: str) -> tuple[float, float, float] | None:
+        """The bias reading RIGHT NOW: (higher net, lower net, bar_ts).
+
+    WHY THIS EXISTS. 2026-09-01: a NAS100 long and a BTC long both ran to
+    their stops, and this reading called it 90 minutes early on BOTH. The
+    lower net went +29.7 -> -60.0 on the Nasdaq and -6.6 -> -66.7 on BTC
+    while the higher-timeframe net sat frozen at 42.5 and 46.2 and the
+    direction, which is taken from the higher net alone, never changed.
+    The desk owned the rule -- `weak` in build(), the same WEAK_GATE -- but
+    computed it ONCE, at birth, and nothing read it again.
+
+    The lower net is the SAME (30m+15m+5m)/3 that build() gates on, so a
+    trade born aligned and a trade read later are judged by one number
+    (2026-09-04; the first version averaged 15m/5m only and disagreed with
+    the gate that had passed the trade). bar_ts is the epoch of the newest
+    5m bar the reads came from -- a transition is confirmed by BARS, not
+    by wall-clock minutes. Returns None when the tape cannot be read: an
+    outage must not be able to look like a reversal, or like a recovery.
+    """
+        try:
+            v = self.source.read_symbol(symbol, tfs=('4h', '1h', '30m', '15m', '5m'))
+            return ((v['4h'].net + v['1h'].net) / 2.0, (v['30m'].net + v['15m'].net + v['5m'].net) / 3.0, float(v['5m'].bar_ts))
+        except Exception:
+            return None
warning: in the working copy of 'trading_system/tree_replay/_vendor/tracker_symbols.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/tracker_symbols.py b/trading_system/tree_replay/_vendor/tracker_symbols.py
new file mode 100644
index 0000000..a8eb39f
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tracker_symbols.py
@@ -0,0 +1,222 @@
+"""Symbol identity: TradingView tickers in, Yahoo tickers and asset facts out.
+
+The bridge reads whatever symbol the user has open in TradingView Desktop
+("OANDA:XAUUSD", "BINANCE:BTCUSDT", "NASDAQ:AAPL"). The analysis engine needs
+Yahoo tickers. This module is the translation layer, and it also answers the
+questions every downstream module asks about an instrument: what asset class is
+it, what is a pip worth, how many decimals do I print, does it trade weekends.
+
+Getting the asset class right matters more than it looks. Session logic,
+psychological-level spacing and range statistics all behave differently for a
+24/7 crypto pair than for a US equity with a 6.5-hour cash session.
+"""
+
+from __future__ import annotations
+
+import re
+from dataclasses import dataclass, asdict
+
+__all__ = ["Instrument", "resolve", "to_yahoo", "asset_class"]
+
+
+# ======================================================================
+# tables
+# ======================================================================
+
+# TradingView index / CFD tickers that have no mechanical mapping.
+_INDEX_MAP = {
+    "SPX": "^GSPC", "SPX500": "^GSPC", "SPX500USD": "^GSPC", "US500": "^GSPC",
+    "ES1!": "ES=F", "MES1!": "ES=F",
+    "NDX": "^NDX", "NAS100": "NQ=F", "NAS100USD": "NQ=F", "US100": "NQ=F",
+    "NQ1!": "NQ=F", "MNQ1!": "NQ=F",
+    "DJI": "^DJI", "US30": "^DJI", "YM1!": "YM=F",
+    "RUT": "^RUT", "US2000": "^RUT", "RTY1!": "RTY=F",
+    "VIX": "^VIX", "VX1!": "^VIX",
+    "DXY": "DX-Y.NYB", "USDX": "DX-Y.NYB", "DX1!": "DX=F",
+    "DAX": "^GDAXI", "GER40": "^GDAXI", "DE40": "^GDAXI", "FDAX1!": "^GDAXI",
+    "UKX": "^FTSE", "UK100": "^FTSE",
+    "NI225": "^N225", "JP225": "^N225",
+    "HSI": "^HSI", "HK50": "^HSI",
+    "CAC40": "^FCHI", "FRA40": "^FCHI",
+    "STOXX50E": "^STOXX50E", "EU50": "^STOXX50E",
+    "TA35": "^TA125.TA", "TA125": "^TA125.TA",
+    "US10Y": "^TNX", "US02Y": "^IRX", "US30Y": "^TYX",
+}
+
+# Metals and energy quoted as FX-style pairs in TradingView.
+_COMMODITY_PAIR_MAP = {
+    "XAUUSD": "GC=F", "GOLD": "GC=F", "GC1!": "GC=F", "MGC1!": "GC=F",
+    "XAGUSD": "SI=F", "SILVER": "SI=F", "SI1!": "SI=F",
+    "XPTUSD": "PL=F", "XPDUSD": "PA=F",
+    "USOIL": "CL=F", "WTICOUSD": "CL=F", "CL1!": "CL=F", "MCL1!": "CL=F",
+    "UKOIL": "BZ=F", "BCOUSD": "BZ=F", "BRENT": "BZ=F",
+    "NATGAS": "NG=F", "NGAS": "NG=F", "NG1!": "NG=F",
+    "COPPER": "HG=F", "HG1!": "HG=F",
+    "XCUUSD": "HG=F",
+    "ZC1!": "ZC=F", "ZW1!": "ZW=F", "ZS1!": "ZS=F",
+}
+
+_FIAT = {
+    "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK",
+    "DKK", "PLN", "HUF", "CZK", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNH",
+    "CNY", "ILS", "INR", "KRW", "BRL", "RUB",
+}
+
+_STABLE = {"USDT", "USDC", "BUSD", "TUSD", "DAI", "FDUSD", "USDD"}
+
+# Crypto bases we accept without a stablecoin suffix hint.
+_CRYPTO_BASES = {
+    "BTC", "XBT", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE", "DOT",
+    "MATIC", "LINK", "LTC", "BCH", "ATOM", "UNI", "TRX", "ETC", "XLM", "NEAR",
+    "APT", "ARB", "OP", "SUI", "INJ", "TIA", "SEI", "FIL", "ICP", "HBAR",
+    "RNDR", "IMX", "AAVE", "MKR", "SHIB", "PEPE", "WIF", "TON", "KAS",
+}
+
+# Exchange prefixes that tell us the class outright.
+_CRYPTO_EXCHANGES = {
+    "BINANCE", "BINANCEUS", "COINBASE", "BITSTAMP", "BITFINEX", "KRAKEN",
+    "BYBIT", "OKX", "KUCOIN", "GEMINI", "HUOBI", "MEXC", "BITGET", "CRYPTO",
+    "BITMEX", "DERIBIT", "PHEMEX", "GATEIO", "UPBIT", "CRYPTOCAP",
+}
+_FX_EXCHANGES = {"OANDA", "FX", "FX_IDC", "FOREXCOM", "SAXO", "PEPPERSTONE",
+                 "ICMARKETS", "EIGHTCAP", "VANTAGE", "CURRENCYCOM", "ACTIVTRADES"}
+_EQUITY_EXCHANGES = {"NASDAQ", "NYSE", "AMEX", "ARCA", "BATS", "OTC", "CBOE",
+                     "LSE", "XETR", "FWB", "TSX", "TSXV", "ASX", "TASE", "EURONEXT"}
+
+
+@dataclass(frozen=True)
+class Instrument:
+    """Everything downstream code needs to know about one instrument."""
+
+    tv_symbol: str          # as typed / as read from TradingView, e.g. OANDA:XAUUSD
+    yahoo: str              # Yahoo Finance ticker, e.g. GC=F
+    base: str               # symbol without the exchange prefix
+    exchange: str | None    # exchange prefix, if there was one
+    asset_class: str        # equity | index | fx | crypto | commodity | rates
+    quote_ccy: str          # currency the price is quoted in
+    pip: float              # one pip in price units (FX convention; else one tick)
+    digits: int             # sensible display precision
+    trades_weekends: bool   # crypto true, everything else false
+    session: str            # 24h | fx_week | rth  -- how the clock behaves
+
+    def as_dict(self) -> dict:
+        return asdict(self)
+
+    @property
+    def is_24h(self) -> bool:
+        return self.session in ("24h", "fx_week")
+
+
+# ======================================================================
+# resolution
+# ======================================================================
+
+def _split(symbol: str) -> tuple[str | None, str]:
+    """'BINANCE:BTCUSDT' -> ('BINANCE', 'BTCUSDT'); 'AAPL' -> (None, 'AAPL')."""
+    s = symbol.strip().upper().replace(" ", "")
+    if ":" in s:
+        ex, _, base = s.partition(":")
+        return ex or None, base
+    return None, s
+
+
+def _fx_pair(base: str) -> tuple[str, str] | None:
+    """Return (base_ccy, quote_ccy) if this looks like a 6-letter fiat pair."""
+    if len(base) != 6:
+        return None
+    a, b = base[:3], base[3:]
+    return (a, b) if a in _FIAT and b in _FIAT else None
+
+
+def _crypto_pair(base: str, exchange: str | None) -> tuple[str, str] | None:
+    """Return (coin, quote) for crypto tickers like BTCUSDT / ETHUSD / SOLUSDT.PERP."""
+    b = re.sub(r"(\.P|PERP|\.PERP|_PERP)$", "", base)
+    for q in sorted(_STABLE | {"USD", "EUR", "BTC", "ETH"}, key=len, reverse=True):
+        if b.endswith(q) and len(b) > len(q):
+            coin = b[: -len(q)]
+            known = coin in _CRYPTO_BASES or (exchange in _CRYPTO_EXCHANGES)
+            if known:
+                return coin, q
+    if b in _CRYPTO_BASES:
+        return b, "USD"
+    return None
+
+
+def _digits_for(price_class: str, quote: str) -> int:
+    if price_class == "fx":
+        return 3 if quote == "JPY" else 5
+    if price_class == "crypto":
+        return 2
+    if price_class in ("index", "rates"):
+        return 2
+    return 2
+
+
+def resolve(symbol: str) -> Instrument:
+    """Turn any TradingView-style or plain ticker into a full Instrument.
+
+    Unknown symbols fall through to 'equity' with the base used as the Yahoo
+    ticker, which is right for the overwhelming majority of stock tickers.
+    """
+    exchange, base = _split(symbol)
+    tv = symbol.strip().upper()
+
+    # 1. explicit index / commodity tables
+    if base in _INDEX_MAP:
+        y = _INDEX_MAP[base]
+        cls = "rates" if base.startswith("US") and base.endswith("Y") else "index"
+        return Instrument(tv, y, base, exchange, cls, "USD", 0.01,
+                          _digits_for(cls, "USD"), False, "rth")
+
+    if base in _COMMODITY_PAIR_MAP:
+        y = _COMMODITY_PAIR_MAP[base]
+        pip = 0.01 if base in ("XAUUSD", "GOLD", "GC1!", "MGC1!") else 0.001
+        return Instrument(tv, y, base, exchange, "commodity", "USD", pip,
+                          2 if pip == 0.01 else 3, False, "fx_week")
+
+    # 2. crypto
+    cp = _crypto_pair(base, exchange)
+    if cp and (exchange in _CRYPTO_EXCHANGES or cp[0] in _CRYPTO_BASES):
+        coin, quote = cp
+        coin = "BTC" if coin == "XBT" else coin
+        fiat = "USD" if quote in _STABLE or quote == "USD" else quote
+        return Instrument(tv, f"{coin}-{fiat}", base, exchange, "crypto", fiat,
+                          0.01, 2, True, "24h")
+
+    # 3. fx
+    fp = _fx_pair(base)
+    if fp and (exchange in _FX_EXCHANGES or exchange is None or exchange == "TVC"):
+        a, b = fp
+        pip = 0.01 if b == "JPY" else 0.0001
+        return Instrument(tv, f"{a}{b}=X", base, exchange, "fx", b, pip,
+                          _digits_for("fx", b), False, "fx_week")
+
+    # 4. continuous futures written as ROOT1!
+    m = re.fullmatch(r"([A-Z]{1,3})[12]!", base)
+    if m:
+        return Instrument(tv, f"{m.group(1)}=F", base, exchange, "commodity",
+                          "USD", 0.01, 2, False, "fx_week")
+
+    # 5. anything else is an equity
+    y = base
+    if exchange in ("LSE",):
+        y = f"{base}.L"
+    elif exchange in ("XETR", "FWB"):
+        y = f"{base}.DE"
+    elif exchange == "TSX":
+        y = f"{base}.TO"
+    elif exchange == "ASX":
+        y = f"{base}.AX"
+    elif exchange == "TASE":
+        y = f"{base}.TA"
+    return Instrument(tv, y, base, exchange, "equity", "USD", 0.01, 2, False, "rth")
+
+
+def to_yahoo(symbol: str) -> str:
+    """Convenience: just the Yahoo ticker."""
+    return resolve(symbol).yahoo
+
+
+def asset_class(symbol: str) -> str:
+    return resolve(symbol).asset_class
+
warning: in the working copy of 'trading_system/tree_spec/tracker_admission_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/tracker_admission_source.py b/trading_system/tree_spec/tracker_admission_source.py
new file mode 100644
index 0000000..61b14f3
--- /dev/null
+++ b/trading_system/tree_spec/tracker_admission_source.py
@@ -0,0 +1,316 @@
+"""Independent inert-source audit of the private tracker gate/record closure.
+
+Only ASTs are transformed here, never compiled, imported or executed. The fixed
+authority below is independent of the declarative manifest and prior auditors.
+"""
+from __future__ import annotations
+
+import ast
+import copy
+import hashlib
+import json
+import os
+from pathlib import Path
+import subprocess
+
+ROOT = Path(__file__).resolve().parents[2]
+REPOSITORIES = {
+    "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9",
+    "trading-floor": "d827dd792cbd1d396b4ee325879c63e57388e07a",
+}
+VENDOR = "trading_system/tree_replay/_vendor/"
+TRACKER_SYMBOLS = ["MAX_STOP_BLOCK_H", "QUOTE_MAX_AGE_S", "_trade_identity",
+    "record", "_born_in_zone", "_record_locked", "_entry_band", "has_open",
+    "_higher_bias", "_live_prices", "_thesis_baseline", "_anchor_names", "_tail",
+    "_recent_rejection", "_cooldown_release", "blocked_after_stop",
+    "LEVEL_COOLDOWN_S", "blocked_same_level"]
+TRADEPLAN_SYMBOLS = ["born_in_zone", "WEAK_GATE", "THESIS_RECOVER",
+                     "thesis_now", "thesis_verdict"]
+METHODS = ["record", "_born_in_zone", "_record_locked", "_entry_band", "has_open",
+    "_higher_bias", "_live_prices", "_thesis_baseline", "_recent_rejection",
+    "_cooldown_release", "blocked_after_stop", "blocked_same_level", "thesis_now"]
+TRACKER_IMPORTS = """from __future__ import annotations
+import json
+import hashlib
+import math
+from io import BytesIO
+import pandas as pd
+from . import basis_symbols as basis
+from .pricing import entry_zone"""
+FILES = [
+    {"path": "chartdesk/tracker.py", "git_blob_sha1": "b616b34022e436545d8c1daf85eced51614fd74e",
+     "vendor_path": VENDOR + "tracker_admission.py", "symbols": TRACKER_SYMBOLS,
+     "projection": "tracker_ports"},
+    {"path": "chartdesk/tradeplan.py", "git_blob_sha1": "d09e9be39ce8dadf1674029e0c03751c70502135",
+     "vendor_path": VENDOR + "tracker_admission.py", "symbols": TRADEPLAN_SYMBOLS,
+     "projection": "tracker_thesis_and_build_band"},
+    {"path": "chartdesk/symbols.py", "git_blob_sha1": "c2fd40c8a97d98aa3650d95c8fbe64a5ce43e8f7",
+     "vendor_path": VENDOR + "tracker_symbols.py", "symbols": "whole_module",
+     "projection": "whole_module"},
+    {"path": "chartdesk/tradeplan.py", "git_blob_sha1": "d09e9be39ce8dadf1674029e0c03751c70502135",
+     "vendor_path": VENDOR + "pricing.py",
+     "symbols": ["MIN_RR", "SWING_MULT", "STYLE_MULT", "INTRADAY_MULT", "INTRADAY_TARGET_COUNT",
+        "FAR_TP1_R", "INSERT_TP1_R", "_with_measured_rung", "ENTRY_ZONE", "entry_zone",
+        "STOP_BANDS", "apply_stop_band", "Plan", "MIN_TARGET_SEP_ATR", "ladder_ready",
+        "ordered_ladder", "distinct_targets", "_n_levels", "resolve_ladder"],
+     "imports": "from __future__ import annotations\nfrom dataclasses import dataclass, field\nfrom . import basis_symbols as basis",
+     "projection": "pricing_plan"},
+    {"path": "chartdesk/basis.py", "git_blob_sha1": "f3396f3a9fefd71f0f71422001a5521af0a05cd2",
+     "vendor_path": VENDOR + "basis_symbols.py", "symbols": ["_BARE_ALIASES", "canonical_symbol"],
+     "imports": "from __future__ import annotations", "projection": "pure"},
+    {"path": "chartdesk/quarters.py", "git_blob_sha1": "d540b7bba60e992ff711954716ad265337116fc1",
+     "vendor_path": VENDOR + "quarters.py", "symbols": ["GRID", "_asset", "Level", "_kind", "nearest"],
+     "imports": "from __future__ import annotations\nfrom dataclasses import dataclass", "projection": "pure"},
+    {"path": "chartdesk/entry_quality.py", "git_blob_sha1": "0cd76eb8c607690610f4559e5946a60e8f7647ac",
+     "vendor_path": VENDOR + "admission_quality.py",
+     "symbols": ["MAX_REJECTION_AGE_S", "LABEL_NO_ANCHOR", "LABEL_NO_TRIGGER", "PREDICATE",
+        "_ANCHOR_PREFIXES", "_PRICE_TAIL", "_NAME_SPLIT", "_COUNT_PREFIX", "anchor_names",
+        "aligned_trigger", "still_defending", "opposing_label", "evaluate", "_rej"],
+     "imports": "from __future__ import annotations\nimport re", "projection": "pure"},
+    {"path": "chartdesk/zones.py", "git_blob_sha1": "92f7b99373b4f266a1d80e2d997b965f973d7698",
+     "vendor_path": VENDOR + "admission_swing.py", "symbols": ["SWING_K", "_last_swing"],
+     "imports": "from __future__ import annotations", "projection": "pure"},
+]
+# Each replacement is scoped to a named function and exact source AST. Counts
+# are independently fixed, not inferred from the candidate runtime/manifest.
+EXPRESSIONS = {
+    "record": [("_higher_bias(sym)", "self._higher_bias(sym)"),
+        ("_thesis_baseline(sym, plan.direction)", "self._thesis_baseline(sym, plan.direction)"),
+        ("_born_in_zone(plan, sym)", "self._born_in_zone(plan, sym)"),
+        ("_locked()", "self.source.locked()"),
+        ("_record_locked(plan, variant, to_group, bias_at_send, thesis, born)",
+         "self._record_locked(plan, variant, to_group, bias_at_send, thesis, born)")],
+    "_born_in_zone": [("_live_prices()", "self._live_prices()"),
+        ('_entry_band({"symbol": plan.symbol, "entry": plan.entry})',
+         'self._entry_band({"symbol": plan.symbol, "entry": plan.entry})')],
+    "_record_locked": [("_load()", "self.source.load()"),
+        ("has_open(basis.canonical_symbol(plan.symbol), plan.direction, state=d)",
+         "self.has_open(basis.canonical_symbol(plan.symbol), plan.direction, state=d)"),
+        ("time.time()", "self.source.now_epoch()"), ("_save(d)", "self.source.save(d)")],
+    "has_open": [("_load()", "self.source.load()")],
+    "_higher_bias": [("matrix.read_symbol(symbol, tfs=tfs)", "self.source.read_symbol(symbol, tfs=tfs)")],
+    "_live_prices": [("json.loads(QUOTES.read_text())", "self.source.quote_payload()"),
+                     ("time.time()", "self.source.now_epoch()")],
+    "_thesis_baseline": [("_tp.thesis_now(symbol)", "self.thesis_now(symbol)"),
+                         ("_tp.thesis_verdict(now[1], direction)", "thesis_verdict(now[1], direction)")],
+    "_recent_rejection": [("_tail(EVENTS)", "_tail_reader(self.source.event_log_reader)")],
+    "_cooldown_release": [("time.time()", "self.source.now_epoch()"),
+        ("_recent_rejection(symbol, direction, stopped_ts, self.source.now_epoch() if asof is None else float(asof), entry)",
+         "self._recent_rejection(symbol, direction, stopped_ts, self.source.now_epoch() if asof is None else float(asof), entry)")],
+    "blocked_after_stop": [("_load()", "self.source.load()"), ("time.time()", "self.source.now_epoch()"),
+        ('matrix.read_symbol(symbol, tfs=("4h", "1h"))', 'self.source.read_symbol(symbol, tfs=("4h", "1h"))'),
+        ('basis.fetch_corrected(symbol, "15m", 5)', 'self.source.fetch_corrected(symbol, "15m", 5)'),
+        ("_cooldown_release(symbol, direction, plan, last, stopped_ts, hours)",
+         "self._cooldown_release(symbol, direction, plan, last, stopped_ts, hours)")],
+    "blocked_same_level": [("time.time()", "self.source.now_epoch()"), ("_load()", "self.source.load()")],
+    "thesis_now": [('matrix.read_symbol(symbol, tfs=("4h", "1h", "30m", "15m", "5m"))',
+                    'self.source.read_symbol(symbol, tfs=("4h", "1h", "30m", "15m", "5m"))')],
+}
+STATEMENTS = {
+    "_born_in_zone": [("from .tradeplan import born_in_zone", None)],
+    "_entry_band": [("from .tradeplan import entry_zone", "from .pricing import entry_zone")],
+    "_higher_bias": [("from . import matrix", None)],
+    "_thesis_baseline": [("from . import tradeplan as _tp", None)],
+    "_anchor_names": [("from .entry_quality import anchor_names", "from .admission_quality import anchor_names")],
+    "_recent_rejection": [("from .tradeplan import entry_zone", "from .pricing import entry_zone")],
+    "_cooldown_release": [("from . import symbols as _sym", "from . import tracker_symbols as _sym")],
+    "blocked_after_stop": [("from . import matrix, zones", "from . import admission_swing as zones")],
+    "blocked_same_level": [("from .tradeplan import entry_zone", "from .pricing import entry_zone")],
+}
+EXPECTED_CONTRACT = {
+    "schema_version": "tracker-admission-source-contracts-v1",
+    "repositories": REPOSITORIES, "files": FILES,
+    "methods": METHODS, "tracker_imports": TRACKER_IMPORTS,
+    "expression_substitutions_once_per_function": EXPRESSIONS,
+    "statement_substitutions_once_per_function": STATEMENTS,
+    "tail_adaptation": "path:Path -> open_reader; path.open(rb) -> open_reader() inside original try; fixed small-fixture BytesIO wrapper",
+    "scope": "Private original tracker admission/record dependency; no causal binding, lifecycle, simulation or labels",
+    "ready_for_replay": False, "ready_for_training": False,
+}
+INPUT_ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
+                subprocess.SubprocessError)
+
+
+def _dump(node):
+    return ast.dump(node, include_attributes=False)
+
+
+def _name(node):
+    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
+        return node.name
+    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
+        return node.targets[0].id
+    return None
+
+
+def _without_doc(tree):
+    return tree.body[1:] if ast.get_docstring(tree) is not None else tree.body
+
+
+def _replace_exact(tree, old, new, *, statement=False):
+    original = ast.parse(old).body[0] if statement else ast.parse(old, mode="eval").body
+    replacement = None if new is None else (ast.parse(new).body[0] if statement else ast.parse(new, mode="eval").body)
+    class Replace(ast.NodeTransformer):
+        count = 0
+        def visit(self, node):
+            if _dump(node) == _dump(original):
+                self.count += 1
+                return copy.deepcopy(replacement)
+            return super().visit(node)
+    visitor = Replace()
+    result = visitor.visit(tree)
+    if visitor.count != 1:
+        raise ValueError(f"SUBSTITUTION_PRECONDITION:{old}:count={visitor.count}")
+    return result
+
+
+def _selected(text, symbols):
+    selected = [n for n in ast.parse(text).body if _name(n) in symbols]
+    if [_name(n) for n in selected] != symbols:
+        raise ValueError("SOURCE_SYMBOL_ORDER_OR_SET_MISMATCH")
+    return selected
+
+
+def _tracker_projection(tracker_text, tradeplan_text):
+    tracker = _selected(tracker_text, TRACKER_SYMBOLS)
+    tradeplan = _selected(tradeplan_text, TRADEPLAN_SYMBOLS)
+    nodes = {_name(n): n for n in tracker + tradeplan}
+    for name, edits in EXPRESSIONS.items():
+        for old, new in edits:
+            nodes[name] = _replace_exact(nodes[name], old, new)
+    for name, edits in STATEMENTS.items():
+        for old, new in edits:
+            nodes[name] = _replace_exact(nodes[name], old, new, statement=True)
+    tail = nodes["_tail"]
+    signature = ast.parse("def _tail(path: Path, window: int = 400_000, cap: int = 8_000_000) -> bytes | None: pass").body[0]
+    if _dump(tail.args) != _dump(signature.args) or _dump(tail.returns) != _dump(signature.returns) or tail.decorator_list:
+        raise ValueError("TAIL_SIGNATURE_MISMATCH")
+    _replace_exact(tail, 'path.open("rb")', "open_reader()")
+    tail.name = "_tail_reader"
+    tail.args.args[0] = ast.arg(arg="open_reader")
+    wrapper = ast.parse(
+        "def _tail_bytes(raw, window: int=400000, cap: int=8000000) -> bytes | None:\n"
+        "    if raw is None:\n        return None\n"
+        "    return _tail_reader(lambda: BytesIO(raw), window, cap)"
+    ).body[0]
+    cls = ast.parse("class TrackerAdmission:\n    def __init__(self, source):\n        self.source = source").body[0]
+    for name in METHODS:
+        node = nodes[name]
+        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(a.arg == "self" for a in node.args.args):
+            raise ValueError(f"METHOD_SHAPE_MISMATCH:{name}")
+        node.args.args.insert(0, ast.arg(arg="self"))
+        cls.body.append(node)
+    return ast.parse(TRACKER_IMPORTS).body + [nodes[n] for n in
+        ("MAX_STOP_BLOCK_H", "QUOTE_MAX_AGE_S", "LEVEL_COOLDOWN_S", "WEAK_GATE",
+         "THESIS_RECOVER", "_trade_identity", "_anchor_names", "_tail")] + [wrapper] + [
+         nodes["born_in_zone"], nodes["thesis_verdict"], cls]
+
+
+def _dependency_projection(text, row):
+    if row["projection"] == "whole_module":
+        return _without_doc(ast.parse(text))
+    nodes = _selected(text, row["symbols"])
+    if row["projection"] == "pricing_plan":
+        plan = next(n for n in nodes if _name(n) == "Plan")
+        methods = ("risk", "rr", "rr_far", "tradeable")
+        plan.body = [n for n in plan.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) or n.name in methods]
+        kept = [n for n in plan.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
+        if [n.name for n in kept] != list(methods) or any(
+                not isinstance(n, ast.FunctionDef) or [_dump(d) for d in n.decorator_list] !=
+                [_dump(ast.Name(id="property", ctx=ast.Load()))] for n in kept):
+            raise ValueError("PLAN_PROPERTY_PROJECTION_MISMATCH")
+    return ast.parse(row["imports"]).body + nodes
+
+
+def _git(repo, *args):
+    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
+    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
+        env.pop(key, None)
+    result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(repo),
+                             "rev-parse", *args], env=env, text=True, encoding="utf-8",
+                            capture_output=True, timeout=10, check=True)
+    return result.stdout.strip()
+
+
+def _no_duplicates(pairs):
+    result = {}
+    for k, v in pairs:
+        if k in result:
+            raise ValueError(f"DUPLICATE_JSON_KEY:{k}")
+        result[k] = v
+    return result
+
+
+def _read_json(path):
+    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)
+
+
+def _report(blockers, checked):
+    return {"status": "BLOCKED" if blockers else "VERIFIED",
+        "source_subset_verified": not blockers, "blockers": blockers,
+        "checked_projections": checked, "source_commits": dict(REPOSITORIES),
+        "ready_for_replay": False, "ready_for_training": False}
+
+
+def audit_tracker_admission_source(source_root) -> dict:
+    """Verify explicit retained parent, complete projection and inherited bodies."""
+    blockers, checked = [], []
+    try:
+        source_root = Path(source_root)
+    except INPUT_ERRORS as exc:
+        return _report([f"SOURCE_ROOT_INVALID:{type(exc).__name__}"], checked)
+    try:
+        manifest = _read_json(ROOT / "configs/trees/tracker-admission-source-contracts.json")
+        if json.dumps(manifest, sort_keys=True, allow_nan=False) != json.dumps(EXPECTED_CONTRACT, sort_keys=True, allow_nan=False):
+            blockers.append("CONTRACT_MISMATCH")
+        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
+        for repo, commit in REPOSITORIES.items():
+            if [r.get("commit") for r in baseline["repositories"] if r.get("name") == repo] != [commit]:
+                blockers.append(f"BASELINE_COMMIT_MISMATCH:{repo}")
+    except INPUT_ERRORS as exc:
+        blockers.append(f"CONTRACT_UNREADABLE:{type(exc).__name__}:{exc}")
+    for repo, commit in REPOSITORIES.items():
+        try:
+            path = source_root / repo
+            if Path(_git(path, "--show-toplevel")).resolve() != path.resolve():
+                blockers.append(f"NOT_REPOSITORY_ROOT:{repo}")
+            if _git(path, "HEAD") != commit:
+                blockers.append(f"SOURCE_COMMIT_MISMATCH:{repo}")
+        except INPUT_ERRORS as exc:
+            blockers.append(f"SOURCE_IDENTITY_UNREADABLE:{repo}:{type(exc).__name__}")
+    sources = {}
+    for row in FILES:
+        path = row["path"]
+        if path in sources:
+            continue
+        try:
+            text = (source_root / "chart-desk" / path).read_text(encoding="utf-8")
+            data = text.encode("utf-8")  # normalize checkout CRLF to Git LF
+            digest = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
+            if digest != row["git_blob_sha1"]:
+                blockers.append(f"SOURCE_BLOB_MISMATCH:chart-desk/{path}")
+                continue
+            sources[path] = text
+        except INPUT_ERRORS as exc:
+            blockers.append(f"SOURCE_UNREADABLE:chart-desk/{path}:{type(exc).__name__}")
+    projections = {}
+    try:
+        projections[VENDOR + "tracker_admission.py"] = _tracker_projection(
+            sources["chartdesk/tracker.py"], sources["chartdesk/tradeplan.py"])
+    except INPUT_ERRORS as exc:
+        blockers.append(f"SOURCE_PROJECTION_UNREADABLE:tracker_admission:{type(exc).__name__}:{exc}")
+    for row in FILES[2:]:
+        try:
+            projections[row["vendor_path"]] = _dependency_projection(sources[row["path"]], row)
+        except INPUT_ERRORS as exc:
+            blockers.append(f"SOURCE_PROJECTION_UNREADABLE:{row['path']}:{type(exc).__name__}:{exc}")
+    for vendor, expected in projections.items():
+        try:
+            actual = _without_doc(ast.parse((ROOT / vendor).read_text(encoding="utf-8")))
+            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
+                blockers.append(f"VENDOR_AST_MISMATCH:{vendor}")
+            else:
+                checked.append(vendor)
+        except INPUT_ERRORS as exc:
+            blockers.append(f"VENDOR_UNREADABLE:{vendor}:{type(exc).__name__}")
+    return _report(blockers, checked)
warning: in the working copy of 'configs/trees/tracker-admission-source-contracts.json', LF will be replaced by CRLF the next time Git touches it
diff --git a/configs/trees/tracker-admission-source-contracts.json b/configs/trees/tracker-admission-source-contracts.json
new file mode 100644
index 0000000..58fcc98
--- /dev/null
+++ b/configs/trees/tracker-admission-source-contracts.json
@@ -0,0 +1,356 @@
+{
+  "schema_version": "tracker-admission-source-contracts-v1",
+  "repositories": {
+    "chart-desk": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9",
+    "trading-floor": "d827dd792cbd1d396b4ee325879c63e57388e07a"
+  },
+  "files": [
+    {
+      "path": "chartdesk/tracker.py",
+      "git_blob_sha1": "b616b34022e436545d8c1daf85eced51614fd74e",
+      "vendor_path": "trading_system/tree_replay/_vendor/tracker_admission.py",
+      "symbols": [
+        "MAX_STOP_BLOCK_H",
+        "QUOTE_MAX_AGE_S",
+        "_trade_identity",
+        "record",
+        "_born_in_zone",
+        "_record_locked",
+        "_entry_band",
+        "has_open",
+        "_higher_bias",
+        "_live_prices",
+        "_thesis_baseline",
+        "_anchor_names",
+        "_tail",
+        "_recent_rejection",
+        "_cooldown_release",
+        "blocked_after_stop",
+        "LEVEL_COOLDOWN_S",
+        "blocked_same_level"
+      ],
+      "projection": "tracker_ports"
+    },
+    {
+      "path": "chartdesk/tradeplan.py",
+      "git_blob_sha1": "d09e9be39ce8dadf1674029e0c03751c70502135",
+      "vendor_path": "trading_system/tree_replay/_vendor/tracker_admission.py",
+      "symbols": [
+        "born_in_zone",
+        "WEAK_GATE",
+        "THESIS_RECOVER",
+        "thesis_now",
+        "thesis_verdict"
+      ],
+      "projection": "tracker_thesis_and_build_band"
+    },
+    {
+      "path": "chartdesk/symbols.py",
+      "git_blob_sha1": "c2fd40c8a97d98aa3650d95c8fbe64a5ce43e8f7",
+      "vendor_path": "trading_system/tree_replay/_vendor/tracker_symbols.py",
+      "symbols": "whole_module",
+      "projection": "whole_module"
+    },
+    {
+      "path": "chartdesk/tradeplan.py",
+      "git_blob_sha1": "d09e9be39ce8dadf1674029e0c03751c70502135",
+      "vendor_path": "trading_system/tree_replay/_vendor/pricing.py",
+      "symbols": [
+        "MIN_RR",
+        "SWING_MULT",
+        "STYLE_MULT",
+        "INTRADAY_MULT",
+        "INTRADAY_TARGET_COUNT",
+        "FAR_TP1_R",
+        "INSERT_TP1_R",
+        "_with_measured_rung",
+        "ENTRY_ZONE",
+        "entry_zone",
+        "STOP_BANDS",
+        "apply_stop_band",
+        "Plan",
+        "MIN_TARGET_SEP_ATR",
+        "ladder_ready",
+        "ordered_ladder",
+        "distinct_targets",
+        "_n_levels",
+        "resolve_ladder"
+      ],
+      "imports": "from __future__ import annotations\nfrom dataclasses import dataclass, field\nfrom . import basis_symbols as basis",
+      "projection": "pricing_plan"
+    },
+    {
+      "path": "chartdesk/basis.py",
+      "git_blob_sha1": "f3396f3a9fefd71f0f71422001a5521af0a05cd2",
+      "vendor_path": "trading_system/tree_replay/_vendor/basis_symbols.py",
+      "symbols": [
+        "_BARE_ALIASES",
+        "canonical_symbol"
+      ],
+      "imports": "from __future__ import annotations",
+      "projection": "pure"
+    },
+    {
+      "path": "chartdesk/quarters.py",
+      "git_blob_sha1": "d540b7bba60e992ff711954716ad265337116fc1",
+      "vendor_path": "trading_system/tree_replay/_vendor/quarters.py",
+      "symbols": [
+        "GRID",
+        "_asset",
+        "Level",
+        "_kind",
+        "nearest"
+      ],
+      "imports": "from __future__ import annotations\nfrom dataclasses import dataclass",
+      "projection": "pure"
+    },
+    {
+      "path": "chartdesk/entry_quality.py",
+      "git_blob_sha1": "0cd76eb8c607690610f4559e5946a60e8f7647ac",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_quality.py",
+      "symbols": [
+        "MAX_REJECTION_AGE_S",
+        "LABEL_NO_ANCHOR",
+        "LABEL_NO_TRIGGER",
+        "PREDICATE",
+        "_ANCHOR_PREFIXES",
+        "_PRICE_TAIL",
+        "_NAME_SPLIT",
+        "_COUNT_PREFIX",
+        "anchor_names",
+        "aligned_trigger",
+        "still_defending",
+        "opposing_label",
+        "evaluate",
+        "_rej"
+      ],
+      "imports": "from __future__ import annotations\nimport re",
+      "projection": "pure"
+    },
+    {
+      "path": "chartdesk/zones.py",
+      "git_blob_sha1": "92f7b99373b4f266a1d80e2d997b965f973d7698",
+      "vendor_path": "trading_system/tree_replay/_vendor/admission_swing.py",
+      "symbols": [
+        "SWING_K",
+        "_last_swing"
+      ],
+      "imports": "from __future__ import annotations",
+      "projection": "pure"
+    }
+  ],
+  "methods": [
+    "record",
+    "_born_in_zone",
+    "_record_locked",
+    "_entry_band",
+    "has_open",
+    "_higher_bias",
+    "_live_prices",
+    "_thesis_baseline",
+    "_recent_rejection",
+    "_cooldown_release",
+    "blocked_after_stop",
+    "blocked_same_level",
+    "thesis_now"
+  ],
+  "tracker_imports": "from __future__ import annotations\nimport json\nimport hashlib\nimport math\nfrom io import BytesIO\nimport pandas as pd\nfrom . import basis_symbols as basis\nfrom .pricing import entry_zone",
+  "expression_substitutions_once_per_function": {
+    "record": [
+      [
+        "_higher_bias(sym)",
+        "self._higher_bias(sym)"
+      ],
+      [
+        "_thesis_baseline(sym, plan.direction)",
+        "self._thesis_baseline(sym, plan.direction)"
+      ],
+      [
+        "_born_in_zone(plan, sym)",
+        "self._born_in_zone(plan, sym)"
+      ],
+      [
+        "_locked()",
+        "self.source.locked()"
+      ],
+      [
+        "_record_locked(plan, variant, to_group, bias_at_send, thesis, born)",
+        "self._record_locked(plan, variant, to_group, bias_at_send, thesis, born)"
+      ]
+    ],
+    "_born_in_zone": [
+      [
+        "_live_prices()",
+        "self._live_prices()"
+      ],
+      [
+        "_entry_band({\"symbol\": plan.symbol, \"entry\": plan.entry})",
+        "self._entry_band({\"symbol\": plan.symbol, \"entry\": plan.entry})"
+      ]
+    ],
+    "_record_locked": [
+      [
+        "_load()",
+        "self.source.load()"
+      ],
+      [
+        "has_open(basis.canonical_symbol(plan.symbol), plan.direction, state=d)",
+        "self.has_open(basis.canonical_symbol(plan.symbol), plan.direction, state=d)"
+      ],
+      [
+        "time.time()",
+        "self.source.now_epoch()"
+      ],
+      [
+        "_save(d)",
+        "self.source.save(d)"
+      ]
+    ],
+    "has_open": [
+      [
+        "_load()",
+        "self.source.load()"
+      ]
+    ],
+    "_higher_bias": [
+      [
+        "matrix.read_symbol(symbol, tfs=tfs)",
+        "self.source.read_symbol(symbol, tfs=tfs)"
+      ]
+    ],
+    "_live_prices": [
+      [
+        "json.loads(QUOTES.read_text())",
+        "self.source.quote_payload()"
+      ],
+      [
+        "time.time()",
+        "self.source.now_epoch()"
+      ]
+    ],
+    "_thesis_baseline": [
+      [
+        "_tp.thesis_now(symbol)",
+        "self.thesis_now(symbol)"
+      ],
+      [
+        "_tp.thesis_verdict(now[1], direction)",
+        "thesis_verdict(now[1], direction)"
+      ]
+    ],
+    "_recent_rejection": [
+      [
+        "_tail(EVENTS)",
+        "_tail_reader(self.source.event_log_reader)"
+      ]
+    ],
+    "_cooldown_release": [
+      [
+        "time.time()",
+        "self.source.now_epoch()"
+      ],
+      [
+        "_recent_rejection(symbol, direction, stopped_ts, self.source.now_epoch() if asof is None else float(asof), entry)",
+        "self._recent_rejection(symbol, direction, stopped_ts, self.source.now_epoch() if asof is None else float(asof), entry)"
+      ]
+    ],
+    "blocked_after_stop": [
+      [
+        "_load()",
+        "self.source.load()"
+      ],
+      [
+        "time.time()",
+        "self.source.now_epoch()"
+      ],
+      [
+        "matrix.read_symbol(symbol, tfs=(\"4h\", \"1h\"))",
+        "self.source.read_symbol(symbol, tfs=(\"4h\", \"1h\"))"
+      ],
+      [
+        "basis.fetch_corrected(symbol, \"15m\", 5)",
+        "self.source.fetch_corrected(symbol, \"15m\", 5)"
+      ],
+      [
+        "_cooldown_release(symbol, direction, plan, last, stopped_ts, hours)",
+        "self._cooldown_release(symbol, direction, plan, last, stopped_ts, hours)"
+      ]
+    ],
+    "blocked_same_level": [
+      [
+        "time.time()",
+        "self.source.now_epoch()"
+      ],
+      [
+        "_load()",
+        "self.source.load()"
+      ]
+    ],
+    "thesis_now": [
+      [
+        "matrix.read_symbol(symbol, tfs=(\"4h\", \"1h\", \"30m\", \"15m\", \"5m\"))",
+        "self.source.read_symbol(symbol, tfs=(\"4h\", \"1h\", \"30m\", \"15m\", \"5m\"))"
+      ]
+    ]
+  },
+  "statement_substitutions_once_per_function": {
+    "_born_in_zone": [
+      [
+        "from .tradeplan import born_in_zone",
+        null
+      ]
+    ],
+    "_entry_band": [
+      [
+        "from .tradeplan import entry_zone",
+        "from .pricing import entry_zone"
+      ]
+    ],
+    "_higher_bias": [
+      [
+        "from . import matrix",
+        null
+      ]
+    ],
+    "_thesis_baseline": [
+      [
+        "from . import tradeplan as _tp",
+        null
+      ]
+    ],
+    "_anchor_names": [
+      [
+        "from .entry_quality import anchor_names",
+        "from .admission_quality import anchor_names"
+      ]
+    ],
+    "_recent_rejection": [
+      [
+        "from .tradeplan import entry_zone",
+        "from .pricing import entry_zone"
+      ]
+    ],
+    "_cooldown_release": [
+      [
+        "from . import symbols as _sym",
+        "from . import tracker_symbols as _sym"
+      ]
+    ],
+    "blocked_after_stop": [
+      [
+        "from . import matrix, zones",
+        "from . import admission_swing as zones"
+      ]
+    ],
+    "blocked_same_level": [
+      [
+        "from .tradeplan import entry_zone",
+        "from .pricing import entry_zone"
+      ]
+    ]
+  },
+  "tail_adaptation": "path:Path -> open_reader; path.open(rb) -> open_reader() inside original try; fixed small-fixture BytesIO wrapper",
+  "scope": "Private original tracker admission/record dependency; no causal binding, lifecycle, simulation or labels",
+  "ready_for_replay": false,
+  "ready_for_training": false
+}
warning: in the working copy of 'tools/check_tracker_admission_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_tracker_admission_source_parity.py b/tools/check_tracker_admission_source_parity.py
new file mode 100644
index 0000000..16a84f1
--- /dev/null
+++ b/tools/check_tracker_admission_source_parity.py
@@ -0,0 +1,23 @@
+"""Audit the pinned offline tracker closure without executing retained source."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ""):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.tracker_admission_source import audit_tracker_admission_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True,
+                        help="Explicit parent of retained chart-desk and trading-floor checkouts")
+    report = audit_tracker_admission_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())
warning: in the working copy of 'tests/tree_replay/test_tracker_admission.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_tracker_admission.py b/tests/tree_replay/test_tracker_admission.py
new file mode 100644
index 0000000..3e5ede0
--- /dev/null
+++ b/tests/tree_replay/test_tracker_admission.py
@@ -0,0 +1,530 @@
+"""Behavioral source-contract tests; all state, frames, quotes and bytes synthetic."""
+from contextlib import contextmanager
+from copy import deepcopy
+from dataclasses import replace
+import importlib
+import json
+from io import BytesIO
+from pathlib import Path
+import subprocess
+import sys
+from types import SimpleNamespace
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay._vendor.pricing import Plan
+
+NOW = 1788775200.0
+SYM = "OANDA:XAUUSD"
+LONG, SHORT = "לונג", "שורט"
+
+
+def module():
+    try:
+        return importlib.import_module("trading_system.tree_replay._vendor.tracker_admission")
+    except ModuleNotFoundError as exc:
+        pytest.fail(f"tracker admission implementation missing: {exc}")
+
+
+class MemoryPorts:
+    def __init__(self, rows=None):
+        self.rows = deepcopy(rows if rows is not None else {})
+        self.calls = []
+        self.nets = {tf: 0.0 for tf in ("4h", "1h", "30m", "15m", "5m")}
+        self.frame = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
+        self.quotes = {}
+        self.raw = b""
+        self.on_lock = None
+        self.fail = set()
+
+    def load(self):
+        self.calls.append("load")
+        if "load" in self.fail:
+            raise OSError("state unavailable")
+        return deepcopy(self.rows)
+
+    def save(self, rows):
+        self.calls.append("save")
+        if "save" in self.fail:
+            raise OSError("sink failed")
+        self.rows = deepcopy(rows)
+
+    def now_epoch(self):
+        return NOW
+
+    @contextmanager
+    def locked(self):
+        self.calls.append("lock")
+        if self.on_lock:
+            self.on_lock()
+        yield
+        self.calls.append("unlock")
+
+    def event_log_reader(self):
+        self.calls.append("log")
+        if "log" in self.fail:
+            raise OSError("log unavailable")
+        if self.raw is None:
+            raise OSError("log unavailable")
+        return BytesIO(self.raw)
+
+    def quote_payload(self):
+        self.calls.append("quotes")
+        if "quotes" in self.fail:
+            raise OSError("quotes unavailable")
+        return self.quotes
+
+    def read_symbol(self, symbol, tfs):
+        self.calls.append(("matrix", symbol, tfs))
+        if "matrix" in self.fail:
+            raise OSError("matrix unavailable")
+        return {tf: SimpleNamespace(net=self.nets[tf], bar_ts=NOW) if tf in self.nets else None
+                for tf in tfs}
+
+    def fetch_corrected(self, symbol, timeframe, lookback_days):
+        self.calls.append(("frame", symbol, timeframe, lookback_days))
+        if "frame" in self.fail:
+            raise OSError("frame unavailable")
+        return self.frame.copy(), None
+
+
+def plan(**kw):
+    return replace(Plan(SYM, 110.0, "reversal", LONG, entry=100.0, stop=90.0,
+                        targets=[("TP1", 120.0), ("TP2", 130.0)],
+                        reasons=["רמה: DAY-OPEN"], obstacles=[("near", 105.0)]), **kw)
+
+
+def stopped(**kw):
+    return dict(symbol=SYM, direction=LONG, state="STOPPED", ts=NOW-7200,
+                resolved_ts=NOW-3600, stop=90.0, entry=100.0, **kw)
+
+
+@pytest.mark.parametrize("rows,want", [({}, False), ({"x": {"state": "PENDING"}}, False),
+    ({"x": {"state": "OPEN", "symbol": SYM, "direction": LONG}}, True),
+    ({"x": {"state": "OPEN", "symbol": SYM, "direction": SHORT}}, False),
+    ({"x": {}}, True), ({"x": None}, True), ([], True),
+    ({"x": {"state": "OPEN"}}, True)])
+def test_exposure_is_open_only_and_corruption_fails_closed(rows, want):
+    assert module().TrackerAdmission(MemoryPorts(rows)).has_open(SYM, LONG) is want
+
+
+def test_record_persists_complete_pending_row_and_calculates_before_lock():
+    p, ports = plan(), MemoryPorts()
+    assert module().TrackerAdmission(ports).record(p, variant="test", to_group=True)
+    assert p.born_open is False
+    key, row = next(iter(ports.rows.items()))
+    assert key.startswith(SYM + ":" + LONG + ":100.0:intraday:")
+    assert len(row["trade_id"]) == 16 and key.endswith(row["trade_id"])
+    assert row == dict(symbol=SYM, direction=LONG, entry=100.0, stop=90.0,
+        targets=[["TP1", 120.0], ["TP2", 130.0]], obstacles=[["near", 105.0]],
+        reasons=["רמה: DAY-OPEN"], variant="test", to_group=True, style="intraday",
+        trade_id=row["trade_id"], kind="reversal", state="PENDING", hit=[], ts=NOW,
+        thesis_state="held", thesis_warned=False, bias_at_send={"4h": 0.0, "1h": 0.0})
+    assert ports.calls == [("matrix", SYM, ("4h", "1h")),
+        ("matrix", SYM, ("4h", "1h", "30m", "15m", "5m")), "lock", "load", "save", "unlock"]
+
+
+def test_record_born_open_is_not_broker_verified():
+    ports, p = MemoryPorts(), plan(close=100.0)
+    assert module().TrackerAdmission(ports).record(p)
+    row = next(iter(ports.rows.values()))
+    assert p.born_open is True and row["state"] == "OPEN"
+    assert row["born_in_zone"] is True and row["revalidation_verified"] is False
+    assert row["fill_verification_reason"] == "born_open_not_broker_verified"
+    assert row["ts"] == row["filled_ts"] == row["progress_ts"] == NOW
+
+
+def test_record_duplicate_geometry_and_resolved_archive_collision():
+    ports = MemoryPorts()
+    tracker = module().TrackerAdmission(ports)
+    assert tracker.record(plan())
+    original = deepcopy(ports.rows)
+    assert tracker.record(plan()) is False and ports.rows == original
+    key = next(iter(ports.rows))
+    ports.rows[key]["state"] = "DONE"
+    ports.rows[key]["ts"] = 123.75
+    old = deepcopy(ports.rows[key])
+    ports.rows[key + "@123"] = {"state": "CANCELLED"}
+    assert tracker.record(plan())
+    assert ports.rows[key + "@123"] == old
+    assert ports.rows[key]["state"] == "PENDING"
+
+
+@pytest.mark.parametrize("change", [dict(style="swing"), dict(stop=89.0),
+    dict(targets=[("TP1", 120.0), ("TP2", 131.0)]), dict(entry=100.00001)])
+def test_pending_distinct_geometry_coexists(change):
+    ports = MemoryPorts()
+    tracker = module().TrackerAdmission(ports)
+    assert tracker.record(plan()) and tracker.record(plan(**change))
+    assert len(ports.rows) == 2
+
+
+def test_record_reloads_and_rechecks_open_inside_lock():
+    ports = MemoryPorts()
+    ports.on_lock = lambda: ports.rows.update(x={"state": "OPEN", "symbol": SYM, "direction": LONG})
+    assert module().TrackerAdmission(ports).record(plan()) is False
+    assert ports.calls[-3:] == ["lock", "load", "unlock"]
+    assert list(ports.rows) == ["x"]
+
+
+def test_save_failure_propagates_without_persisting_success():
+    ports = MemoryPorts()
+    ports.fail.add("save")
+    with pytest.raises(OSError, match="sink failed"):
+        module().TrackerAdmission(ports).record(plan())
+    assert ports.rows == {}
+
+
+@pytest.mark.parametrize("side,net,want", [(SHORT, 25, True), (SHORT, 24.999, False),
+    (LONG, -25, True), (LONG, -24.999, False), (LONG, 25, False), (SHORT, -25, False)])
+def test_post_stop_signed_sum_boundary_precedes_structure(side, net, want):
+    row = stopped(); row["direction"] = side
+    ports = MemoryPorts({"x": row}); ports.nets.update({"4h": net+5, "1h": -5})
+    result = module().TrackerAdmission(ports).blocked_after_stop(SYM, side)
+    assert (result is None) is want
+    assert ports.calls[:2] == ["load", ("matrix", SYM, ("4h", "1h"))]
+    assert (("frame", SYM, "15m", 5) in ports.calls) is not want
+
+
+@pytest.mark.parametrize("age,released", [(14400, True), (14399.999, False)])
+def test_stop_age_boundary_before_dependencies(age, released):
+    row = stopped(); row["resolved_ts"] = NOW-age
+    ports = MemoryPorts({"x": row})
+    assert (module().TrackerAdmission(ports).blocked_after_stop(SYM, LONG) is None) is released
+    if released:
+        assert ports.calls == ["load"]
+
+
+@pytest.mark.parametrize("side,n,want", [(LONG, 8, True), (SHORT, 8, True), (LONG, 7, False), (SHORT, 7, False)])
+def test_post_stop_uses_actual_confirmed_swing(side, n, want):
+    row = stopped(); row.update(direction=side, stop=90 if side == LONG else 110)
+    ports = MemoryPorts({"x": row})
+    highs = [80,80,80,85,80,80,80,80] if side == LONG else [140]*8
+    lows = [60]*8 if side == LONG else [130,130,130,120,130,130,130,130]
+    ports.frame = pd.DataFrame({"high": highs[:n], "low": lows[:n]},
+        index=pd.to_datetime([row["resolved_ts"] + 60*(i+1) for i in range(n)], unit="s", utc=True))
+    assert (module().TrackerAdmission(ports).blocked_after_stop(SYM, side) is None) is want
+
+
+@pytest.mark.parametrize("side,entry,released", [(LONG, 89.99, True), (LONG, 89.991, False),
+    (SHORT, 90.01, True), (SHORT, 90.009, False)])
+@pytest.mark.parametrize("anchors", [False, True])
+def test_entry_crosses_by_source_pip_with_optional_unchanged_anchor(side, entry, released, anchors):
+    row = stopped(); row["direction"] = side
+    if anchors:
+        row["reasons"] = ["רמה: DAY-OPEN"]
+    ports, p = MemoryPorts({"x": row}), plan(entry=entry, direction=side)
+    assert (module().TrackerAdmission(ports).blocked_after_stop(SYM, side, p) is None) is released
+    if released:
+        assert p.cooldown_release["boundary_margin"] == .01
+        assert p.cooldown_release["anchor_changed"] is (False if anchors else None)
+        assert p.cooldown_release["recent_rejection"] is None
+    else:
+        assert p.cooldown_release is None
+
+
+@pytest.mark.parametrize("state,age,entry,blocked", [("DONE", 7199, 98, True),
+    ("CANCELLED", 7199, 102, True), ("DONE", 7200, 100, False),
+    ("DONE", 10, 102.001, False), ("STOPPED", 10, 100, False),
+    ("PENDING", 10, 100, False), ("DONE", -1, 100, True)])
+def test_same_level_state_age_and_inclusive_band(state, age, entry, blocked):
+    row = stopped(); row.update(state=state, resolved_ts=NOW-age)
+    result = module().TrackerAdmission(MemoryPorts({"x": row})).blocked_same_level(SYM, LONG, entry)
+    assert (result is not None) is blocked
+
+
+@pytest.mark.parametrize("age,price,valid", [(0, 100, True), (420,100,True),
+    (420.0001,100,False), (-.001,100,False), (0,0,False), (0,-1,False),
+    (0,float("nan"),False), (0,float("inf"),False)])
+def test_quote_freshness_and_price_validation(age, price, valid):
+    ports = MemoryPorts(); ports.quotes = {SYM: {"lp": price, "ts": NOW-age}}
+    assert module().TrackerAdmission(ports)._live_prices() == ({SYM: price} if valid else {})
+
+
+@pytest.mark.parametrize("side,close,spot,age,born", [(LONG,100,90,0,True),
+    (SHORT,100,110,0,True), (LONG,100,103,0,False), (SHORT,100,97,0,False),
+    (LONG,100,103,421,True), (LONG,103,100,0,False), (LONG,98,100,0,True),
+    (LONG,102,100,0,True)])
+def test_born_requires_build_band_then_one_sided_quote(side, close, spot, age, born):
+    ports = MemoryPorts(); ports.quotes = {SYM: {"lp": spot, "ts": NOW-age}}
+    assert module().TrackerAdmission(ports)._born_in_zone(plan(direction=side, close=close), SYM) is born
+
+
+@pytest.mark.parametrize("side,lo,want", [(LONG,-25,"broken"),(LONG,-24.99,None),
+    (LONG,0,"held"),(SHORT,25,"broken"),(SHORT,24.99,None),(SHORT,0,"held")])
+def test_thesis_hysteresis(side, lo, want):
+    assert module().thesis_verdict(lo, side) == want
+
+
+def rejection(**kw):
+    row = dict(kind="rejection", symbol=SYM, direction=LONG, ts=NOW-20,
+               zone_lo=99, zone_hi=101, levels=["first"], close=100, wick_atr=1.5)
+    row.update(kw)
+    return json.dumps(row, ensure_ascii=False).encode() + b"\n"
+
+
+def test_rejection_equal_timestamp_keeps_first_and_ignores_trailing_malformed():
+    ports = MemoryPorts()
+    ports.raw = b'junk\xff\n' + rejection() + rejection(levels=["second"]) + b'{"kind":"rejection",'
+    result = module().TrackerAdmission(ports)._recent_rejection(SYM, LONG, NOW-100, NOW, 100)
+    assert result == dict(ts=NOW-20, direction=LONG, zone_lo=99, zone_hi=101,
+        levels=["first"], close=100, wick_atr=1.5, age_s=20.0, gap=0.0)
+
+
+@pytest.mark.parametrize("age,gap,overlap,max_dist,want", [(1200,0,True,None,True),
+    (1200.001,0,True,None,False), (0,0,True,None,True), (-1,0,True,None,False),
+    (10,1,True,None,False), (10,1,False,1,True), (10,1.001,False,1,False)])
+def test_rejection_age_overlap_distance_boundaries(age,gap,overlap,max_dist,want):
+    ports = MemoryPorts(); ports.raw = rejection(ts=NOW-age, zone_lo=102+gap, zone_hi=104+gap)
+    result = module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-1200,NOW,100,
+        require_overlap=overlap,max_distance=max_dist)
+    assert (result is not None) is want
+
+
+def test_tail_expands_huge_last_line_and_preserves_partial_trailing_line():
+    tail = module()._tail_bytes
+    assert tail(b"first\nsecond\nthird", window=10) == b"third"
+    raw = b"evidence\n" + b"x"*100 + b"\n"
+    assert tail(raw, window=4, cap=16) == raw
+    assert tail(None) is None
+    assert tail(b"") == b""
+
+
+def test_non_rejection_bytes_eject_old_rejection_from_original_tail():
+    ports = MemoryPorts(); ports.raw = rejection() + (b'{"kind":"other"}\n'*26000)
+    assert module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-100,NOW,100) is None
+
+
+def test_port_errors_retain_asymmetric_source_outcomes():
+    ports = MemoryPorts(); ports.fail.add("load")
+    tracker = module().TrackerAdmission(ports)
+    assert tracker.has_open(SYM,LONG) is True
+    assert tracker.blocked_after_stop(SYM,LONG) is None
+    assert tracker.blocked_same_level(SYM,LONG,100) is None
+    with pytest.raises(OSError,match="state unavailable"):
+        tracker.record(plan())
+    ports.fail = {"matrix", "quotes"}
+    assert tracker._higher_bias(SYM) is None and tracker._thesis_baseline(SYM,LONG) == "held"
+    assert tracker._born_in_zone(plan(close=100),SYM) is True
+
+
+def test_thesis_actual_frames_and_incomplete_higher_reading():
+    ports = MemoryPorts(); ports.nets.update({"4h":40,"1h":20,"30m":-90,"15m":0,"5m":0})
+    tracker = module().TrackerAdmission(ports)
+    assert tracker.thesis_now(SYM) == (30,-30,NOW)
+    assert tracker._thesis_baseline(SYM,LONG) == "broken"
+    del ports.nets["1h"]
+    assert tracker._higher_bias(SYM) is None and tracker.thesis_now(SYM) is None
+
+
+def test_reader_opens_lazily_and_catches_open_failure():
+    ports = MemoryPorts(); ports.fail.add("log")
+    assert module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-100,NOW,100) is None
+    assert ports.calls == ["log"]
+
+
+def test_reader_consumes_tail_bytes_not_full_historical_prefix():
+    # A virtual ten-billion-byte prefix: the spy never allocates that prefix.
+    class Reader:
+        size = 10_000_000_000
+        def __init__(self):
+            self.pos = 0; self.consumed = 0; self.seeks = []; self.closed = False
+        def __enter__(self):
+            return self
+        def __exit__(self,*args):
+            self.closed = True
+        def seek(self,offset,whence=0):
+            self.seeks.append((offset,whence))
+            self.pos = offset + (self.size if whence == 2 else 0)
+        def tell(self):
+            return self.pos
+        def read(self):
+            n = self.size-self.pos
+            assert n <= 400000, "source tail eagerly read the entire historical prefix"
+            self.consumed += n; self.pos = self.size
+            return b"x\n"*(n//2)
+    reader = Reader()
+    result = module()._tail_reader(lambda: reader)
+    assert result == b"x\n"*199999
+    assert reader.consumed == 400000 and reader.closed
+    assert reader.seeks == [(0,2),(9_999_600_000,0)]
+
+
+def test_private_closure_isolated_import_and_run_has_no_hidden_io():
+    script = r'''
+import sys, time, json
+from pathlib import Path
+from io import BytesIO
+from copy import deepcopy
+from contextlib import nullcontext
+from types import SimpleNamespace
+import pandas as pd
+import numpy.rec
+from trading_system.tree_replay._vendor.pricing import Plan
+import trading_system.tree_replay._vendor.admission_quality
+import trading_system.tree_replay._vendor.admission_swing
+sys.dont_write_bytecode = True
+violations = []
+importing = True
+def audit(event,args):
+    if event == 'open':
+        path = str(args[0]).replace('\\','/')
+        if importing and '/trading_system/tree_replay/_vendor/' in path and path.endswith(('.py','.pyc')):
+            return
+        violations.append((event,path))
+        raise RuntimeError('hidden filesystem access')
+    if event.startswith(('socket.','subprocess.','os.system')):
+        violations.append((event,''))
+        raise RuntimeError('hidden external I/O')
+def wall():
+    violations.append(('wall-clock',''))
+    raise RuntimeError('hidden wall clock')
+sys.addaudithook(audit)
+time.time = wall
+from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
+from trading_system.tree_replay._vendor import tracker_symbols
+importing = False
+class Ports:
+    def __init__(self): self.rows = {}
+    def load(self): return deepcopy(self.rows)
+    def save(self,rows): self.rows = deepcopy(rows)
+    def locked(self): return nullcontext()
+    def now_epoch(self): return 1788775200.0
+    def read_symbol(self,symbol,tfs): return {tf:SimpleNamespace(net=0.,bar_ts=1788775200.) for tf in tfs}
+    def fetch_corrected(self,*args): return pd.DataFrame(columns=['high','low']),None
+    def event_log_reader(self): return BytesIO(b'')
+    def quote_payload(self): return {}
+p = Ports(); t = TrackerAdmission(p)
+long = '\u05dc\u05d5\u05e0\u05d2'; sym = 'OANDA:XAUUSD'
+plan = Plan(sym,100.,'reversal',long,entry=100.,stop=90.,targets=[('TP1',120.)])
+assert not t.has_open(sym,long)
+assert t.record(plan) and t.has_open(sym,long)
+row = next(iter(p.rows.values())); row.update(state='STOPPED',resolved_ts=1788771600.)
+plan.entry = 89.99
+assert t.blocked_after_stop(sym,long,plan) is None and plan.cooldown_release is not None
+row['state'] = 'DONE'
+assert t.blocked_same_level(sym,long,100.) is not None
+assert violations == [], violations
+print('isolated tracker closure: no hidden I/O')
+'''
+    result = subprocess.run([sys.executable,"-B","-c",script],capture_output=True,text=True,
+                            cwd=Path(__file__).resolve().parents[2],timeout=30)
+    assert result.returncode == 0, result.stdout + result.stderr
+    assert "no hidden I/O" in result.stdout
+
+
+def test_latest_same_side_stop_controls_gate_and_missing_ts_preserves_source_catch():
+    old = stopped(); old["resolved_ts"] = NOW-20000
+    recent = stopped(); recent["resolved_ts"] = NOW-100
+    ports = MemoryPorts({"old": old,"new": recent})
+    tracker = module().TrackerAdmission(ports)
+    assert tracker.blocked_after_stop(SYM,LONG) is not None
+    # Source evaluates t['ts'] as the get default even with resolved_ts present.
+    del ports.rows["new"]["ts"]
+    assert tracker.blocked_after_stop(SYM,LONG) is None
+
+
+def test_swing_excludes_bar_exactly_at_stop_time():
+    row = stopped(); ports = MemoryPorts({"x": row})
+    ports.frame = pd.DataFrame({"high": [80,80,80,85,80,80,80,80], "low": [60]*8},
+        index=pd.to_datetime([row["resolved_ts"]+60*i for i in range(8)],unit="s",utc=True))
+    assert module().TrackerAdmission(ports).blocked_after_stop(SYM,LONG) is not None
+
+
+@pytest.mark.parametrize("rows,want", [
+    ({"x": {"state":"OPEN","symbol":SYM}}, True),
+    ({"x": {"state":"OTHER"}}, False),
+    ({"x": {"state":"OPEN","symbol":"other"}}, False),
+])
+def test_exposure_direction_none_and_source_unknown_state(rows,want):
+    assert module().TrackerAdmission(MemoryPorts()).has_open(SYM,state=rows) is want
+
+
+@pytest.mark.parametrize("resolved,want", [(0,False),(None,False),("bad",False),(float("nan"),False)])
+def test_same_level_unreadable_or_legacy_clock(resolved,want):
+    row = stopped(); row.update(state="DONE",resolved_ts=resolved)
+    assert (module().TrackerAdmission(MemoryPorts({"x":row})).blocked_same_level(SYM,LONG,100) is not None) is want
+
+
+def test_same_level_first_match_and_malformed_row_abort():
+    a = stopped(); a.update(state="DONE",entry=100,resolved_ts=NOW-60)
+    b = stopped(); b.update(state="CANCELLED",entry=101,resolved_ts=NOW-30)
+    ports = MemoryPorts({"a":a,"b":b}); tracker = module().TrackerAdmission(ports)
+    assert "100.00" in tracker.blocked_same_level(SYM,LONG,101)
+    del ports.rows["a"]["entry"]
+    assert tracker.blocked_same_level(SYM,LONG,101) is None
+
+
+@pytest.mark.parametrize("change", [dict(entry=0),dict(stop=0),dict(entry=None),dict(stop=None)])
+def test_record_missing_geometry_does_not_read_dependencies(change):
+    ports = MemoryPorts()
+    assert module().TrackerAdmission(ports).record(plan(**change)) is False
+    assert ports.rows == {} and ports.calls == []
+
+
+def test_record_unread_matrix_omits_optional_bias_and_defaults_thesis():
+    ports = MemoryPorts(); ports.fail.add("matrix")
+    assert module().TrackerAdmission(ports).record(plan())
+    row = next(iter(ports.rows.values()))
+    assert "bias_at_send" not in row and row["thesis_state"] == "held"
+
+
+def test_identity_canonical_rounding_target_names_and_style_case():
+    identity = module()._trade_identity
+    a = identity("GOLD",LONG,100,90,[("one",120),("two",130)],"INTRADAY")
+    b = identity(SYM,LONG,100.000000001,90,[("renamed",120),("two",130)],"intraday")
+    assert a == b
+    assert identity("GC",LONG,100,90,[("one",120),("two",130)],"intraday") != a
+    assert identity(SYM,LONG,100,90,[("two",130),("one",120)],"intraday") != a
+
+
+@pytest.mark.parametrize("fault", ["seek","tell","read","enter","exit"])
+def test_reader_all_original_io_errors_return_none(fault):
+    class Broken(BytesIO):
+        def seek(self,*args):
+            if fault == "seek": raise OSError("seek")
+            return super().seek(*args)
+        def tell(self):
+            if fault == "tell": raise OSError("tell")
+            return super().tell()
+        def read(self,*args):
+            if fault == "read": raise OSError("read")
+            return super().read(*args)
+        def __enter__(self):
+            if fault == "enter": raise OSError("enter")
+            return super().__enter__()
+        def __exit__(self,*args):
+            super().__exit__(*args)
+            if fault == "exit": raise OSError("exit")
+    assert module()._tail_reader(lambda:Broken(b"hello\n")) is None
+
+
+def test_rejection_inclusive_stop_time_newest_not_last_and_gap_rounding():
+    ports = MemoryPorts()
+    ports.raw = rejection(ts=NOW-10, levels=["newest"],zone_lo=103.234567,zone_hi=104) + rejection(ts=NOW-20)
+    result = module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-10,NOW,100,
+        require_overlap=False,max_distance=2)
+    assert result["levels"] == ["newest"] and result["gap"] == 1.2346
+
+
+def test_rejection_missing_zone_fields_retains_source_permissive_selection():
+    ports = MemoryPorts(); ports.raw = rejection(zone_lo=None,zone_hi=None)
+    result = module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-100,NOW,100)
+    assert result["gap"] == 0.0
+
+
+def test_rejection_bad_numeric_timestamp_propagates_outside_json_catch():
+    ports = MemoryPorts(); ports.raw = rejection(ts="bad")
+    with pytest.raises(ValueError):
+        module().TrackerAdmission(ports)._recent_rejection(SYM,LONG,NOW-100,NOW,100)
+
+
+def test_cooldown_uses_explicit_asof_and_survives_missing_log_telemetry():
+    ports = MemoryPorts({"x": stopped()}); ports.raw = rejection(ts=NOW,zone_lo=88,zone_hi=90)
+    tracker = module().TrackerAdmission(ports); p = plan(entry=89.99)
+    rel = tracker._cooldown_release(SYM,LONG,p,stopped(),NOW-3600,1,asof=NOW-1)
+    assert rel["recent_rejection"] is None
+    ports.fail.add("log")
+    assert tracker.blocked_after_stop(SYM,LONG,p) is None
+    assert p.cooldown_release["recent_rejection"] is None
warning: in the working copy of 'tests/tree_spec/test_tracker_admission_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_tracker_admission_source.py b/tests/tree_spec/test_tracker_admission_source.py
new file mode 100644
index 0000000..34123e8
--- /dev/null
+++ b/tests/tree_spec/test_tracker_admission_source.py
@@ -0,0 +1,115 @@
+"""Mandatory pinned source evidence and adversarial audit checks."""
+import importlib
+import os
+from pathlib import Path
+import json
+import subprocess
+import sys
+
+import pytest
+
+SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT",
+    "C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149"))
+
+
+def auditor():
+    try:
+        return importlib.import_module("trading_system.tree_spec.tracker_admission_source")
+    except ModuleNotFoundError as exc:
+        pytest.fail(f"tracker source auditor missing: {exc}")
+
+
+def test_complete_pinned_closure_is_verified():
+    report = auditor().audit_tracker_admission_source(SOURCE)
+    assert report["source_subset_verified"], f"Required pinned source evidence at {SOURCE}: {report['blockers']}"
+    assert report["status"] == "VERIFIED" and report["blockers"] == []
+    assert report["ready_for_replay"] is False and report["ready_for_training"] is False
+
+
+def test_missing_source_is_descriptive_blocker(tmp_path):
+    report = auditor().audit_tracker_admission_source(tmp_path)
+    assert report["status"] == "BLOCKED" and report["source_subset_verified"] is False
+    assert any("SOURCE" in b and "chart-desk" in b for b in report["blockers"])
+
+
+@pytest.mark.parametrize("relative,old,new,blocker", [
+    ("trading_system/tree_replay/_vendor/tracker_admission.py", "hours >= MAX_STOP_BLOCK_H", "hours > MAX_STOP_BLOCK_H", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/tracker_admission.py", "self.source.load()", "self.source.quote_payload()", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/tracker_admission.py", "bias_at_send = self._higher_bias(sym)", "bias_at_send = self._thesis_baseline(sym, plan.direction)", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/tracker_admission.py", "bias_at_send = self._higher_bias(sym)\n        thesis = self._thesis_baseline(sym, plan.direction)", "thesis = self._thesis_baseline(sym, plan.direction)\n        bias_at_send = self._higher_bias(sym)", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/tracker_admission.py", "_tail_reader(self.source.event_log_reader)", "_tail_reader(self.source.event_log_reader())", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/tracker_admission.py", "lambda: BytesIO(raw)", "lambda: BytesIO(b'')", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/tracker_admission.py", "from io import BytesIO", "from io import BytesIO\nimport socket", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/tracker_symbols.py", "pip = 0.01 if", "pip = 0.02 if", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/pricing.py", "entry - half", "entry + half", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/basis_symbols.py", "return s", "return s.upper()", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/admission_quality.py", "return names or None", "return None", "VENDOR_AST_MISMATCH"),
+    ("trading_system/tree_replay/_vendor/admission_swing.py", "SWING_K = 3", "SWING_K = 2", "VENDOR_AST_MISMATCH"),
+    ("chart-desk/chartdesk/tracker.py", "MAX_STOP_BLOCK_H = 4.0", "MAX_STOP_BLOCK_H = 5.0", "SOURCE_BLOB_MISMATCH"),
+])
+def test_audit_rejects_body_port_dependency_and_source_mutations(monkeypatch, relative, old, new, blocker):
+    audit = auditor()
+    target = ((SOURCE if relative.startswith("chart-desk/") else audit.ROOT) / relative).resolve()
+    read = Path.read_text
+    original = read(target, encoding="utf-8")
+    assert old in original, f"Mutation precondition missing: {relative}: {old}"
+    def changed(path, *args, **kwargs):
+        text = read(path, *args, **kwargs)
+        return text.replace(old,new,1) if path.resolve() == target else text
+    monkeypatch.setattr(Path,"read_text",changed)
+    report = audit.audit_tracker_admission_source(SOURCE)
+    assert report["source_subset_verified"] is False
+    assert any(blocker in b for b in report["blockers"]), report
+
+
+@pytest.mark.parametrize("mode", ["narrow", "pin", "duplicate"])
+def test_manifest_cannot_redefine_audit_authority(monkeypatch,mode):
+    audit = auditor(); read = Path.read_text
+    target = (audit.ROOT / "configs/trees/tracker-admission-source-contracts.json").resolve()
+    def changed(path,*args,**kwargs):
+        text = read(path,*args,**kwargs)
+        if path.resolve() != target:
+            return text
+        data = json.loads(text)
+        if mode == "narrow":
+            data["files"] = data["files"][:1]
+        elif mode == "pin":
+            data["repositories"]["chart-desk"] = "0"*40
+        else:
+            return text.replace('"ready_for_replay": false','"ready_for_replay": true, "ready_for_replay": false')
+        return json.dumps(data)
+    monkeypatch.setattr(Path,"read_text",changed)
+    report = audit.audit_tracker_admission_source(SOURCE)
+    assert report["source_subset_verified"] is False
+    assert any("CONTRACT" in b for b in report["blockers"])
+
+
+def test_repository_pin_mismatch_blocks(monkeypatch):
+    audit = auditor(); git = audit._git
+    def changed(repo,*args):
+        return "0"*40 if args == ("HEAD",) else git(repo,*args)
+    monkeypatch.setattr(audit,"_git",changed)
+    assert any("SOURCE_COMMIT_MISMATCH" in b for b in audit.audit_tracker_admission_source(SOURCE)["blockers"])
+
+
+def test_cli_requires_explicit_root_and_reports_missing_source(tmp_path):
+    cli = Path(__file__).resolve().parents[2] / "tools/check_tracker_admission_source_parity.py"
+    absent = subprocess.run([sys.executable,str(cli)],capture_output=True,text=True)
+    assert absent.returncode == 2 and "--source-root" in absent.stderr
+    missing = subprocess.run([sys.executable,str(cli),"--source-root",str(tmp_path)],capture_output=True,text=True)
+    assert missing.returncode == 2
+    assert json.loads(missing.stdout)["status"] == "BLOCKED"
+
+
+@pytest.mark.parametrize("old,new", [("from . import matrix, zones", "from . import matrix"),
+    ("_locked()", "_different_lock()"), ("path.open(\"rb\")", "path.open(\"r\")")])
+def test_projection_refuses_missing_substitution_preconditions(old,new):
+    audit = auditor()
+    try:
+        tracker = (SOURCE/"chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")
+        tradeplan = (SOURCE/"chart-desk/chartdesk/tradeplan.py").read_text(encoding="utf-8")
+    except OSError as exc:
+        pytest.fail(f"Required pinned source evidence missing at {SOURCE}: {exc}")
+    assert old in tracker
+    with pytest.raises(ValueError,match="SUBSTITUTION_PRECONDITION"):
+        audit._tracker_projection(tracker.replace(old,new),tradeplan)
warning: in the working copy of 'docs/architecture/TRACKER-ADMISSION-SOURCE-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/TRACKER-ADMISSION-SOURCE-USAGE.md b/docs/architecture/TRACKER-ADMISSION-SOURCE-USAGE.md
new file mode 100644
index 0000000..9adb1f9
--- /dev/null
+++ b/docs/architecture/TRACKER-ADMISSION-SOURCE-USAGE.md
@@ -0,0 +1,135 @@
+# Offline original tracker admission and recording
+
+This private dependency executes the pinned original exposure, post-stop,
+same-level and record decisions on explicit supplied ports. It does not bind
+the market-watch loop, generate subsequent tracker lifecycle transitions,
+simulate economic fills/exits, produce labels or authorize training. Acceptance
+belongs to the controller's exchange status, not this usage document.
+
+Source authority: chart-desk `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and
+trading-floor `d827dd792cbd1d396b4ee325879c63e57388e07a`. The latter remains a
+required baseline identity; none of its live code is imported by this closure.
+All runtime code is static under `trading_system/tree_replay/_vendor/`.
+Retained checkouts are read only as inert text by the auditor.
+
+## Calling the private closure
+
+```python
+from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
+
+tracker = TrackerAdmission(source)  # explicit per-instance offline ports
+occupied = tracker.has_open(symbol, direction)
+stop_reason = tracker.blocked_after_stop(symbol, direction, plan)
+level_reason = tracker.blocked_same_level(symbol, direction, plan.entry)
+# Caller controls source gate order and whether recording is appropriate.
+recorded = tracker.record(plan, variant="engine", to_group=False)
+```
+
+This example is not the full outer admission sequence. `record` accepts the
+private source `pricing.Plan` geometry; it does not itself certify producer
+admission or run all three gates shown above. `to_group` only stores the source
+advisory flag; it has no messaging or broker side effect.
+
+The source object must implement all these ports, with no host discovery or
+wall-clock defaults:
+
+| Port | Required supplied behavior |
+| --- | --- |
+| `now_epoch()` | Explicit decision epoch, float |
+| `load()` | Detached dict of source advisory rows; unavailable state raises |
+| `save(rows)` | Offline transactional sink; failure raises |
+| `locked()` | Context manager spanning source load, recheck, mutation and save |
+| `read_symbol(symbol, tfs)` | Original TFView-compatible values with `net` and `bar_ts` |
+| `fetch_corrected(symbol, timeframe, lookback_days)` | Supplied `(DataFrame, correction)`; source post-stop call is `15m`, 5 days |
+| `event_log_reader()` | Fresh seekable binary context manager over the entire causal log prefix; unavailable/open/read failure raises |
+| `quote_payload()` | Source mapping from symbol to `lp`/`ts` rows |
+
+The reader factory is passed without calling it to `_tail_reader(open_reader,
+window=400000, cap=8000000)`. Opening occurs inside the original try/with;
+opening, seeking, reading and context-manager failures return `None`. The source
+algorithm seeks to the end, reads the tail, drops a leading partial line, and
+expands the window by four when needed. A pathological last line may trigger the
+original full-prefix fallback; the cap is not an absolute bytes-read limit.
+The ordinary 10 GB virtual-prefix test reads exactly 400,000 bytes.
+
+`_tail_bytes(raw, window=400000, cap=8000000)` is only a small-fixture convenience
+using a lazy `BytesIO` factory. It returns `None` for `raw=None`; empty bytes are
+an empty log. Runtime rejection selection never eagerly asks for a full byte
+prefix. No reader implementation backed by files/services is supplied here.
+
+All source method signatures retain their original arguments after `self`:
+`has_open`, `blocked_after_stop`, `blocked_same_level`, `record`, `_record_locked`,
+`_born_in_zone`, `_entry_band`, `_higher_bias`, `_thesis_baseline`, `_live_prices`,
+`_recent_rejection`, `_cooldown_release`, and `thesis_now`. `_trade_identity`,
+`_anchor_names` and `thesis_verdict` are module functions. The exact pure
+`tradeplan.born_in_zone` helper is also included in this private module because
+the accepted pricing subset does not contain it; no accepted runtime file was
+extended. Its `entry_zone` dependency comes from the audited private pricing.
+
+## Source behavior retained
+
+- Only OPEN occupies a symbol/side. PENDING does not. Missing/corrupt exposure
+  state fails closed, while the source post-stop and same-level outer catches
+  return no block. Unknown explicit state names follow the original comparisons.
+- Latest same-symbol/side STOPPED controls post-stop. At four hours it releases
+  before matrix/frame reads. Earlier it sums 4h/1h at the original +/-25 boundary,
+  then tests the confirmed source swing on at least eight strictly post-stop
+  rows, then tests entry beyond the old stop by source symbol pip. The long/short
+  swing asymmetry is preserved. Anchor changes/rejection are optional telemetry.
+- Same-level checks DONE/CANCELLED, nonzero resolved time, age below 7200 seconds,
+  and inclusive entry-band edges. First matching row wins. Future rows can match;
+  causal state filtering remains the future binding's responsibility. Malformed
+  fields can abort the source scan. Post-stop's eager `t['ts']` default is retained.
+- Record reads higher bias, thesis and build/quote state before entering the lock,
+  then reloads and rechecks OPEN. Complete geometry deduplicates PENDING/OPEN;
+  resolved duplicates archive with the original integer send-time suffix. Suffix
+  collisions retain original overwrite behavior. Failed saves propagate.
+- Geometry identity canonicalizes source aliases, rounds eight decimals, hashes
+  all target prices/style/stop to 16 hex characters, and rounds display entry to
+  two decimals. Target names are not identity; order of prices is. This private
+  source behavior does not authorize GC/OANDA feed substitution.
+- Born-open requires a truthy build close in the entry band. Fresh quotes use a
+  one-sided reached test. Missing/stale quote defers to build. Freshness is
+  inclusive 0..420 seconds with finite positive price; future quotes are rejected.
+  OPEN-at-send explicitly stores broker revalidation false and is not a fill.
+- Higher bias requires both 4h/1h readings. Thesis uses the lower 30m/15m/5m
+  average, breaking at signed -25 and recovering at zero. Deadband/unread baseline
+  defaults to held. These are advisory readings, not economic labels.
+- Rejection selection preserves original substring prefilter, UTF-8 ignore,
+  malformed-JSON handling, inclusive stop/asof/max-age boundaries, overlap/gap
+  and output rounding. Equal timestamps retain the first encountered row.
+  Malformed numeric timestamps can raise outside JSON parsing; missing zone
+  fields retain source permissiveness. Non-rejection log bytes affect the tail.
+
+Every unavailable/error dependency must eventually be recorded by causal ports.
+A swallowed source failure is not verified replay readiness. The independent
+audit always reports `ready_for_replay=false` and `ready_for_training=false`.
+
+## Verification
+
+The auditor checks both repository roots/commits, baseline pins, canonical Git
+source blobs, a fixed independent manifest authority, full ordered runtime ASTs
+including imports/constants/methods and exact substitution preconditions. It
+independently covers inherited pricing (all Plan fields and four original
+properties), basis aliases, quarters, entry-quality and swing modules. It does
+not infer this closure from a passing unrelated audit or execute retained code.
+
+```powershell
+python -m pytest tests/tree_replay/test_tracker_admission.py tests/tree_spec/test_tracker_admission_source.py -q --tb=short
+python tools/check_tracker_admission_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
+```
+
+The runtime and source-audit tests use distinct basenames and run together under
+the repository's default pytest settings. The combined dependency check is:
+
+```powershell
+python -m pytest tests/tree_replay/test_tracker_admission.py tests/tree_spec/test_tracker_admission_source.py tests/tree_replay/test_admission_calculations.py tests/tree_spec/test_admission_source.py tests/tree_replay/test_pricing_source.py tests/tree_replay/test_pricing.py tests/tree_replay/test_state.py -q --tb=short
+```
+
+Tests accept `TR_TREE_SOURCE_ROOT` as an explicit alternate retained parent.
+Missing pinned checkouts fail descriptively; source evidence is never skipped.
+
+Remaining full binding must reconstruct actual source log appends/spacing and
+sessions, including pre/post detection and recording events. It must also bind
+causal frames, publication mode, outer gate/producer ordering, active-before-
+episode state, source lifecycle generation and separate economic simulation.

```

