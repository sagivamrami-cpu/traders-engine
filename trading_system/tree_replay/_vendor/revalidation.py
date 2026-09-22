"""Original pending-plan checks over offline ports; not full causal replay."""
from __future__ import annotations
import json
import pandas as pd
from pathlib import PurePosixPath
from . import lifecycle_voice as voice
from . import admission_matrix, pvsra, watch_sessions
from .tracker_admission import TrackerAdmission
from .stretch import StretchReader
from .ema_windows import EmaReader
AGED_PENDING_RECHECK_H = 2.0
_BIAS_AGAINST_AS_SENT = voice.check('ההטיה הגבוהה נגד העסקה — כך גם בשליחה', False)
_BIAS_AGAINST_FLAT_AT_SEND = voice.check('ההטיה הגבוהה נגד העסקה — בשליחה הייתה ניטרלית', False)
_BIAS_AGAINST_UNREAD = voice.check('ההטיה הגבוהה נגד העסקה — בשליחה לא נקראה', False)
SOFT_STALE_MIN = 20.0
HARD_STALE_MIN = 120.0

def calendar_event_ts(ev: dict) -> float | None:
    """Seconds since epoch for a calendar row, or None. ONE implementation.

    THE BLACKOUT NEVER FIRED. Until 2026-09-01 the gate read
    `e.get("dateline")` -- a field the cached ForexFactory feed does not have.
    Verified against the live cache: 0 of 112 rows carried it; all 112 carry
    `date`, ISO with an offset. Every event scored 0, the +/-15 minute test was
    never true, and the desk traded through every High-impact print while
    logging that it had checked.

    It lives here, module level, because the first fix put a copy in
    liveness.py too and the scanner flagged the duplicate within the minute --
    correctly. Two readers of one feed format is how one gets fixed and the
    other silently keeps the old shape. `dateline` stays as a fallback in case
    the upstream feed restores it.
    """
    from datetime import datetime as _d
    raw = ev.get('dateline')
    if isinstance(raw, (int, float)) and raw and (not isinstance(raw, bool)):
        return float(raw)
    txt = ev.get('date')
    if not txt:
        return None
    try:
        return _d.fromisoformat(str(txt)).timestamp()
    except (ValueError, TypeError):
        return None

def calendar_high_impact_in_window(events: list[dict], now_ts: float, window_s: float) -> dict | None:
    """Return the High-impact row inside ``window_s``, if one exists.

    This is the one firing condition for the cached ForexFactory shape. The
    trade plan, tree, and revalidation shadow used to each read the feed on
    their own; one asked for the nonexistent ``dateline`` field and silently
    stayed false forever. Consumers may choose different windows, but they do
    not get to invent different field names.
    """
    for event in events:
        ts = calendar_event_ts(event)
        if ts is None or abs(ts - now_ts) > window_s:
            continue
        impact = event.get('impact')
        if not isinstance(impact, str) or not impact.strip():
            raise ValueError('calendar event inside blackout window has no impact')
        if impact.lower().startswith('high'):
            return event
    return None

def _bias_against(nets: dict, short: bool) -> bool:
    """Every higher frame siding against the trade, and with weight.

    A FLIP SHOWS ON EVERY HIGHER TIMEFRAME, NOT IN AN AVERAGE. Summing let
    one timeframe outvote the other: on 2026-08-31 the BTC short carried 4h
    +43 and 1h -2, so the sum read +41 and the veto cancelled a filled,
    profitable position while the 1h agreed with the trade. Two timeframes
    pointing opposite ways is uncertainty, not a flip, and the tree may not
    veto on its own uncertainty -- so no higher frame may still side with
    the trade.
    """
    vals = [float(x) for x in (nets or {}).values()]
    if not vals:
        return False
    net = sum(vals)
    worst = min(vals) if short else max(vals)
    return net >= 25.0 and short and (worst >= 0.0) or (net <= -25.0 and (not short) and (worst <= 0.0))

class Revalidation:

    def __init__(self, source):
        self.source = source
        self.admission = TrackerAdmission(source)
        self.stretch = StretchReader(source)
        self.ema = EmaReader(source)

    def _tree_agrees(self, symbol: str, direction: str) -> tuple[bool, str]:
        """Does the decision tree still reach a trade, on this side, right now?

    Consulted but NOT given a veto on its own: measured over 26-27.08 the
    tree's verdict split outcomes 39% vs 40%, no demonstrated edge either way,
    so it reports and the caller decides. When the tree cannot run at all this
    returns True -- a broken tree must not silently block every revival, which
    is exactly the shape of failure this repo keeps producing.
    """
        try:
            w = self.source.tree_walk(symbol)
            if w is None:
                return (True, 'העץ לא החזיר תשובה')
            if w.direction and w.direction != direction:
                return (False, f'העץ מצביע לכיוון ההפוך ({w.direction})')
            if w.stopped_because:
                return (True, f'העץ נעצר ב-{w.reached}: {w.stopped_because}')
            return (True, 'העץ מאשר')
        except Exception as e:
            return (True, f'העץ לא זמין ({type(e).__name__})')

    def revalidate_pending(self, t: dict, *, now: float | None=None) -> tuple[bool, str, bool]:
        """Fill-time recheck; aged plans also need a non-opposing current tree.

    This does not build or send a new trade. It decides whether an old plan
    may transition PENDING->OPEN when its entry zone is finally reached.
    """
        ok, why, verified = self.still_valid(t)
        if not ok:
            return (ok, why, verified)
        now = self.source.now_epoch() if now is None else now
        try:
            age_h = max(0.0, (now - float(t['ts'])) / 3600.0)
        except (KeyError, TypeError, ValueError):
            return (True, why, False)
        if age_h < AGED_PENDING_RECHECK_H:
            return (True, why, verified)
        tree_ok, tree_note = self._tree_agrees(t['symbol'], t['direction'])
        if not tree_ok:
            return (False, f'בדיקה חוזרת אחרי {age_h:.1f} שעות: {tree_note}', True)
        clean = tree_note == 'העץ מאשר'
        note = f'בדיקה חוזרת אחרי {age_h:.1f} שעות: {tree_note}'
        return (True, '\n'.join((x for x in (why, note) if x)), bool(verified and clean))

    def _shadow(self, symbol: str, name: str, fired: bool, detail: str) -> None:
        """Record what a not-yet-enabled check WOULD have done.

    The four new checks Sagiv asked for have never been measured on this
    tape. Giving them veto power immediately risks trading one failure
    (entering on a dead thesis) for a worse one (cancelling everything and
    publishing nothing). So they run, they write here, and they do not vote
    until the log says how often they fire.
    """
        try:
            self.source.ensure_shadow_parent(parents=True, exist_ok=True)
            with self.source.shadow_open('a', encoding='utf-8') as fh:
                fh.write(json.dumps({'ts': self.source.now_epoch(), 'symbol': symbol, 'check': name, 'would_block': bool(fired), 'detail': detail}, ensure_ascii=False) + '\n')
        except Exception:
            pass

    def still_valid(self, t: dict) -> tuple[bool, str, bool]:
        """Is the thesis behind a PENDING trade still alive at fill time?

    Sagiv, 2026-08-26: *"אם הגיעו יש בחינה מחדש אם היא עדיין רלוונטית?"* --
    it did not. A trade sent at 09:00 and filled at 20:00 was opened on the
    09:00 thesis with no re-read, which is how a signal channel ends up long
    into a tape that turned hours earlier.

    Returns (ok, reason_when_not, verified).

    `verified` is the third value because the honest answer has three states,
    not two: the thesis holds, the thesis broke, or we could not tell. The
    first version collapsed the third into the first -- `except: return True`
    -- so a dead feed produced a confident "still valid" and the caller had no
    way to know the check had not run. That silence is the project's signature
    bug, and it was found here again on 2026-08-30 review.

    VETOING checks (measured or mechanical, allowed to cancel a trade):
      1. Higher-timeframe bias must not have FLIPPED against the trade. Bias
         decaying to neutral is tolerated -- a retest into a flat tape is
         still the trade that was sent; a bias that inverted is not.
      2. The tape must not now be extended in the trade's own direction.
      3. Evidence must not be older than HARD_STALE_MIN.

    SHADOW checks (run, logged, no vote yet -- see _shadow): EMA stack side,
    market structure, session/event window, and whether the stop is still a
    sane distance from the live entry.
    """
        symbol = t.get('symbol', '?')
        short = t['direction'] == 'שורט'
        verified = True
        label = ''
        try:
            nets = self.admission._higher_bias(symbol)
            if nets is None:
                raise RuntimeError('matrix.read_symbol returned nothing')
            net = sum(nets.values())
            if _bias_against(nets, short):
                sent = t.get('bias_at_send') or {}
                sent_net = sum((float(x) for x in sent.values())) if sent else None
                with_trade_at_send = sent_net is not None and (sent_net < 0 if short else sent_net > 0)
                if with_trade_at_send:
                    return (False, f'ההטיה הגבוהה התהפכה מאז השליחה ({net:+.0f})', True)
                if not sent:
                    label = _BIAS_AGAINST_UNREAD
                elif sent_net == 0:
                    label = _BIAS_AGAINST_FLAT_AT_SEND
                else:
                    label = _BIAS_AGAINST_AS_SENT
            st = self.stretch.state(symbol)
            if st is None:
                verified = False
                self._shadow(symbol, 'stretch', False, 'stretch.state() returned None')
            if st and st.is_extended and st.side:
                if (st.side == 'up') != short:
                    return (False, f'הטווח היומי כבר נוצל לכיוון העסקה ({st.budget_used * 100:.0f}% מה-ADR) — הכניסה איחרה', True)
        except Exception as exc:
            verified = False
            self._shadow(symbol, 'core', False, f'core checks unavailable: {exc}')
        age_min = None
        try:
            worst_ratio = None
            for tf, bar_min in (('15m', 15.0), ('1h', 60.0), ('4h', 240.0)):
                _df, _c = self.source.fetch_corrected(symbol, tf, 3)
                if _df is None or not len(_df):
                    continue
                last = _df.index[-1]
                a = (self.source.now_timestamp(tz=last.tz) - last).total_seconds() / 60.0
                ratio = a / (bar_min / 15.0)
                if worst_ratio is None or ratio > worst_ratio:
                    worst_ratio, age_min = (ratio, ratio)
        except Exception:
            age_min = None
        if age_min is not None and age_min > HARD_STALE_MIN:
            return (False, f'אין נתונים לאימות מחדש — הנר האחרון בן {age_min:.0f} דקות. לא נכנסים על תזה שלא ניתן לבדוק.', False)
        if age_min is None or age_min > SOFT_STALE_MIN:
            verified = False
        try:
            stack = self.ema.read_stack(symbol, timeframes=('1h', '15m'))
            for tf, es in (stack or {}).items():
                if es is None:
                    continue
                w = es.window(50)
                if w is None:
                    continue
                above = es.close > w.value
                against = above if short else not above
                self._shadow(symbol, f'ema50_{tf}', against, f'close {es.close:.2f} vs ema50 {w.value:.2f}, short={short}')
        except Exception as exc:
            self._shadow(symbol, 'ema', False, f'unavailable: {exc}')
        try:
            cur = watch_sessions.current_session_at(decision_time=self.source.now_timestamp(tz='UTC'))
            self._shadow(symbol, 'session', not bool(cur), f'sessions={cur}')
        except Exception as exc:
            self._shadow(symbol, 'session', False, f'unavailable: {exc}')
        try:
            entry, stop = (float(t['entry']), float(t['stop']))
            risk = abs(entry - stop)
            self._shadow(symbol, 'stop_distance', risk <= 0, f'entry {entry:.2f} stop {stop:.2f} risk {risk:.2f}')
        except Exception as exc:
            self._shadow(symbol, 'stop_distance', False, f'unavailable: {exc}')
        try:
            _d4, _ = self.source.fetch_corrected(symbol, '4h', 400)
            stru = admission_matrix.read_structure(_d4)
            against = stru.direction != 0 and (stru.direction < 0 if not short else stru.direction > 0)
            self._shadow(symbol, 'structure_4h', bool(against), f'structure dir {stru.direction}, short={short}')
        except Exception as exc:
            self._shadow(symbol, 'structure_4h', False, f'unavailable: {exc}')
        try:
            _d15, _ = self.source.fetch_corrected(symbol, '15m', 60)
            _p = pvsra.pvsra(_d15).tail(12)
            opp = {'red', 'violet'} if not short else {'green', 'blue'}
            fired = bool(_p['kind'].isin(opp).any())
            self._shadow(symbol, 'opposing_vector_15m', fired, f"last12 kinds={list(_p['kind'].tail(4))}")
        except Exception as exc:
            self._shadow(symbol, 'opposing_vector_15m', False, f'unavailable: {exc}')
        try:
            import json as _json
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td
            _cal = PurePosixPath('news-desk') / 'data' / 'ff_calendar.json'
            if not self.source.calendar_exists(_cal.as_posix()):
                self._shadow(symbol, 'news_window', False, 'calendar file missing')
            else:
                _now = self.source.now_utc()
                _event = calendar_high_impact_in_window(_json.loads(self.source.calendar_text(_cal.as_posix())), _now.timestamp(), 30 * 60)
                _title = _event.get('title', '?') if _event is not None else None
                self._shadow(symbol, 'news_window', _event is not None, f'inside ±30m of: {_title}' if _event is not None else 'clear')
        except Exception as exc:
            self._shadow(symbol, 'news_window', False, f'unavailable: {exc}')
        return (True, label, verified)
