# Correction source/as-of evidence

`trading_system.tree_replay.corrections` assesses caller-supplied correction
evidence at an explicit historical instant. It is a dependency of the approved
historical tree replay, not a historical level map, frame loader, feed resolver,
price-offset application, producer admission, outcome generator or dataset.
`ready_for_replay` and `ready_for_training` are always false.

## Source and audit

Pinned chart-desk commit: `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`.
`chartdesk/basis.py` Git blob: `f3396f3a9fefd71f0f71422001a5521af0a05cd2`.
The vendor module retains the complete `Correction` class (including its
presentation methods), `EXCHANGE_NATIVE`, and the original broker-shape
predicate. Only three predicate changes are authorized: rename it to
`broker_shape_ok_at`; require keyword-only `decision_time`; replace the one
`pd.Timestamp.now("UTC")` call with `pd.Timestamp(decision_time)`.
All remaining executable statements, docstrings, constants and branch order
match the pinned source.

Run these focused checks from the repository root:

```powershell
python -m pytest tests/tree_replay/test_correction_source.py tests/tree_replay/test_corrections.py -q --tb=short
python tools/check_correction_source_parity.py
```

CLI `--source-root` overrides `TR_CHARTDESK_SOURCE_ROOT`, then the retained default:
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`.
The tests use the same environment/default source fixture and fail if absent;
they never skip missing source. Source is read as text only. The auditor uses
independently fixed expectations, normalized Git blob bytes, exactly one
baseline chart-desk pin, strict JSON comparison (false differs from 0), and the
entire ordered vendor module AST. It verifies exactly one original clock call
before specializing. Extra imports, executable statements or rebound definitions
are rejected. Missing/invalid prerequisites and mismatches exit 2; verified
subset exits 0. Neither live source nor vendor code executes during auditing.
The adapter imports only the local pure vendor subset. Test mutations use
temporary copies and never change production pins or the retained source.

## Supplied evidence

```python
from datetime import datetime, timedelta, timezone
from trading_system.tree_replay.corrections import (
    CorrectionEvidence, assess_correction_asof,
)

t = datetime(2020, 2, 1, tzinfo=timezone.utc)
e = CorrectionEvidence(
    evidence_id="synthetic-e1", frame_id="synthetic-daily-1",
    instrument="OANDA:XAUUSD", version="synthetic-v1",
    observed_at=t - timedelta(days=1), available_at=t - timedelta(days=1),
    provenance="synthetic engineering fixture", offset=-12.0,
    source="tv_spliced", confidence="high", note="",
    tv_from=t - timedelta(days=20),
)
result = assess_correction_asof(
    e, instrument=e.instrument, frame_id=e.frame_id, decision_time=t,
    lookback_days=20, max_age_seconds=30 * 86400,
)
assert result["status"] == "ASSESSED"
assert result["broker_shape_ok"] is True
```

These are synthetic example policies, not freshness recommendations or permission
to access real data. Original level-map consumers use 20-day daily shape and
7-day PSY shape windows; callers must select explicit policy for their consumer.

Evidence is a frozen keyword-only dataclass. Non-note text must be nonempty and
trimmed; note accepts any string, including empty. Instruments are exact
`venue:symbol` identities. Source/confidence preserve vendor strings, including
`tv_daily`, `mt5_broker`, `tv_spliced`, `n/a` and future additions; the old source
comment is not an enum. Offset is a finite native int/float, including negative
or zero, never bool. Aware datetimes normalize to UTC with microseconds preserved;
naive/string/submicrosecond timestamps are rejected. Availability cannot precede
observation; a supplied TV seam cannot follow observation. Missing splice seam
is valid evidence and gives false shape for a non-native instrument.

Calls require matching instrument and frame_id, a validated decision timestamp,
finite native nonnegative lookback days, and a native nonnegative integer age
budget (zero is valid; bool is not). Structural validation precedes temporal
assessment and raises ValueError. Association is caller-attested metadata, not
proof that a frame was constructed from those bars or that provenance is genuine.
No aliases, case folding, feed inference or GC-to-OANDA mapping occur.

The pinned `basis.fetch_corrected` legacy replay hook constructs
`Correction(symbol, 0.0, 'replay', 'high', {'replay': True})`. Its source `replay`
does not qualify OANDA:XAUUSD for broker shape; exact native BINANCE:BTCUSDT
still qualifies through the native branch. This adapter does not reinterpret
`replay` as `tv_daily` and is not a loader for that legacy object: public evidence
requires an attested string note and rejects the hook's dictionary note.

## Assessment and hashing

Temporal blockers have this precedence:

1. None: `CORRECTION_MISSING`.
2. Observation after T: `CORRECTION_FUTURE_OBSERVATION`.
3. Availability after T: `CORRECTION_UNAVAILABLE`.
4. Elapsed observation age strictly exceeds the budget: `CORRECTION_STALE`.
5. Otherwise `ASSESSED` with null blocker, including unverified/false-shape evidence.

Blocked results have null evidence, unverified and broker_shape_ok. Their hash
cannot disclose changes to blocked evidence IDs, offsets or source payloads.
Assessed results include the complete canonical dataclass dictionary with UTC Z
timestamps. Original predicates remain independent: unverified means exactly
source `none` plus confidence `unknown`; pure broker sources qualify for shape,
as does exact native `BINANCE:BTCUSDT`. A non-native splice qualifies only when
the elapsed genuine span at T is at least the supplied lookback. Exactly 20 days
qualifies; one microsecond earlier does not. Offset cannot repair proxy shape.
Native BTC with `none`/`n/a` has true shape and false unverified; `none`/`unknown`
has both flags true. These flags are observations, not source-level admission.

Every result includes schema `correction-asof-v1`, calculation version
`chartdesk-correction-asof-v1`, identity, decision time, explicit policies, status,
blocker, evidence, quality flags, SHA256 evidence_hash, and both false readiness
flags. The digest covers the complete result except evidence_hash, serialized
with sorted keys, compact JSON separators and allow_nan=False. Native numbers
handled by `_number` normalize to float; timestamps use `isoformat()` with Z.
No hidden wall clock, input mutation, offset application, automatic data fetching,
live alert changes, labels, training or promotion is included. Full historical
map construction and each downstream consumer's asymmetric gates remain later work.
