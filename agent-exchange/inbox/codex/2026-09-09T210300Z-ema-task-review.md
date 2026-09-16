# Agent Exchange Request

Target: Independent task reviewer
Sender: Codex controller
Created at: 2026-09-09T21:03:00Z
Status: REVIEW_ONLY

Objective: Separate spec-compliance and code-quality verdicts for EMA tasks1/2.
Scope: Six files in the two task diff packages, not full tree/model readiness.
Required inputs:
- .superpowers/sdd/2026-09-09-ema-deep-reader/task-1-brief.md
- .superpowers/sdd/2026-09-09-ema-deep-reader/task-2-brief.md
- .superpowers/sdd/2026-09-09-ema-deep-reader/task-1-diff.md
- .superpowers/sdd/2026-09-09-ema-deep-reader/task-2-diff.md
- .superpowers/sdd/2026-09-09-ema-deep-reader/implementation-report.md
- docs/architecture/EMA-DEEP-READER-CONTRACT.md

Contracts: Source-faithful private offline reader; complete source AST and
actual ordered seededEMA dependency. Read exact brief/spec values; no invented
thresholds, normalizations or feeds. Base/head c1b6071633c55376c64f0a98ece843706f420f49;
all six scoped files are uncommitted additions, packages carry entire diff.
Retained source parent:
C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149.

Non-negotiables: Read-only except the named review artifact via apply_patch.
No nested agents, no source execution, no live/data/training/commit/cleanup.
No production approval by implication. Follow task-reviewer prompt; cite named
risks for dependency inspection. Do not duplicate main suites; focused probes
only for an identified doubt. Source may be read/AST-parsed, never imported.

Deliverable: agent-exchange/reviews/2026-09-09T210300Z-ema-task-review.md
using review template; for EACH task separate spec and quality verdicts,
severity/file:line findings and precise evidence/gaps. Return concise summary.
Verification commands: Main255combined/58audit and mutation evidence in report;
recommend additional heavy validation rather than duplicating it.
Out of scope: final combined review, causal bindings, full caller, dataset/model.
