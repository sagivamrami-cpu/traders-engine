"""Actual tree and matrix -> original pending checks; raw ports, not causal proof."""
from ._vendor.basis_operation import BasisOperation
from ._vendor.matrix_reader import MatrixReader
from ._vendor.revalidation import Revalidation
from ._vendor.tree_walk import TreeReader


class TreeRevalidation(BasisOperation):
    """Bind real calculated readers; the provider supplies only raw IO and clocks."""

    def __init__(self, source):
        super().__init__(source)
        self.matrix = MatrixReader(source)
        self.tree = TreeReader(source)
        self.checks = Revalidation(self)

    def read_symbol(self, symbol, tfs=('4h', '1h', '15m', '5m')):
        return self.matrix.read_symbol(symbol, tfs=tfs)

    def tree_walk(self, symbol):
        return self.tree.walk(symbol)

    def still_valid(self, t):
        return self.checks.still_valid(t)

    def revalidate_pending(self, t, *, now=None):
        return self.checks.revalidate_pending(t, now=now)

    def now_epoch(self):
        return self.source.now_epoch()

    def now_timestamp(self, *, tz):
        return self.source.now_timestamp(tz=tz)

    def deep_exists(self, key):
        return self.source.deep_exists(key)

    def deep_bytes(self, key):
        return self.source.deep_bytes(key)

    def calendar_exists(self, path):
        return self.source.calendar_exists(path)

    def calendar_text(self, path):
        return self.source.calendar_text(path)

    def ensure_shadow_parent(self, *, parents, exist_ok):
        return self.source.ensure_shadow_parent(parents=parents, exist_ok=exist_ok)

    def shadow_open(self, mode, encoding):
        return self.source.shadow_open(mode, encoding)
