"""Changed-only lifecycle persistence over supplied offline tracker effects."""
from __future__ import annotations

from ._vendor.lifecycle_gate import LifecycleGate
from ._vendor.tracker_lock import LockBusy


class TrackerLifecycleCaller:
    """Compose source mutation kernels with the accepted gate and lock policies."""

    def __init__(self, source):
        self.source = source
        self.gate = LifecycleGate(source)

    def _run(self, resolve):
        state = self.source.load()
        if not state:
            return []
        out, changed = self._result(resolve(state))
        if not changed:
            return out
        return self._commit(out, state)

    @staticmethod
    def _result(result):
        if not isinstance(result, tuple) or len(result) != 2:
            raise TypeError("resolver must return (list[tuple[str, bool]], bool)")
        out, changed = result
        if not isinstance(out, list) or not isinstance(changed, bool):
            raise TypeError("resolver must return (list[tuple[str, bool]], bool)")
        if any(not isinstance(message, tuple) or len(message) != 2
               or not isinstance(message[0], str) or not isinstance(message[1], bool)
               for message in out):
            raise TypeError("resolver must return (list[tuple[str, bool]], bool)")
        return out, changed

    def _commit(self, out, state):
        out = self.gate._persist_gated_lifecycle(out, state)
        self.source.save(state)
        return out

    def check(self, resolve):
        return self._run(resolve)

    def _check_live_locked(self, resolve):
        return self._run(resolve)

    def check_live(self, resolve):
        try:
            with self.source.locked(skip_if_busy=True):
                return self._check_live_locked(resolve)
        except LockBusy:
            return []
