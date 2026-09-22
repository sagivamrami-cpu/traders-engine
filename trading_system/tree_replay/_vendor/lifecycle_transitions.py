"""Pinned tracker transition/message helpers over offline source clocks only."""
from __future__ import annotations

import re

from . import basis_symbols as basis
from . import lifecycle_voice as voice
from .desk_success import DeskSuccess
from .lifecycle_bars import _entry_band


class LifecycleTransitions:
    def __init__(self, source):
        self.source = source
        self.desk_success = DeskSuccess(source)

    def _tp_management_line(self, i: int, total: int) -> str:
        """Report target `i` of `total` without choosing management for clients.

        "full close" belongs on the LAST target only. Saying it at TP2 of three
        told people to close a position the tracker still considered open, and
        then reported TP3 to subscribers who had already exited.
        """
        if i >= total:
            return "היעד האחרון בתוכנית הושג.\n\nמימוש לשיקולכם."
        left = "נותר יעד אחד" if total - i == 1 else f"נותרו {total - i} יעדים"
        if i == 1:
            return f"{left} במעקב.\n\nאפשר לשקול הגנה בכניסה — {voice.OPTIONAL}"
        return f"{left} במעקב."

    _UNVERIFIED_NOTE = ("\nהתזה לא אומתה מחדש בכניסה — "
                        "העסקה נפתחה על התזה המקורית.")

    def _fill_caveat(self, why: str, verified: bool) -> str:
        """What follows the fill line: the re-validation's label, then its silence."""
        return (f"\n{why}" if why else "") + ("" if verified else self._UNVERIFIED_NOTE)

    def _il_clock(self, ts) -> str:
        """`19:43` in Israel time, or "" when the stamp is missing."""
        try:
            import datetime as _dt
            from zoneinfo import ZoneInfo
            il = ZoneInfo("Asia/Jerusalem")
            return f"{_dt.datetime.fromtimestamp(float(ts), il):%H:%M}"
        except Exception:
            return ""

    def _journey(self, t: dict) -> str:
        """What the trade did before it ended, as the clients saw it."""
        bits = []
        step = int(t.get("progress_step") or 0)
        if step > 0:
            pts = t.get("reported_progress_points", voice.rung_points(t["entry"], self._progress_pct(t["symbol"]), step))
            bits.append(f"הגיעה ל-{voice.move(t['symbol'], pts)}")
        if t.get("be_level") is not None:
            when = self._il_clock(t.get("be_ts"))
            bits.append("ההגנה הוצעה" + (f" ב-{when}" if when else ""))
        return " · ".join(bits)

    def _ambiguous_touch(self, t: dict, lo: float, hi: float, short: bool,
                         protective: float) -> bool:
        """Did this window touch BOTH the protective level and an unhit target?"""
        if not ((hi >= protective) if short else (lo <= protective)):
            return False
        return any(((lo <= px) if short else (hi >= px))
                   for i, (_n, px) in enumerate(t["targets"], 1)
                   if f"TP{i}" not in t["hit"])

    def _resolve_ambiguous(self, t: dict, name: str, side: str) -> tuple[str, str]:
        msg, result = self._ambiguous_result(t, name, side)
        t["terminal_result"] = result
        return msg, result

    def _ambiguous_result(self, t: dict, name: str, side: str) -> tuple[str, str]:
        """(message, outcome_result) for a window that cannot be ordered."""
        entry = float(t["entry"])
        if not t.get("hit"):
            head, res = f"סטופ @ {float(t['stop']):,.2f}", "stopped_ambiguous"
        elif abs(float(t["stop"]) - entry) < 1e-9:
            head, res = (f"חזרה לכניסה (BE) אחרי {t['hit'][-1]}", "be_after_tp_ambiguous")
        elif (float(t["stop"]) > entry if t["direction"] != "שורט"
              else float(t["stop"]) < entry):
            head = f"סטופ נגרר @ {float(t['stop']):,.2f} אחרי {t['hit'][-1]}"
            res = "trailed_stop_ambiguous"
        else:
            head = f"הסטופ המקורי @ {float(t['stop']):,.2f} אחרי {t['hit'][-1]}"
            res = "published_stop_after_tp_ambiguous"
        msg = (voice.head("🛑", t["symbol"], t["direction"], entry, head) + "\n\n"
               "סדר האירועים אינו ידוע\nבאותו חלון נצפו גם רמת היעד וגם רמת הסטופ.\n"
               "הנתונים אינם מאפשרים לקבוע מה קרה קודם.\n"
               "הרישום השמרני הוא סטופ; לא נטען שהיעד הושג לפניו."
               + self.desk_success.stop_note(t))
        return msg, res

    def _resolve_protective(self, t: dict, name: str, side: str) -> tuple[str, str, str]:
        msg, result, state = self._protective_result(t, name, side)
        t["terminal_result"] = result
        return msg, result, state

    def _protective_result(self, t: dict, name: str, side: str) -> tuple[str, str, str]:
        """Message, outcome and terminal state for the published protective hit."""
        stop = float(t["stop"])
        entry = float(t["entry"])
        sym, dr = t["symbol"], t["direction"]
        signed = (entry - stop) if dr == "שורט" else (stop - entry)
        if not t.get("hit"):
            road = self._journey(t)
            return (voice.head("🛑", sym, dr, entry, f"סטופ @ {stop:,.2f}")
                    + f"\n{voice.move(sym, signed)}"
                    + (f"\nבדרך: {road}." if road else "") + self.desk_success.stop_note(t),
                    "stopped", "STOPPED")
        last = t["hit"][-1]
        if abs(stop - entry) < 1e-9:
            return (voice.head("🏁", sym, dr, entry, f"חזרה לכניסה (BE) אחרי {last}")
                    + "\nהסטופ המדווח עמד בכניסה.",
                    "be_after_tp", "DONE")
        profitable = (stop > entry if dr != "שורט" else stop < entry)
        if profitable:
            return (voice.head("🏁", sym, dr, entry,
                               f"סטופ נגרר @ {stop:,.2f} אחרי {last}")
                    + f"\n{voice.move(sym, signed)}",
                    "trailed_stop", "DONE")
        return (voice.head("🛑", sym, dr, entry,
                           f"הסטופ המקורי @ {stop:,.2f} אחרי {last}")
                + f"\n{voice.move(sym, signed)} למי שלא הגן · {last} נגע קודם.",
                "published_stop_after_tp", "DONE")

    def _mark_terminal(self, t: dict, state: str) -> None:
        """Persist when a lifecycle result happened, separately from send time."""
        t["state"] = state
        t["resolved_ts"] = self.source.now_epoch()

    PROGRESS_PCT = {"XAU": 0.09, "GOLD": 0.09, "NAS": 0.12, "US100": 0.12,
                    "NQ": 0.12, "BTC": 2.0}

    def _progress_pct(self, symbol: str) -> float:
        u = basis.canonical_symbol(symbol).upper()
        return next((v for k, v in self.PROGRESS_PCT.items() if k in u), 0.10)

    def _progress_steps(self, t: dict, best: float, short: bool) -> list[tuple[int, float]]:
        """Which +N steps this trade has newly reached, capped below TP1."""
        entry = float(t["entry"])
        gain = (entry - best) if short else (best - entry)
        if gain <= 0:
            return []
        step = entry * self._progress_pct(t["symbol"]) / 100.0
        if step <= 0:
            return []
        reached = int(gain // step)
        if not reached:
            return []
        targets = t.get("targets") or []
        if not targets:
            return []
        if targets:
            tp1 = float(targets[0][1])
            tp1_gain = (entry - tp1) if short else (tp1 - entry)
            if tp1_gain > 0:
                reached = min(reached, max(0, int((tp1_gain - 1e-9) // step)))
        done = int(t.get("progress_step") or 0)
        return [(n, entry - n * step if short else entry + n * step)
                for n in range(done + 1, reached + 1)]

    def _progress_messages(self, t: dict, best: float, short: bool,
                           name: str, side: str) -> list[tuple[str, bool]]:
        """Report every newly crossed rung and advance the shared ladder state."""
        steps = self._progress_steps(t, best, short)
        if not steps:
            return []
        entry_px = float(t["entry"])
        sym, dr = t["symbol"], t["direction"]
        tp1_px = float(t["targets"][0][1]) if t.get("targets") else None
        out = []
        for _n, level in steps:
            moved = abs(level - entry_px)
            where = f"רמת ההתקדמות: {level:,.2f}"
            if tp1_px is not None:
                where += (f"\nהיעד הבא: TP1 ב־{tp1_px:,.2f}"
                          f"\nמרחק שנותר: {voice.dist(sym, tp1_px - level)}")
            out.append((voice.head("📈", sym, dr, entry_px, voice.move(sym, moved))
                        + f"\n\nהתקדמות מאז הכניסה\n{where}"
                        + "\n\nזו תנועת המחיר, לא רווח ממומש.\nמימוש וניהול לפי החלטת הסוחר.",
                        t["to_group"]))
        t["progress_step"] = steps[-1][0]
        t["reported_progress_points"] = abs(steps[-1][1] - entry_px)
        return out

    def _protective(self, t: dict, short: bool) -> float:
        """The level that closes this trade defensively, right now."""
        return float(t["stop"])

    def _fill_line(self, t: dict, name: str, side: str) -> str:
        """What to SAY when a pending trade fills."""
        zlo, zhi = _entry_band(t)
        e = float(t["entry"])
        if zhi - zlo <= 0:
            head = voice.head("▶️", t["symbol"], t["direction"], e,
                              "המחיר הגיע לכניסה")
            zone = ""
        else:
            head = voice.head("▶️", t["symbol"], t["direction"], e,
                              "המחיר הגיע לאזור הכניסה")
            zone = f"אזור {zlo:,.2f}–{zhi:,.2f} · "
        return f"{head}\n{zone}סטופ {float(t['stop']):,.2f}"

    def _target_line(self, t: dict, i: int, tag: str, px: float) -> str:
        """Target message plus source management wording."""
        entry = float(t["entry"])
        gained = (entry - float(px)) if t["direction"] == "שורט" else (float(px) - entry)
        return (voice.head("✅", t["symbol"], t["direction"], entry,
                           f"{tag} הושג @ {float(px):,.2f}")
                + f"\n\nתנועה מהכניסה: {voice.move(t['symbol'], gained)}\n"
                + self._tp_management_line(i, len(t["targets"])))

    def _no_score(self, why: str) -> str:
        """The engine's reason without its score."""
        return re.sub(r"\s*\([+-]?\d[\d.,]*\)\s*$", "", why or "").strip()

    def _cancel_line(self, t: dict, why: str) -> str:
        """A pending trade re-validated at the fill and failed: say so, once."""
        reason = self._no_score(why)
        return (voice.head("✖️", t["symbol"], t["direction"], t["entry"],
                           "בוטלה בכניסה")
                + (f"\n{reason}" if reason else ""))
