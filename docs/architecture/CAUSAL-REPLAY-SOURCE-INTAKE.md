# Causal replay source intake

This is a static, source-pinned intake for the outer `market_watch.py::main()`
pass. It reads and parses only the retained `chart-desk` checkout supplied as
`--source-root/chart-desk`; it never imports, compiles, or executes retained
source.

The required identity is chart-desk commit
`68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and
`scripts/market_watch.py` blob
`f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b`.

The audit proves this source order in `main()`:

1. watch state load (line 494);
2. pre-producer watch-state write (line 905);
3. locked `closeout_check() + check()` (line 964), followed by tracker gate
   (line 972);
4. `level_reversal.find` (line 1014), ahead of tree walking and engine builds;
5. source outer-gate sequence before the level-reversal `tracker.record`, with
   `--telegram` as its enclosing guard; and
6. final watch-state write (line 1599).

Windows, market-closed, producer-arbitration, post-stop, occupied-slot, and
same-level checks are deliberately projected as `UNWIRED_OUTER_ADMISSION`.
They are not replay booleans and this audit does not implement them.

```powershell
python -B -m pytest tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider
python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

The checker emits JSON only. `VERIFIED` exits 0; every missing, malformed,
identity, parsing, projection, or report-shape failure exits 2 as `BLOCKED`.
Both `ready_for_replay` and `ready_for_training` are always false.

This is not a replay runner, tracker registration, persistence/delivery path,
market-data archive, economics/fill/P&L contract, dataset, training, model, or
live-trading approval.
