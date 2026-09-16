# Task1: Complete original reader and state

Create trading_system/tree_replay/_vendor/ema_windows.py,
tests/tree_replay/test_ema_windows.py, docs/architecture/EMA-DEEP-READER-USAGE.md.
Consumes actual indicators.ema plus supplied correctedframes and CSVbytes.
Produces Window/EmaState/_atr/_read_with_deep and EmaReader(source).read(symbol,
timeframe,lookback=None)/read_stack(symbol,timeframes=('4h','1h','15m','5m')).

- [ ] Write normal missingmoduleRED tests before runtime:
  ```python
  def api():
      name='trading_system.tree_replay._vendor.ema_windows'
      assert importlib.util.find_spec(name) is not None, 'EMA reader missing'
      return importlib.import_module(name)
  s=api().EmaReader(ports).read('OANDA:XAUUSD','1h')
  assert s.atr==2. and s.close==1699. and s.unconverged==[]
  assert s.window(800).value==pytest.approx(1299.5,abs=1e-10)
  assert s.window(800).slope_atr==pytest.approx(1.5,abs=1e-10)
  ```
  Ports contain real1600 ascending closes100..1699 with H=C+1/L=C-1; capture
  exact fetch request and deep path requests. No finishedWindow replacement.
  Literal tests for1599vs1600 convergence, shortlive with sufficient prehistory,
  constantflat windows, zeroATR/missing slope, unseededATR and varying volatility.
  With1500constantdeep100 and100live closes100..199, fastEMA50 uses live only
  (174.5); EMA800 closed-form oracle is199-399.5*(1-(799/801)**99), independently
  derived from recursion. Deep overlap/futurelargevalues must not replace live.
  Test exact strict-prefix boundary; differing live ranges prove windowATRlive,
  shortlive+deep differing ranges prove slope spanATR can include deep.
  Test all5 source-symbol filename mappings, bareunknown skips deep_exists;
  knownsymbol5m probes deep/XAUUSD_.csv; mapped1h deep/XAUUSD_H1.csv. Preserve
  lookback0=>default, explicitvalue, daily2200/other2000, same ordered duplicates.
  Actual pd.read_csv over bytes handles validCSV, empty/malformed/timeparseerror;
  exists/read exceptions fall back, correctedfetch exception propagates and
  read_stack omits only that frame. Missingcorr source'', unverifiedcorr still
  evaluated. Long live history still makes optional deep IO; unknown typed
  deep values must not be silently accepted as certified provenance.
  Add full property tests driven by generatedwindows where possible: strict/
  loose trend zero/asymmetry/unknown; partial stacklabel; cascade/deepestlost/
  signedgap; glued5vs7; nearestopen tie stableorder; magnitudeweighted agreement,
  median strength and coverageNonevszero; original rendering of missingEMAs.
- [x] Run `python -B -m pytest tests/tree_replay/test_ema_windows.py -q --tb=short -p no:cacheprovider`; observe normalmissingmodule failures.
- [x] Inertly extract fullsource symbols and MT5_SYMBOL_MAP, then exact6adaptations
  from spec. Imports/class layout as spec; no source read code executed.
  ```python
  class EmaReader:
      def __init__(self, source):
          self.source=source
  # pd.read_csv(_dp) => pd.read_csv(BytesIO(self.source.deep_bytes(_dp.as_posix())))
  # _dp.exists() => self.source.deep_exists(_dp.as_posix())
  ```
  Original parsing/stateproperties/try boundaries untouched. _read_with_deep
  remains actual pure function, independent _atr remains original, no extraIO.
- [ ] Run focusedGREEN plus tests/tree_replay/test_ema.py and test_stretch.py;
  document actualports, files/deepseam limits, slope3vsold5 and rawunknown states.
  Package full3files; independent spec/qualityreview; fix real findings with tests.

## Global constraints

- Approved existing feature checkout; main inline criticalpath, independent
  review sidecars with no nested agents. Preserve unrelated work; apply_patch.
- Exact chart-desk commit68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9,
  emawin.py e4ce74f49973ce7aeea8e33ec1c64ea86e8181e8 and
  basis.py f3396f3a9fefd71f0f71422001a5521af0a05cd2.
- No originalsource execution, realdata acquisition/labels/training/live IO,
  commits/pushes/cleanup. PurePosixPath is logical; no filesystem exists/read.
- Do not change existing ema_snapshot or normalize source behavior/thresholds.
- Raw supplied inputs are not causal or seam certification. Full master stays.
