# Agent Exchange Result

Target:
Codex controller

Sender:
Codex source-pricing implementer

Created at:
2026-09-09T09:56:09Z

Request:
`agent-exchange/inbox/codex/2026-09-09T092000Z-pricing-source-sidecar.md`

Status:
IMPLEMENTED_AWAITING_CODEX_REVIEW

Summary:
Implemented the pure pricing dependency closure at the exact pinned source AST,
with synthetic numerical tests written and observed RED before implementation.
The TDD and verification-before-completion skills governed the RED/GREEN checks.
`reversal_pricing.build_plan(event, levels, history)` uses the existing vendored
`Reversal` and `_normalise`, pure pricing/quarters/basis symbols, and precisely
`chartdesk.tr.atr`'s unseeded `ewm(alpha=1/length, adjust=False)` calculation.

The Plan projection preserves the original dataclass decorator, all 22 dataclass
fields, both other class constants (`CLIENT_CAVEATS`, `NOT_DRAWN_TAGS`), and only
the four properties `risk`, `rr`, `rr_far`, `tradeable`. It is not the full Plan
class. The manifest documents this projection; the auditor constructs it from
the pinned original AST and compares the entire ordered vendor module, including
imports. Other selected functions/classes are copied without AST modification.

Changed files:

- `trading_system/tree_replay/_vendor/pricing.py`
- `trading_system/tree_replay/_vendor/basis_symbols.py`
- `trading_system/tree_replay/_vendor/quarters.py`
- `trading_system/tree_replay/_vendor/atr.py`
- `trading_system/tree_replay/_vendor/reversal_pricing.py`
- `tools/check_pricing_source_parity.py`
- `configs/trees/reversal-pricing-contracts.json`
- `tests/tree_replay/test_pricing_source.py`
- `agent-exchange/status/2026-09-09T092000Z-worker-pricing-source.md`

Verification results:

- RED: `python -m pytest tests/tree_replay/test_pricing_source.py -q`
  exited 1, 74 failed on explicit missing-sidecar/auditor assertions before
  implementation. Repeated with `--tb=no` after manually refining snapping
  fixtures, still 74 expected failures before implementation.
- GREEN (final rerun): `python -m pytest tests/tree_replay/test_pricing_source.py -q`
  exited 0, **74 passed in 2.61s**.
- PASS: `python tools/check_pricing_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`
  exited 0; both subset-verification flags true, blockers empty, both
  replay/training readiness flags false.
- PASS: `git diff --check` exited 0. Git emitted existing AGENTS.md/README.md
  CRLF conversion warnings. Assigned files are new/untracked, so they were also
  inspected directly; no existing tracked file was changed by this worker.
- Read-only source `git rev-parse HEAD` confirmed
  `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`; `git ls-tree HEAD` established
  independent blob pins below. Auditor recomputes the canonical LF Git blob
  digest from source text and validates the repository baseline commit.

Source pin evidence:

| Source file | Git blob SHA-1 |
| --- | --- |
| `chartdesk/tradeplan.py` | `d09e9be39ce8dadf1674029e0c03751c70502135` |
| `chartdesk/basis.py` | `f3396f3a9fefd71f0f71422001a5521af0a05cd2` |
| `chartdesk/quarters.py` | `d540b7bba60e992ff711954716ad265337116fc1` |
| `chartdesk/tr.py` | `8297c712d20404880d4d8949e96efbf48613909c` |
| `chartdesk/level_reversal.py` | `7c0eee53d97a1ba9280626fdb2d20eba61b5aa1b` |

The pricing auditor invokes the existing
`check_reversal_source_parity.check_source_parity` for inherited Reversal,
normalization and detector/PVSRA closure verification; that audit additionally
pins `chartdesk/auction.py`. No prior vendor or checker files were modified.

Test coverage includes zone-edge stop bounds, long/short psychological snapping
and its midpoint-based upper ceiling (including equality), all style tiers,
NAS intraday's source exception, identity pass-through without new GC aliases,
pure quarters rendering, in-zone/wrong-side target rejection, strict 0.5ATR
merging, inclusive 1.2R qualification, strict FAR_TP1_R insertion/refusal,
measured 1.5R rounding/capping, refusal geometry, and ATR initialization.
Manifest omission/tampering, all source blobs and baseline changes, vendor
extra imports/statements/methods, Plan field/property/decorator mutation, and
inherited vendor changes are rejected. Audit tampering tests replace text reads
in memory; they do not modify the retained source or shared dependency files.

Decisions needed:
None for this scoped implementation.

Blockers:
None.

Recommended next action:
Parent independently reruns the two requested checks and integrates the pricing
wrapper with the exact `build_plan` interface. Wrapper ownership remains with
the parent; acceptance remains pending controller review.

Notes:
The real-source audit tests require the retained chart-desk path named in this
brief (also set as the test module's SOURCE constant). No source checkout code
was imported or executed: only Git metadata, source text and ASTs were read.
Source Python was parsed to extract exact selected text, and all new files were
written with apply_patch. No network, installs, nested agents, commits, cleanup,
live alerts, raw market data, or changes to prior source modules were performed.

Source limitations are deliberately preserved: unknown symbols may pass through
with permissive geometry, so supported identity validation belongs to the parent
wrapper. Quarters' existing `_asset` recognition of GC is copied exactly; no GC
alias was added to basis_symbols. ATR filtering in build_plan alone is not an
as-of closed-bar contract. No historical level construction, admission,
arbitration, fills, economic labels, outcomes or training readiness is provided.
This result grants no live/production/promotion/deployment approval.
