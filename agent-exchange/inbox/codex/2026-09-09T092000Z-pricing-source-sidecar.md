# Agent Exchange Request

Target:
Codex source-pricing implementer

Sender:
Codex controller

Created at:
2026-09-09

Status:
ACCEPTED_BY_CODEX

Objective:
Pure pinned pricing dependency implementation, Task1 of reversal-pricing plan.
Read this brief first; it contains your complete scoped requirements. No need to
read the whole plan. Parent concurrently owns pricing wrapper/tests.

Scope:
New files only: trading_system/tree_replay/_vendor/pricing.py,
_vendor/basis_symbols.py, _vendor/quarters.py, _vendor/atr.py,
_vendor/reversal_pricing.py; tools/check_pricing_source_parity.py;
configs/trees/reversal-pricing-contracts.json; tests/tree_replay/test_pricing_source.py;
agent-exchange/status/2026-09-09T092000Z-worker-pricing-source.md.

Required inputs:
AGENTS/protocol. Source checkout read-only:
C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk
commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9. Inspect source functions fully
and dependencies; use previous check_reversal_source_parity as a reference only.

Contracts:
1. pricing.py copies tradeplan constants MIN_RR, SWING_MULT, STYLE_MULT,
INTRADAY_MULT, INTRADAY_TARGET_COUNT, FAR_TP1_R, INSERT_TP1_R, ENTRY_ZONE,
STOP_BANDS, MIN_TARGET_SEP_ATR; functions _with_measured_rung, entry_zone,
apply_stop_band, ladder_ready, ordered_ladder, distinct_targets, _n_levels,
resolve_ladder. Plan: original class/decorator, ALL original dataclass fields,
only properties risk,rr,rr_far,tradeable. Class projection documented and AST
audited, not claimed complete Plan class. Imports __future__ annotations,
dataclasses dataclass/field, .basis_symbols as basis. apply_stop_band's exact
local `from . import quarters` resolves to your pure quarters module.
2. basis_symbols.py copies _BARE_ALIASES and canonical_symbol exactly. Never
introduce GC/futures aliases. Only __future__ annotations if needed.
3. quarters.py copies GRID, _asset, Level (including its pure render), _kind,
nearest exactly; dataclasses and future import only; no read or I/O needed.
4. atr.py copies chartdesk.tr.atr EXACTLY with pandas import. This is unseeded
ewm(alpha=1/length, adjust=False), NOT chartdesk.indicators.atr or seeded RMA.
5. reversal_pricing.py copies ONLY level_reversal.build_plan, exact AST. Import
existing .level_reversal Reversal/_normalise; .pricing as tradeplan; .atr as tr;
pandas and future annotations. Do not modify prior vendor/checker files.
6. Auditor --source-root path: fixed independent blob pins and fixed file/symbol
coverage/imports. Full ordered module AST except documented Plan projection.
Projection keeps all class non-method fields plus exactly four methods; include
original decorators, names/types/defaults and reject vendor extras/mutations.
Reuse/invoke check_reversal_source_parity.check_source_parity for inherited
Reversal/_normalise dependency verification (read-only tools, not source import).
Validate baseline commit, fail closed on omitted/tampered manifests, source blobs,
imports, symbols, class fields or properties; runtime flags false in all cases.
7. Synthetic numerical expectations independently derived, including exact
zone-edge bands, psyche snapping and upper bound, long/short, style multipliers,
in-zone filtering, 0.5ATR target merging, 1.2R equality, FAR_TP1_R strictness,
1.5R measured rounding, preserved refusal geometry, source ATR initialization.
Example: XAU entry100/rawstop98/atr2/scalp clamps to93. With finalstop93 and
levels[("far",130)] resolver prepends110.5; obstacle105 before130 refuses farTP1.
Use real pure code, no forced-quarter-import failure to omit anchoring.

Non-negotiables:
- TDD, apply_patch, no new model/strategy thresholds or feeds
- No source checkout execution, network, installs, alerts, raw market data
- No nested agents, commits, cleanup, writes outside scope; preserve shared work
- No replay/training readiness or live/production approval

Deliverables:
Listed code/contracts/tests and result note using template, referencing this brief.
Report RED/GREEN commands, changed paths, source pin evidence and limitations.

Verification commands:
python -m pytest tests/tree_replay/test_pricing_source.py -q
python tools/check_pricing_source_parity.py --source-root <retained-chart-desk>

Out of scope:
Parent wrapper, history level construction, whole Plan display/render/live methods,
admission/arbitration/fills/outcomes/models. Source functions may return permissive
geometry for unknown symbols; wrapper owns supported-identity validation.

Notes:
No commits requested. Do not change the previous detector/EMA source modules.
