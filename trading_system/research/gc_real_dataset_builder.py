"""Deterministic builder for the first real GC 30m research dataset.

Encodes the v1 rules approved in D1/D3/D4/D6/D7/D8 (see
docs/superpowers/plans/2026-09-02-phases-43-47-gc-real-dataset-to-training-start.md):

- 30m UTC half-open bars resampled from Databento 1s OHLCV (ts_event = start).
- Session membership through the registered ``cme-globex-metals-research-v1``
  calendar; weekends and the daily break are not gaps.
- Fail-closed missing-bar exclusion: no forward fill, every exclusion reason
  recorded per row and counted by reason and split.
- Outcome-contract labels (ATR14 risk unit, 1R target, 1R stop, 8-bar horizon,
  next-bar-open entry, same-bar ambiguity excluded).
- Chronological walk-forward split with purge and embargo.
- Order-flow variant limited to volume/delta/trades, 2017 damaged window
  excluded through the shared mask function.

Everything here is research-only. Nothing in this module is execution truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from trading_system.data_foundation.sessions import SessionCalendar, load_session_calendar, resolve_session
from trading_system.research.gc_order_flow_row_mask_cumulative_policy import (
    apply_gc_order_flow_training_mask,
)

BUILDER_VERSION = "gc-30m-real-dataset-builder-0.1.0"
FEATURE_SCHEMA_VERSION = "gc-30m-real-feature-schema-0.1.0"
LABEL_VERSION = "gc-outcome-contract-label-0.1.0"
CONTRACT_VERSION = "gc-atr14-1r-1r-8bar-zero-cost-0.1.0"
CALENDAR_ID = "cme-globex-metals-research-v1"
CALENDAR_PATH = Path(__file__).resolve().parents[2] / "configs/data/session-calendar.yaml"

BAR = pd.Timedelta(minutes=30)
ONE_SECOND = pd.Timedelta(seconds=1)
ATR_BARS = 14
FEATURE_LOOKBACK_BARS = 15  # 14 true ranges need 15 closed bars
HORIZON_BARS = 8
EMBARGO_BARS = 8
TARGET_MULTIPLE = 1.0
STOP_MULTIPLE = 1.0
TRAIN_END = pd.Timestamp("2022-01-01T00:00:00Z")
VALIDATION_END = pd.Timestamp("2024-01-01T00:00:00Z")
DIRECTIONS = ("LONG", "SHORT")
VARIANTS = ("ohlcv_only", "order_flow")

REASON_OHLCV_MISSING_BAR = "OHLCV_MISSING_BAR"
REASON_OHLCV_GAP_LOOKBACK = "OHLCV_GAP_IN_FEATURE_LOOKBACK"
REASON_INSUFFICIENT_LOOKBACK = "INSUFFICIENT_LOOKBACK"
REASON_OHLCV_GAP_HORIZON = "OHLCV_GAP_IN_LABEL_HORIZON"
REASON_INSUFFICIENT_HORIZON = "INSUFFICIENT_HORIZON"
REASON_DAMAGED_2017 = "DAMAGED_2017_WINDOW"
REASON_AMBIGUOUS = "AMBIGUOUS_LABEL"
REASON_PURGED = "PURGED_HORIZON_CROSSES_SPLIT_BOUNDARY"
REASON_EMBARGO = "EMBARGO_AFTER_SPLIT_BOUNDARY"
REASON_OF_OUTSIDE_COVERAGE = "ORDER_FLOW_OUTSIDE_COVERAGE"
REASON_OF_MISSING_ACTIVE = "ORDER_FLOW_MISSING_FOR_ACTIVE_BAR"
REASON_OF_GAP_LOOKBACK = "ORDER_FLOW_GAP_IN_FEATURE_LOOKBACK"
REASON_STRADDLE = "STRADDLES_SESSION_BOUNDARY"

ALL_VARIANT_REASONS = (
    REASON_OHLCV_GAP_LOOKBACK,
    REASON_INSUFFICIENT_LOOKBACK,
    REASON_OHLCV_GAP_HORIZON,
    REASON_INSUFFICIENT_HORIZON,
    REASON_DAMAGED_2017,
    REASON_AMBIGUOUS,
    REASON_PURGED,
    REASON_EMBARGO,
)
ORDER_FLOW_VARIANT_REASONS = (
    REASON_OF_OUTSIDE_COVERAGE,
    REASON_OF_MISSING_ACTIVE,
    REASON_OF_GAP_LOOKBACK,
)

OHLCV_FEATURES = (
    "close",
    "atr_14",
    "ret_1",
    "ret_4",
    "ret_8",
    "ret_14",
    "range_over_atr",
    "volume_30m",
    "seconds_with_trades",
)
ORDER_FLOW_FEATURES = (
    "of_volume",
    "of_delta",
    "of_trades",
    "of_minutes_present",
    "of_volume_sum_14",
    "of_delta_sum_14",
    "of_trades_sum_14",
)


def rule_constants() -> dict[str, Any]:
    """Constants that define the dataset; hashed into the dataset identity."""
    return {
        "builder_version": BUILDER_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "label_version": LABEL_VERSION,
        "contract_version": CONTRACT_VERSION,
        "calendar_id": CALENDAR_ID,
        "bar_minutes": 30,
        "interval_semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE",
        "available_at": "BAR_END_UTC",
        "atr_bars": ATR_BARS,
        "atr_method": "SIMPLE_MEAN_TRUE_RANGE",
        "feature_lookback_bars": FEATURE_LOOKBACK_BARS,
        "horizon_bars": HORIZON_BARS,
        "embargo_bars": EMBARGO_BARS,
        "target_multiple": TARGET_MULTIPLE,
        "stop_multiple": STOP_MULTIPLE,
        "entry": "NEXT_BAR_OPEN_AFTER_DECISION_BAR_CLOSE",
        "train_end": TRAIN_END.isoformat().replace("+00:00", "Z"),
        "validation_end": VALIDATION_END.isoformat().replace("+00:00", "Z"),
        "directions": list(DIRECTIONS),
        "variants": list(VARIANTS),
        "ohlcv_features": list(OHLCV_FEATURES),
        "order_flow_features": list(ORDER_FLOW_FEATURES),
        "fill_truth": "ZERO_COST_RESEARCH_SIMULATOR_ONLY_NOT_EXECUTION_TRUTH",
    }


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------


def resample_1s_to_30m(ohlcv_1s: pd.DataFrame) -> pd.DataFrame:
    """Resample Databento 1s OHLCV (index ts_event UTC) to 30m half-open bars."""
    if ohlcv_1s.empty:
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume", "seconds_with_trades"],
            index=pd.DatetimeIndex([], name="bar_start", tz="UTC"),
        )
    index = pd.DatetimeIndex(ohlcv_1s.index)
    if index.tz is None:
        raise ValueError("ohlcv_1s index must be timezone-aware UTC")
    index = index.tz_convert("UTC")
    frame = pd.DataFrame(
        {
            "open": ohlcv_1s["gc_open"].to_numpy(),
            "high": ohlcv_1s["gc_high"].to_numpy(),
            "low": ohlcv_1s["gc_low"].to_numpy(),
            "close": ohlcv_1s["gc_close"].to_numpy(),
            "volume": ohlcv_1s["gc_volume"].to_numpy(),
        },
        index=index,
    ).sort_index()
    frame["bar_start"] = frame.index.floor("30min")
    grouped = frame.groupby("bar_start", sort=True)
    bars = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        seconds_with_trades=("close", "size"),
    )
    bars.index.name = "bar_start"
    return bars


def aggregate_order_flow_30m(order_flow_1m: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 1m volume/delta/trades (index minute, naive = UTC wall clock) to 30m."""
    if order_flow_1m.empty:
        return pd.DataFrame(
            columns=["of_volume", "of_delta", "of_trades", "of_minutes_present"],
            index=pd.DatetimeIndex([], name="bar_start", tz="UTC"),
        )
    index = pd.DatetimeIndex(order_flow_1m.index)
    index = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    frame = pd.DataFrame(
        {
            "of_volume": order_flow_1m["volume"].to_numpy(dtype=float),
            "of_delta": order_flow_1m["delta"].to_numpy(dtype=float),
            "of_trades": order_flow_1m["trades"].to_numpy(dtype=float),
        },
        index=index,
    ).sort_index()
    frame["bar_start"] = frame.index.floor("30min")
    grouped = frame.groupby("bar_start", sort=True)
    bars = grouped.agg(
        of_volume=("of_volume", "sum"),
        of_delta=("of_delta", "sum"),
        of_trades=("of_trades", "sum"),
        of_minutes_present=("of_volume", "size"),
    )
    bars.index.name = "bar_start"
    return bars


# ---------------------------------------------------------------------------
# Session grid
# ---------------------------------------------------------------------------


def load_calendar() -> SessionCalendar:
    return load_session_calendar(CALENDAR_PATH, CALENDAR_ID)


@dataclass(frozen=True)
class _SessionFlags:
    in_session: bool
    trade_date: str


def _session_resolver(calendar: SessionCalendar):
    @lru_cache(maxsize=None)
    def resolve(ts_value: int) -> _SessionFlags:
        ts = pd.Timestamp(ts_value, tz="UTC").to_pydatetime()
        state = resolve_session(ts, calendar)
        return _SessionFlags(in_session=state.in_session, trade_date=state.trade_date)

    return resolve


def build_expected_grid(
    first_bar_start: pd.Timestamp,
    last_bar_start: pd.Timestamp,
    calendar: SessionCalendar,
) -> pd.DataFrame:
    """All 30m grid bars in [first, last] with session flags.

    Returns columns: bar_start (index), bar_end, in_session_start, in_session_end,
    in_session (both), straddle, trade_date. Only ``in_session`` bars are
    "expected"; ``session_seq`` numbers them consecutively.
    """
    first = pd.Timestamp(first_bar_start).tz_convert("UTC").floor("30min")
    last = pd.Timestamp(last_bar_start).tz_convert("UTC").floor("30min")
    starts = pd.date_range(first, last, freq="30min", tz="UTC")
    resolve = _session_resolver(calendar)
    start_flags = [resolve(int(ts.value)) for ts in starts]
    end_flags = [resolve(int((ts + BAR - ONE_SECOND).value)) for ts in starts]
    grid = pd.DataFrame(
        {
            "bar_end": starts + BAR,
            "in_session_start": [f.in_session for f in start_flags],
            "in_session_end": [f.in_session for f in end_flags],
            "trade_date": [f.trade_date for f in start_flags],
        },
        index=pd.DatetimeIndex(starts, name="bar_start"),
    )
    grid["in_session"] = grid["in_session_start"] & grid["in_session_end"]
    grid["straddle"] = grid["in_session_start"] != grid["in_session_end"]
    seq = np.full(len(grid), -1, dtype=np.int64)
    seq[grid["in_session"].to_numpy()] = np.arange(int(grid["in_session"].sum()))
    grid["session_seq"] = seq
    return grid


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssembledBars:
    bars: pd.DataFrame  # expected in-session bars, one row per session_seq
    out_of_session_bars_with_data: int
    straddle_bars: int
    straddle_bars_with_data: int


def assemble_session_bars(
    ohlcv_30m: pd.DataFrame,
    calendar: SessionCalendar,
    order_flow_30m: pd.DataFrame | None = None,
) -> AssembledBars:
    if ohlcv_30m.empty:
        raise ValueError("no 30m OHLCV bars to assemble")
    grid = build_expected_grid(ohlcv_30m.index.min(), ohlcv_30m.index.max(), calendar)
    joined = grid.join(ohlcv_30m, how="left")
    has_data = joined["close"].notna()
    out_of_session_with_data = int((has_data & ~joined["in_session"]).sum())
    straddle_bars = int(joined["straddle"].sum())
    straddle_with_data = int((has_data & joined["straddle"]).sum())
    bars = joined[joined["in_session"]].copy()
    bars["present"] = bars["close"].notna()
    if order_flow_30m is not None and not order_flow_30m.empty:
        bars = bars.join(order_flow_30m, how="left")
        of_first = order_flow_30m.index.min()
        of_last = order_flow_30m.index.max()
        bars["of_in_coverage"] = (bars.index >= of_first) & (bars.index <= of_last)
    else:
        for column in ("of_volume", "of_delta", "of_trades", "of_minutes_present"):
            bars[column] = np.nan
        bars["of_in_coverage"] = False
    bars["of_minutes_present"] = bars["of_minutes_present"].fillna(0).astype(int)
    bars = bars.drop(columns=["in_session_start", "in_session_end", "in_session", "straddle"])
    bars = bars.sort_values("session_seq")
    return AssembledBars(
        bars=bars,
        out_of_session_bars_with_data=out_of_session_with_data,
        straddle_bars=straddle_bars,
        straddle_bars_with_data=straddle_with_data,
    )


# ---------------------------------------------------------------------------
# Gap propagation, features, labels, splits
# ---------------------------------------------------------------------------


def _trailing_any(flags: np.ndarray, window: int) -> np.ndarray:
    """True at i if any of flags[i-window:i] is True (previous ``window`` bars, excluding i)."""
    values = flags.astype(np.int64)
    cumulative = np.concatenate([[0], np.cumsum(values)])
    n = len(values)
    idx = np.arange(n)
    lo = np.maximum(idx - window, 0)
    counts = cumulative[idx] - cumulative[lo]
    return counts > 0


def _leading_any(flags: np.ndarray, window: int) -> np.ndarray:
    """True at i if any of flags[i+1:i+window+1] is True (next ``window`` bars, excluding i)."""
    values = flags.astype(np.int64)
    cumulative = np.concatenate([[0], np.cumsum(values)])
    n = len(values)
    idx = np.arange(n)
    hi = np.minimum(idx + window + 1, n)
    counts = cumulative[hi] - cumulative[idx + 1]
    return counts > 0


def compute_gap_flags(bars: pd.DataFrame) -> pd.DataFrame:
    bars = bars.copy()
    missing = ~bars["present"].to_numpy()
    n = len(bars)
    idx = np.arange(n)
    bars["ohlcv_gap_lookback"] = _trailing_any(missing, FEATURE_LOOKBACK_BARS)
    bars["insufficient_lookback"] = idx < FEATURE_LOOKBACK_BARS
    bars["ohlcv_gap_horizon"] = _leading_any(missing, HORIZON_BARS)
    bars["insufficient_horizon"] = idx + HORIZON_BARS > n - 1
    of_missing_active = (
        bars["of_in_coverage"].to_numpy()
        & bars["present"].to_numpy()
        & (bars["volume"].fillna(0).to_numpy() > 0)
        & (bars["of_minutes_present"].to_numpy() == 0)
    )
    of_unavailable = of_missing_active | ~bars["of_in_coverage"].to_numpy()
    bars["of_missing_active"] = of_missing_active
    bars["of_gap_lookback"] = _trailing_any(of_unavailable, FEATURE_LOOKBACK_BARS)
    return bars


def compute_features(bars: pd.DataFrame) -> pd.DataFrame:
    bars = bars.copy()
    close = bars["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            bars["high"] - bars["low"],
            (bars["high"] - prev_close).abs(),
            (bars["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    bars["atr_14"] = true_range.rolling(ATR_BARS, min_periods=ATR_BARS).mean()
    for lag in (1, 4, 8, 14):
        bars[f"ret_{lag}"] = close / close.shift(lag) - 1.0
    bars["range_over_atr"] = (bars["high"] - bars["low"]) / bars["atr_14"]
    bars["volume_30m"] = bars["volume"]
    for column in ("of_volume", "of_delta", "of_trades"):
        bars[f"{column}_sum_14"] = bars[column].rolling(ATR_BARS, min_periods=ATR_BARS).sum()
    return bars


def _outcome_arrays(
    entry: np.ndarray,
    risk: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    direction: str,
) -> dict[str, np.ndarray]:
    """Vectorised outcome contract over the next HORIZON_BARS bars.

    highs/lows/closes are (n, HORIZON_BARS) arrays for bars t+1..t+8.
    """
    n = len(entry)
    if direction == "LONG":
        target = entry + TARGET_MULTIPLE * risk
        stop = entry - STOP_MULTIPLE * risk
        target_hit = highs >= target[:, None]
        stop_hit = lows <= stop[:, None]
        expiry_r = (closes[:, -1] - entry) / risk
    else:
        target = entry - TARGET_MULTIPLE * risk
        stop = entry + STOP_MULTIPLE * risk
        target_hit = lows <= target[:, None]
        stop_hit = highs >= stop[:, None]
        expiry_r = (entry - closes[:, -1]) / risk
    big = HORIZON_BARS + 1
    first_target = np.where(target_hit.any(axis=1), target_hit.argmax(axis=1) + 1, big)
    first_stop = np.where(stop_hit.any(axis=1), stop_hit.argmax(axis=1) + 1, big)
    outcome = np.full(n, "EXPIRED", dtype=object)
    time_to = np.full(n, HORIZON_BARS, dtype=np.int64)
    net_r = expiry_r.astype(float)
    ambiguous = (first_target == first_stop) & (first_target <= HORIZON_BARS)
    target_first = (first_target < first_stop) & (first_target <= HORIZON_BARS)
    stop_first = (first_stop < first_target) & (first_stop <= HORIZON_BARS)
    outcome[ambiguous] = "AMBIGUOUS"
    outcome[target_first] = "TARGET_FIRST"
    outcome[stop_first] = "STOP_FIRST"
    time_to[ambiguous] = first_target[ambiguous]
    time_to[target_first] = first_target[target_first]
    time_to[stop_first] = first_stop[stop_first]
    net_r[ambiguous] = np.nan
    net_r[target_first] = TARGET_MULTIPLE
    net_r[stop_first] = -STOP_MULTIPLE
    return {
        "target_price": target,
        "stop_price": stop,
        "outcome_class": outcome,
        "time_to_outcome_bars": time_to,
        "net_return_r": net_r,
    }


def _future_matrix(series: pd.Series) -> np.ndarray:
    values = series.to_numpy(dtype=float)
    n = len(values)
    matrix = np.full((n, HORIZON_BARS), np.nan)
    for k in range(1, HORIZON_BARS + 1):
        matrix[: n - k, k - 1] = values[k:]
    return matrix


def label_outcomes(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Per-direction outcome labels for every session bar (NaN-safe; exclusions applied later)."""
    entry = bars["open"].shift(-1).to_numpy(dtype=float)
    risk = bars["atr_14"].to_numpy(dtype=float)
    highs = _future_matrix(bars["high"])
    lows = _future_matrix(bars["low"])
    closes = _future_matrix(bars["close"])
    valid = np.isfinite(entry) & np.isfinite(risk) & (risk > 0) & np.isfinite(highs).all(axis=1)
    safe_entry = np.where(valid, entry, 0.0)
    safe_risk = np.where(valid, risk, 1.0)
    safe_highs = np.where(np.isfinite(highs), highs, 0.0)
    safe_lows = np.where(np.isfinite(lows), lows, 0.0)
    safe_closes = np.where(np.isfinite(closes), closes, 0.0)
    result: dict[str, pd.DataFrame] = {}
    for direction in DIRECTIONS:
        arrays = _outcome_arrays(safe_entry, safe_risk, safe_highs, safe_lows, safe_closes, direction)
        frame = pd.DataFrame(arrays, index=bars.index)
        frame["entry_price"] = entry
        frame["risk_r"] = risk
        frame["label_valid"] = valid
        frame.loc[~valid, ["outcome_class"]] = None
        frame.loc[~valid, ["net_return_r"]] = np.nan
        result[direction] = frame
    return result


def assign_split(bar_end: pd.Series) -> pd.Series:
    ends = pd.DatetimeIndex(bar_end)
    split = np.where(ends < TRAIN_END, "TRAIN", np.where(ends < VALIDATION_END, "VALIDATION", "TEST"))
    return pd.Series(split, index=bar_end.index)


def compute_split_flags(bars: pd.DataFrame) -> pd.DataFrame:
    bars = bars.copy()
    bars["split"] = assign_split(bars["bar_end"]).to_numpy()
    split_codes = pd.Series(bars["split"]).map({"TRAIN": 0, "VALIDATION": 1, "TEST": 2}).to_numpy()
    horizon_end_codes = np.concatenate([split_codes[HORIZON_BARS:], np.full(HORIZON_BARS, -1)])
    bars["purged"] = (horizon_end_codes >= 0) & (horizon_end_codes != split_codes)
    boundary = np.concatenate([[False], split_codes[1:] != split_codes[:-1]])
    rank_in_split = np.zeros(len(bars), dtype=np.int64)
    counter = 0
    for i in range(len(bars)):
        counter = 0 if boundary[i] else counter + 1
        rank_in_split[i] = counter
    # Embargo the first EMBARGO_BARS session bars after every boundary; the first
    # split has no preceding boundary and is never embargoed at data start.
    bars["embargo"] = (rank_in_split < EMBARGO_BARS) & (np.cumsum(boundary) > 0)
    mask_keep = apply_gc_order_flow_training_mask(pd.Series(bars.index, index=bars.index)).to_numpy()
    horizon_end = pd.Series(bars["bar_end"].shift(-HORIZON_BARS), index=bars.index)
    horizon_keep = apply_gc_order_flow_training_mask(horizon_end.fillna(bars["bar_end"])).to_numpy()
    bars["damaged_2017"] = ~(mask_keep & horizon_keep)
    return bars


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuiltDataset:
    rows: pd.DataFrame
    bars: pd.DataFrame
    summary: dict[str, Any]


def _reason_lists(bars: pd.DataFrame, label: pd.DataFrame) -> tuple[list[list[str]], list[list[str]]]:
    """Vectorised exclusion reasons: (common-to-all-variants, order-flow-only) per row."""
    common_columns = (
        ("ohlcv_gap_lookback", REASON_OHLCV_GAP_LOOKBACK),
        ("insufficient_lookback", REASON_INSUFFICIENT_LOOKBACK),
        ("ohlcv_gap_horizon", REASON_OHLCV_GAP_HORIZON),
        ("insufficient_horizon", REASON_INSUFFICIENT_HORIZON),
        ("damaged_2017", REASON_DAMAGED_2017),
        ("ambiguous", REASON_AMBIGUOUS),
        ("purged", REASON_PURGED),
        ("embargo", REASON_EMBARGO),
    )
    order_flow_columns = (
        ("of_outside_coverage", REASON_OF_OUTSIDE_COVERAGE),
        ("of_missing_active", REASON_OF_MISSING_ACTIVE),
        ("of_gap_lookback", REASON_OF_GAP_LOOKBACK),
    )
    flags = {
        "ambiguous": (label["outcome_class"].to_numpy() == "AMBIGUOUS"),
        "of_outside_coverage": ~bars["of_in_coverage"].to_numpy(dtype=bool),
    }
    for column, _ in (*common_columns, *order_flow_columns):
        if column not in flags:
            flags[column] = bars[column].to_numpy(dtype=bool)
    n = len(bars)
    common: list[list[str]] = [[] for _ in range(n)]
    order_flow: list[list[str]] = [[] for _ in range(n)]
    for column, reason in common_columns:
        for i in np.flatnonzero(flags[column]):
            common[i].append(reason)
    for column, reason in order_flow_columns:
        for i in np.flatnonzero(flags[column]):
            order_flow[i].append(reason)
    return common, order_flow


def build_rows(bars: pd.DataFrame, labels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    present = bars[bars["present"]]
    frames = []
    for direction in DIRECTIONS:
        label = labels[direction].loc[present.index]
        frame = pd.DataFrame(index=present.index)
        frame["bar_start"] = present.index
        frame["bar_end"] = present["bar_end"].to_numpy()
        frame["trade_date"] = present["trade_date"].to_numpy()
        frame["session_seq"] = present["session_seq"].to_numpy()
        frame["direction"] = direction
        for column in ("open", "high", "low", "close", "volume", "seconds_with_trades"):
            frame[column] = present[column].to_numpy()
        for column in OHLCV_FEATURES:
            if column not in frame.columns:
                frame[column] = present[column].to_numpy()
        for column in ORDER_FLOW_FEATURES:
            frame[column] = present[column].to_numpy()
        for column in ("entry_price", "risk_r", "target_price", "stop_price", "outcome_class", "time_to_outcome_bars", "net_return_r"):
            frame[column] = label[column].to_numpy()
        frame["split"] = present["split"].to_numpy()
        common_reasons, of_reasons = _reason_lists(present, label)
        frame["exclusion_reasons_ohlcv_only"] = ["|".join(r) for r in common_reasons]
        frame["exclusion_reasons_order_flow"] = ["|".join(c + o) for c, o in zip(common_reasons, of_reasons)]
        frame["included_ohlcv_only"] = [not r for r in common_reasons]
        frame["included_order_flow"] = [not (c or o) for c, o in zip(common_reasons, of_reasons)]
        frame["label_quality"] = np.where(
            frame["outcome_class"].isin(["TARGET_FIRST", "STOP_FIRST", "EXPIRED"]),
            "HIGH",
            "EXCLUDED_FROM_TRAINING",
        )
        frames.append(frame)
    rows = pd.concat(frames, ignore_index=True)
    rows = rows.sort_values(["session_seq", "direction"], kind="mergesort").reset_index(drop=True)
    rows["candidate_id"] = [
        f"GC:30m:{bar_start.strftime('%Y%m%dT%H%M%SZ')}:{direction}"
        for bar_start, direction in zip(pd.DatetimeIndex(rows["bar_start"]), rows["direction"])
    ]
    return rows


def exclusion_summary(rows: pd.DataFrame, bars: pd.DataFrame) -> dict[str, Any]:
    splits = ("TRAIN", "VALIDATION", "TEST")
    summary: dict[str, Any] = {"variants": {}}
    missing = bars[~bars["present"]]
    missing_split = assign_split(missing["bar_end"]) if len(missing) else pd.Series(dtype=object)
    summary["expected_session_bars"] = int(len(bars))
    summary["present_session_bars"] = int(bars["present"].sum())
    summary["missing_expected_bars"] = int((~bars["present"]).sum())
    summary["missing_expected_bars_by_split"] = {
        split: int((missing_split == split).sum()) for split in splits
    }
    # Dated observed-gap table: this is the v1 holiday/special-hours overlay
    # evidence (missing bars per trade date), as transferred from the session
    # calendar gate into the missing-bar policy.
    by_trade_date = missing.groupby("trade_date").size() if len(missing) else pd.Series(dtype=int)
    summary["missing_expected_bars_by_trade_date"] = {
        str(trade_date): int(count) for trade_date, count in sorted(by_trade_date.items())
    }
    summary["rows_total"] = int(len(rows))
    summary["rows_by_split"] = {split: int((rows["split"] == split).sum()) for split in splits}
    for variant in VARIANTS:
        included = rows[f"included_{variant}"]
        reasons_column = rows[f"exclusion_reasons_{variant}"]
        by_reason: dict[str, int] = {}
        by_reason_and_split: dict[str, dict[str, int]] = {}
        for reasons, split in zip(reasons_column, rows["split"]):
            if not reasons:
                continue
            for reason in reasons.split("|"):
                by_reason[reason] = by_reason.get(reason, 0) + 1
                by_reason_and_split.setdefault(reason, {s: 0 for s in splits})[split] += 1
        class_counts = rows.loc[included, "outcome_class"].value_counts()
        summary["variants"][variant] = {
            "included_rows": int(included.sum()),
            "excluded_rows": int((~included).sum()),
            "included_rows_by_split": {split: int(((rows["split"] == split) & included).sum()) for split in splits},
            "excluded_rows_by_split": {split: int(((rows["split"] == split) & ~included).sum()) for split in splits},
            "excluded_rows_by_reason": dict(sorted(by_reason.items())),
            "excluded_rows_by_reason_and_split": {k: by_reason_and_split[k] for k in sorted(by_reason_and_split)},
            "included_outcome_class_counts": {str(k): int(v) for k, v in sorted(class_counts.items())},
        }
    return summary


def build_dataset(
    ohlcv_30m: pd.DataFrame,
    order_flow_30m: pd.DataFrame | None,
    calendar: SessionCalendar | None = None,
) -> BuiltDataset:
    calendar = calendar or load_calendar()
    assembled = assemble_session_bars(ohlcv_30m, calendar, order_flow_30m)
    bars = compute_gap_flags(assembled.bars)
    bars = compute_features(bars)
    bars = compute_split_flags(bars)
    labels = label_outcomes(bars)
    rows = build_rows(bars, labels)
    summary = exclusion_summary(rows, bars)
    summary["out_of_session_bars_with_data"] = assembled.out_of_session_bars_with_data
    summary["straddle_bars"] = assembled.straddle_bars
    summary["straddle_bars_with_data"] = assembled.straddle_bars_with_data
    summary["first_bar_start"] = bars.index.min().isoformat().replace("+00:00", "Z")
    summary["last_bar_start"] = bars.index.max().isoformat().replace("+00:00", "Z")
    summary["rules"] = rule_constants()
    return BuiltDataset(rows=rows, bars=bars, summary=summary)
