# Full-tree historical identity decision requested

Request: `agent-exchange/inbox/human/2026-09-15T093000Z-human-full-tree-historical-identity-decision.md`

Sender: Codex

Created at: 2026-09-15T09:30:00Z

Status: DECISION_RECEIVED_AWAITING_SOURCE_PROFILE

## Completed before the block

The supplied-evidence full-tree capture/replay boundary is implemented locally
and independently review-requested.  It records only actual source calls made
by the existing tree and keeps public receipts payload-free.  It has no vendor
client, archive reader, economic outcome, dataset, trained model or live
trading behavior.

## Blocking fact

The currently approved first research archive is GC futures, while the
source-faithful existing tree contracts use `OANDA:XAUUSD`.  The codebase and
prior human decisions prohibit silently treating those identities as equal.

## Required human input

Option A was selected and recorded in
`agent-exchange/decisions/2026-09-15T065418Z-human-full-tree-historical-identity-option-a.md`.
The exact provider/source-profile details are now the only blocking input; see
`agent-exchange/inbox/human/2026-09-15T065418Z-human-xauusd-source-profile-required.md`.
Until they arrive, no actual historical adapter, tree capture, dataset or
training run may be represented as source-faithful.

## Verification completed

```powershell
python -B -m pytest tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_contracts.py tests/tree_replay/test_full_tree_provider.py tests/tree_replay/test_full_tree_replay.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_causal_replay.py tests/tree_spec/test_full_tree_capture_source.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider
# 186 passed in 22.21s
python -B tools/check_full_tree_capture_source.py
# VERIFIED; readiness remains false
```
