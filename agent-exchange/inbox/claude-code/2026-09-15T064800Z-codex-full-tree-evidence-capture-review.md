# Agent Exchange Request

Target: Claude Code reviewer

Sender: Codex architecture controller

Created at: 2026-09-15T06:48:00Z

Status:
REVIEW_ONLY

Objective:

Independently review the full-tree evidence-capture implementation for API
integrity, error behavior, mutation/privacy safety and adequacy of its tests and
static audit.

Scope:

- commits `3bde463`, `13b7524`, `dfd2f53`, `d39763b`
- full-tree capture implementation/audit/tests/usage document named in the
  parallel Groq request

Required inputs:

Read-only code/test inspection; listed offline tests are permitted. No edits,
external source execution, network/data access or secrets.

Contracts:

The recorder's only data path is `FullTreeCaptureInput.read`. It must create one
artifact/operation per actual call, execute actual reader/revalidation only to
discover calls, and never accept a final tree result. The returned bundle is
not an outcome/dataset/model artifact.

Non-negotiables:
- fail closed on input errors and availability violations
- preserve independent clocks, repeated reads, supplied exceptions and shadow
  writes without external effects
- public receipt contains only commitments
- no readiness claim beyond local prerequisite evidence

Deliverables:

Write one review under `agent-exchange/reviews/` using the review template. Give
PASS / NEEDS_REVISION, reproducible evidence, findings with file/line references
and minimal remedy.

Verification commands:

- `python -B -m pytest tests/tree_replay/test_full_tree_capture.py tests/tree_spec/test_full_tree_capture_source.py -q --tb=short -p no:cacheprovider`
- `python -B tools/check_full_tree_capture_source.py`

Out of scope:

Data adapters, economics, labels, training, model usage, broker or live behavior.
