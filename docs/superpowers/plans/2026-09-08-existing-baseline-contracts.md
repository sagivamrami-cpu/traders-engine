# Existing Baseline Contracts Implementation Plan

> **For agentic workers:** Use subagent-driven-development for the isolated economic-contract task, TDD for code, and requesting-code-review before handoff. User authorized implementation; no repeat approval needed.

**Goal:** Make the approved existing-source baseline and fixed economic outcome contract executable and testable without claiming a complete replay.

**Architecture:** Add independent source-verification and economic-contract modules to `trading_system.tree_spec`. The first validates pinned repositories without importing them. The second validates explicit research settings and computes net outcomes only from already resolved, supplied fills. A read-only CLI exposes source verification, always keeping replay/training readiness false in this slice.

**Tech Stack:** Python standard library and existing pytest; no dependencies installed.

**Spec:** `docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md` and `agent-exchange/decisions/2026-09-08T180046Z-user-economic-target-and-baseline.md`.

## Global Constraints

- Existing local research branch; preserve all earlier uncommitted work. No commits/pushes or new worktree in this slice, per the existing foundation plan.
- No source-repository edits/imports/entrypoints, network feeds, notifications, broker calls or training.
- No invented market thresholds, instrument conversions, fees or time exits.
- Missing economic settings block construction of a usable policy. Synthetic fixture values are not approved market settings.
- Economic success and movement success remain separate. Outputs are outcomes, not pre-entry features.
- This implements a bounded part of phase B and the outcome arithmetic interface, not phases C–J or a complete simulator.

## Task 1: Pinned source manifest and read-only verifier (controller critical path)

Files: create `configs/trees/existing-alerts-baseline.json`, `trading_system/tree_spec/baseline.py`, `tests/tree_spec/test_baseline.py`, `tools/inspect_alert_baseline.py`.

Interfaces: `load_baseline(path: Path) -> Baseline`; `Baseline.to_payload() -> dict`; `verify_checkouts(baseline: Baseline, root: Path) -> dict`.

Manifest schema `existing-alerts-baseline-v1`: list of repositories with name, GitHub URL, full lowercase commit and source references (relative path, symbol, role). Producer records carry id, repository and source path. Store all six hashes from the decision, all eight concrete producer identities (two timeframes each reversal/reaction, two tree variants, two engine styles), and explicit target-only/shadow/not-integrated limits. Source refs are evidence, not claims of atomic feature completeness.

- [x] Write tests before the module. Real tiny git fixture with a committed Python module must verify; HEAD changes, tracked edits, missing repo/source, parent-directory masquerading as checkout must block. Manifest rejects malformed hashes, duplicate IDs, absolute/traversal paths, unknown producer repositories and source paths. No subprocess execution beyond read-only git inspection.

```python
def test_a_manifest_is_not_training_readiness(baseline_file):
    report = load_baseline(baseline_file).to_payload()
    assert report['ready_for_training'] is False
    assert report['ready_for_replay'] is False
```

- [x] Run `python -m pytest tests/tree_spec/test_baseline.py -q`; confirm missing implementation failure.
- [x] Implement frozen records/strict parsing, deterministic canonical manifest SHA256, copy-safe payloads. Verify exact git top-level and HEAD, tracked/untracked dirtiness, and referenced tracked paths. Use argument-list subprocesses, no shell/network/imports. Return explicit blockers and aggregate source_verified flag, never readiness=true.
- [x] CLI accepts `--manifest`, optional `--root`, and `--require-source-verified`; JSON stdout, exit 0 for inventory, 2 for missing/failed required source verification, 1 for malformed input. No latest-branch fetching or mutation.
- [x] Run focused tests, CLI inventory, and explicit-root check against the isolated reviewed clones. Existing sibling checkouts may intentionally fail pin verification.

## Task 2: Explicit economic policy and resolved-outcome arithmetic (delegated)

Files: create only `trading_system/tree_spec/economics.py` and `tests/tree_spec/test_economics.py`; own report under agent-exchange/status.

Interface design (use frozen dataclasses, keyword-only fields to avoid argument mistakes):

```python
@dataclass(frozen=True, kw_only=True)
class EconomicPolicy:
    policy_id: str
    instrument: str             # exact venue:symbol, no automatic mapping
    currency: str
    point_value: Decimal        # currency / one price-point / one quantity unit
    quantity: Decimal
    commission_per_side: Decimal
    spread_points: Decimal     # total round-trip mid-price spread deduction
    slippage_points_per_side: Decimal
    pending_expiry_seconds: int
    max_holding_seconds: int
    fill_rule: str              # 'supplied_verified_fills'
    simultaneous_rule: str      # 'ambiguous' or 'stop_first'
    cost_basis: str             # 'mid_price_plus_costs' or 'executable_fills'
    provenance: str             # explicit source/assumption record, synthetic in tests

@dataclass(frozen=True, kw_only=True)
class ResolvedTrade:
    candidate_id: str
    instrument: str
    direction: str              # 'LONG' or 'SHORT'
    decision_time: datetime
    filled_at: datetime
    exited_at: datetime
    available_at: datetime
    entry_price: Decimal
    initial_stop: Decimal
    tp1: Decimal
    exit_price: Decimal
    exit_reason: str            # 'TP1', 'STOP', 'TIME_EXIT', 'INVALIDATION'
    evidence: str

def evaluate_resolved_trade(policy: EconomicPolicy, trade: ResolvedTrade) -> dict:
    ...
```

- [x] Write tests first, run RED. Missing constructor fields must fail; reject None/bool/float/string for Decimal money fields, nonfinite or invalid sign values, blank IDs/provenance, nonpositive/bool durations, unsupported modes, naive/future-order timestamps, venue mismatch, wrong geometry, entry at/after pending deadline, exit beyond maximum holding horizon, and unsupported outcomes (unfilled/ambiguous cannot be resolved).
- [x] Implement explicit, validated policy only (no defaults). Initial risk = abs(entry_price-initial_stop)*point_value*quantity, fixed across outcomes. Gross P&L = signed(exit-entry)*point_value*quantity. Mid-price costs = 2*commission_per_side + (spread_points+2*slippage_points_per_side)*point_value*quantity. For executable_fills require spread/slippage components ==0 to avoid double charging; commission still applies. Commission is the total currency amount per side for the supplied position, not per unit; document it.
- [x] Compute net_P&L/net_R with Decimal (bounded deterministic local decimal context), classify exact positive/negative/zero, serialize monetary outputs as decimal strings. Reject nonfinite arithmetic. Do not infer movement success from exit P&L, do not infer fill prices or create trades. Same-instant exits are allowed with supplied evidence; this is chronology validation, not proof of intrabar sequence.
- [x] Return candidate/policy identity, economic_label, gross_pnl, total_cost, net_pnl, initial_risk, net_R, currency, label_end_time=exited_at, available_at, provenance and a stable policy SHA256. Normalize datetimes to UTC before comparisons and serialization, including DST folds. No binary failure probability and no invented trade-signal score.
- [x] Literal tests: long 100->104, stop98, quantity2, point_value10, commission1/side, spread0.1, slippage0.05/side => gross80, cost6, net74, risk40, net_R1.85. Short mirror matches. A target exit can be net-negative after costs. Zero P&L is BREAK_EVEN. Changed costs change policy identity. External caller decimal precision must not change output.
- [x] Run `python -m pytest tests/tree_spec/test_economics.py -q`, self-review, report RED/GREEN and changed paths. No commits, no subagents, no outside files.

This function evaluates supplied settled evidence; it does NOT validate that TP1/STOP was truly touched or simulate fills/management. The caller must obtain causal verified events from the next replay phase. Arbitrary supplied data passing structural validation is not proof of profitable trades.

## Task 3: Integration verification and durable handoff

- [x] Read both implementations and run `python -m pytest tests/tree_spec -q`.
- [x] Run `python -m pytest -q --ignore-glob='*validator*'`; the legacy validator suites remain excluded as in the foundation handoff, not claimed passing.
- [x] Read-only code review of all new files for spec and quality; address significant findings with regressions before handoff.
- [x] Update master-plan progress and AGENTS links, without replacing the larger roadmap. Record exact test and CLI results under agent-exchange/status.
- [x] Report implemented slice, lack of full replay/training, and next as-of feature/producer adapter work.

## Preflight and progress ledger

| Task/pair | Interface / scope check |
|---|---|
| 1 | Source verification is not executable coverage; readiness remains false |
| 2 | Resolved arithmetic is not a fill simulator; numeric settings required, none inferred |
| 1 / 2 | Disjoint files; no dependency between modules, stable provenance will be joined later |
| 1 / 3 | CLI and immutable source report tested before status claims |
| 2 / 3 | Controller independently reruns tests and reviews arithmetic boundary |

Process adaptation: scoped work stays uncommitted per prior project instructions;
reviewers receive explicit new-file lists rather than an empty HEAD-to-HEAD diff.
Skill scratch helpers requiring Bash may be replaced by this persistent plan and
agent-exchange report files on Windows. No cleanup deletes or source mutations.

Accepted bounded slice: final tree-spec 349 passed; broad regression 729 passed
with legacy validator files excluded. All six pinned sources verified; replay
and training flags remain false. See
`agent-exchange/status/2026-09-08T182000Z-codex-baseline-contracts.md`.
