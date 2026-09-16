"""Private original tracker lock policy; caller supplies IO and time ports."""
from __future__ import annotations
from contextlib import contextmanager

LOCK_TIMEOUT_S = 30.0
RESOLVE_LOCK_WAIT_S = 3.0
LOCK_STALL_S = 120.0

class LockBusy(RuntimeError):
    """The tracker lock is held elsewhere and the caller chose not to wait."""


class TrackerLock:
    def __init__(self, source):
        self.source = source
        self.held = {"depth": 0}

    def _busy_for(self) -> float:
        """Seconds the lock has been continuously refused to skippers."""
        try:
            return self.source.now_epoch() - float(self.source.read_busy())
        except Exception:
            try:
                self.source.write_busy(str(self.source.now_epoch()))
            except Exception:
                pass
            return 0.0

    @contextmanager
    def locked(self, *, wait: float | None = None, skip_if_busy: bool = False):
        """Hold the tracker lock across a read-modify-write of the state file.

    THE BUG THIS FIXES, found 2026-08-27. Two different gold shorts went out in
    the same second (4,609.65 and 4,625.00) and only ONE survived in
    open_trades.json. record() was called from market_watch OUTSIDE the lock,
    while trade_live.py -- running every 60 seconds -- holds that same lock for
    its own load/modify/save. A record written between trade_live's load and
    its save is erased by that save, silently. The trade then existed in the
    channel and nowhere in the tracker: no fill report, no stop report, and no
    row in the record the whole measurement depends on.

    Every state mutation now goes through here, so load and save are one
    atomic section rather than two independent ones.

    `wait` bounds the poll (default LOCK_TIMEOUT_S). After it, a writer
    proceeds unlocked; with `skip_if_busy` the caller gets LockBusy instead
    and does nothing this pass -- the resolvers' choice, see
    RESOLVE_LOCK_WAIT_S.
    """
        if wait is None:
            wait = RESOLVE_LOCK_WAIT_S if skip_if_busy else LOCK_TIMEOUT_S
        if self.held["depth"] > 0:          # already ours — do not re-acquire
            self.held["depth"] += 1
            try:
                yield
            finally:
                self.held["depth"] -= 1
            return
        self.source.ensure_lock_directory()
        # Append mode avoids truncating the one-byte Windows lock region while
        # another process owns it. POSIX flock did not expose that portability bug.
        f = self.source.open_lock()
        got = False
        try:
            # BOUNDED wait, not LOCK_EX. The first version blocked indefinitely and
            # deadlocked immediately: trade_live.py holds this lock every 60
            # seconds, so anything else taking it could wait forever -- the test
            # suite hung, and in production it would have stalled a whole
            # market_watch pass behind a 60-second job.
            #
            # Failing OPEN after the timeout is the right trade for a WRITER. The
            # lock prevents a lost write, which is rare; blocking forever prevents
            # every trade from being recorded, which is total. A rare lost record
            # beats a stalled desk, and the sentry's "sent but not tracked" check
            # is what catches the rare case. A resolver is the opposite case and
            # skips instead (RESOLVE_LOCK_WAIT_S).
            got = self.source.try_acquire(f, timeout=wait)
            if got:
                try:
                    self.source.clear_busy()
                except Exception:
                    pass
            elif skip_if_busy:
                stuck = self._busy_for()
                if stuck < LOCK_STALL_S:
                    raise LockBusy(f"tracker lock held elsewhere for {wait:.0f}s")
                self.source.warn(f"[tracker] lock refused for {stuck:.0f}s -- treating the "
                                 "holder as hung and proceeding unlocked")
            self.held["depth"] += 1
            yield
        finally:
            self.held["depth"] = max(0, self.held["depth"] - 1)
            try:
                if got:
                    self.source.release(f)
            finally:
                f.close()
