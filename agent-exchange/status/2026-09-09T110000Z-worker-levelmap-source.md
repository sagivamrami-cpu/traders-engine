# Agent Exchange Result

Target:
Codex controller

Sender:
Codex scoped Task 1 implementer

Created at:
2026-09-09T11:14:44Z

Request:
agent-exchange/inbox/codex/2026-09-09T110000Z-levelmap-source.md

Status:
IMPLEMENTED_AWAITING_CODEX_REVIEW

Summary:
Implemented Task 1 complete original level-map calculation graph with injected
offline source and explicit decision time. Preserves exact family ordering,
source guards, formulas, missing strings and exception behavior. New text-only
audit verifies complete ordered modules and all inherited dependencies, with
independent strict EMA projections addressing the controller's follow-up.

Detailed report:
.superpowers/sdd/2026-09-09-historical-levelmap-core/task-1-report.md

Changed files:

- trading_system/tree_replay/_vendor/levelmap_build.py
- trading_system/tree_replay/_vendor/map_sessions.py
- trading_system/tree_replay/_vendor/map_tr.py
- tools/check_levelmap_source_parity.py
- configs/trees/levelmap-source-contracts.json
- tests/tree_replay/test_levelmap_source.py
- docs/architecture/LEVELMAP-SOURCE-USAGE.md
- Detailed scratch report and this exchange result.

Verification results:

- Task 1 RED before production edits:
  python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short
  -> 123 expected missing-module assertion failures in 6.81s, exit 1.
  An earlier fixture-harness run had 63 failed/60 setup errors and was corrected
  before the clean RED; detailed intermediate results are in the report.
- Initial GREEN: same command -> 123 passed78.21s, exit 0.
  Supplementary characterization -> 139 passed82.18s, exit 0.
- Controller-named EMA RED:
  python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short -k 'joint_indicators or tr_emas_after or strict_ema_projection'
  -> 6 failed,1 passed,139 deselected11.64s, exit 1.
- EMA GREEN: same command -> 7 passed,139 deselected12.23s, exit 0.
- Final Task 1 GREEN:
  python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short
  -> 146 passed96.96s (0:01:36), exit 0.
- Final sourceaudit:
  python tools/check_levelmap_source_parity.py
  -> PASS exit 0; blockers=[], subset_verified=true; range/pricing/EMA/correction
  inherited audits all verified; strict EMA projections also checked;
  ready_for_replay=false, ready_for_training=false.
- Read-only Git commit:path verification returned indicators blob
  672f0428c3a81b86376d4f792ae40ecd174a2025 and tr blob
  8297c712d20404880d4d8949e96efbf48613909c before adding independent pins.
  Exact command/output in detailed report.
- Per-owned-file git diff --no-index --check -- NUL <file>: exit 1 for additions;
  LF/CRLF advisories only, no whitespace errors. Git status/diff inspected.
- Self-review completed. Independent review and broad testing remain controller
  work and are not claimed here. Counts overlap and must not be summed.

Controller EMA finding:
Relocated mutation tests demonstrate the unchanged old EMA audit accepting both
a coordinated indicators source/vendor/manifest mutation and TR_EMAS moved after
its use in emas's default argument. The new audit rejects them using independent
manifest seals, a fixed Git-verified indicators blob and complete ordered EMA
vendor projections. It also rejects reordered/duplicate imports, function order
changes and noninitial strings, allowing only harmless initial module docstrings.
All required inherited audits remain; no accepted old tool was changed.
No source or mutated vendor module executes during auditing.

Decisions needed:
None for Task 1. No GC/OANDA equivalence, production-data or training approval
is inferred.

Blockers:
None for the Task 1 handoff. Awaiting independent controller acceptance.

Recommended next action:
Review the owned files and detailed report, independently rerun Task 1/sourceaudit,
then complete causal-frame/public-map integration and the controller's broad tests.

Notes:
Input-frame/clock/provenance validation belongs upstream. Source asymmetries and
silent omissions remain: source=replay does not earn OANDA broker shape; native
BTC with source=none can pass shape while session opens remain absent; coarse or
empty-after-seam accepted PSY frames stop fallback. CLOUD50 means EMA50 basis;
duplicate Q-QUARTER names/prices/order are preserved. Full replay/readiness,
admission, simulation, economics/datasets and models remain outside this task.

Only the seven listed Task 1 files and two authorized reports were written.
Preserved accepted dependencies, existing dirty files and parent frame work.
No nested agents, source execution, real data/downloads, training, live alerts,
commits, worktrees, cleanup or external messages.
