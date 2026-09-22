"""Dependency integration: causal daily OHLC into actual pinned range formulas."""
from datetime import datetime, timedelta, timezone

import pandas as pd

from trading_system.tree_replay.bars import ClosedBar
from trading_system.tree_replay.calendar import SessionInterval, SessionSchedule
from trading_system.tree_replay.periods import DailyPeriod, aggregate_daily_asof


def test_range_calculation_uses_running_day_extremes_not_final_day_values():
    from trading_system.tree_replay._vendor.ranges import average_range
    today = datetime(2026,1,3,tzinfo=timezone.utc)
    bars, periods, intervals = [], [], []
    prices = [([(100,105,95,100)]*3), ([(100,110,90,100)]*3),
              [(100,110,95,108),(108,115,100,110),(110,1000,1,900)]]
    for offset, day_prices in zip((-2,-1,0),prices):
        start = today+timedelta(days=offset)
        periods.append(DailyPeriod(instrument="OANDA:XAUUSD", period_id=f"day{offset}",
                                   opened_at=start,closed_at=start+timedelta(days=1),
                                   available_at=start,source="synthetic-boundaries",version="v1"))
        intervals.append(SessionInterval(opened_at=start,closed_at=start+timedelta(minutes=15)))
        for i,(o,h,l,c) in enumerate(day_prices):
            close = start+timedelta(minutes=5*(i+1))
            bars.append(ClosedBar(instrument="OANDA:XAUUSD",timeframe="5m",
                                  opened_at=close-timedelta(minutes=5),closed_at=close,
                                  available_at=close,open=o,high=h,low=l,close=c,
                                  volume=10,source="synthetic-price-evidence"))
    cal = SessionSchedule(instrument="OANDA:XAUUSD",calendar_id="synthetic",version="v1",
                          coverage_start=periods[0].opened_at,coverage_end=periods[-1].closed_at,
                          available_at=periods[0].opened_at,source="synthetic-session-evidence",
                          intervals=tuple(intervals))
    decision = today+timedelta(minutes=10)
    observations = [aggregate_daily_asof(bars,period=p,decision_time=decision,
                                        base_timeframe="5m",session_schedule=cal) for p in periods]
    assert [r["status"] for r in observations] == ["CLOSED","CLOSED","FORMING"]
    assert observations[-1]["ohlcv"]["high"] == 115
    assert observations[-1]["ohlcv"]["low"] == 95
    frame = pd.DataFrame([r["ohlcv"] for r in observations],index=[p.opened_at for p in periods])
    moving = average_range(frame,2,broker_bars=False)
    assert moving["range"] == 15 and moving["high"] == 110 and moving["low"] == 100
    assert moving["used"] == 20 and not moving["verified"]
    anchored = average_range(frame,2,from_open=True,broker_bars=False)
    assert anchored["high"] == 107.5 and anchored["low"] == 92.5
    without_future = aggregate_daily_asof(bars[:-1],period=periods[-1],decision_time=decision,
                                         base_timeframe="5m",session_schedule=cal)
    assert without_future == observations[-1]
