# Agent Exchange Request

Target: Groq reviewer

Sender: Codex architecture controller

Created at: 2026-09-15T06:37:44Z

Status:
REVIEW_ONLY

Objective:

Add this commit to the pending full-tree causal-provider implementation review:
`424b9ed fix: pin full-tree audit to source tree`.

Scope:

- `trading_system/tree_spec/full_tree_replay_source.py`
- `tests/tree_spec/test_full_tree_replay_source.py`
- prior request `agent-exchange/inbox/groq/2026-09-15T063341Z-codex-full-tree-causal-provider-implementation-review.md`

Required inputs:

Read-only. Do not modify code, access external data, execute retained source
modules, or use secrets.

Contracts:

The audit must reject a directory that merely has the name `chart-desk`; it
must require the separately pinned full `TreeReader` source audit. If that
source audit is unavailable, it must return a structured blocked report.

Non-negotiables:
- no relaxation of source identity or point-in-time boundaries
- no readiness, data, economic, training or live-trading claim

Deliverables:

Include this commit in the review result for the original request. Record any
additional finding with file/line evidence.

Verification commands:

- `python -B -m pytest tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider`
- `python -B tools/check_full_tree_replay_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`

Out of scope:

All implementation beyond the listed audit change, acceptance and model work.
