# Docstring fidelity fix

Both current strings now retain original literal values. No calculation, signature, exception or port changes. Original full diff task-1-diff.md plus this supplement is complete.
diff --git a/trading_system/tree_replay/_vendor/basis_operation.py b/trading_system/tree_replay/_vendor/basis_operation.py
--- a/trading_system/tree_replay/_vendor/basis_operation.py
+++ b/trading_system/tree_replay/_vendor/basis_operation.py
@@
-        """May a RANGE object looking `days` back trust this frame's shape?
-
-        A constant offset shifts a level but never fixes a range, so range-shaped
-        objects (ADR, RD, psy levels, session ranges, yesterday's extremes) need
-        bars that are genuinely his. Pure broker sources qualify outright; a
-        spliced frame qualifies only when its genuine-TV span reaches back at
-        least `days` -- the window being measured must lie entirely on the TV side
-        of the seam.
-        """
+        "May a RANGE object looking `days` back trust this frame's shape?\n\n    A constant offset shifts a level but never fixes a range, so range-shaped\n    objects (ADR, RD, psy levels, session ranges, yesterday's extremes) need\n    bars that are genuinely his. Pure broker sources qualify outright; a\n    spliced frame qualifies only when its genuine-TV span reaches back at\n    least `days` -- the window being measured must lie entirely on the TV side\n    of the seam.\n    "
diff --git a/trading_system/tree_replay/_vendor/levelmap_operation.py b/trading_system/tree_replay/_vendor/levelmap_operation.py
--- a/trading_system/tree_replay/_vendor/levelmap_operation.py
+++ b/trading_system/tree_replay/_vendor/levelmap_operation.py
@@
-        """LONDON-OPEN / NY-OPEN — the price the session actually opened at.
-
-        04.09 is the case that earned these. Gold's day open sat at 4,476.07 and
-        London opened at 4,462.92 -- thirteen points BELOW it, onto the
-        EMA200-1h/D3-HI/CLOUD50-4h cluster -- and price left that open for
-        4,490.9. The map had no name for where the session began, so the desk
-        could describe the cluster and not the arrival.
-
-        EXACT BAR OR NOTHING. The level is one bar's open price, so the nearest
-        bar is a different number wearing this one's name; a missing bar is
-        reported and the level is omitted. Live from the moment the opening bar
-        exists (a forming bar's open is already final) until the session closes,
-        and never carried into the next day -- yesterday's London open is a fact
-        about yesterday.
-        """
+        "LONDON-OPEN / NY-OPEN — the price the session actually opened at.\n\n    04.09 is the case that earned these. Gold's day open sat at 4,476.07 and\n    London opened at 4,462.92 -- thirteen points BELOW it, onto the\n    EMA200-1h/D3-HI/CLOUD50-4h cluster -- and price left that open for\n    4,490.9. The map had no name for where the session began, so the desk\n    could describe the cluster and not the arrival.\n\n    EXACT BAR OR NOTHING. The level is one bar's open price, so the nearest\n    bar is a different number wearing this one's name; a missing bar is\n    reported and the level is omitted. Live from the moment the opening bar\n    exists (a forming bar's open is already final) until the session closes,\n    and never carried into the next day -- yesterday's London open is a fact\n    about yesterday.\n    "
