from __future__ import annotations
import json
import re
import pandas as pd
from pathlib import PurePosixPath
from . import basis_symbols as basis
from .tracker_admission import _trade_identity

def _fmt(sym: str) -> str:
    return sym.split(':')[-1]

def _side_from_text(text: str) -> str | None:
    if ' SELL' in text:
        return 'שורט'
    if ' BUY' in text:
        return 'לונג'
    return None

def _prices_in_text(text: str) -> list[float]:
    out = []
    for raw in re.findall('\\d[\\d,]*\\.\\d+', text or ''):
        try:
            out.append(float(raw.replace(',', '')))
        except ValueError:
            pass
    return out

def _text_has_price(text: str, price: float, tol: float=0.02) -> bool:
    return any((abs(px - float(price)) <= tol for px in _prices_in_text(text)))

def _trade_has_named_level_in_text(trade: dict, text: str) -> bool:
    if trade.get('stop') is not None and _text_has_price(text, float(trade['stop'])):
        return True
    for _name, px in trade.get('targets') or []:
        if _text_has_price(text, float(px)):
            return True
    return False

def _match_trade_for_text(text: str, state: dict) -> tuple[dict | None, list[dict]]:
    """Return (trade, ambiguous_matches) for a lifecycle message."""
    side = _side_from_text(text)
    entry_matches = []
    stop_matches = []
    fallback = []
    for t in state.values():
        nm = _fmt(t['symbol'])
        if nm not in text:
            continue
        if side and t.get('direction') != side:
            continue
        if _text_has_price(text, float(t['entry'])):
            entry_matches.append(t)
        elif t.get('stop') is not None and _text_has_price(text, float(t['stop'])):
            stop_matches.append(t)
        elif t.get('state') not in ('CANCELLED',):
            fallback.append(t)
    if len(entry_matches) == 1:
        return (entry_matches[0], [])
    if len(entry_matches) > 1:
        level_matches = [t for t in entry_matches if _trade_has_named_level_in_text(t, text)]
        if len(level_matches) == 1:
            return (level_matches[0], [])
        if len(level_matches) > 1:
            return (None, level_matches)
        return (None, entry_matches)
    if len(stop_matches) == 1:
        return (stop_matches[0], [])
    if len(stop_matches) > 1:
        return (None, stop_matches)
    if not fallback:
        return (None, [])
    live = [t for t in fallback if t.get('state') == 'OPEN']
    pending = [t for t in fallback if t.get('state') == 'PENDING']
    pool = live or pending or fallback
    if len(pool) != 1:
        return (None, pool)
    return (pool[0], [])
HEAD = re.compile('^[👀▶️📈⏳🛑✅🔒🏁⚠️✖️🔄🔁♻️🔧]+\\s+(\\S+)\\s+(BUY|SELL)\\s+([\\d,]+(?:\\.\\d+)?)')

def identity(text):
    core = text.strip()
    if core.startswith('⏰'):
        core = core.partition('\n')[2].strip()
    return HEAD.match(core)

class LifecycleIdentity:

    def __init__(self, source):
        self.source = source
        self._receipt_cache = {'mtime': 0, 'keys': set()}

    def _receipt_from_queue_file(self, r: dict) -> dict:
        """Candidate (style, trade_id) rows for a pre-schema receipt, or [].

    ALWAYS A LIST. The early exits returned {} while the success path
    returned a list, so the caller's `for m in ...` iterated dict KEYS on
    a miss. It happened to be empty and therefore harmless, which is the
    worst kind of type confusion: correct by accident.
    """
        name = str(r.get('file') or '')
        if not name.endswith('.json'):
            return []
        for folder in ('done', ''):
            f = PurePosixPath('chart-desk') / 'out' / 'group_queue' / folder / name
            if self.source.queue_exists(f.as_posix()):
                break
        else:
            return []
        try:
            plan = json.loads(self.source.queue_text(f.as_posix(), encoding='utf-8'))
        except Exception:
            return []
        if plan.get('stop') is None:
            return []
        out = []
        for style in ('scalp', 'intraday', 'swing'):
            try:
                _k, tid = _trade_identity(plan['symbol'], plan['direction'], plan['entry'], plan['stop'], plan.get('targets') or [], style)
            except Exception:
                continue
            out.append({'style': style, 'trade_id': tid})
        return out

    def _group_has(self, t: dict) -> bool:
        """Did the GROUP actually receive this trade's entry message?"""
        try:
            st = self.source.receipt_stat()
        except OSError:
            return False
        if st.st_mtime_ns != self._receipt_cache['mtime']:
            keys = set()
            try:
                for line in self.source.receipt_text(encoding='utf-8').splitlines():
                    if not line.strip():
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    rows = [r]
                    if r.get('symbol') and r.get('entry') is not None and (not r.get('style')):
                        rows = [dict(r) | m for m in self._receipt_from_queue_file(r)] or [r]
                    for r in rows:
                        if not (r.get('symbol') and r.get('entry') is not None and r.get('style')):
                            continue
                        try:
                            rts = pd.Timestamp(r.get('ts')).timestamp()
                        except Exception:
                            rts = 0.0
                        keys.add((basis.canonical_symbol(r['symbol']), r.get('direction'), round(float(r['entry']), 2), str(r['style']).lower(), r.get('trade_id'), rts))
            except OSError:
                return False
            self._receipt_cache['keys'] = keys
            self._receipt_cache['mtime'] = st.st_mtime_ns
        want = (basis.canonical_symbol(t.get('symbol', '')), t.get('direction'), round(float(t.get('entry', 0)), 2), str(t.get('style') or 'intraday').lower())
        want_id = t.get('trade_id')
        if not want_id and t.get('stop') is not None:
            _key, want_id = _trade_identity(t.get('symbol', ''), t.get('direction'), t.get('entry', 0), t.get('stop'), t.get('targets') or [], want[3])
        try:
            sent_ts = float(t.get('ts', 0))
        except (TypeError, ValueError):
            sent_ts = 0.0
        for sym, dirn, entry, style, trade_id, rts in self._receipt_cache['keys']:
            if (sym, dirn, entry, style) != want:
                continue
            if trade_id != want_id:
                continue
            if rts >= sent_ts - 120.0:
                return True
        return False

    def context(self, text, state=None):
        head = identity(text)
        if not head:
            return None
        state = self.source.load() if state is None else state
        tr, ambiguous = _match_trade_for_text(text, state)
        if tr is None or ambiguous or abs(float(tr['entry']) - float(head[3].replace(',', ''))) > 0.011:
            return None
        fields = ('symbol', 'direction', 'entry', 'stop', 'targets', 'style', 'trade_id', 'ts')
        return {**{key: tr.get(key) for key in fields}, 'event_ts': self.source.now_epoch()}
