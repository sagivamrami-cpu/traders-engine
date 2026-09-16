# SDD ledger — plan: docs/superpowers/plans/2026-09-10-tree-pattern-readers.md

Source files completely main-read in fulltreeintake; approved architecture
continuation, no newstrategychoice. Spec/plan selfreview:

| Scope | Produced/consumed | Check |
| --- | --- | --- |
| Task1 | four real readers +2importshim -> rawframes/clocks | source exceptions, priorities and repeatedreads retained |
| Task2 | full moduleprojection consumes Task1 andreal memory/PVSRA audits | literalpins/counts/signatures and sourceorderednode inventories |
| Task1 -> Task2 | seven Task1files, exactinterfaces | class names/signatures and two-dependencyshim consistent |

No implementation started. tree-tr-memory task/finalacceptance pending, required
before this component acceptance. Existing featurecheckout, no commits/cleanup.
Main inline criticalpath; independent review sidecars. No human blocker to tests.

Task1: main read originals/generated modules;50normalmissingmoduleRED1.48s,
then166combinedGREEN1.76s; expanded66cases/182combinedGREEN1.77s. First AST
command failed PowerShell quoting before writes; stdin transformation succeeded.
Taskreview215229Z specissues(Minor M1 only)/qualityApproved. Reviewer Euler
confirmed missing rawvectorerror test, not a runtimebug; closed. Main verified
that catch is distinct from later checklistzonefetch. Added persistent rawbad-
volume fixture, actual PVSRA and memory, boxformed/countNone/bounds/order.
No runtimechanges. Must receive independent M1closure before Task1acceptance.

Task2:56normalmissingauditorRED0.24s, separate -x trace proves expectedassertion;
implemented whole4modules+shim audit with independent pins/imports/inventory/
signatures and realtwo inheritedaudits. Planned281combinedGREEN29.38s exit0
session79391terminal, before M1test addition. Candidate-only three mutations
(wrongWMdirection, wrongBrinkswindow, missingliquiditypool) each caught by
existing literalbehavioraltest. No sourceexecution/diskmutations. Current
combinedverification and Task2review/finalreview remain. Memoryaccepted215229Z.

Task 1: complete (base/HEAD c1b6071 unchanged; Task1M1test fix independently
ADDRESSED by Task2review215637Z). Task2review specPASS/qualityApproved, nofindings.
Task 2: complete at task gate; finalcomponent reviewpending. Fresh282combined
29.08s/session87426 terminal, standaloneCLI VERIFIED; currenthashes recorded
task-2-report and independentlymatched byreviewer. Euler/Galileo closed.
Next options reader is disjoint and does not change these reviewedfiles.

Final220017Z specPASS/qualityApproved/M1closed; full10filepackagematches verified
byreviewer. Main postreview sourceCLI VERIFIED/currenthashesmatch. Accepted
220345Z-codex-pattern-readers. Wegener closed. No componenttestprocess live.
Fullmaster remains active; no cleanup/commits. No parked findings.
