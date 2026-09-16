"""Fault-oriented tests for local metadata inspection, not data certification."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def audit():
    script = Path(__file__).resolve().parents[2] / 'tools/audit_xauusd_local_sources.py'
    assert script.exists(), 'The read-only XAUUSD audit tool is not implemented'
    spec = importlib.util.spec_from_file_location('xauusd_audit', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def csv_file(tmp_path, times, prices=None):
    frame = pd.DataFrame({'time': times, 'open': 10., 'high': 12., 'low': 9.,
                          'close': 11., 'volume': 2.})
    if prices is not None:
        frame.loc[0, 'close'] = prices
    path = tmp_path / 'bars.csv'
    frame.to_csv(path, index=False)
    return path


def test_naive_times_are_not_certified_as_utc(audit, tmp_path):
    path = csv_file(tmp_path, ['2026-08-01 10:00:00', '2026-08-01 10:05:00'])
    before = path.read_bytes()
    report = audit.profile_bars(path, time_column='time', step_seconds=300)
    assert report['time']['timezone_status'] == 'NAIVE_UNVERIFIED'
    assert not report['time']['first'].endswith('Z')
    assert report['sha256'] == hashlib.sha256(before).hexdigest()
    assert report['publication_status'] == 'UNKNOWN'
    assert path.read_bytes() == before
    assert 'open' not in report  # no market row exported


def test_weekend_interval_is_not_automatically_a_data_loss(audit, tmp_path):
    path = csv_file(tmp_path, ['2026-08-07T20:55:00Z', '2026-08-09T22:00:00Z'])
    report = audit.profile_bars(path, time_column='time', step_seconds=300)
    assert report['time']['intervals_longer_than_step'] == 1
    assert report['time']['calendar_completeness'] == 'NOT_ASSESSED'
    assert 'missing_bars' not in report['time']


def test_duplicates_disorder_and_bad_geometry_remain_visible(audit, tmp_path):
    path = csv_file(tmp_path, ['2026-08-01T10:05:00Z', '2026-08-01T10:00:00Z',
                              '2026-08-01T10:05:00Z'], prices=13.)
    report = audit.profile_bars(path, time_column='time', step_seconds=300)
    assert report['rows'] == 3
    assert report['time']['duplicate_rows'] == 1
    assert report['time']['out_of_order_steps'] == 1
    assert report['invalid_ohlc_rows'] == 1


def test_mixed_awareness_and_invalid_time_do_not_gain_a_utc_range(audit, tmp_path):
    path = csv_file(tmp_path, ['2026-08-01T10:00:00Z', '2026-08-01 10:05:00', 'bad'])
    report = audit.profile_bars(path, time_column='time', step_seconds=300)
    assert report['time']['timezone_status'] == 'MIXED_AWARENESS'
    assert report['time']['invalid_rows'] == 1
    assert report['time']['first'] is None


def test_nonfinite_prices_and_negative_volume_are_counted(audit, tmp_path):
    path = csv_file(tmp_path, ['2026-08-01T10:00:00Z', '2026-08-01T10:05:00Z'])
    frame = pd.read_csv(path)
    frame.loc[0, 'open'] = float('inf')
    frame.loc[1, 'volume'] = -1.
    frame.to_csv(path, index=False)
    report = audit.profile_bars(path, time_column='time', step_seconds=300)
    assert report['invalid_ohlc_rows'] == 1
    assert report['invalid_volume_rows'] == 1


@pytest.mark.parametrize('extension', ['csv.gz', 'parquet'])
def test_compressed_and_parquet_inputs_use_their_stored_bytes(audit, tmp_path, extension):
    path = csv_file(tmp_path, ['2026-08-01T10:00:00Z'])
    dest = tmp_path / ('bars.' + extension)
    if extension == 'csv.gz':
        dest.write_bytes(gzip.compress(path.read_bytes()))
    else:
        frame = pd.read_csv(path)
        frame['time'] = pd.to_datetime(frame['time'])
        frame.set_index('time').to_parquet(dest)
    report = audit.profile_bars(dest, time_column='time', step_seconds=300)
    assert report['rows'] == 1
    assert report['sha256'] == hashlib.sha256(dest.read_bytes()).hexdigest()
    assert report['time']['timezone_status'] == 'AWARE'


def test_empty_calendar_is_not_proof_of_no_events(audit, tmp_path):
    path = tmp_path / 'calendar.json'
    path.write_text('[]', encoding='utf-8')
    report = audit.profile_calendar(path)
    assert report['event_count'] == 0
    assert report['coverage_status'] == 'NOT_ESTABLISHED'


def test_event_extent_does_not_certify_publication_or_full_coverage(audit, tmp_path):
    path = tmp_path / 'calendar.json'
    path.write_text(json.dumps([{'date': '2026-08-01T10:00:00Z', 'title': 'private payload'},
                                {'date': '2026-08-02T10:00:00Z'}]), encoding='utf-8')
    report = audit.profile_calendar(path)
    assert report['event_count'] == 2
    assert report['coverage_status'] == 'NOT_ESTABLISHED'
    assert 'private payload' not in json.dumps(report)


def test_missing_sources_remain_missing_with_false_readiness(audit, tmp_path):
    report = audit.audit_local_sources(tmp_path)
    assert all(row['status'] == 'MISSING' for row in report['tv'])
    assert report['options']['report_files'] == 0
    assert report['ready_for_training'] is False


def test_invalid_csv_reports_diagnostic_without_raw_payload(audit, tmp_path):
    path = tmp_path / 'broken.csv'
    path.write_text('time,open\n"private unclosed string', encoding='utf-8')
    report = audit.profile_bars(path, time_column='time', step_seconds=300)
    assert report['status'] == 'UNREADABLE'
    assert 'private unclosed' not in json.dumps(report)


def test_missing_columns_do_not_count_as_valid_ohlcv(audit, tmp_path):
    path = tmp_path / 'partial.csv'
    path.write_text('time,close\n2026-08-01T10:00:00Z,10\n', encoding='utf-8')
    report = audit.profile_bars(path, time_column='time', step_seconds=300)
    assert set(report['missing_columns']) == {'open', 'high', 'low', 'volume'}
    assert report['invalid_ohlc_rows'] is None


def test_summary_does_not_hide_unassessed_months_as_zero_errors(audit, tmp_path):
    folder = tmp_path / 'chart-desk/data/duka/candles/XAUUSD'
    folder.mkdir(parents=True)
    (folder / 'BID_hour_202601.csv.gz').write_bytes(gzip.compress(
        b'ts,close\n2026-01-01T10:00:00Z,10\n'))
    summary = audit.compact_report(audit.audit_local_sources(tmp_path))
    assert summary['duka_hourly']['ohlc_assessed_files'] == 0
    assert summary['duka_hourly']['files_not_fully_assessed'] == 1


def test_simultaneous_calendar_events_are_not_called_duplicate_events(audit, tmp_path):
    path = tmp_path / 'calendar.json'
    path.write_text(json.dumps([{'date': '2026-08-01T10:00:00Z', 'title': 'A'},
                                {'date': '2026-08-01T10:00:00Z', 'title': 'B'}]), encoding='utf-8')
    report = audit.profile_calendar(path)
    assert report['event_times']['coincident_timestamp_rows'] == 1
    assert 'duplicate_rows' not in report['event_times']


def test_numeric_timestamp_requires_a_unit_contract(audit, tmp_path):
    path = csv_file(tmp_path, [1780000000, 1780000300])
    report = audit.profile_bars(path, time_column='time', step_seconds=300)
    assert report['time']['invalid_rows'] == 2
    assert report['time']['first'] is None


def test_cli_emits_json_and_does_not_write_into_source_folder(audit, tmp_path):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-B', audit.__file__, '--repos-root',
                             str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['ready_for_training'] is False
    assert list(tmp_path.iterdir()) == []


def test_nullable_parquet_fields_count_as_invalid_not_skipped(audit, tmp_path):
    path = csv_file(tmp_path, ['2026-08-01T10:00:00Z'])
    frame = pd.read_csv(path)
    for column in ['open', 'high', 'low', 'close', 'volume']:
        frame[column] = frame[column].astype('Float64')
    frame.loc[0, ['open', 'volume']] = pd.NA
    dest = tmp_path / 'nullable.parquet'
    frame.to_parquet(dest, index=False)
    report = audit.profile_bars(dest, time_column='time', step_seconds=300)
    assert report['invalid_ohlc_rows'] == 1
    assert report['invalid_volume_rows'] == 1
