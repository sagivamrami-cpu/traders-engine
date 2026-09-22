# Lifecycle closed-bar PENDING source intake

Authority is retained chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, tracker blob
`b616b34022e436545d8c1daf85eced51614fd74e`, read as text only. This intake
covers `tracker.py::check()` lines 1119–1264, only while a selected record is
`PENDING`.

The caller first obtains a corrected 15-minute frame for exactly three days,
rejecting unverified or `tv_stale` corrections and per-record read failures.
It forms `since` from bars strictly after the trade timestamp. The source uses
the aggregate `since` high/low only to decide entry/stop and pending expiry;
post-fill extrema are a different later calculation.

For PENDING, a long touches entry at `low <= zone_high`; a short at
`high >= zone_low`. If the plan is expired and entry was not touched, source
marks it CANCELLED, calculates missed movement in R from the first post-send
open to the directional aggregate extreme, writes raw `expired` fact with
rounded `missed_r`/`missed_points`, shelves the record, emits one expiry
message, and continues.

On entry touch, source first prevents a same-symbol/same-direction OPEN slot,
then revalidates with the pass clock. Each failure marks CANCELLED, emits the
source cancellation and writes its raw tracker fact. A successful revalidation
sets OPEN, records verification fields, sets `filled_ts` and `progress_ts`
from the source clock, and marks changed. If aggregate since-send bars also
touch stop, source conservatively marks STOPPED, records
`stopped_ambiguous`, emits its stop/ambiguity message and continues. Otherwise
it emits the fill notice and falls through to the later OPEN branch.

This does not yet define corrected-bar acquisition, OPEN progression,
persistence/gating, economics, replay or a dataset/training label. Shelf and
outcome writes are raw lifecycle facts, not realised P&L.
