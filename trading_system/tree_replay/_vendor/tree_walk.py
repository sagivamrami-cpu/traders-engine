from __future__ import annotations
import pandas as pd
from . import admission_matrix as matrix, map_sessions as sessions, watch_sessions
from . import tree_signals as tr
from .basis_operation import BasisOperation
from .levelmap_operation import LevelmapOperation
from .brinks import BrinksReader
from .checklists import ChecklistReader
from .wm import WmReader
from .liquidity import LiquidityReader
from .optionswall import OptionsWallReader
from .stretch import StretchReader
from .tree_core import VECTOR_BASE, RECOVERY, MAX_MAGNET_ATR, AGGRESSIVE_ATR, AGGRESSIVE_BARS, EXTREME_LOOKBACK, BUY_SIDE, SELL_SIDE, EXTREME_PCT, MAX_DECISION_DRIFT_ATR, LEVEL_ZONE_ATR, STOP_CUSHION_ATR, TREE_STYLE, SV_BODY_MAX, SV_WICK_MIN, SV_VOLUME_MULT, LevelsUnavailable, FINAL_STAGE, STAGES, _news_stop, Walk, _atr, _stopping_volume, _levels_ahead, _stamp_decision, _levels_unavailable_reason, TREND_LADDER, HI_FRAMES, LO_FRAMES, _side, _trend_from_ladder, _ladder_text, trap_direction

class TreeReader:

    def __init__(self, source):
        self.source = source
        self.basis = BasisOperation(source)
        self.levelmap = LevelmapOperation(source)
        self.brinks = BrinksReader(source)
        self.checklists = ChecklistReader(source)
        self.wm = WmReader(source)
        self.liquidity = LiquidityReader(source)
        self.optionswall = OptionsWallReader(source)
        self.stretch = StretchReader(self.basis)

    def _variant_levels(self, symbol: str, variant: str, missing: list | None=None) -> list | None:
        """The level list a variant sees. This is the whole difference between them.

    house  -- his toolkit: levelmap as-is, floor pivots EXCLUDED (his 2026-08-11
              decision: "לא בערכת הכלים שלי").
    strict -- the tree exactly as written: layer 4 demands PIVOTS (7) and
              M LEVELS (6), so daily_pivots' 13 objects are added.

    Sagiv, 2026-08-26: run both IN PARALLEL and measure which is more accurate,
    rather than letting the authority order settle it untested. Neither variant
    is "right" yet -- the tree_trade log, split by variant, is what will say.
    """
        basis = self.basis
        levelmap = self.levelmap
        try:
            lv, _ = levelmap.build(symbol, missing)
            out = [(l.name, float(l.price)) for l in lv]
        except Exception:
            return None
        if variant == 'strict':
            try:
                d1, _ = basis.fetch_corrected(symbol, '1d', 30)
                for name, px in tr.daily_pivots(d1).items():
                    out.append((name, float(px)))
            except Exception:
                return None
        return out

    def _trend_ladder(self, symbol: str, d4h, r4) -> dict:
        """read_tr on every frame in the stack. A frame that fails is absent."""
        basis = self.basis
        out = {'4h': r4}
        for tf in TREND_LADDER[1:]:
            try:
                df, corr = basis.fetch_corrected(symbol, tf, 30)
                if corr is not None and getattr(corr, 'unverified', False):
                    continue
                out[tf] = matrix.read_tr(df)
            except Exception:
                continue
        return out

    def walk(self, symbol: str, variant: str='house') -> Walk:
        """Run the tree. `variant` picks the level universe -- see _variant_levels."""
        basis = self.basis
        brinks = self.brinks
        checklists = self.checklists
        wm = self.wm
        stretch = self.stretch
        w = Walk(symbol=symbol, reached='DATA', variant=variant)
        w.assumptions = [f"מסלול={('עץ-מלא' if variant == 'strict' else 'בית')}", f'וקטור={VECTOR_BASE}', f'אישוש={RECOVERY}', f'קצה={int(EXTREME_PCT * 100)}% / {EXTREME_LOOKBACK} נרות', f'רוחב רמה={LEVEL_ZONE_ATR} ATR']
        try:
            d15, corr = basis.fetch_corrected(symbol, '15m', 10)
            d4h, corr4 = basis.fetch_corrected(symbol, '4h', 60)
        except Exception as e:
            w.stopped_because = f'אין נתונים ({type(e).__name__})'
            return w
        for _frame, _c in (('15m', corr), ('4h', corr4)):
            if _c is not None and getattr(_c, 'unverified', False):
                w.stopped_because = f'מקור המחיר של {_frame} לא מאומת — הקריאה והרמות יהיו שגויות'
                return w
        if len(d15) < 5 or len(d4h) < 5:
            w.stopped_because = f'אין מספיק נרות ({len(d15)}×15m, {len(d4h)}×4h) — העץ קורא עד שלושה נרות אחורה'
            return w
        _stale = [(f, c) for f, c in (('15m', corr), ('4h', corr4)) if c is not None and getattr(c, 'source', '').endswith('_stale')]
        if _stale:
            w.stopped_because = 'הטייפ מפגר: ' + ' · '.join((f'{f} — {c.note}' for f, c in _stale))
            return w
        atr = _atr(d15) or 1e-09
        close = float(d15['close'].iloc[-1])
        w.passed.append('DATA')
        w.reached = 'CONTEXT'
        try:
            r4 = matrix.read_tr(d4h)
        except Exception as exc:
            from types import SimpleNamespace as _NS
            r4 = _NS(direction=0, strength=0, note='לא נקרא')
            w.missing.append(f'קריאת המגמה 4h לא נקראה ({type(exc).__name__})')
        ladder = self._trend_ladder(symbol, d4h, r4)
        hi_dir, lo_dir, dir_src, dir_tf = _trend_from_ladder(ladder)
        w.facts['מגמה גבוהה'] = _ladder_text(ladder, ('4h', '1h'))
        w.facts['מגמה קצרה'] = _ladder_text(ladder, ('30m', '15m', '5m'))
        if dir_src is None:
            w.missing.append('אין מגמה באף מסגרת — 4h/1h/30m/15m/5m כולן דחוסות')
        else:
            w.facts['מסגרת הכיוון'] = f'{dir_src} · נקרא מ-{dir_tf}'
            if dir_src != 'טווח גבוה (4h+1h)':
                w.facts['מגמה'] = f'הטווח הגבוה לא הכריע — הכיוון מ{dir_src}'
        if hi_dir and lo_dir and (hi_dir != lo_dir):
            w.facts['פער מגמות'] = f'הטווח הגבוה {hi_dir} מול הטווח הקצר {lo_dir} — לא מיושר'
        r4 = ladder.get(dir_tf, r4) if dir_tf else r4
        try:
            optionswall = self.optionswall
            _ow = optionswall.load(symbol, close)
            if _ow is not None:
                w.facts['אופציות'] = _ow.line()
        except Exception:
            pass
        st = stretch.state(symbol)
        if st is None:
            regime = 'UNKNOWN'
            dev = 0.0
        else:
            dev = st.max_dev
            regime = 'DEVIATED' if abs(dev) >= 3.0 else 'CONSOLIDATING'
        try:
            struct = matrix.read_structure(d4h)
        except Exception as exc:
            from types import SimpleNamespace as _NS
            struct = _NS(direction=0, note='מבנה לא נקרא')
            w.missing.append(f'מבנה השוק לא נקרא ({type(exc).__name__})')
        try:
            e = tr.emas(d4h)
            slopes = []
            for n in (50, 200, 800):
                col = e[f'ema{n}']
                a, b = (float(col.iloc[-1]), float(col.iloc[-6]))
                if a != a or b != b:
                    slopes.append('?')
                else:
                    slopes.append('↑' if a > b else '↓')
            slope_txt = '/'.join(slopes)
        except Exception:
            slope_txt = '?'
        w.facts[f"הקשר {dir_tf or '4h'}"] = f'{r4.note} · {regime} · {struct.note} · שיפוע 4h 50/200/800: {slope_txt}'
        if struct.direction != 0 and struct.direction != r4.direction:
            w.facts['מבנה'] = 'המבנה נגד המניפה — סימן היפוך מוקדם'
        w.passed.append('CONTEXT')
        w.reached = 'LEVELS'
        levels = self._variant_levels(symbol, variant, w.missing)
        if levels is None:
            w.stopped_because = _levels_unavailable_reason(variant)
            return w
        if not levels:
            w.stopped_because = 'מפת הרמות לא נבנתה'
            return w
        if variant == 'strict':
            w.facts['רמות'] = f'{len(levels)} כולל פיבוטים ו-M (העץ המלא)'
        w.passed.append('LEVELS')
        w.reached = 'SESSION'
        try:
            import json as _json
            from datetime import datetime as _dt, timezone as _tz
            from pathlib import PurePosixPath
            cal = PurePosixPath('news-desk') / 'data' / 'ff_calendar.json'
            now_ts = self.source.now_utc().timestamp()
            reason = _news_stop(_json.loads(self.source.calendar_text(cal.as_posix())), now_ts)
            if reason is not None:
                w.stopped_because = reason
                return w
        except Exception as exc:
            w.stopped_because = f'לוח החדשות לא שמיש ({exc}) — לא סוחרים עד שהלוח מתרענן'
            return w
        active = sorted(watch_sessions.current_session_at(decision_time=self.source.now_utc()))
        box = None
        try:
            box = brinks.today_box(symbol)
        except Exception:
            pass
        w.facts['סשן'] = '/'.join(active) if active else 'מחוץ לסשן'
        try:
            import pandas as _pd
            mode = 'crypto' if 'BTC' in symbol.upper() else 'forex'
            d15i = d15.copy()
            d15i.index = _pd.to_datetime(d15i.index, utc=True)
            psy = sessions.psy_levels(d15i, mode=mode)
            if psy.get('available') and psy.get('window_end'):
                now_utc = _pd.Timestamp(self.source.now_utc())
                if now_utc < _pd.Timestamp(psy['window_end']):
                    w.facts['PSY'] = 'בתוך חלון הגיבוש — הרמות זזות, provisional'
        except Exception:
            pass
        if box:
            w.facts['ברינקס'] = f'{box.lo:,.2f}–{box.hi:,.2f} ⇒ {box.side}'
        w.passed.append('SESSION')
        w.reached = 'PATTERN'
        formation = None
        formation_read = False
        try:
            formation = wm.detect(symbol, '1h') or wm.detect(symbol, '15m')
            formation_read = True
        except Exception as exc:
            w.facts['W/M'] = f'לא נקרא ({type(exc).__name__})'
        try:
            fv = self.first_vector_above_50(symbol, '5m')
            if fv is not None:
                w.facts['First Vector'] = f"{fv['note']}  [{fv['source']}]"
        except Exception:
            pass
        rvc_pattern = None
        rvc_read = False
        try:
            rg = checklists.rvc_gvc(symbol, '15m')
            rvc_read = True
            if rg is not None:
                w.facts['RVC/GVC'] = rg.line()
                if formation is None and rg.recovered and rg.wick_ok:
                    rvc_pattern = rg.name
        except Exception as exc:
            w.facts['RVC/GVC'] = f'לא נקרא ({type(exc).__name__})'
        if formation is not None:
            w.facts['תבנית'] = f"{formation.kind} {('מאושרת' if formation.confirmed else 'מתגבשת')}"
        elif rvc_pattern:
            w.facts['תבנית'] = f'{rvc_pattern} — התבנית היחידה כרגע'
        elif not formation_read or not rvc_read:
            w.facts['תבנית'] = 'לא נקראה — אין כאן ממצא שלילי'
        else:
            w.facts['תבנית'] = 'אין — דירוג נמוך'
        w.passed.append('PATTERN')
        w.reached = 'LOCATION'
        near = [(n, p) for n, p in levels if abs(p - close) <= LEVEL_ZONE_ATR * atr]
        if not near:
            w.missing.append('המחיר לא על רמה מזוהה')
        names = ' · '.join((n for n, _ in near[:3]))
        w.facts['רמה'] = names or 'אין רמה קרובה — מיקום בין רמות'
        exhaustion = any((n.startswith(('ADR', 'AWR', 'RD', 'RW')) for n, _ in near))
        if exhaustion:
            w.facts['מצב'] = 'RANGE EXHAUSTION — הטיה מוקדמת להיפוך'
        w.passed.append('LOCATION')
        w.reached = 'VECTOR'
        VECTOR_KINDS = ('green', 'red', 'blue', 'violet')
        has_vector = False
        vec_kind = None
        vector_read = True
        try:
            pv = tr.pvsra(d15)
            if pv is not None and bool(pv['available'].iloc[-1]):
                k = str(pv['kind'].iloc[-2])
                if k in VECTOR_KINDS:
                    has_vector, vec_kind = (True, k)
        except Exception as exc:
            w.missing.append(f'הווקטור לא נקרא ({type(exc).__name__})')
            vector_read = False
        sv = _stopping_volume(d15)
        if vector_read and (not has_vector) and (not sv):
            w.missing.append('אין וקטור ואין Stopping Volume באזור')
        ctx = []
        ema_context_read = False
        try:
            e15 = tr.emas(d15)
            for n_ in (50, 200, 800):
                if abs(close - float(e15[f'ema{n_}'].iloc[-1])) <= 1.0 * atr:
                    ctx.append('ממוצע')
                    break
            ema_context_read = True
        except Exception as exc:
            w.facts['קרבה לממוצע'] = f'לא נקראה ({type(exc).__name__})'
        if regime == 'CONSOLIDATING':
            ctx.append('לא מתוח')
        if formation is not None:
            ctx.append('תבנית')
        elif rvc_pattern:
            ctx.append(f'תבנית ({rvc_pattern})')
        if not ctx:
            if not ema_context_read or not formation_read or (not rvc_read):
                w.missing.append('הקשר הווקטור לא נקרא במלואו — לא ממירים unknown לאין-הקשר')
            else:
                w.missing.append('וקטור ללא הקשר — לא ליד ממוצע, לא בטווח, לא בתבנית')
        where = f" · הקשר: {'/'.join(ctx)}" if ctx else ' · ללא הקשר'
        if has_vector:
            w.facts['וקטור'] = f'וקטור {vec_kind}{where}'
        elif sv:
            w.facts['וקטור'] = f'Stopping Volume — נר ההיפוך היחיד בשיטה{where}'
        elif not vector_read:
            w.facts['וקטור'] = 'לא נקרא — אין כאן ממצא שלילי'
        else:
            w.facts['וקטור'] = 'אין — העסקה נבנית משאר הפרמטרים'
        w.passed.append('VECTOR')
        w.reached = 'MTF'
        nested = 0
        one_hour_read = False
        try:
            d1h, corr1 = basis.fetch_corrected(symbol, '1h', 30)
            if corr1 is not None and getattr(corr1, 'unverified', False):
                raise ValueError('1h unverified')
            pv1 = tr.pvsra(d1h)
            if pv1 is not None and bool(pv1['available'].iloc[-1]):
                nested = int(pv1['kind'].iloc[-7:-1].isin(VECTOR_KINDS).sum())
                one_hour_read = True
        except Exception:
            pass
        if not one_hour_read:
            w.facts['צפיפות וקטורים (6×1h)'] = 'לא נקרא — אין נתוני 1h, לא קריאת שוק'
        else:
            w.facts['צפיפות וקטורים (6×1h)'] = f'{nested} נרות וקטור בשש השעות האחרונות' if nested else 'אין — שש שעות בלי נר וקטור'
        w.passed.append('MTF')
        w.reached = 'TRAP'
        try:
            br = checklists.brinks_read(symbol)
            if br.formed:
                w.facts['ברינקס'] = br.render().replace('\n', ' · ')
                if br.swept_asia:
                    w.facts['מלכודת ברינקס'] = 'הקופסה סחפה את קצה אסיה — היערך לצד הנגדי  [C8 pt4]'
        except Exception:
            pass
        seg = d15.iloc[-(EXTREME_LOOKBACK + 1):-1]
        hi_thresh = float(seg['high'].quantile(EXTREME_PCT))
        lo_thresh = float(seg['low'].quantile(1 - EXTREME_PCT))
        evidence_close = float(d15['close'].iloc[-2])
        trend_dir = None if r4.direction == 0 else 'לונג' if r4.direction > 0 else 'שורט'
        at_high = evidence_close >= hi_thresh
        at_low = evidence_close <= lo_thresh
        strength = 'שיא' if vec_kind in ('green', 'red') else 'מעל ממוצע'
        w.direction, verdict = trap_direction(at_high, at_low, vec_kind, sv, trend_dir)
        what = f'וקטור {vec_kind}' if vec_kind else 'Stopping Volume' if sv else 'המחיר'
        if verdict == 'trap':
            edge = 'העליון' if at_high else 'התחתון'
            caught = 'לונגים' if at_high else 'שורטים'
            w.facts['מלכודת'] = f'{what} ({strength}) בקצה {edge} — {caught} במלכודת, היערך ל{w.direction}'
        elif verdict == 'committed':
            edge = 'העליון' if at_high else 'התחתון'
            act = 'קונה' if vec_kind in BUY_SIDE else 'מוכר'
            w.facts['מלכודת'] = f'{what} בקצה {edge} — לא מלכודת, זה הצד ש{act} ומחויב ⇒ {w.direction}'
        else:
            w.facts['מלכודת'] = f'{what} לא בקצה — הכיוון מהמגמה'
        if not _stamp_decision(w, d15):
            return w
        w.passed.append('TRAP')
        w.reached = 'MEMORY'
        magnet_txt = 'אין מגנט בטווח'
        try:
            _liq = self.liquidity
            unswept = [p for p in _liq.pools(symbol) if not p.swept]
            if unswept:
                near = min(unswept, key=lambda p: abs(p.price - close))
                dist = abs(near.price - close) / atr
                if dist <= MAX_MAGNET_ATR:
                    magnet_txt = f'{near.line()} · {dist:.1f} ATR מכאן'
                else:
                    magnet_txt = f'המגנט הקרוב {dist:.1f} ATR מכאן — מעבר לסף {MAX_MAGNET_ATR} , לא יעד'
            r = _liq.run(symbol)
            if r.detected:
                w.facts['ריצת נזילות'] = r.line()
        except Exception as exc:
            magnet_txt = f'לא נקרא ({type(exc).__name__}) — אין ממצא שלילי'
        w.facts['מגנט נזילות (EQH/EQL)'] = magnet_txt
        try:
            zones = tr.vector_zones(d15)
            open_z = zones[zones['open']] if len(zones) else zones
            if not len(open_z):
                w.missing.append('אין אזורי וקטור פתוחים')
                w.facts['זיכרון וקטור'] = 'אין אזור פתוח'
            else:
                mid = (open_z['top'] + open_z['bottom']) / 2.0
                w.zones = [(float(m), str(k), int(tc)) for m, k, tc in zip(mid, open_z['kind'], open_z['touches'])]
                d = (mid - close).abs()
                i = d.idxmin()
                z = open_z.loc[i]
                side = 'מעל' if float(mid.loc[i]) > close else 'מתחת'
                untested = 'לא נבחן' if int(z['touches']) == 0 else f"נבחן {int(z['touches'])}×"
                above = int((mid > close).sum())
                w.facts['זיכרון וקטור'] = f"{len(open_z)} אזורים פתוחים ({above} מעל · {len(open_z) - above} מתחת) · הקרוב {z['kind']} {float(z['bottom']):,.2f}-{float(z['top']):,.2f} {side}, {float(d.loc[i]) / atr:.1f} ATR, {untested}"
        except Exception as exc:
            w.facts['זיכרון וקטור'] = f'לא נקרא ({type(exc).__name__})'
        w.passed.append('MEMORY')
        if w.direction is None:
            w.stopped_because = 'אין כיוון מאף מסגרת — אין צד למדוד טריגר או יעד מולו'
            return w
        w.reached = 'TRIGGER'
        prev = float(d15['close'].iloc[-3])
        last = float(d15['close'].iloc[-2])
        moved = (last - prev if w.direction == 'לונג' else prev - last) / atr
        w.facts.setdefault('commitment', f'הנר האחרון זז {moved:+.2f} ATR עם הכיוון')
        if moved < 0.15:
            why = 'הנר האחרון לא זז' if abs(moved) < 0.15 else f'הנר האחרון זז נגד הכיוון ({moved:+.2f} ATR)'
            w.facts['commitment'] = f'אין ({why}) — סף 0.15 ATR, היוריסטיקה'
        w.passed.append('TRIGGER')
        w.reached = 'TARGET'
        short = w.direction == 'שורט'
        ahead = _levels_ahead(levels, close, short, atr)
        if not ahead:
            w.stopped_because = 'אין רמה בכיוון העסקה לשמש יעד'
            return w
        w.facts['רמות לפנים'] = ' · '.join((f'{n} {p:,.2f}' for n, p in ahead[:3]))
        w.passed.append('TARGET')
        return w

    def first_vector_above_50(self, symbol: str, timeframe: str='5m'):
        """The First Vector setup: the initial break of structure with a vector.

    Source, fully specified for once:
      "Initial break of THE STRUCTURE with a green vector"   [09 @ 02m11s]
      fallback with no retrace -- a FULL CLOSE above the 50   [09 @ 07m31s]
      requires a clean break of the CLOUD, not the line       [13 @ 21m01s]
      read on 5m specifically -- the 1m manufactures shakeouts [13 @ 00m40s]

    That last citation is why the default frame here is 5m and not the tree's
    usual 15m: the source names the frame for THIS setup explicitly, and a
    named frame outranks the layer-0 default.

    "Clean break of the cloud" is the load-bearing clause. The 50 EMA in this
    method is a BAND (`tr.ema_cloud`), not a line, so a close that pokes into
    the cloud has not broken anything -- the bar must close beyond the far
    edge. Reading it as a line would fire this setup on every touch.

    Returns a dict or None. Reports; never trades on its own.
    """
        basis = self.basis
        try:
            df, corr = basis.fetch_corrected(symbol, timeframe, 5)
            if corr and getattr(corr, 'unverified', False) or len(df) < 60:
                return None
            pv = tr.pvsra(df)
            cloud = tr.ema_cloud(df)
        except Exception:
            return None
        hi = cloud['upper'] if 'upper' in cloud else cloud.iloc[:, 0]
        lo = cloud['lower'] if 'lower' in cloud else cloud.iloc[:, -1]
        close = df['close']
        n = len(df)
        i = n - 2
        kind = str(pv['kind'].iloc[i])
        up = kind in ('green', 'blue')
        dn = kind in ('red', 'violet')
        if not (up or dn):
            return None
        c, edge_hi, edge_lo = (float(close.iloc[i]), float(hi.iloc[i]), float(lo.iloc[i]))
        if up and c <= edge_hi:
            return None
        if dn and c >= edge_lo:
            return None
        look = df.iloc[max(0, i - 6):i]
        prev_in_or_below = (look['close'] <= hi.iloc[max(0, i - 6):i]).all() if up else (look['close'] >= lo.iloc[max(0, i - 6):i]).all()
        if not prev_in_or_below:
            return None
        return {'setup': 'First Vector above 50', 'direction': 'לונג' if up else 'שורט', 'timeframe': timeframe, 'vector': kind, 'close': c, 'cloud_edge': edge_hi if up else edge_lo, 'source': '09 @ 02m11s · 13 @ 21m01s · 13 @ 00m40s', 'note': f"וקטור {kind} שסוגר מלא {('מעל' if up else 'מתחת')} לענן ה-50 ב-{timeframe} — השבירה הראשונה"}

    def levels_to_trade(self, symbol: str, close: float, direction: str, atr: float, variant: str='house'):
        """(stop, targets) from the level map — HIS documented rule, one copy of it.

    `00-method.md`: "יעדים — יעד פסיכולוגי / רמה נקובה מהמפה, לעולם לא מספר
    עגול שרירותי". `08-tree-coverage.md`: "סטופ מאחורי הרמה שמאחור, יעדים =
    הרמות שלפנים". The R gate itself is tradeplan.MIN_RR (1.2 since
    2026-08-27), not the 1.5 that doc still names.
    `05-risk-and-execution.md`: "targets are levels
    that are actually in the way, not round-number wishes".

    trade_from_walk has computed exactly this since the tree started building
    trades. Extracted here because nine detectors fire without any numbers at
    all -- 287 banked firings that no resolver can ever score -- and the answer
    for them was never six new trading decisions. It is this rule, which is
    already his, applied consistently.

    Returns None when the map has no level ahead or none behind: a setup with
    no obstacle in front has no target that pays, and the method says decline
    rather than invent one.
    """
        short = direction in ('שורט', 'short', 'sell')
        L = self._variant_levels(symbol, variant)
        if L is None:
            raise LevelsUnavailable('level universe could not be read')
        ahead = _levels_ahead(L, close, short, atr)
        behind = sorted([(n, p) for n, p in L if (p > close if short else p < close)], key=lambda r: abs(r[1] - close))[:1]
        if not ahead or not behind:
            return None
        stop = behind[0][1] + (STOP_CUSHION_ATR * atr if short else -STOP_CUSHION_ATR * atr)
        from .pricing import apply_stop_band, resolve_ladder
        stop = apply_stop_band(symbol, close, stop, atr, [], style=TREE_STYLE)
        if stop <= behind[0][1] if short else stop >= behind[0][1]:
            return None
        risk = abs(close - stop)
        if risk <= 0:
            return None
        targets, _obstacles, refusal = resolve_ladder(ahead, symbol, close, stop, short, atr)
        if refusal is not None:
            return None
        return (stop, targets)

    def trade_from_walk(self, w: Walk):
        """Build the actual trade a completed walk implies, or None.

    This is what makes the tree a TRADING system rather than a commentary: a
    walk that clears every gate turns into entry/stop/targets using the same
    objects the walk already gathered. The final audit (2026-08-25) found the
    tree annotated plans but nothing in the live pipeline ever BUILT a trade
    from it -- the whole point, per Sagiv: "המערכת בונה עסקאות על בסיס עץ
    ההחלטות".

    Geometry follows STAGE 11-13: stop behind the nearest level BEHIND the
    trade (+0.35 ATR buffer, his gold >=5pt floor via tradeplan's rules),
    targets = the next named levels ahead, R:R gate MIN_RR (1.2 -- the 1.5
    once written here described a gate the runtime never had) -- below it the walk
    stays a walk.
    """
        basis = self.basis
        from .pricing import MIN_RR, Plan
        if not w.complete or not w.direction:
            return None
        try:
            d15, _ = basis.fetch_corrected(w.symbol, '15m', 10)
        except Exception:
            w.facts['בניית עסקה'] = 'טייפ 15m לא נקרא מחדש — אין מסקנת R:R'
            return None
        close = float(d15['close'].iloc[-1])
        atr = _atr(d15) or 1e-09
        if w.decided_close is not None:
            drift = abs(close - w.decided_close) / atr
            if drift > MAX_DECISION_DRIFT_ATR:
                w.facts['נדחה'] = f'המחיר זז {drift:.2f} ATR מאז שהעץ החליט ({w.decided_close:,.2f} → {close:,.2f})'
                return None
        short = w.direction == 'שורט'
        L = self._variant_levels(w.symbol, w.variant)
        if L is None:
            w.facts['בניית עסקה'] = 'מפת הרמות לא נקראה מחדש — אין מסקנת R:R'
            return None
        for _mid, _kind, _tc in getattr(w, 'zones', []) or []:
            if abs(_mid - close) <= MAX_MAGNET_ATR * atr:
                _tag = 'לא נבחן' if _tc == 0 else f'{_tc}×'
                L = list(L) + [(f'VZ50-{_kind} ({_tag})', float(_mid))]
        ahead = _levels_ahead(L, close, short, atr)
        behind = sorted([(n, p) for n, p in L if (p > close if short else p < close)], key=lambda r: abs(r[1] - close))[:1]
        if not ahead or not behind:
            w.facts['נדחה'] = 'אין רמה ' + ('לפנים' if not ahead else 'מאחור') + ' לבנות מולה — אין גיאומטריה'
            return None
        stop = behind[0][1] + (STOP_CUSHION_ATR * atr if short else -STOP_CUSHION_ATR * atr)
        _warn: list = []
        from .pricing import apply_stop_band, resolve_ladder
        _style = TREE_STYLE
        stop = apply_stop_band(w.symbol, close, stop, atr, _warn, style=_style)
        targets, obstacles, refusal = resolve_ladder(ahead, w.symbol, close, stop, short, atr)
        p = Plan(symbol=w.symbol, close=close, kind='trend', direction=w.direction, entry=close, stop=stop, targets=targets, atr=atr, style=_style, obstacles=obstacles, refusal=refusal)
        p.warnings.extend(_warn)
        p.not_drawn = list(w.missing)
        p.reasons = [f"עץ ההחלטות ({('עץ-מלא' if w.variant == 'strict' else 'בית')}): כל {len(w.passed)} השלבים עברו", f"מסלול העץ: {' → '.join(w.passed)}", *(f'{k}: {v}' for k, v in w.facts.items()), *([f'נקודת החלטת העץ: {w.decided_close:,.2f} · {w.decided_bar}'] if w.decided_close is not None else []), f"הנחות העץ: {' · '.join(w.assumptions)}", f'ביטול: {behind[0][0]}']
        if 'מלכודת' in w.facts and 'היערך' in str(w.facts.get('מלכודת', '')):
            p.kind = 'reversal'
            p.warnings.append('עסקת מלכודת — נגד הצד שנתפס. משפחת היפוך, לא נמדדה.')
        anchor_px = behind[0][1]
        stop_ok = p.stop > anchor_px if short else p.stop < anchor_px
        if not stop_ok:
            w.facts['נדחה'] = f'הרצועה הידקה את הסטופ ל-{p.stop:,.2f}, לפני נקודת הביטול {behind[0][0]} {anchor_px:,.2f} — העסקה לא נכנסת לרצועת הסיכון'
            w.refused = p
            return None
        if not p.tradeable:
            _tp1 = f' · TP1 {p.targets[0][0]} {p.targets[0][1]:,.2f}' if p.targets else ''
            w.facts['נדחה'] = (p.refusal or f'R:R {p.rr:.2f} מתחת לסף {MIN_RR}') + f' — כניסה {p.entry:,.2f} · סטופ {p.stop:,.2f}{_tp1}'
            w.refused = p
            return None
        return p
