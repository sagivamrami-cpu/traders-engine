# Agent Exchange Review

Reviewer: Codex independent Task2 source-audit reviewer

Target request: agent-exchange/inbox/codex/2026-09-09T174338Z-claim-verifier-audit-review.md

Request: agent-exchange/inbox/codex/2026-09-09T174338Z-claim-verifier-audit-review.md

Created at: 2026-09-09T17:46:33Z

Status: REVIEW_READY_FOR_CODEX

Verdict: PASS for Task2 specification and code quality. No Critical, Important,
or Minor findings identified. Suitable for controller integration review;
this is not combined component acceptance or authorization to merge/deploy.

Findings:

- Literal chart-desk commit and verify.py blob match independent Git inspection:
  `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and
  `3329fdb71f8aebdf13a6fa823e8be0d85e1ced03`. Baseline identity cannot redefine
  these constants. Retained checkout text is LF-normalized for the blob check,
  consistent with the inherited audit policy.
- `trading_system/tree_spec/claim_verifier_source.py:45` selects all 17 source
  symbols in their literal order, preserves the ten pure symbols and seven
  method order, and applies 15 expression plus four statement substitutions.
  The inherited `_replace_exact` requires exactly one occurrence per function.
  Complete ordered candidate AST comparison includes imports, Verdict,
  constructor, signatures, annotations, decorators, method bodies and extra
  statements; only the initial module docstring is excluded.
- `trading_system/tree_spec/claim_verifier_source.py:104` invokes the actual
  lifecycle audit, which invokes the tracker-admission audit. This closes the
  real DeskSuccess, voice/bar geometry, pricing.entry_zone and canonical-symbol
  projections rather than accepting dependency names or manifest booleans.
  Failed dependencies propagate blockers, including an explicit fallback when
  the dependency reports false verification without a blocker list entry.
- The 25 candidate mutations exercise tolerance, fill slack, strict/inclusive
  boundaries, fill-bar inclusion, claim/stop clocks, grace, venue selection,
  request/decoder, routing, proof, imports, constructor and class/signature drift.
  Additional tests cover source bytes/order/duplicates, pins/baseline, missing
  files, actual DeskSuccess/pricing drift, unrelated working directories and
  prohibited runtime/source imports. Audit code parses source/candidate text;
  it does not execute either implementation.
- CLI requires an explicit source root, emits JSON for audit outcomes, and
  returns VERIFIED/0 or BLOCKED/2. Successful and blocked reports retain false
  replay/training readiness. Missing required arguments correctly use argparse
  exit 2 rather than an audit JSON report.

Open questions: None blocking Task2. No changes requested.

Recommended next action: Controller may use this review for Task2 intake and
perform its own combined acceptance with the separate Task1 review. Integration
and the next source/provider design remain with the controller.

Verification reviewed:

1. Read startup instructions/protocol, inspected Codex inbox, read the complete
   current verifier plan/contract/usage and applicable design/source-intake
   instructions. Read the actual three Task2 files, complete package, verifier
   runtime and retained verify.py, inherited lifecycle/tracker auditors and their
   helpers, and the relevant DeskSuccess/pricing/canonical implementations.
   Applied the code-reviewer checklist directly; no nested reviewer.
2. Inspected `git status --short`, `git diff --stat`, and
   `git diff -- AGENTS.md README.md`. HEAD is
   `c1b6071633c55376c64f0a98ece843706f420f49`. The three additions are untracked,
   so review used their full actual contents. In-memory package reconstruction
   matched all three files exactly after ordinary text newline normalization.
3. PASS, exit 0:
   `$env:PYTHONDONTWRITEBYTECODE='1'; python -B -m pytest tests/tree_spec/test_claim_verifier_source.py -q --tb=short -p no:cacheprovider`
   -> **37 passed in 34.30s**. This includes the actual inherited audits and
   guarded subprocess import test. No broad or combined suite was duplicated.
4. PASS, exit 0:
   `python -B tools/check_claim_verifier_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`
   -> VERIFIED, empty blockers, one verifier projection plus three lifecycle
   and seven tracker/dependency projections; both readiness flags false.
5. PASS: independent `python -B -` in-memory AST probes exercised all 19 allowed
   substitutions at counts zero and two. Each of the **38 cases** raised
   `SUBSTITUTION_PRECONDITION` with the expected count. No source/candidate file
   was edited: each probe parsed the source afresh, removed or duplicated only
   the selected expression/statement, then called `_projection` on its unparse.
6. PASS: three in-memory dependency probes supplied false verification with
   empty blockers, false verification with a sentinel blocker, and OSError.
   They produced `DEPENDENCY:NOT_VERIFIED`, `DEPENDENCY:sentinel`, and
   `DEPENDENCY_UNREADABLE:OSError`, respectively, with BLOCKED/false readiness.
   Two Path.read_text interception probes appended a raising top-level statement
   separately to source and candidate text. Both blocked with the appropriate
   blob/AST mismatch without executing the statement. These are **five separate
   probes**, not additional pytest cases.
7. PASS: independent `python -B -` subprocess harness launched the absolute CLI
   from `C:/Users/roeea/sagiv-repos`, using the explicit retained root (VERIFIED,
   exit 0), a nonexistent `traders-engine/__claim_review_missing_source__` path
   (BLOCKED JSON, exit 2), and no arguments (required-root error, exit 2).
   Both JSON responses had both readiness flags false. No fixture files needed.
8. `git hash-object` identities for the reviewed additions match the package:
   - claim_verifier_source.py: `7c3e497aac46bb1dd25d4310a8a9bd1aa4412455`
   - check_claim_verifier_source_parity.py: `4eaa334adf56814dee64ee74d32ce5b957d2bd79`
   - test_claim_verifier_source.py: `1d12495ca3c2239bc6bacf514cd97dc8fe6faf6f`
   Runtime inspected: `683aa8c57c9e226aead575ca83da0a53ebeaa2c5`.

Limits: Main's historical RED/GREEN and combined-suite claims were read, not
independently reproduced or adopted as this review's results. Task1 behavior
review is separate. This establishes bounded source-projection fidelity, not
causal provider correctness, full caller/lifecycle parity, economic execution,
labels, dataset or training readiness. No source execution, network/data/live
operations, implementation/test/inbox/status edits, commits or cleanup occurred.
Only this requested report was written, via apply_patch.
