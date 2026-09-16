from __future__ import annotations
from . import admission_matrix as matrix
from .admission_matrix import TFView

class MatrixReader:

    def __init__(self, source):
        self.source = source

    def read_tf(self, symbol: str, tf: str) -> TFView:
        df, corr = self.source.fetch_corrected(symbol, tf, matrix.LOOKBACK[tf])
        note = corr.render() if corr.show else None
        return matrix.read_frame(df, tf, note)

    def read_symbol(self, symbol: str, tfs: tuple[str, ...]=('4h', '1h', '15m', '5m')) -> dict[str, TFView]:
        return {tf: self.read_tf(symbol, tf) for tf in tfs}
