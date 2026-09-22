"""Private pinned tracker decisions on explicit offline ports. No lifecycle or readiness."""
from __future__ import annotations
import json
import hashlib
import math
from io import BytesIO
import pandas as pd
from . import basis_symbols as basis
from .pricing import entry_zone
MAX_STOP_BLOCK_H = 4.0
QUOTE_MAX_AGE_S = 420.0
LEVEL_COOLDOWN_S = 2 * 3600.0
WEAK_GATE = 25.0
THESIS_RECOVER = 0.0


def _trade_identity(symbol: str, direction: str, entry: float, stop: float, targets: list, style: str) -> tuple[str, str]:
    """Stable (state key, receipt id) for one exact trade geometry."""
    canonical = basis.canonical_symbol(symbol)
    geometry = {
        'symbol': canonical,
        'direction': direction,
        'entry': round(float(entry), 8),
        'stop': round(float(stop), 8),
        'targets': [round(float(px), 8) for _name, px in targets or []],
        'style': (style or 'intraday').lower(),
    }
    digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]
    key = f"{canonical}:{direction}:{round(float(entry), 2)}:{geometry['style']}:{digest}"
    return (key, digest)


def _anchor_names(reasons) -> set[str] | None:
    """See entry_quality.anchor_names — ONE parser, imported, not restated."""
    from .admission_quality import anchor_names
    return anchor_names(reasons)


def _tail_reader(open_reader, window: int=400000, cap: int=8000000) -> bytes | None:
    """The last `window` bytes of a JSONL file, whole lines only.

    This was `read_bytes()[-window:]`, which loaded all 10 MB of watch_events
    twice per plan AND — Codex's catch — silently returned NOTHING whenever
    the final line was longer than the window: the slice began inside that
    line, the leading partial was dropped, and every earlier rejection
    disappeared with no error. Seek from the end, and widen until a line
    boundary is actually inside the window rather than assuming one is.
    """
    try:
        with open_reader() as fh:
            fh.seek(0, 2)
            size = fh.tell()
            while True:
                start = max(0, size - window)
                fh.seek(start)
                raw = fh.read()
                if start == 0:
                    return raw
                cut = raw.find(b'\n')
                if cut != -1 and cut + 1 < len(raw):
                    return raw[cut + 1:]
                if window >= cap:
                    fh.seek(0)
                    return fh.read()
                window *= 4
    except Exception:
        return None


def _tail_bytes(raw, window: int=400000, cap: int=8000000) -> bytes | None:
    if raw is None:
        return None
    return _tail_reader(lambda: BytesIO(raw), window, cap)


def born_in_zone(symbol: str, entry: float, close: float | None) -> bool:
    """Was the plan built with price already inside its entry band?

    Such a trade is active the moment it is sent; a ▶️ "המחיר הגיע לאזור"
    ten seconds later tells the client nothing they did not just read
    (three of the night's four fills, 2026-09-04). The signal says it
    instead, and the tracker records the trade OPEN.
    """
    if not close:
        return False
    zlo, zhi = entry_zone(symbol, float(entry))
    return zlo <= float(close) <= zhi


def thesis_verdict(lo: float, direction: str) -> str | None:
    """Classify a lower-net reading for a trade: 'broken', 'held', or None.

    HYSTERESIS (2026-09-04). One threshold, WEAK_GATE, was both the break
    and the recovery line, and gold sat ON it all night: -25, -29, -25, -30
    against a gate of 25 gave five ⚠️/🔄 flips in an hour, none of which
    was a change of anything. Break at -WEAK_GATE; recover only at
    THESIS_RECOVER; in between the trade KEEPS whatever state it has, and
    this returns None so the caller cannot mistake the deadband for either.
    The desk reports direction, the client decides -- this is a reading,
    never an instruction.
    """
    signed = lo * (1 if direction == 'לונג' else -1)
    if signed <= -WEAK_GATE:
        return 'broken'
    if signed >= THESIS_RECOVER:
        return 'held'
    return None


class TrackerAdmission:

    def __init__(self, source):
        self.source = source

    def record(self, plan, *, variant: str='engine', to_group: bool=False) -> bool:
        """Register a trade for outcome tracking.

    Failures intentionally propagate. A caller must never publish or queue an
    entry after tracking failed; swallowing this error is how a shipped trade
    becomes invisible for its entire move.
    """
        if not getattr(plan, 'entry', None) or not getattr(plan, 'stop', None):
            return False
        sym = basis.canonical_symbol(plan.symbol)
        bias_at_send = self._higher_bias(sym)
        thesis = self._thesis_baseline(sym, plan.direction)
        born = self._born_in_zone(plan, sym)
        try:
            plan.born_open = born
        except Exception:
            pass
        with self.source.locked():
            return self._record_locked(plan, variant, to_group, bias_at_send, thesis, born)

    def _born_in_zone(self, plan, sym: str) -> bool:
        """Is this trade active from the send? The build's close must sit inside
    the entry band AND the live tap must say the band has been reached.

    The build's close alone is the state of the tape when the plan was
    made; build_all() makes every symbol and style before market_watch
    records any of them, so by record() the price can have left the band
    (Codex, 2026-09-04). A fresh quote that disagrees means PENDING and the
    fill machinery takes over -- an extra ▶️ is a true message, a wrong
    "פעילה" is not. A stale or missing quote defers to the build.

    "Reached" is check_live's own one-sided fill test (a short fills at or
    above the band's floor, a long at or below its ceiling), not "inside
    the band": a short built at 4,600 with the tap at 4,603 would otherwise
    be recorded PENDING here and filled by the very next pass -- a ▶️ under
    a signal that already said the trade is active (Codex, second pass).
    """
        try:
            if not born_in_zone(plan.symbol, plan.entry, getattr(plan, 'close', None)):
                return False
            spot = self._live_prices().get(sym)
            if spot is None:
                return True
            zlo, zhi = self._entry_band({'symbol': plan.symbol, 'entry': plan.entry})
            return spot >= zlo if plan.direction == 'שורט' else spot <= zhi
        except Exception:
            return False

    def _record_locked(self, plan, variant: str, to_group: bool, bias_at_send: dict | None=None, thesis: str='held', born: bool=False) -> bool:
        d = self.source.load()
        if self.has_open(basis.canonical_symbol(plan.symbol), plan.direction, state=d):
            return False
        _style = getattr(plan, 'style', 'intraday')
        key, trade_id = _trade_identity(plan.symbol, plan.direction, plan.entry, plan.stop, plan.targets, _style)
        prev = d.get(key)
        if prev is not None:
            if prev.get('state') in ('PENDING', 'OPEN'):
                return False
            d[f"{key}@{int(prev.get('ts', 0))}"] = prev
        if True:
            d[key] = {
                'symbol': basis.canonical_symbol(plan.symbol),
                'direction': plan.direction,
                'entry': float(plan.entry), 'stop': float(plan.stop),
                'targets': [[n, float(p)] for n, p in plan.targets],
                'obstacles': [[n, float(p)] for n, p in getattr(plan, 'obstacles', None) or []],
                'reasons': [str(r) for r in getattr(plan, 'reasons', None) or []],
                'variant': variant, 'to_group': bool(to_group),
                'style': getattr(plan, 'style', 'intraday'),
                'trade_id': trade_id, 'kind': getattr(plan, 'kind', 'trend'),
                'state': 'PENDING', 'hit': [], 'ts': self.source.now_epoch(),
                'thesis_state': thesis, 'thesis_warned': False,
            }
            if born:
                d[key]['state'] = 'OPEN'
                d[key]['born_in_zone'] = True
                d[key]['revalidation_verified'] = False
                d[key]['fill_verification_reason'] = 'born_open_not_broker_verified'
                d[key]['filled_ts'] = d[key]['progress_ts'] = d[key]['ts']
            if bias_at_send:
                d[key]['bias_at_send'] = bias_at_send
            self.source.save(d)
            return True

    def _entry_band(self, t: dict) -> tuple[float, float]:
        """The price band that fills this trade. Falls back to the exact level."""
        try:
            from .pricing import entry_zone
            return entry_zone(t['symbol'], float(t['entry']))
        except Exception:
            e = float(t['entry'])
            return (e, e)

    def has_open(self, symbol: str, direction: str | None=None, *, state: dict | None=None) -> bool:
        """Does an actually filled position occupy this symbol/side?

    A PENDING retest is a plan, not exposure. Sagiv's 2026-09-07 ruling:
    pending scalp/intraday/swing plans may coexist and must not suppress a
    fresh valid plan. Exact duplicate geometry is still refused by record();
    once one plan fills, OPEN owns the direction slot.

    Corrupt or unreadable state fails closed because it cannot prove there is
    no open position. A row explicitly known to be PENDING never blocks.
    """
        try:
            trades = state if state is not None else self.source.load()
        except Exception:
            return True
        if not isinstance(trades, dict):
            return True
        for t_ in trades.values():
            if not isinstance(t_, dict) or 'state' not in t_:
                return True
            if t_['state'] != 'OPEN':
                continue
            if 'symbol' not in t_:
                return True
            if t_['symbol'] != symbol:
                continue
            if direction is None:
                return True
            if 'direction' not in t_:
                return True
            if t_['direction'] == direction:
                return True
        return False

    def _higher_bias(self, symbol: str) -> dict[str, float] | None:
        """The higher-timeframe reading, {tf: net} for 4h and 1h. None = unread.

    TFView exposes `net`, not `score` (a wrong name caught by reading the
    source before deploying). One reader for the send and the fill, so the
    two values still_valid compares were taken the same way.

    Both frames or nothing. _bias_against needs every higher frame to side
    against the trade; a reading with one frame missing would let the other
    frame veto alone -- the 08-31 BTC sum-vote in a new shape.
    """
        tfs = ('4h', '1h')
        try:
            v = self.source.read_symbol(symbol, tfs=tfs)
            nets = {tf: float(x.net) for tf, x in v.items() if x is not None}
            return nets if all((tf in nets for tf in tfs)) else None
        except Exception:
            return None

    def _live_prices(self) -> dict:
        """Spot from HIS TradingView tap, only while genuinely fresh."""
        out = {}
        try:
            d = self.source.quote_payload()
        except Exception:
            return out
        now = self.source.now_epoch()
        for sym, q in d.items():
            try:
                price = float(q.get('lp', 0))
                age = now - float(q.get('ts', 0))
                if math.isfinite(price) and price > 0 and (0 <= age <= QUOTE_MAX_AGE_S):
                    out[sym] = price
            except Exception:
                continue
        return out

    def _thesis_baseline(self, symbol: str, direction: str) -> str:
        """The thesis state a trade is BORN with, read at record time.

    Not at the first post-fill read: a trade sent aligned that fills an
    hour later, after the short frames reversed, would have its reversal
    swallowed as the baseline. A trap reversal is born with the short
    frames against it by construction -- that is stored as 'broken' and
    never warned about (it was the setup), and when they join the trade
    the client hears that they joined, not that something 'recovered'.
    Unreadable tape defaults to 'held': the conservative side is a warning
    the client can weigh, not a silence.
    """
        try:
            now = self.thesis_now(symbol)
            if now is None:
                return 'held'
            return thesis_verdict(now[1], direction) or 'held'
        except Exception:
            return 'held'

    def _recent_rejection(self, symbol: str, direction: str, stopped_ts: float, asof_ts: float, entry: float, max_age_s: float=20 * 60, require_overlap: bool=True, max_distance: float | None=None) -> dict | None:
        """The newest logged rejection that could have informed this entry.

    CAUSAL, not retrospective: only rows already written when the plan was
    built count. On 2026-09-04 the 10:07 rejection at 4,461.69–4,462.54
    supports the 10:07–10:19 longs and says nothing about the 10:01 one --
    it did not exist yet -- which is exactly why the release rule below does
    not depend on it.

    Two callers, two geometries. A rejection that AGREES with a trade has to
    be where the trade is (`require_overlap`) -- support you are buying. A
    rejection that argues AGAINST it does not: the cluster the 10:25 short
    sold into sat five points below its entry and outside its zone, and that
    is precisely the distance that made it dangerous. `max_distance` bounds
    how far away "against this trade" still reaches.
    """
        raw = _tail_reader(self.source.event_log_reader)
        if raw is None:
            return None
        zlo, zhi = (0.0, 0.0)
        try:
            from .pricing import entry_zone
            zlo, zhi = entry_zone(symbol, float(entry))
        except Exception:
            pass
        canon = basis.canonical_symbol(symbol)
        best, best_gap = (None, 0.0)
        for line in raw.decode('utf-8', 'ignore').splitlines():
            if '"rejection"' not in line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get('kind') != 'rejection' or r.get('direction') != direction:
                continue
            if basis.canonical_symbol(str(r.get('symbol', ''))) != canon:
                continue
            ts = float(r.get('ts', 0.0))
            if not stopped_ts <= ts <= asof_ts or asof_ts - ts > max_age_s:
                continue
            lo, hi = (r.get('zone_lo'), r.get('zone_hi'))
            gap = 0.0
            if zhi > zlo and isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
                gap = max(zlo - float(hi), float(lo) - zhi, 0.0)
                if gap > 0:
                    if require_overlap:
                        continue
                    if max_distance is not None and gap > float(max_distance):
                        continue
            if best is None or ts > float(best.get('ts', 0.0)):
                best, best_gap = (r, gap)
        if best is None:
            return None
        out = {k: best.get(k) for k in ('ts', 'direction', 'zone_lo', 'zone_hi', 'levels', 'close', 'wick_atr')}
        out['age_s'] = round(asof_ts - float(best.get('ts', asof_ts)), 1)
        out['gap'] = round(best_gap, 4)
        return out

    def _cooldown_release(self, symbol: str, direction: str, plan, last: dict, stopped_ts: float, hours: float, asof: float | None=None) -> dict | None:
        """Is this plan a NEW setup rather than the stopped one, re-priced?

    Codex, leading the 2026-09-04 gold post-mortem, ruled the boundary is the
    stop that rejected us. The morning supplies both cases: after the 4,475.01
    long stopped at 4,465.51, the 08:23 rebuild at 4,471.56 sat ABOVE that
    stop -- the same thesis at a better price, and the day low at 4,460.155
    would have taken it out too. The 10:01 rebuild at 4,463.24 sat BELOW it:
    price had traded through the invalidation, made a new low, and come back.
    That is not a re-entry, it is a different trade at a different level.

    The anchor and the rejection are recorded as telemetry so the exception
    can be scored later. Neither may veto: requiring a logged rejection would
    have released nothing before 10:07, and by 10:07 the target economics had
    already moved the trade out of reach.
    """
        if plan is None:
            return None
        entry = getattr(plan, 'entry', None)
        stop = getattr(plan, 'stop', None)
        if entry is None:
            return None
        try:
            entry = float(entry)
            old_stop = float(last['stop'])
        except (TypeError, ValueError, KeyError):
            return None
        if entry != entry or entry in (float('inf'), float('-inf')):
            return None
        if getattr(plan, 'direction', direction) != direction:
            return None
        try:
            if basis.canonical_symbol(getattr(plan, 'symbol', symbol)) != basis.canonical_symbol(symbol):
                return None
        except Exception:
            pass
        try:
            from . import tracker_symbols as _sym
            pip = float(_sym.resolve(symbol).pip)
        except Exception:
            pip = 0.0
        if direction == 'שורט':
            crossed = entry >= old_stop + pip
        else:
            crossed = entry <= old_stop - pip
        if not crossed:
            return None
        new_anchor = _anchor_names(getattr(plan, 'reasons', None))
        old_anchor = _anchor_names(last.get('reasons'))
        changed = None
        if new_anchor is not None and old_anchor is not None:
            changed = new_anchor != old_anchor
        return {
            'plan_entry': entry, 'plan_stop': None if stop is None else float(stop),
            'stopped_trade_id': last.get('trade_id'), 'stopped_entry': last.get('entry'),
            'stopped_stop': old_stop, 'stopped_resolved_ts': stopped_ts,
            'hours_since_stop': round(hours, 2),
            'boundary_margin': round(abs(entry - old_stop), 4),
            'release_rule': 'entry_beyond_stopped_stop',
            'new_anchor': sorted(new_anchor) if new_anchor else None,
            'stopped_anchor': sorted(old_anchor) if old_anchor else None,
            'anchor_changed': changed,
            'recent_rejection': self._recent_rejection(
                symbol, direction, stopped_ts,
                self.source.now_epoch() if asof is None else float(asof), entry),
        }

    def blocked_after_stop(self, symbol: str, direction: str, plan=None) -> str | None:
        """Refuse a re-entry on the same thesis until the STRUCTURE changes.

    Sagiv, 2026-08-27, choosing between a fixed cooldown and a structural one:
    *"צינון עד שהמבנה משתנה"*. The night before, a gold short stopped at 01:06
    and an identical gold short went out at 01:12 -- same direction, same
    reasoning, six minutes later, entry re-priced 30 points away. The slot
    guard stops PARALLEL trades; it says nothing about a SEQUENCE.

    A clock-based cooldown would have been the easy version and the wrong one:
    an hour is arbitrary, and if the market genuinely turns in twenty minutes
    the block is pure cost. What actually invalidates "the market already told
    us no" is the market saying something new. So the block lifts on one of:

      1. a NEW confirmed 15m swing has formed beyond the stopped trade's stop
         -- structure has moved past the level that rejected us; or
      2. the higher-timeframe bias has FLIPPED -- the thesis itself changed; or
      3. MAX_STOP_BLOCK_H has elapsed, so a quiet tape cannot freeze the
         instrument forever; or
      4. the plan's own ENTRY lies beyond the stop that rejected us -- see
         _cooldown_release. Added 2026-09-04, after the block refused three
         gold longs at 4,462-4,463 (TP1 = DAY-OPEN, 1.35-1.47R) built on the
         cluster London then opened on, and price ran to 4,490.9.

    Returns a reason string while blocked, None when clear.
    """
        from . import admission_swing as zones
        try:
            last = None
            for t in self.source.load().values():
                if t['symbol'] == symbol and t['direction'] == direction and (t.get('state') == 'STOPPED'):
                    if last is None or float(t.get('resolved_ts', t['ts'])) > float(last.get('resolved_ts', last['ts'])):
                        last = t
            if last is None:
                return None
            stopped_ts = float(last.get('resolved_ts', last['ts']))
            hours = (self.source.now_epoch() - stopped_ts) / 3600.0
            if hours >= MAX_STOP_BLOCK_H:
                return None
            short = direction == 'שורט'
            try:
                v = self.source.read_symbol(symbol, tfs=('4h', '1h'))
                net = sum((x.net for x in v.values() if x is not None))
                if net >= 25.0 and short or (net <= -25.0 and (not short)):
                    return None
            except Exception:
                pass
            try:
                df, _c = self.source.fetch_corrected(symbol, '15m', 5)
                idx = pd.to_datetime(df.index, utc=True)
                after = df[[ts.timestamp() > stopped_ts for ts in idx]]
                if len(after) >= 8:
                    sw = zones._last_swing(after, up=short)
                    if sw is not None:
                        lvl = float(sw[0])
                        moved = lvl > last['stop'] if short else lvl < last['stop']
                        if moved:
                            return None
            except Exception:
                pass
            try:
                rel = self._cooldown_release(symbol, direction, plan, last, stopped_ts, hours)
            except Exception:
                rel = None
            if rel is not None:
                try:
                    plan.cooldown_release = rel
                except Exception:
                    pass
                return None
            return f'סטופ לפני {hours:.1f} שעות באותו כיוון — ממתינים לשינוי מבנה או להיפוך הטיה'
        except Exception:
            return None

    def blocked_same_level(self, symbol: str, direction: str, entry: float) -> str | None:
        """Refuse a plan whose entry sits inside the zone of a trade on the same
    symbol+direction that finished (DONE / CANCELLED) within LEVEL_COOLDOWN_S.

    Returns a reason string while blocked, None when clear. STOPPED is
    blocked_after_stop's business; PENDING/OPEN is has_active's.
    """
        try:
            from .pricing import entry_zone
            now = self.source.now_epoch()
            for t in self.source.load().values():
                if not isinstance(t, dict) or t.get('symbol') != symbol:
                    continue
                if t.get('direction') != direction:
                    continue
                if t.get('state') not in ('DONE', 'CANCELLED'):
                    continue
                ended = float(t.get('resolved_ts') or 0.0)
                if not ended or now - ended >= LEVEL_COOLDOWN_S:
                    continue
                lo, hi = entry_zone(symbol, float(t['entry']))
                if lo <= float(entry) <= hi:
                    mins = max(1, int((now - ended) // 60))
                    return f"אותה רמה נסחרה זה עתה: {float(t['entry']):,.2f} סיימה לפני {mins} דק׳"
            return None
        except Exception:
            return None

    def thesis_now(self, symbol: str) -> tuple[float, float, float] | None:
        """The bias reading RIGHT NOW: (higher net, lower net, bar_ts).

    WHY THIS EXISTS. 2026-09-01: a NAS100 long and a BTC long both ran to
    their stops, and this reading called it 90 minutes early on BOTH. The
    lower net went +29.7 -> -60.0 on the Nasdaq and -6.6 -> -66.7 on BTC
    while the higher-timeframe net sat frozen at 42.5 and 46.2 and the
    direction, which is taken from the higher net alone, never changed.
    The desk owned the rule -- `weak` in build(), the same WEAK_GATE -- but
    computed it ONCE, at birth, and nothing read it again.

    The lower net is the SAME (30m+15m+5m)/3 that build() gates on, so a
    trade born aligned and a trade read later are judged by one number
    (2026-09-04; the first version averaged 15m/5m only and disagreed with
    the gate that had passed the trade). bar_ts is the epoch of the newest
    5m bar the reads came from -- a transition is confirmed by BARS, not
    by wall-clock minutes. Returns None when the tape cannot be read: an
    outage must not be able to look like a reversal, or like a recovery.
    """
        try:
            v = self.source.read_symbol(symbol, tfs=('4h', '1h', '30m', '15m', '5m'))
            return ((v['4h'].net + v['1h'].net) / 2.0, (v['30m'].net + v['15m'].net + v['5m'].net) / 3.0, float(v['5m'].bar_ts))
        except Exception:
            return None
