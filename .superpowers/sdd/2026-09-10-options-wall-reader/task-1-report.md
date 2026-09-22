# Options reader Task1 report

Actual source status/load/anchor reader over raw report JSON/CSV and clock;
originalpurehelpers/classes/constants retained. Inert AST extraction checked
complete3methodsignatures, exactly3import/2globalremovals and7expressionchanges.
Main read full211lineoriginal and generatedmodule. No retainedsourceexecution.

RED: python -B -m pytest tests/tree_replay/test_optionswall.py -q --tb=short -x
-p no:cacheprovider => expected missingmodulefailure0.80s. Fullsamefile --tb=no
without-x =>38normalmissingmodulefailures0.74s. Thenruntime added viaapply_patch.
GREEN: python -B -m pytest tests/tree_replay/test_optionswall.py
tests/tree_replay/test_pattern_readers.py -q --tb=short -p no:cacheprovider
=>105passed1.22s exit0, no warnings, no code/testchanges afterwards.

Literalrawfixtures cover frozenratio/currentprice independence, originalports
and order, supportedmappings/noGC, failure reasons/no fallback, age boundaries,
explicitclock/naiveUTC, optional exactsrc/75minuteanchor/futureexclusion/latest
badprice, firstundegradedETF/firstliveexpiry/NYday, optionalzero/None, firstwall
nonfinite, loadcomposition and malformeddecodedreport uncaughterror.

No parsed-verdictprovider; actual pandas/json retained. Raw ports not historical
availability certification; sourcevalidation quirks retained and documented.
Task2 fullsourceaudit, task/finalreviews remain. No live/data/modelactions.
