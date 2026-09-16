# Complete original EMA windows and optional deep-history reader

Continuation of approved master C/D revalidation closure. No replacement model,
source threshold or feed permission; no modification of existing ema_snapshot.

## Authority and approach

chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
emawin.py e4ce74f49973ce7aeea8e33ec1c64ea86e8181e8;
basis.py f3396f3a9fefd71f0f71422001a5521af0a05cd2.
Read the whole emawin.py module and exact
MT5_SYMBOL_MAP assignment. Retained source is read/parsed, never executed.

Reusing ema_snapshot would omit EMA7, full slope/cascade/window semantics and
deep prehistory. Supplying finished Window/EmaState objects would skip actual
calculations. Chosen: complete original module projected over explicit offline
frame/CSV byte ports; original classes and real seededEMA calculations retained.
Physical TV_DIR location becomes a logical root only; filename rules stay exact.

## Private runtime

Create _vendor/ema_windows.py with imports: future annotations, dataclass/field,
pandas as pd, BytesIO from io, PurePosixPath from pathlib, .indicators as I.
Copy MT5_SYMBOL_MAP from basis.py before all original constants. Preserve full
LENGTHS/FAST/SLOW/OPEN_ATR/GLUED_ATR/SLOPE_BARS, Window, EmaState, _atr and
_read_with_deep in their relative order. Full class bodies/annotations remain.
EmaReader(source) stores self.source; methods read and read_stack retain source
relative order and signatures with self prepended.

Exact read changes, all once per expression:

- basis.fetch_corrected(symbol,timeframe,lookback) -> source equivalent.
- basis.TV_DIR -> PurePosixPath('.') (logical only, no filesystem access).
- basis.MT5_SYMBOL_MAP.get(symbol,'') -> MT5_SYMBOL_MAP.get(symbol,'').
- _dp.exists() -> self.source.deep_exists(_dp.as_posix()).
- pd.read_csv(_dp) -> pd.read_csv(BytesIO(self.source.deep_bytes(_dp.as_posix()))).
- read_stack's read(symbol,tf) -> self.read(symbol,tf).

Keep path composition, leading-underscore short circuit, byte decoding/CSV
parsing and time conversion/sort, all exception boundaries, return fields and
numerical behavior. The _read_with_deep call remains actual module function.
Do not import basis/tr/live source or substitute another ATR implementation.

Ports: fetch_corrected(symbol,timeframe,lookback)->(df,correction),
deep_exists(logical_path)->bool, deep_bytes(logical_path)->bytes. They supply
captured offline evidence; unknown/exceptions may trigger original fallback
but must remain distinguishable in the future causal provider trace. No default
filesystem/network loader. These ports do not certify causal availability.
Both deep operations use exact `deep/<stem>_<suffix>.csv` identity. No alias
before map lookup; preserve known symbol+unknown timeframe underscore filename.

## Calculation contracts

Defaultlookback:1d2200,else2000; explicit nonzero overrides pass unchanged,
including source truthiness. Fetch outside deep try; errors propagate from read
and are per-timeframe omissions in read_stack. Reads repeat for duplicate TFs.
Deep optional failures do not replace live read; source tag corr.source or''.
No new correction veto. CSV parse remains pandas default over supplied bytes.

Only len(live)<2*n permits a deep prefix for that EMA, with deep.index strictly
before firstlive timestamp. If prefix exists, concatenate, keep-last duplicate
indices, sort. Live endpoints win and newer deep rows cannot override them.
No source row trimming or global duplicate normalization outside splice branch.
Each EMA requires2*n and nonNaN terminal value. Full LENGTHS=(5,7,13,50,200,800).
Window close/distance/ATR come from live. Slope is3barEMAchange divided by ATR
on src.tail(20) if len(src)>20, else liveATR. A deep prefix can therefore affect
slope's ATR for short live histories; not silently described as wholly live-only.
All Window/EmaState properties remain: strict/loose trend asymmetry, unknown
coverage, lost/cascade, nearest open window, weighted slope agreement, median
strength, coverage, glued(5vs7), stack labels and full rendering.

Raw input validity/NaN/infinity/zeroATR behaviors remain original. Neither this
runtime nor a valid window certifies an EMA historical feature for training.
Deep GC-to-spot seam provenance is not approved by reuse of this code. It must
not supply ADR/range data. Public existing ema_snapshot remains independent.

## Verification and gates

Tests must drive actual read/read_stack/CSV/_read_with_deep, not just hand-built
Window lists. Numeric oracle:1600 ascending closes100..1699 with high=C+1 and
low=C-1 produce ATR2, EMA8001299.5, distance399.5, slope1.5; every EMA converges.
At1599,800 is unconverged without deep. Explicit shortlive+constantdeep fixtures
verify fast live-only versus slow splice, strict prefix, live endpoint/ATR,
2*n boundaries and unseeded ATR. Test nonconstant volatility to distinguish
src.tail(20) slope divisor from terminal/full-history ATR.
CSV names for mapped/unmapped/unknown timeframe; byteparse/timeparse failures,
exists errors and read errors keep original catches; fetch errors propagate.
No native filesystem/network calls. Deepread still attempted with long live
history; malformed deep calculations may throw after successful parse, as source.
Full property/rendering edge matrix supplements actual generated-window tests.

Independent audit: literalHEAD/root/baseline/bothblobs, wholeordered candidateAST,
exact substitution counts, real strictEMA dependency audit. Mutationtests cover
lengths/convergence/ATR/slope/deep prefix/live overwrite/CSV/paths/router/property/
exception/signature drift. CLI explicit parentroot, VERIFIED0/BLOCKED2, false
replay/training readiness, no importing/executing source or runtime by auditor.
Task/final reviews before acceptance; no whole-loop certification inferred.

Then complete calendar/tree/shadow revalidation, causal input binding and full
resolver/caller; other producers/economic simulator/dataset/models remain required.
