"""Read-only local XAUUSD inventory. Emits aggregates, never market rows.

No provider loaders are imported. File hashes bind the bytes actually parsed.
Calendar coverage, historical publication, source equivalence and data semantics
are deliberately not inferred from file names or successful parsing.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd


TV_STEPS = {'M5': 300, 'M15': 900, 'M30': 1800, 'H1': 3600,
            'H4': 14400, 'D1': 86400}


def time_profile(values: pd.Series, step_seconds: int | None = None) -> dict:
    """Naive times can have local extents, but never acquire UTC attestation."""
    text = values.astype('string')
    if pd.api.types.is_numeric_dtype(values.dtype):
        parsed = pd.Series(pd.NaT, index=values.index, dtype='datetime64[ns, UTC]')
    else:
        parsed = pd.to_datetime(text, format='mixed', utc=True, errors='coerce')
    valid = parsed.notna()
    offsets = text.str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$', na=False)
    aware_count = int((valid & offsets).sum())
    naive_count = int((valid & ~offsets).sum())
    zone = ('MIXED_AWARENESS' if aware_count and naive_count else
            'NAIVE_UNVERIFIED' if naive_count else 'AWARE' if aware_count else 'UNKNOWN')
    result = {
        'timezone_status': zone, 'invalid_rows': int((~valid).sum()),
        'first': None, 'last': None, 'duplicate_rows': None,
        'out_of_order_steps': None, 'intervals_longer_than_step': None,
        'max_interval_seconds': None, 'calendar_completeness': 'NOT_ASSESSED',
    }
    if not valid.any() or zone == 'MIXED_AWARENESS':
        return result
    times = parsed.loc[valid]
    ordered = times.drop_duplicates().sort_values()
    gaps = ordered.diff().dt.total_seconds().dropna()

    def stamp(value):
        return (value.isoformat().replace('+00:00', 'Z') if zone == 'AWARE'
                else value.tz_localize(None).isoformat())

    result.update({
        'first': stamp(times.min()), 'last': stamp(times.max()),
        'duplicate_rows': int(times.duplicated().sum()),
        'out_of_order_steps': int((times.diff().dt.total_seconds() < 0).sum()),
        'intervals_longer_than_step': (int((gaps > step_seconds).sum())
                                       if step_seconds is not None else None),
        'max_interval_seconds': float(gaps.max()) if len(gaps) else None,
    })
    return result


def _read_bytes(path: Path) -> tuple[dict, bytes | None]:
    report = {'file': path.name, 'status': 'MISSING', 'publication_status': 'UNKNOWN'}
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return report, None
    except OSError as exc:
        report.update(status='UNREADABLE', error_type=type(exc).__name__)
        return report, None
    report.update(status='PROFILED', bytes=len(payload),
                  sha256=hashlib.sha256(payload).hexdigest())
    return report, payload


def profile_bars(path: Path, *, time_column: str, step_seconds: int) -> dict:
    if type(step_seconds) is not int or step_seconds <= 0:
        raise ValueError('step_seconds must be a positive integer')
    report, payload = _read_bytes(path)
    if payload is None:
        return report
    try:
        if path.suffix == '.parquet':
            frame = pd.read_parquet(io.BytesIO(payload))
            if time_column not in frame and frame.index.name == time_column:
                frame = frame.reset_index()
        else:
            frame = pd.read_csv(io.BytesIO(payload), compression='gzip'
                                if path.name.endswith('.gz') else None)
        required = {time_column, 'open', 'high', 'low', 'close', 'volume'}
        report.update(rows=len(frame), missing_columns=sorted(required - set(frame)),
                      invalid_ohlc_rows=None, invalid_volume_rows=None,
                      zero_volume_rows=None)
        if time_column in frame:
            report['time'] = time_profile(frame[time_column], step_seconds)
        price_columns = ['open', 'high', 'low', 'close']
        if all(name in frame for name in price_columns):
            prices = frame[price_columns].apply(pd.to_numeric, errors='coerce')
            valid = (prices.notna().all(axis=1) & np.isfinite(prices).all(axis=1)
                     & (prices > 0).all(axis=1))
            valid &= (prices['high'] >= prices[['open', 'low', 'close']].max(axis=1))
            valid &= (prices['low'] <= prices[['open', 'high', 'close']].min(axis=1))
            report['invalid_ohlc_rows'] = int((~valid).sum())
        if 'volume' in frame:
            volume = pd.to_numeric(frame['volume'], errors='coerce')
            report['invalid_volume_rows'] = int((volume.isna() | ~np.isfinite(volume)
                                                 | (volume < 0)).sum())
            report['zero_volume_rows'] = int((volume == 0).sum())
        return report
    except Exception as exc:
        report.update(status='UNREADABLE', error_type=type(exc).__name__)
        return report


def profile_calendar(path: Path) -> dict:
    report, payload = _read_bytes(path)
    report['coverage_status'] = 'NOT_ESTABLISHED'
    if payload is None:
        return report
    try:
        events = json.loads(payload)
        if not isinstance(events, list) or any(not isinstance(e, dict) for e in events):
            raise ValueError('expected event-list schema')
        report['event_count'] = len(events)
        report['event_times'] = time_profile(pd.Series([e.get('date') for e in events],
                                                       dtype='object'))
        report['event_times']['coincident_timestamp_rows'] = report['event_times'].pop(
            'duplicate_rows')
    except Exception as exc:
        report.update(status='UNREADABLE', error_type=type(exc).__name__)
    return report


def audit_local_sources(repos_root: Path) -> dict:
    root = repos_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('repos_root must be a directory')
    tv = [profile_bars(root / 'chart-desk/data/tv' / f'XAUUSD_{tag}.csv',
                      time_column='time', step_seconds=step)
          for tag, step in TV_STEPS.items()]
    duka = [profile_bars(path, time_column='ts', step_seconds=3600)
            for path in sorted((root / 'chart-desk/data/duka/candles/XAUUSD').glob(
                'BID_hour_*.csv.gz'))]
    options_dir = root / 'options-desk/out'
    options = [_read_bytes(path)[0] for path in sorted(options_dir.glob('report-*.json'))]
    return {
        'schema_version': 'xauusd-local-source-audit-v1',
        'status': 'PROFILE_ONLY', 'ready_for_training': False,
        'tv': tv, 'duka_hourly': duka,
        'order_flow': profile_bars(root / 'chart-desk/data/orderflow/XAUUSD_1min.parquet',
                                   time_column='ts', step_seconds=60),
        'news': profile_calendar(root / 'news-desk/data/ff_calendar.json'),
        'options': {'directory_exists': options_dir.is_dir(),
                    'report_files': len(options), 'files': options,
                    'coverage_status': 'NOT_ESTABLISHED'},
        'interpretation': {
            'calendar_gaps': 'Intervals are observations, not missing-bar verdicts',
            'duka': 'Different price source; no OANDA equivalence inferred',
            'flow': 'Quote-size-derived; executed delta not established',
            'options': 'Only expected report files inventoried; no chain certification',
        },
    }


def compact_report(report: dict) -> dict:
    """Keep monthly hash commitments without printing all monthly diagnostics."""
    result = dict(report)
    monthly = report['duka_hourly']
    starts = [r['time']['first'] for r in monthly if r.get('time', {}).get('first')]
    ends = [r['time']['last'] for r in monthly if r.get('time', {}).get('last')]
    commitment = [{'file': r['file'], 'sha256': r.get('sha256'), 'status': r['status']}
                  for r in monthly]
    result['duka_hourly'] = {
        'files': len(monthly), 'unreadable_files': sum(r['status'] != 'PROFILED' for r in monthly),
        'rows': sum(r.get('rows', 0) for r in monthly),
        'ohlc_assessed_files': sum(r.get('invalid_ohlc_rows') is not None for r in monthly),
        'files_not_fully_assessed': sum(
            r['status'] != 'PROFILED' or bool(r.get('missing_columns')) or
            r.get('time', {}).get('timezone_status') != 'AWARE' or
            r.get('time', {}).get('invalid_rows', 1) != 0
            for r in monthly),
        'first_stored_extent': min(starts) if starts else None,
        'last_stored_extent': max(ends) if ends else None,
        'invalid_ohlc_rows': sum(r.get('invalid_ohlc_rows') or 0 for r in monthly),
        'invalid_volume_rows': sum(r.get('invalid_volume_rows') or 0 for r in monthly),
        'within_file_duplicate_rows': sum(r.get('time', {}).get('duplicate_rows') or 0
                                         for r in monthly),
        'file_commitment_sha256': hashlib.sha256(json.dumps(commitment, sort_keys=True,
                                                     separators=(',', ':')).encode()).hexdigest(),
        'calendar_completeness': 'NOT_ASSESSED',
        'cross_file_overlap': 'NOT_ASSESSED',
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repos-root', required=True, type=Path)
    parser.add_argument('--full', action='store_true', help='Include every monthly profile')
    args = parser.parse_args()
    try:
        report = audit_local_sources(args.repos_root)
        print(json.dumps(report if args.full else compact_report(report), indent=2,
                         sort_keys=True, allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'AUDIT_FAILED', 'error_type': type(exc).__name__}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
