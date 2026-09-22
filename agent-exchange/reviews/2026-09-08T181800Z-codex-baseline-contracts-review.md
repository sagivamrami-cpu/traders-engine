# Agent Exchange Review

Reviewer:
Codex controller; independent source reviewer Erdos and economic reviewer Locke

Target request:
User: proceed with approved implementation;
`docs/superpowers/plans/2026-09-08-existing-baseline-contracts.md`

Created at:
2026-09-08T18:18:28Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
Source and economic contract slices approved after revisions. Controller's
final integration acceptance is recorded separately in the status report.

Findings:

1. Git status could refresh the index during read-only inspection. Reproduced
   with a metadata-only source touch and index-byte comparison. Corrected with
   no-optional-locks flags/environment; regression passed.
2. Content filters and missing promisor objects could invoke external processes.
   Reproduced with synthetic local marker filter and remote-helper fixtures.
   Added metadata preflight blocking tracked filter attributes/submodules and
   explicit no-lazy-fetch/protocol blocking. Unused global LFS settings do not
   block clean unfiltered repositories. Both regressions passed.
3. Assume-unchanged could conceal altered tracked source and falsely verify it.
   Reproduced against a temporary real Git repository. Masked entries now block
   verification; regression passed.
4. Follow-up: stripping NUL-delimited output corrupted a leading-space tracked
   filename and bypassed filter preflight. Controller reproduced actual marker
   execution, then preserved raw Git output and used strict decoding. Both
   ordinary and leading-space filename regressions passed. Source reviewer
   closed the residual finding in a scoped re-review.
5. Minor hash-order coverage gap: added reversal of repository/source/producer/
   limitation lists, not just dictionary keys.

Economic review found no Critical, Important or Minor issues in the bounded
supplied-trade arithmetic contract. It checked chronology, Decimal bounds,
cost bases, fixed risk, canonical hashes and the snapshot/outcome separation.

Open questions:

- Real-market costs, expiry/holding and executable fill evidence are still needed
  before market labels. Synthetic settings authorize none of them.
- Neither source identity nor structural evidence strings prove causal replay,
  true TP1/stop sequence or runtime deployment parity.

Recommended next action:

Accept only this bounded slice after the controller's final regression run.
Continue source-to-feature mapping and an as-of producer adapter with parity
fixtures before full historical replay. No live behavior or training changes.

Verification reviewed:

- Controller independently reran economics: 254 passed.
- Controller final tree-spec suite: 349 passed in 30.76s.
- Controller final six-pinned-clone CLI: exit 0, all source_verified true,
  ready_for_replay=false and ready_for_training=false.
- Economic reviewer reported 297 economics/snapshot tests plus 240 independent
  rational-arithmetic cases passed. These counts are reviewer evidence, not
  additions to the controller suite count.
- Source reviewer inspected corrections and tests; did not claim an independent
  final suite run. Controller owns executed RED/GREEN evidence.
- Earlier broad run: 728 passed before the final filename correction. The final
  broad rerun is separately recorded in the controller acceptance status.
- Reviewers made no files, commits, source changes, feeds or broker calls.
