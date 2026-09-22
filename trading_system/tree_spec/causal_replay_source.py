"""Read-only source proof for the retained market-watch outer-pass order.

The auditor parses retained text only.  It never imports, compiles, or executes
the chart-desk checkout, and it intentionally leaves all replay/training
readiness false.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOB = "f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b"
FLOOR_COMMIT = "d827dd792cbd1d396b4ee325879c63e57388e07a"
OUTER_ADMISSION_DEPENDENCIES = {
    "entry_quality": {
        "repository": "chart-desk", "commit": COMMIT,
        "path": "chartdesk/entry_quality.py", "blob": "0cd76eb8c607690610f4559e5946a60e8f7647ac",
        "function": "evaluate",
    },
    "hunting_window": {
        "repository": "chart-desk", "commit": COMMIT,
        "path": "chartdesk/windows.py", "blob": "53453b73e7f0c48647945e7d58ba6b30ed8d4102",
        "function": "outside_reason",
    },
    "entry_clock": {
        "repository": "trading-floor", "commit": FLOOR_COMMIT,
        "path": "floor/marketclock.py", "blob": "246b01255a2203e2a04c2ef7d549f67087b4f2c9",
        "function": "entry_blocked",
    },
}
REQUIRED_ORDER = (
    "watch_state_load",
    "watch_state_preproducer_save",
    "tracker_closed_pass",
    "tracker_gate",
    "level_reversal_find",
    "level_reversal_outer_gates",
    "level_reversal_record_alert_guard",
    "watch_state_final_save",
)
UNWIRED_OUTER_ADMISSION = (
    "windows",
    "market_closed",
    "producer_arbitration",
    "post_stop",
    "occupied_slot",
    "same_level",
)
OUTER_ADMISSION_GATE_ORDER = (
    "entry_quality_annotation",
    "tradeable_plan",
    "hunting_window",
    "entry_clock",
    "post_stop",
    "occupied_slot",
    "same_level",
    "active_reversal",
    "episode",
    "record_alert_guard",
    "record",
)
EXPECTED_CONTRACT = {
    "schema_version": "causal-replay-source-contracts-v1",
    "repository": {"name": "chart-desk", "commit": "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"},
    "market_watch": {
        "path": "scripts/market_watch.py",
        "git_blob_sha1": "f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b",
        "main": "main",
    },
    "required_order": list(REQUIRED_ORDER),
    "outer_admission_gate_order": list(OUTER_ADMISSION_GATE_ORDER),
    "outer_admission_dependencies": OUTER_ADMISSION_DEPENDENCIES,
    "unwired_outer_admission": list(UNWIRED_OUTER_ADMISSION),
    "scope": "Static source-pinned market_watch outer-pass intake only; no replay runtime, tracker registration, delivery, economics, dataset, training, or model behavior.",
    "ready_for_replay": False,
    "ready_for_training": False,
}
SOURCE_LINES = {
    "watch_state_load": 494,
    "watch_state_preproducer_save": 905,
    "tracker_closed_pass": 964,
    "tracker_gate": 972,
    "level_reversal_find": 1014,
    "level_reversal_record_alert_guard": 1066,
    "level_reversal_record": 1069,
    "tree_walk": 1239,
    "engine_build": 1449,
    "watch_state_final_save": 1599,
}
OUTER_GATE_CONTROL_LINES = {
    "windows": 1035,
    "market_closed": 1040,
    "post_stop": 1045,
    "occupied_slot": 1048,
    "same_level": 1052,
    "producer_arbitration": 1062,
}
OUTER_GATE_PREDICATES = {
    "windows": "outside",
    "market_closed": "closed",
    "post_stop": "cool",
    "occupied_slot": "_trk.has_open(sym, plan.direction)",
    "same_level": "same",
    # The source's producer-arbitration assignment is coupled to its actual
    # duplicate-record rejection branch; it has no invented public boolean.
    "producer_arbitration": "st.get(state_key)",
}
OUTER_ADMISSION_GATE_LINES = {
    "entry_quality_annotation": 1019,
    "tradeable_plan": 1028,
    "hunting_window": 1034,
    "entry_clock": 1039,
    "post_stop": 1044,
    "occupied_slot": 1048,
    "same_level": 1051,
    "active_reversal": 1060,
    "episode": 1062,
    "record_alert_guard": 1066,
    "record": 1069,
}


def _empty_report():
    return {
        "status": "BLOCKED",
        "source_subset_verified": False,
        "blockers": [],
        "checked_projections": [],
        "projection": {},
        "source_commits": {"chart-desk": COMMIT, "trading-floor": FLOOR_COMMIT},
        "ready_for_replay": False,
        "ready_for_training": False,
    }


def _blocked(report, *blockers):
    result = _empty_report()
    result["projection"] = report.get("projection", {}) if isinstance(report, dict) else {}
    values = [str(blocker) for blocker in blockers if isinstance(blocker, str) and blocker]
    result["blockers"] = values or ["AUDIT_UNREADABLE:UnknownError"]
    return result


def _verified(report, projection):
    result = _empty_report()
    result.update({
        "status": "VERIFIED",
        "source_subset_verified": True,
        "blockers": [],
        "checked_projections": list(REQUIRED_ORDER),
        "projection": projection,
    })
    return result


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _read_contract():
    path = ROOT / "configs/trees/causal-replay-source-contracts.json"
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _git(repo: Path, *args: str) -> str:
    """Use local rev-parse only; source hooks, fetches, and prompts stay disabled."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", str(repo), "rev-parse", *args],
        env=env, text=True, encoding="utf-8", capture_output=True, timeout=10, check=True,
    )
    return result.stdout.strip()


def _blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("utf-8") + raw).hexdigest()


def _read_pinned_text(source_root: Path, *, repository: str, commit: str, path: str, blob: str) -> str:
    repo = source_root / repository
    if Path(_git(repo, "--show-toplevel")).resolve() != repo.resolve():
        raise ValueError("NOT_REPOSITORY_ROOT")
    if _git(repo, "HEAD") != commit:
        raise ValueError("SOURCE_COMMIT_MISMATCH")
    source_path = repo / path
    # Text decoding normalizes the retained checkout's CRLF working-tree form
    # to the LF byte sequence recorded in its pinned Git blob.
    text = source_path.read_text(encoding="utf-8")
    raw = text.encode("utf-8")
    if _blob_sha1(raw) != blob:
        raise ValueError(f"SOURCE_BLOB_MISMATCH:{path}")
    return text


def _read_pinned_market_watch(source_root: Path) -> str:
    return _read_pinned_text(
        source_root, repository="chart-desk", commit=COMMIT,
        path="scripts/market_watch.py", blob=BLOB,
    )


def _outer_admission_dependency_projection(source_root: Path) -> dict[str, dict[str, str]]:
    projection: dict[str, dict[str, str]] = {}
    for name, dependency in OUTER_ADMISSION_DEPENDENCIES.items():
        text = _read_pinned_text(
            source_root, repository=dependency["repository"], commit=dependency["commit"],
            path=dependency["path"], blob=dependency["blob"],
        )
        tree = ast.parse(text)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name == dependency["function"]]
        if len(functions) != 1:
            raise ValueError(f"OUTER_DEPENDENCY_FUNCTION_MISMATCH:{name}")
        projection[name] = {
            "repository": dependency["repository"], "path": dependency["path"],
            "function": dependency["function"],
        }
    return projection


def _dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        value = _dotted(node.value)
        return f"{value}.{node.attr}" if value else None
    return None


def _calls(main, dotted):
    return [node for node in ast.walk(main) if isinstance(node, ast.Call) and _dotted(node.func) == dotted]


def _one_line(main, dotted):
    rows = _calls(main, dotted)
    if len(rows) != 1:
        raise ValueError(f"CALL_SET_MISMATCH:{dotted}")
    return rows[0].lineno


def _call_at(main, dotted, line):
    rows = [node for node in _calls(main, dotted) if node.lineno == line]
    if len(rows) != 1:
        raise ValueError(f"CALL_LINE_MISMATCH:{dotted}:{line}")
    return line


def _call_node_at(main, dotted, line):
    rows = [node for node in _calls(main, dotted) if node.lineno == line]
    if len(rows) != 1:
        raise ValueError(f"CALL_LINE_MISMATCH:{dotted}:{line}")
    return rows[0]


def _unique_main(tree):
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(functions) != 1:
        raise ValueError("MAIN_FUNCTION_SET_MISMATCH")
    return functions[0]


def _find_if(main, line):
    rows = [node for node in ast.walk(main) if isinstance(node, ast.If) and node.lineno == line]
    if len(rows) != 1:
        raise ValueError(f"IF_SET_MISMATCH:{line}")
    return rows[0]


def _has_telegram_guard(node):
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.NotIn)
        and isinstance(test.left, ast.Constant)
        and test.left.value == "--telegram"
        and len(test.comparators) == 1
        and _dotted(test.comparators[0]) == "sys.argv"
    )


def _locked_pass(main):
    rows = [node for node in ast.walk(main) if isinstance(node, ast.With) and node.lineno == 963]
    if len(rows) != 1 or len(rows[0].items) != 1:
        raise ValueError("TRACKER_LOCK_MISMATCH")
    context = rows[0].items[0].context_expr
    if not isinstance(context, ast.Call) or _dotted(context.func) != "tracker._locked":
        raise ValueError("TRACKER_LOCK_MISMATCH")
    keywords = {keyword.arg: keyword.value for keyword in context.keywords}
    if (not isinstance(keywords.get("wait"), ast.Constant) or keywords["wait"].value != 30.0
            or not isinstance(keywords.get("skip_if_busy"), ast.Constant)
            or keywords["skip_if_busy"].value is not True):
        raise ValueError("TRACKER_LOCK_MISMATCH")
    expected = ast.parse("_msgs = tracker.closeout_check() + tracker.check()").body[0]
    if len(rows[0].body) != 1 or ast.dump(rows[0].body[0], include_attributes=False) != ast.dump(expected, include_attributes=False):
        raise ValueError("TRACKER_CLOSED_PASS_MISMATCH")
    return rows[0].body[0].lineno


def _assignment(main, target, value, *, line=None):
    rows = []
    for node in ast.walk(main):
        if (not isinstance(node, ast.Assign) or len(node.targets) != 1
                or ast.unparse(node.targets[0]) != target):
            continue
        if ((isinstance(node.value, ast.Call) and _dotted(node.value.func) == value)
                or (isinstance(node.value, ast.Name) and node.value.id == value)):
            rows.append(node)
    if line is not None:
        rows = [node for node in rows if node.lineno == line]
    if len(rows) != 1:
        raise ValueError(f"ASSIGNMENT_SET_MISMATCH:{target}")
    return rows[0]


def _assignment_line(main, target, value, *, line=None):
    return _assignment(main, target, value, line=line).lineno


def _parents(main):
    result = {}
    for parent in ast.walk(main):
        for child in ast.iter_child_nodes(parent):
            result[id(child)] = parent
    return result


def _nearest_loop(node, parents):
    current = parents.get(id(node))
    while current is not None:
        if isinstance(current, (ast.For, ast.AsyncFor, ast.While)):
            return current
        current = parents.get(id(current))
    return None


def _same_expression(node, expression):
    expected = ast.parse(expression, mode="eval").body
    return ast.dump(node, include_attributes=False) == ast.dump(expected, include_attributes=False)


def _rejects_before_record(gate, record, reversal_loop, parents):
    if gate.lineno >= record.lineno or _nearest_loop(gate, parents) is not reversal_loop:
        return False
    return any(
        isinstance(statement, ast.Continue)
        and _nearest_loop(statement, parents) is reversal_loop
        for statement in gate.body
    )


def _validate_outer_gate_controls(main, record):
    """Require the retained predicates and their rejection paths, not just calls."""
    parents = _parents(main)
    reversal_loop = _nearest_loop(record, parents)
    if reversal_loop is None:
        raise ValueError("LEVEL_REVERSAL_RECORD_LOOP_MISMATCH")
    for name in UNWIRED_OUTER_ADMISSION:
        gate = _find_if(main, OUTER_GATE_CONTROL_LINES[name])
        if (not _same_expression(gate.test, OUTER_GATE_PREDICATES[name])
                or not _rejects_before_record(gate, record, reversal_loop, parents)):
            raise ValueError(f"OUTER_GATE_CONTROL_MISMATCH:{name}")


def _validate_outer_admission_gate_order(main, record, guard):
    """Validate every source stop point from annotation through registration."""
    parents = _parents(main)
    reversal_loop = _nearest_loop(record, parents)
    if reversal_loop is None:
        raise ValueError("LEVEL_REVERSAL_RECORD_LOOP_MISMATCH")
    annotation = _call_node_at(main, "_score_entry", OUTER_ADMISSION_GATE_LINES["entry_quality_annotation"])
    if _nearest_loop(annotation, parents) is not reversal_loop:
        raise ValueError("OUTER_GATE_ORDER_MISMATCH:entry_quality_annotation")
    tradeable = _find_if(main, OUTER_ADMISSION_GATE_LINES["tradeable_plan"])
    if (not _same_expression(tradeable.test, "not plan.tradeable")
            or not _rejects_before_record(tradeable, record, reversal_loop, parents)):
        raise ValueError("OUTER_GATE_ORDER_MISMATCH:tradeable_plan")
    episode = _find_if(main, OUTER_ADMISSION_GATE_LINES["episode"])
    if (not _same_expression(episode.test, "st.get(state_key)")
            or not _rejects_before_record(episode, record, reversal_loop, parents)):
        raise ValueError("OUTER_GATE_ORDER_MISMATCH:episode")
    active_reversal = _assignment(
        main, "active_reversals[sym]", "plan", line=OUTER_ADMISSION_GATE_LINES["active_reversal"],
    )
    if _nearest_loop(active_reversal, parents) is not reversal_loop:
        raise ValueError("OUTER_GATE_ORDER_MISMATCH:active_reversal")
    if (not _has_telegram_guard(guard) or not _rejects_before_record(guard, record, reversal_loop, parents)):
        raise ValueError("OUTER_GATE_ORDER_MISMATCH:record_alert_guard")
    return {
        "entry_quality_annotation": annotation.lineno,
        "tradeable_plan": tradeable.lineno,
        "hunting_window": _call_at(main, "_outside", OUTER_ADMISSION_GATE_LINES["hunting_window"]),
        "entry_clock": _call_at(main, "_mc.entry_blocked", OUTER_ADMISSION_GATE_LINES["entry_clock"]),
        "post_stop": _call_at(main, "_trk.blocked_after_stop", OUTER_ADMISSION_GATE_LINES["post_stop"]),
        "occupied_slot": _call_at(main, "_trk.has_open", OUTER_ADMISSION_GATE_LINES["occupied_slot"]),
        "same_level": _call_at(main, "_trk.blocked_same_level", OUTER_ADMISSION_GATE_LINES["same_level"]),
        "active_reversal": active_reversal.lineno,
        "episode": episode.lineno,
        "record_alert_guard": guard.lineno,
        "record": record.lineno,
    }


def _project_required_order(main, outer_admission_dependencies):
    read_lines = [node.lineno for node in _calls(main, "STATE.read_text")]
    write_lines = [node.lineno for node in _calls(main, "STATE.write_text")]
    if read_lines != [SOURCE_LINES["watch_state_load"]] or write_lines != [
        SOURCE_LINES["watch_state_preproducer_save"], SOURCE_LINES["watch_state_final_save"],
    ]:
        raise ValueError("WATCH_STATE_IO_MISMATCH")
    locked_line = _locked_pass(main)
    gate_line = _call_at(main, "tracker.gate", SOURCE_LINES["tracker_gate"])
    reversal_line = _one_line(main, "level_reversal.find")
    tree_line = _one_line(main, "_tree.walk")
    engine_line = _one_line(main, "tradeplan.build_all")
    record = _assignment(main, "recorded", "_trk.record", line=SOURCE_LINES["level_reversal_record"])
    record_line = record.lineno
    guard = _find_if(main, SOURCE_LINES["level_reversal_record_alert_guard"])
    if (not _has_telegram_guard(guard) or len(guard.body) != 1
            or not isinstance(guard.body[0], ast.Continue)
            or record_line <= guard.lineno):
        raise ValueError("LEVEL_REVERSAL_RECORD_GUARD_MISMATCH")
    gate_lines = {
        "windows": _call_at(main, "_outside", 1034),
        "market_closed": _call_at(main, "_mc.entry_blocked", 1039),
        "post_stop": _call_at(main, "_trk.blocked_after_stop", 1044),
        "occupied_slot": _call_at(main, "_trk.has_open", 1048),
        "same_level": _call_at(main, "_trk.blocked_same_level", 1051),
        "producer_arbitration": _assignment_line(main, "active_reversals[sym]", "plan", line=1060),
    }
    _validate_outer_gate_controls(main, record)
    outer_admission_gate_lines = _validate_outer_admission_gate_order(main, record, guard)
    return {
        "required_order": list(REQUIRED_ORDER),
        "source_lines": {
            **SOURCE_LINES,
            "tracker_closed_pass": locked_line,
            "tracker_gate": gate_line,
            "level_reversal_find": reversal_line,
            "level_reversal_record": record_line,
            "tree_walk": tree_line,
            "engine_build": engine_line,
        },
        "level_reversal_record_guard": "--telegram",
        "outer_admission_gate_order": list(OUTER_ADMISSION_GATE_ORDER),
        "outer_admission_gate_lines": outer_admission_gate_lines,
        "outer_admission_dependencies": outer_admission_dependencies,
        "unwired_outer_admission": {name: "UNWIRED_OUTER_ADMISSION" for name in UNWIRED_OUTER_ADMISSION},
        "outer_gate_lines": gate_lines,
    }


def _validate_projection(projection):
    try:
        if projection["required_order"] != list(REQUIRED_ORDER):
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        if projection["outer_admission_gate_order"] != list(OUTER_ADMISSION_GATE_ORDER):
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        if projection["outer_admission_gate_lines"] != OUTER_ADMISSION_GATE_LINES:
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        if projection["outer_admission_dependencies"] != {
            name: {key: value for key, value in dependency.items()
                   if key in {"repository", "path", "function"}}
            for name, dependency in OUTER_ADMISSION_DEPENDENCIES.items()
        }:
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        if projection["source_lines"] != SOURCE_LINES:
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        gate_lines = projection["outer_gate_lines"]
        record = projection["source_lines"]["level_reversal_record"]
        if set(gate_lines) != set(UNWIRED_OUTER_ADMISSION) or any(line >= record for line in gate_lines.values()):
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        if not (
            projection["source_lines"]["watch_state_load"]
            < projection["source_lines"]["watch_state_preproducer_save"]
            < projection["source_lines"]["tracker_closed_pass"]
            < projection["source_lines"]["tracker_gate"]
            < projection["source_lines"]["level_reversal_find"]
            < record
            < projection["source_lines"]["watch_state_final_save"]
        ):
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        if not (projection["source_lines"]["level_reversal_find"] < projection["source_lines"]["tree_walk"]
                and projection["source_lines"]["level_reversal_find"] < projection["source_lines"]["engine_build"]):
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        admission_lines = projection["outer_admission_gate_lines"]
        if list(admission_lines) != list(OUTER_ADMISSION_GATE_ORDER) or list(admission_lines.values()) != sorted(admission_lines.values()):
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        if projection["level_reversal_record_guard"] != "--telegram":
            return ["MARKET_WATCH_ORDER_MISMATCH"]
        if (set(projection["unwired_outer_admission"]) != set(UNWIRED_OUTER_ADMISSION)
                or set(projection["unwired_outer_admission"].values()) != {"UNWIRED_OUTER_ADMISSION"}):
            return ["MARKET_WATCH_ORDER_MISMATCH"]
    except Exception:
        return ["MARKET_WATCH_ORDER_MISMATCH"]
    return []


def check_source_parity(source_root: Path) -> dict:
    """Read/parses ``source_root/chart-desk/scripts/market_watch.py`` only."""
    report = _empty_report()
    try:
        if _canonical(_read_contract()) != _canonical(EXPECTED_CONTRACT):
            return _blocked(report, "CONTRACT_MISMATCH")
    except BaseException as exc:
        return _blocked(report, f"CONTRACT_UNREADABLE:{type(exc).__name__}")
    try:
        root = Path(source_root)
        source = _read_pinned_market_watch(root)
        outer_admission_dependencies = _outer_admission_dependency_projection(root)
        main = _unique_main(ast.parse(source))
    except BaseException as exc:
        message = str(exc)
        if (message in {"NOT_REPOSITORY_ROOT", "SOURCE_COMMIT_MISMATCH"}
                or message.startswith("SOURCE_BLOB_MISMATCH:")):
            return _blocked(report, message)
        return _blocked(report, f"SOURCE_READ_OR_PARSE:{type(exc).__name__}")
    try:
        projection = _project_required_order(main, outer_admission_dependencies)
    except BaseException:
        return _blocked(report, "MARKET_WATCH_ORDER_MISMATCH")
    blockers = _validate_projection(projection)
    if blockers:
        return _blocked({**report, "projection": projection}, *blockers)
    return _verified(report, projection)
