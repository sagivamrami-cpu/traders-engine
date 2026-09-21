# Sagiv Databento Order Flow Download

## Scope

Roee approved retrieval for local research only of Databento `GLBX.MDP3`
continuous front-month `GC.v.0`, from 2026-09-16T00:00:00Z through
2026-09-16T20:15:00Z. CME GC remains cross-market Order Flow context; it is
not an XAUUSD price or execution source.

## Retrieved Local Artifacts

All files are git-ignored under `market-data/sagiv-databento-orderflow/2026-09-16/`:

- `gc-v0-trades-2026-09-16.dbn.zst` (3,004,473 bytes)
- `gc-v0-mbp-10-2026-09-16.dbn.zst` (220,194,184 bytes)
- `gc-v0-mbo-2026-09-16.dbn.zst` (208,548,721 bytes)

Each DBN metadata block validates `GLBX.MDP3`, `GC.v.0`, its expected schema,
and empty `partial` and `not_found` lists. The exact-range cost estimate was
USD 0.00 for each schema. No purchase was made.

## Initial Point-in-Time Findings

Israel was UTC+3 on the research date. The two profitable XAUUSD short baskets
at 21:50:31--21:50:52 and 21:50:53--21:51:31 map to 18:50:31--18:50:52Z and
18:50:53--18:51:31Z. GC price declined 4336.0 to 4330.9 with ask-minus-bid
trade delta +39 in the first basket, then 4329.3 to 4322.5 with delta +26 in
the second. This is consistent with possible sell-side absorption, not proof
of a particular hidden participant or iceberg.

The adverse XAUUSD long episode beginning 18:31:35Z had GC trade delta +1,159
while price declined from 4350.1 to 4326.9 over the episode. It is evidence
that net ask-side aggression alone did not produce upward price progress in
this GC context; it does not establish causation for XAUUSD fills.

`MBO` now enables an order-lifecycle reconstruction. Do not label iceberg,
replenishment, or hidden liquidity as confirmed until a causal detector tracks
individual order add/modify/cancel/fill sequences and validates candidates on
additional dates.

## Verification

`python tools/validate_databento_gc_contract_stype_decision.py --decision configs/data/databento-gc-contract-stype-decision.yaml` passed.
An offline DBN validation opened all three files, verified schema, source
symbol, and complete coverage metadata.
