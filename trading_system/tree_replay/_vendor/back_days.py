from __future__ import annotations


BACK_DAYS = 4


def _back_day_levels(daily) -> list:
    """Highs and lows from 2-4 sessions ago. [שגיב 06-psych-levels @ 02m13s]"""
    out = []
    if daily is None or len(daily) < BACK_DAYS + 1:
        return out
    # -1 is today (forming), -2 is yesterday (already served as YDAY-*).
    for k in range(3, BACK_DAYS + 2):
        try:
            row = daily.iloc[-k]
        except Exception:
            break
        d = k - 1                      # 2 days ago, 3 days ago, ...
        out.append((f"D{d}-HI", float(row["high"])))
        out.append((f"D{d}-LO", float(row["low"])))
    return out
