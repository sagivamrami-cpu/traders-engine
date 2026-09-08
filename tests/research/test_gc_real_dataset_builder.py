from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trading_system.research import gc_real_dataset_builder as builder

CAL = builder.load_calendar()


def session_bar_starts(start: str, end: str) -> pd.DatetimeIndex:
    grid = builder.build_expected_grid(pd.Timestamp(start), pd.Timestamp(end), CAL)
    return grid.index[grid["in_session"]]


def synthetic_bars(starts: pd.DatetimeIndex, *, base: float = 1000.0, drift: float = 0.0) -> pd.DataFrame:
    n = len(starts)
    closes = base + drift * np.arange(n)
    opens = np.concatenate([[base], closes[:-1]])
    highs = np.maximum(opens, closes) + 2.0
    lows = np.minimum(opens, closes) - 2.0
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(n, 100.0),
            "seconds_with_trades": np.full(n, 1200),
        },
        index=pd.DatetimeIndex(starts, name="bar_start"),
    )


def test_resample_1s_to_30m_half_open_bars():
    idx = pd.DatetimeIndex(
        [
            "2026-09-07T10:00:01Z",
            "2026-09-07T10:15:00Z",
            "2026-09-07T10:29:59Z",
            "2026-09-07T10:30:00Z",
        ]
    )
    frame = pd.DataFrame(
        {
            "gc_open": [1.0, 2.0, 3.0, 9.0],
            "gc_high": [1.5, 5.0, 3.5, 9.5],
            "gc_low": [0.5, 1.5, 2.5, 8.5],
            "gc_close": [1.2, 2.2, 3.2, 9.2],
            "gc_volume": [10.0, 20.0, 30.0, 40.0],
        },
        index=idx,
    )
    bars = builder.resample_1s_to_30m(frame)
    assert list(bars.index) == [pd.Timestamp("2026-09-07T10:00Z"), pd.Timestamp("2026-09-07T10:30Z")]
    first = bars.iloc[0]
    assert first["open"] == 1.0 and first["high"] == 5.0 and first["low"] == 0.5 and first["close"] == 3.2
    assert first["volume"] == 60.0 and first["seconds_with_trades"] == 3
    assert bars.iloc[1]["open"] == 9.0 and bars.iloc[1]["seconds_with_trades"] == 1


def test_expected_grid_skips_daily_break_and_weekend_without_counting_gaps():
    grid = builder.build_expected_grid(pd.Timestamp("2026-09-11T20:00Z"), pd.Timestamp("2026-09-14T00:00Z"), CAL)
    # Friday 2026-09-11 16:00 CT = 21:00Z close; Sunday 17:00 CT = 22:00Z open.
    assert grid.loc[pd.Timestamp("2026-09-11T20:30Z"), "in_session"]
    assert not grid.loc[pd.Timestamp("2026-09-11T21:00Z"), "in_session"]
    assert not grid.loc[pd.Timestamp("2026-09-12T12:00Z"), "in_session"]
    assert grid.loc[pd.Timestamp("2026-09-13T22:00Z"), "in_session"]
    assert grid.loc[pd.Timestamp("2026-09-13T22:00Z"), "trade_date"] == "2026-09-14"
    assert grid["straddle"].sum() == 0
    seq = grid.loc[grid["in_session"], "session_seq"].to_numpy()
    assert (np.diff(seq) == 1).all()
    assert grid.loc[pd.Timestamp("2026-09-13T22:00Z"), "session_seq"] == grid.loc[pd.Timestamp("2026-09-11T20:30Z"), "session_seq"] + 1


def test_missing_expected_bar_is_fail_closed_for_lookback_and_horizon():
    starts = session_bar_starts("2026-09-01T00:00Z", "2026-09-04T20:00Z")
    bars = synthetic_bars(starts)
    dropped = starts[40]
    bars = bars.drop(index=dropped)
    built = builder.build_dataset(bars, None, CAL)
    summary = built.summary
    assert summary["missing_expected_bars"] == 1
    assert summary["present_session_bars"] == len(starts) - 1
    seqs = built.bars.reset_index()
    missing_seq = int(seqs.loc[seqs["bar_start"] == dropped, "session_seq"].iloc[0])
    rows = built.rows[built.rows["direction"] == "LONG"].set_index("session_seq")
    # 15 bars after the gap are lookback-contaminated, 8 bars before are horizon-contaminated.
    for seq in range(missing_seq + 1, missing_seq + 1 + builder.FEATURE_LOOKBACK_BARS):
        assert "OHLCV_GAP_IN_FEATURE_LOOKBACK" in rows.loc[seq, "exclusion_reasons_ohlcv_only"]
    assert "OHLCV_GAP_IN_FEATURE_LOOKBACK" not in rows.loc[missing_seq + builder.FEATURE_LOOKBACK_BARS + 1, "exclusion_reasons_ohlcv_only"]
    for seq in range(missing_seq - builder.HORIZON_BARS, missing_seq):
        assert "OHLCV_GAP_IN_LABEL_HORIZON" in rows.loc[seq, "exclusion_reasons_ohlcv_only"]
    assert "OHLCV_GAP_IN_LABEL_HORIZON" not in rows.loc[missing_seq - builder.HORIZON_BARS - 1, "exclusion_reasons_ohlcv_only"]
    # Early bars lack lookback, last bars lack horizon.
    assert "INSUFFICIENT_LOOKBACK" in rows.loc[0, "exclusion_reasons_ohlcv_only"]
    assert "INSUFFICIENT_HORIZON" in rows.loc[rows.index.max(), "exclusion_reasons_ohlcv_only"]
    assert not rows["included_ohlcv_only"].loc[missing_seq + 1]
    # No forward fill: the missing bar has no row at all.
    assert missing_seq not in rows.index
    assert summary["variants"]["ohlcv_only"]["excluded_rows_by_reason"]["OHLCV_GAP_IN_FEATURE_LOOKBACK"] == 2 * builder.FEATURE_LOOKBACK_BARS


def test_outcome_labels_target_stop_expired_and_ambiguous():
    starts = session_bar_starts("2026-09-01T00:00Z", "2026-09-03T00:00Z")
    bars = synthetic_bars(starts)
    n = len(bars)
    # Flat market so ATR = 4.0 (high-low = 4 every bar with open == close).
    bars["open"] = 1000.0
    bars["close"] = 1000.0
    bars["high"] = 1002.0
    bars["low"] = 998.0
    t = 20
    # Decision bar t: entry = open[t+1] = 1000, R = 4 -> long target 1004 / stop 996.
    bars.iloc[t + 2, bars.columns.get_loc("high")] = 1004.5  # long target on 2nd horizon bar
    t2 = 30
    bars.iloc[t2 + 1, bars.columns.get_loc("low")] = 995.0  # long stop on 1st horizon bar
    t3 = 40
    bars.iloc[t3 + 3, bars.columns.get_loc("high")] = 1005.0
    bars.iloc[t3 + 3, bars.columns.get_loc("low")] = 995.0  # both in same bar -> ambiguous
    labels = builder.label_outcomes(builder.compute_features(builder.compute_gap_flags(
        builder.assemble_session_bars(bars, CAL).bars)))
    long = labels["LONG"]
    assert long.iloc[t]["outcome_class"] == "TARGET_FIRST"
    assert long.iloc[t]["time_to_outcome_bars"] == 2
    assert long.iloc[t]["net_return_r"] == 1.0
    assert long.iloc[t2]["outcome_class"] == "STOP_FIRST"
    assert long.iloc[t2]["time_to_outcome_bars"] == 1
    assert long.iloc[t2]["net_return_r"] == -1.0
    assert long.iloc[t3]["outcome_class"] == "AMBIGUOUS"
    assert np.isnan(long.iloc[t3]["net_return_r"])
    assert long.iloc[50]["outcome_class"] == "EXPIRED"
    assert long.iloc[50]["time_to_outcome_bars"] == builder.HORIZON_BARS
    short = labels["SHORT"]
    assert short.iloc[t2]["outcome_class"] == "TARGET_FIRST"  # low 995 <= 996 short target
    assert short.iloc[t]["outcome_class"] == "STOP_FIRST"
    assert short.iloc[t3]["outcome_class"] == "AMBIGUOUS"
    # First bars have no ATR -> no label.
    assert long.iloc[0]["outcome_class"] is None


def test_ambiguous_rows_are_excluded_from_training_with_reason():
    starts = session_bar_starts("2026-09-01T00:00Z", "2026-09-03T00:00Z")
    bars = synthetic_bars(starts)
    bars["open"] = 1000.0
    bars["close"] = 1000.0
    bars["high"] = 1002.0
    bars["low"] = 998.0
    t3 = 40
    bars.iloc[t3 + 3, bars.columns.get_loc("high")] = 1005.0
    bars.iloc[t3 + 3, bars.columns.get_loc("low")] = 995.0
    built = builder.build_dataset(bars, None, CAL)
    row = built.rows[(built.rows["session_seq"] == t3) & (built.rows["direction"] == "LONG")].iloc[0]
    assert row["outcome_class"] == "AMBIGUOUS"
    assert row["label_quality"] == "EXCLUDED_FROM_TRAINING"
    assert "AMBIGUOUS_LABEL" in row["exclusion_reasons_ohlcv_only"]
    assert not row["included_ohlcv_only"]
    clean = built.rows[(built.rows["session_seq"] == 25) & (built.rows["direction"] == "LONG")].iloc[0]
    assert clean["label_quality"] == "HIGH"
    assert clean["included_ohlcv_only"]


def test_split_purge_and_embargo_around_train_boundary():
    starts = session_bar_starts("2021-12-28T00:00Z", "2022-01-06T00:00Z")
    bars = synthetic_bars(starts)
    built = builder.build_dataset(bars, None, CAL)
    rows = built.rows[built.rows["direction"] == "LONG"].set_index("session_seq")
    train_rows = rows[rows["split"] == "TRAIN"]
    val_rows = rows[rows["split"] == "VALIDATION"]
    assert len(train_rows) and len(val_rows)
    assert (train_rows["bar_end"] < builder.TRAIN_END).all()
    assert (val_rows["bar_end"] >= builder.TRAIN_END).all()
    last_train = train_rows.index.max()
    for seq in range(last_train - builder.HORIZON_BARS + 1, last_train + 1):
        assert "PURGED_HORIZON_CROSSES_SPLIT_BOUNDARY" in rows.loc[seq, "exclusion_reasons_ohlcv_only"]
    assert "PURGED_HORIZON_CROSSES_SPLIT_BOUNDARY" not in rows.loc[last_train - builder.HORIZON_BARS, "exclusion_reasons_ohlcv_only"]
    first_val = val_rows.index.min()
    for seq in range(first_val, first_val + builder.EMBARGO_BARS):
        assert "EMBARGO_AFTER_SPLIT_BOUNDARY" in rows.loc[seq, "exclusion_reasons_ohlcv_only"]
    assert "EMBARGO_AFTER_SPLIT_BOUNDARY" not in rows.loc[first_val + builder.EMBARGO_BARS, "exclusion_reasons_ohlcv_only"]
    assert "EMBARGO_AFTER_SPLIT_BOUNDARY" not in rows.loc[0, "exclusion_reasons_ohlcv_only"]


def test_2017_damaged_window_is_excluded_from_every_variant():
    starts = session_bar_starts("2016-12-28T00:00Z", "2017-01-04T00:00Z")
    bars = synthetic_bars(starts)
    built = builder.build_dataset(bars, None, CAL)
    rows = built.rows
    inside = rows[rows["bar_start"] >= pd.Timestamp("2017-01-01T00:00Z")]
    assert len(inside)
    assert inside["exclusion_reasons_ohlcv_only"].str.contains("DAMAGED_2017_WINDOW").all()
    assert inside["exclusion_reasons_order_flow"].str.contains("DAMAGED_2017_WINDOW").all()
    before = rows[rows["bar_end"] < pd.Timestamp("2016-12-30T00:00Z")]
    # Bars whose 8-bar horizon reaches into the window are also excluded; earlier ones are not.
    assert not before["exclusion_reasons_ohlcv_only"].str.contains("DAMAGED_2017_WINDOW").any()


def test_order_flow_variant_flags_missing_active_bars_and_coverage():
    starts = session_bar_starts("2026-09-01T00:00Z", "2026-09-04T20:00Z")
    bars = synthetic_bars(starts)
    of_minutes = pd.DatetimeIndex(
        [ts + pd.Timedelta(minutes=m) for ts in starts[5:-5] for m in (0, 7, 29)]
    ).tz_convert(None)
    of_1m = pd.DataFrame(
        {"volume": 10.0, "delta": 1.0, "trades": 3},
        index=pd.DatetimeIndex(of_minutes, name="minute"),
    )
    hole = starts[60]
    of_1m = of_1m[(of_1m.index < hole.tz_convert(None)) | (of_1m.index >= (hole + pd.Timedelta(minutes=30)).tz_convert(None))]
    of_30m = builder.aggregate_order_flow_30m(of_1m)
    assert of_30m.loc[starts[10], "of_volume"] == 30.0
    assert of_30m.loc[starts[10], "of_minutes_present"] == 3
    assert hole not in of_30m.index
    built = builder.build_dataset(bars, of_30m, CAL)
    rows = built.rows[built.rows["direction"] == "LONG"].set_index("session_seq")
    assert "ORDER_FLOW_OUTSIDE_COVERAGE" in rows.loc[2, "exclusion_reasons_order_flow"]
    assert "ORDER_FLOW_OUTSIDE_COVERAGE" not in rows.loc[2, "exclusion_reasons_ohlcv_only"]
    assert "ORDER_FLOW_MISSING_FOR_ACTIVE_BAR" in rows.loc[60, "exclusion_reasons_order_flow"]
    assert "ORDER_FLOW_GAP_IN_FEATURE_LOOKBACK" in rows.loc[61, "exclusion_reasons_order_flow"]
    assert "ORDER_FLOW_GAP_IN_FEATURE_LOOKBACK" not in rows.loc[61 + builder.FEATURE_LOOKBACK_BARS, "exclusion_reasons_order_flow"]
    assert rows.loc[61, "included_ohlcv_only"] or "OHLCV" in rows.loc[61, "exclusion_reasons_ohlcv_only"] or rows.loc[61, "exclusion_reasons_ohlcv_only"] == ""
    assert not rows.loc[61, "included_order_flow"]
    clean = 90
    assert rows.loc[clean, "included_order_flow"]
    assert rows.loc[clean, "of_volume_sum_14"] == 14 * 30.0
    variants = built.summary["variants"]
    assert variants["order_flow"]["included_rows"] < variants["ohlcv_only"]["included_rows"]
    assert variants["order_flow"]["excluded_rows_by_reason"]["ORDER_FLOW_MISSING_FOR_ACTIVE_BAR"] == 2


def test_out_of_session_data_is_dropped_not_filled():
    starts = session_bar_starts("2026-09-01T00:00Z", "2026-09-03T00:00Z")
    bars = synthetic_bars(starts)
    # 2026-09-01 16:30 CT (21:30Z, CDT) is inside the daily break: data there is dropped, not a gap.
    break_bar = pd.Timestamp("2026-09-01T21:30Z")
    bars.loc[break_bar] = bars.iloc[0]
    bars = bars.sort_index()
    built = builder.build_dataset(bars, None, CAL)
    assert built.summary["out_of_session_bars_with_data"] == 1
    assert break_bar not in set(built.rows["bar_start"])
    assert built.summary["missing_expected_bars"] == 0


def test_rule_constants_are_stable_and_json_safe():
    import json

    constants = builder.rule_constants()
    json.dumps(constants)
    assert constants["horizon_bars"] == 8
    assert constants["embargo_bars"] == 8
    assert constants["calendar_id"] == "cme-globex-metals-research-v1"
    assert "CVD" not in " ".join(constants["order_flow_features"]).upper()


@pytest.mark.parametrize("direction", ["LONG", "SHORT"])
def test_candidate_ids_are_unique_and_deterministic(direction):
    starts = session_bar_starts("2026-09-01T00:00Z", "2026-09-02T00:00Z")
    bars = synthetic_bars(starts)
    built = builder.build_dataset(bars, None, CAL)
    subset = built.rows[built.rows["direction"] == direction]
    assert subset["candidate_id"].is_unique
    assert subset["candidate_id"].str.endswith(direction).all()
    again = builder.build_dataset(bars, None, CAL)
    pd.testing.assert_frame_equal(built.rows, again.rows)
