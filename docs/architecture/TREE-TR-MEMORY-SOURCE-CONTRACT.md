# Original TR vector memory and daily pivots

Continuation of approved master C/D. This implements source dependencies of
fulltree/Brinks/checklists, not a new signal. Full intake FULL-TREE-WALK-SOURCE-
INTAKE.md records main's complete source read. Existing feature checkout;
main inline implementation, independent review sidecars, no commits/cleanup.

Authority chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
chartdesk/tr.py8297c712d20404880d4d8949e96efbf48613909c. Read/ASTparse only.
Private runtime trading_system/tree_replay/_vendor/tree_tr.py contains pandas
import, from .pvsra import pvsra, then vector_zones and daily_pivots in source
order. Both retain complete source bodies/docstrings/annotations. The one
specialization is the default non-auction vector path, as already used by the
accepted PVSRA dependency. No customauction/seasonality support is claimed.

## Projection and interfaces

Original vector_zones(df,pv=None,*,zone_from='body',cleared_by='wick',
max_zones=500,auction=False,session_tz=A.DEFAULT_TZ) has the two final keyword
parameters removed and exactly one call
`pvsra(df,auction=auction,session_tz=session_tz)` replaced by `pvsra(df)`.
Auditor checks the exact complete original signature before specialization,
including annotations/defaults and no decorators. No other executable statement
changes. daily_pivots(daily,include_m=True) is copied unchanged.

Default PVSRA is the actual accepted dependency; optional supplied pv parameter
keeps its original meaning. Do not replace the entire vector_zones calculation
by provider-supplied final zones. No hidden globals/defaultclock/physical IO.

## Required behavior

Vector zones first inspect pv.available.iloc[0] (not last); false/missing gives
empty columns top,bottom,kind,open,touches,time. A supplied empty available
Series can raise; do not sanitize rawsource inputs or invent availability.
Only climax rows createzones (rising alone does not). Last max_zones index slice
retained exactly, including source0/negative behavior. Body high/low or fullwick
as selected; clearing wick or body as selected. Aftermask is df.index>zone time,
not rownumber. Zone remains open until price departs entirely then overlaps;
initial continuous overlap is not a return. Boundary contact overlaps inclusive.
Every overlapping laterbar after firstdeparture counts, not only entries from
outside. Lastrow climax remains open with0touches. Nonempty output indexed time;
empty output retains the source empty time column. Delivered order/duplicates
are not globally normalized. Raw exceptions remain visible.

Daily pivots use penultimate supplied row, need>=2rows, do not resample daily
or inferclosedness. PP/R1/R2/R3/S1/S2/S3 original formulas and insertionorder;
include_m adds six adjacent midpoints M0..M5. No instrumentalias or unitconversion.

## Evidence and acceptance

Task1 tests literal hand-derived zone states, top/bottom/touches and pivots;
exercise both suppliedpv and actual PVSRA composition. Require normalmissing-
moduleRED, passing GREEN and independent review. Task2 fullordered projection,
literalcommit/blob/root/baseline audit plus real inherited PVSRA audit. Candidate,
dependency, sourceidentity/order/substitution/signature drift blocks; no original
or runtime imports by auditor. CLI explicitparentroot JSON VERIFIED0/BLOCKED2;
always ready_for_replay=False and ready_for_training=False.

No causalframe/feature certification: original functions consume raw delivered
rows. Fulltree must retain its own[-1]/[-2] conventions and subsequent causal
provider evidence. No labels/dataacquisition/models/liveactions. Fullmaster and
human gates remain unchanged. Task/final reviews required before acceptance.
