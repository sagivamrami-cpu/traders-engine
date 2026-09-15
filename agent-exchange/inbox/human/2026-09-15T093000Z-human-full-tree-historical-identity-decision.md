# Human Decision Request — identity for the first full-tree historical replay

Target: Roee, Sagiv, Yuval

Sender: Codex

Created at: 2026-09-15T09:30:00Z

Status:
DECIDED_OPTION_A

## Objective

Choose the market-data identity that the first **actual historical full-tree
replay** will represent.  This is required before a data adapter can supply
evidence to the completed capture/replay boundary.

## What is already true

- The existing alert tree and historical level-map contracts use the exact
  instrument identity `OANDA:XAUUSD` in their source-faithful path.
- The approved first research archive is Databento **GC futures**, not XAUUSD;
  see `agent-exchange/decisions/2026-08-31T175802Z-human-first-symbol-gc.md`.
- Existing contracts explicitly forbid silent GC-to-OANDA normalization; see
  `docs/architecture/HISTORICAL-LEVELMAP-USAGE.md`.
- The new full-tree evidence capture component is source-agnostic and ready to
  record an approved adapter's point-in-time calls, but it deliberately does
  not read a vendor archive, invent a translation, or create labels.

Therefore, connecting the GC archive to the XAUUSD tree without an explicit
choice would make a misleading claim: that the tree saw the same instrument,
prices, sessions, levels and execution context that it actually uses.

## Decision required

Select exactly one path for the first real-data full-tree replay.

### Option A — Source-faithful XAUUSD path

Provide/approve a historical source whose identity is genuinely compatible
with `OANDA:XAUUSD` (or formally define the tree's supported XAUUSD source
variant).  The adapter will use that identity end-to-end.

**Result:** strongest answer to “how would this alert tree have behaved?”
and the only option that can later support source-faithful economic research.

**Needed from Roee/Yuval:** source/provider name, exact symbol, available
history, bar/session/calendar semantics, correction/revision policy and a
per-artifact provenance/digest mechanism.  Do not send credentials or raw
data through agent-exchange.

### Option B — GC research-tree variant

Declare `CME:GC` (with explicit contract/roll policy) as a separate research
tree variant.  Implement/approve only source rules that are valid for GC; do
not describe its results as XAUUSD-tree results.

**Result:** uses the already approved GC archive honestly, but it is a
different tree version and requires a source-variant specification before
historical capture.  It remains research-only; continuous/stitched GC is not
execution truth under the existing decision.

**Needed from Sagiv:** confirmation that the desired strategy is GC futures,
and which source-dependent rules change or become unavailable.  **Needed from
Roee/Yuval:** exact contract/roll/calendar identity and adapter provenance.

### Option C — Explicit GC-to-XAUUSD proxy study

Authorize a versioned, research-only translation study that feeds GC-derived
observations into a declared proxy variant of the tree.

**Result:** may be useful for learning whether the ideas transfer, but every
candidate and result must be marked `PROXY`; it cannot establish XAUUSD tree
fidelity, executable fills, P&L, model promotion or live trading.

**Needed from Sagiv:** which conceptual rules may transfer and the business
question the proxy is allowed to answer.  **Needed from Roee/Yuval:** the
written transformation/version, no-look-ahead availability rule, validation
plan and a decision to keep proxy output isolated from source-faithful labels.

## Recommendation

Choose **Option A** if the immediate goal is to train a model that improves
the existing XAUUSD alert tree.  Choose **Option B** only if the intended
strategy itself is GC futures.  Do not choose Option C as the first model
baseline; reserve it for a separately labelled transferability study after A
or B has a clean baseline.

## Required response format

Reply with:

1. `Option: A | B | C`;
2. canonical instrument string and source/provider;
3. whether the output is source-faithful or proxy-only;
4. the named owner for market-data adapter/provenance (Roee or Yuval) and for
   rule semantics (Sagiv);
5. any rule that must be disabled because the chosen source cannot support it.

The Option A decision is recorded in
`agent-exchange/decisions/2026-09-15T065418Z-human-full-tree-historical-identity-option-a.md`.
The provider/source-profile details remain required in
`agent-exchange/inbox/human/2026-09-15T065418Z-human-xauusd-source-profile-required.md`.

## Non-negotiables

- No silent `GC` ↔ `OANDA:XAUUSD` alias or price-offset conversion.
- No vendor query, archive read, raw-data retention change, model training,
  promotion, broker execution or live trading is authorized by this request.
- Missing source capability must be represented as unavailable; it may not be
  filled with invented values.

## Deliverable after the decision

Codex will define the selected adapter contract, create point-in-time capture
tests, and run the tree only against supplied, digest-bound evidence.  Dataset
construction and model training remain later gated work.
