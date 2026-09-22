"""Original admission frame reads from explicit causal evidence, never live I/O.

Requested lookback is an identity, not a delivered-history minimum. The matrix
retains source correction handling and known forming target rows. This provider
does not implement state/quote/log ports, admit trades or certify full replay.
"""
from dataclasses import dataclass
from datetime import datetime

from .bars import _utc, _validate_identity
from .corrections import CorrectionEvidence
from .frames import FrameSpec
from .levelmap import _DataUnavailable, _OfflineSource
from .pricing import SUPPORTED_INSTRUMENTS
from ._vendor import admission_matrix as matrix


_REQUEST_KEYS = frozenset({("4h", 240), ("1h", 240), ("30m", 90),
                           ("15m", 55), ("5m", 55), ("15m", 5), ("15m", 3)})


@dataclass(frozen=True, kw_only=True)
class AdmissionFrameRequest:
    timeframe: str
    lookback_days: int
    frame: FrameSpec
    correction: CorrectionEvidence | None
    max_correction_age_seconds: int

    def __post_init__(self):
        if (type(self.timeframe) is not str or type(self.lookback_days) is not int
                or (self.timeframe, self.lookback_days) not in _REQUEST_KEYS):
            raise ValueError("unsupported original admission timeframe/lookback pair")
        if type(self.frame) is not FrameSpec or self.frame.timeframe != self.timeframe:
            raise ValueError("frame must be an exact matching FrameSpec")
        if (type(self.max_correction_age_seconds) is not int
                or self.max_correction_age_seconds < 0):
            raise ValueError("correction age must be a native nonnegative integer")
        if self.correction is not None:
            if type(self.correction) is not CorrectionEvidence:
                raise ValueError("correction must be exact CorrectionEvidence or None")
            if (self.correction.instrument != self.frame.instrument
                    or self.correction.frame_id != self.frame.frame_id):
                raise ValueError("correction must match exact frame identity and instrument")


class AdmissionFrameSource(_OfflineSource):
    """Per-decision frame ports; traces remain visible through source catches."""

    def __init__(self, *, instrument: str, decision_time: datetime,
                 requests: tuple[AdmissionFrameRequest, ...]):
        _validate_identity(instrument, "5m")
        if instrument not in SUPPORTED_INSTRUMENTS:
            raise ValueError("unsupported exact producer instrument")
        decision = _utc(decision_time, "decision_time")
        if type(requests) is not tuple or any(type(r) is not AdmissionFrameRequest for r in requests):
            raise ValueError("requests must be a tuple of exact AdmissionFrameRequest objects")
        for req in requests:
            req.__post_init__()
            if req.frame.instrument != instrument:
                raise ValueError("all frames must match the exact provider instrument")
        if len({(r.timeframe, r.lookback_days) for r in requests}) != len(requests):
            raise ValueError("duplicate admission request keys")
        if len({r.frame.frame_id for r in requests}) != len(requests):
            raise ValueError("duplicate admission frame IDs")
        super().__init__(instrument, decision, requests, closed_base_prefix=True)
        self.matrix_trace = []

    def fetch_corrected(self, symbol, timeframe, lookback_days):
        # The inherited fetch validates symbol before its trace starts. Preserve
        # evidence of unexpected caller bindings too, even if tracker catches it.
        blocker = None
        if type(symbol) is not str or symbol != self.instrument:
            blocker = "INSTRUMENT_MISMATCH"
        elif (type(timeframe) is not str or type(lookback_days) is not int
              or (timeframe, lookback_days) not in _REQUEST_KEYS):
            blocker = "REQUEST_UNSUPPORTED"
        if blocker:
            self.fetch_trace.append(dict(timeframe=timeframe, lookback_days=lookback_days,
                frame_id=None, status="BLOCKED", blocker=blocker, policies=None,
                frame=None, correction=None))
            raise ValueError(blocker)
        return super().fetch_corrected(symbol, timeframe, lookback_days)

    def read_symbol(self, symbol, tfs=("4h", "1h", "15m", "5m")):
        return {tf: self._read_tf(symbol, tf) for tf in tfs}

    def _read_tf(self, symbol, tf):
        trace = dict(timeframe=tf, fetch_index=len(self.fetch_trace), status="BLOCKED",
                     blocker=None, exception_type=None)
        self.matrix_trace.append(trace)
        try:
            frame, corr = self.fetch_corrected(symbol, tf, matrix.LOOKBACK[tf])
            note = corr.render() if corr.show else None
            result = matrix.read_frame(frame, tf, note)
        except Exception as exc:
            trace["blocker"] = (str(exc) if isinstance(exc, _DataUnavailable)
                                else "MATRIX_CALCULATION_ERROR")
            trace["exception_type"] = type(exc).__name__
            raise
        trace["status"] = "AVAILABLE"
        return result
