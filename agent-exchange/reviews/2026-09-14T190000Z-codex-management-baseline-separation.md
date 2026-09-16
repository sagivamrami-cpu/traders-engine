# Agent Exchange Review

Reviewer: Codex

Target request: Active goal — continue the approved outcome-learning and dynamic-management plan without inventing trading rules.

Created at: 2026-09-14T19:00:00Z

Status: REVIEW_READY_FOR_CODEX

Verdict: REQUIRED BASELINE SEPARATION RECORDED

Findings:

- The approved research decision
  `agent-exchange/decisions/2026-09-08T180046Z-user-economic-target-and-baseline.md`
  requires fixed original entry/stop and a full-position exit at TP1, without
  partials, additions, optional BE or trailing, for the first selection study.
- At chart-desk commit `e79c3f...`, `chartdesk/management_trial.py` labels one
  arm `CONTROL`, but its weights are 25% / 25% / 50% over three targets.
- The names do not imply equivalence. The policies have different exits,
  outcome end times and therefore different economic labels. Reusing the
  management-trial arm as the selection control would change the approved
  experiment silently.
- The master plan, implementation tracker and source mapping now require
  distinct policy identities. This is a documentation and research-integrity
  change only; no runtime code, trading parameter, broker order or dataset was
  created.

Open questions:

- J1/J2 still require Sagiv's executable thesis/action definitions and action
  priority. This finding does not decide them.
- J3 still needs the approved instrument-aware fill, cost and time-horizon
  contract before market outcomes can be generated.

Recommended next action:

When J3 begins, implement the fixed full-TP1 control as its own policy and
compare any partial/BE/dynamic policy against it at equal entry, risk, costs and
time window. Preserve policy/horizon identity in every action/outcome record.

Verification reviewed:

- Read the approved decision and `trading_system/tree_spec/economics.py`.
- Inspected the verified `management_trial.py` source at `e79c3f...` in an
  isolated audit clone.
- `git diff --check` passed for the associated documentation updates.
