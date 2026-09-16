# Actual tree / matrix pending revalidation

Status: accepted after task/final reviews and full binding source audit;
see agent-exchange/status/2026-09-10T200014Z-codex-tree-revalidation-binding.md.
Not a historical-feed, economic outcome or training gate.

```python
from trading_system.tree_replay.tree_revalidation import TreeRevalidation

checks = TreeRevalidation(raw_source)  # inert: no IO or clock reads
ok, reason, verified = checks.revalidate_pending(pending_trade, now=decision_epoch)
```

`raw_source` must supply the raw frame/correction, artifact, clock and shadow
writer operations documented in TREE-REVALIDATION-BINDING-CONTRACT.md. There is
no default network/filesystem loader. Shadow writes happen only through the
supplied writer. All readers share this provider, without caching operation
times or replacing calculated decisions with a provider verdict.

The facade composes the actual MatrixReader, TreeReader and original
Revalidation, inheriting the original lazy broker-shape gate through
BasisOperation. Existing source modules and fixed-time public adapters are
unchanged. `read_symbol(symbol, tfs=...)` retains original timeframe order,
LOOKBACK request identity and the entire delivered frame; LOOKBACK is not a
row-trimming instruction. `still_valid(trade)` exposes the original precheck.

Pending checks run `still_valid` first. An early veto skips age/tree checks.
Only after that does omitted `now` read the provider clock. Under two hours
skips the tree; exactly two hours consults it. The call retains the original
house variant even if unrelated pending metadata says strict. It does not
build a new Plan or simulate entry. An opposite tree direction takes priority
over a later tree stop. A stopped/unavailable same-side tree allows only an
unverified result. A clean tree cannot upgrade earlier unavailable evidence.
Do not collapse `(ok, reason, verified)` to a binary success/failure label.

Runtime verification (counts overlap component suites):

```text
python -B -m pytest tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_revalidation.py tests/tree_replay/test_admission_frames.py -q --tb=short -p no:cacheprovider
240 passed in 19.87s, exit0; includes27 binding cases.
```

Raw multiframe fixtures exercise actual numerical readers, tree stages, missing
data/news/map, higher-bias veto, source shape clocks, deep-file fallback and
shadow effects. A hand-derived ATR history case rejects a local
tail(LOOKBACK) mutant: history older than the requested row count still affects
the actual output. No original live repository module is imported or executed.

Full binding audit and task/final reviews passed. Remaining: causal artifact/provider operation
scheduling; original market-watch caller, arbitration and generated lifecycle;
other producers and all simulator/dataset/model/evaluation gates. The GC versus
OANDA source variant remains a real-data decision, not an automatic alias.
