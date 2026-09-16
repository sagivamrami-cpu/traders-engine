"""Inert independent audit of watch logger, session clock and inherited tables."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from .tracker_admission_source import _dump, _git, _replace_exact, _selected, _without_doc


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "trading_system/tree_replay/_vendor"
COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
BLOBS = {"chartdesk/sessions.py": "2f44d322178feb14b0488abda51b40581db5b31f",
         "scripts/market_watch.py": "f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b"}
ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
          subprocess.SubprocessError)


def _logger_projection(text):
    method, = _selected(text, ["_log"])
    for old, new in [("sessions.current_session()", "self.source.current_session()"),
                     ("OUT.mkdir(exist_ok=True)", "self.source.ensure_out()"),
                     ('EVENTS.open("a", encoding="utf-8")', "self.source.event_log_writer()"),
                     ("time.time()", "self.source.now_epoch()")]:
        _replace_exact(method, old, new)
    method.name = "log"
    method.args.args.insert(0, ast.arg(arg="self"))
    tree = ast.parse("import json\nclass WatchLogger:\n    def __init__(self, source):\n        self.source = source")
    tree.body[1].body.append(method)
    return tree.body


def _session_projections(text):
    mask, current = _selected(text, ["session_mask", "current_session"])
    signature = ast.parse("def current_session(now: pd.Timestamp | None = None, **kw) -> list[str]: pass").body[0]
    if _dump(current.args) != _dump(signature.args) or current.decorator_list:
        raise ValueError("SOURCE_CLOCK_SIGNATURE_MISMATCH")
    _replace_exact(current, 'pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")',
                   "pd.Timestamp(decision_time)")
    current.name = "current_session_at"
    current.args = ast.parse("def current_session_at(*, decision_time: pd.Timestamp, **kw): pass").body[0].args
    imports = ast.parse("from __future__ import annotations\nfrom zoneinfo import ZoneInfo\n"
        "import numpy as np\nimport pandas as pd\nfrom .map_sessions import SessionSpec, SESSIONS, _hm").body
    inherited_imports = ast.parse("from __future__ import annotations\nfrom dataclasses import dataclass, field\n"
        "from zoneinfo import ZoneInfo\nimport numpy as np\nimport pandas as pd").body
    # The earlier tracker selector handles plain assignments, but SESSIONS is
    # an annotated assignment. Preserve all four nodes in their actual order.
    names = ["SessionSpec", "SESSIONS", "_hm", "psy_levels"]
    inherited, found = [], []
    for node in ast.parse(text).body:
        name = (node.name if isinstance(node, (ast.ClassDef, ast.FunctionDef)) else
                node.target.id if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) else None)
        if name in names:
            inherited.append(node)
            found.append(name)
    if found != names:
        raise ValueError("SOURCE_SESSION_DEPENDENCY_ORDER_OR_SET_MISMATCH")
    return {"watch_sessions.py": imports+[mask, current],
            "map_sessions.py": inherited_imports+inherited}


def audit_watch_io_source(source_root):
    blockers = []
    report = dict(status="BLOCKED", source_subset_verified=False, blockers=blockers,
                  checked_projections=[], source_commits={"chart-desk": COMMIT},
                  ready_for_replay=False, ready_for_training=False)
    try:
        root = Path(source_root) / "chart-desk"
        if Path(_git(root, "--show-toplevel")).resolve() != root.resolve():
            blockers.append("NOT_REPOSITORY_ROOT")
        if _git(root, "HEAD") != COMMIT:
            blockers.append("SOURCE_COMMIT_MISMATCH")
        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
        if [r.get("commit") for r in baseline["repositories"] if r.get("name") == "chart-desk"] != [COMMIT]:
            blockers.append("BASELINE_COMMIT_MISMATCH")
        sources = {}
        for path, blob in BLOBS.items():
            text = (root / path).read_text(encoding="utf-8")
            data = text.encode("utf-8")  # universal newline read matches Git LF
            if hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest() != blob:
                blockers.append(f"SOURCE_BLOB_MISMATCH:{path}")
            sources[path] = text
        expected = {"watch_io.py": _logger_projection(sources["scripts/market_watch.py"])}
        expected.update(_session_projections(sources["chartdesk/sessions.py"]))
    except ERRORS as exc:
        blockers.append(f"SOURCE_UNREADABLE:{type(exc).__name__}:{exc}")
        return report
    for file, nodes in expected.items():
        try:
            actual = _without_doc(ast.parse((VENDOR / file).read_text(encoding="utf-8")))
            if [_dump(n) for n in actual] != [_dump(n) for n in nodes]:
                blockers.append(f"VENDOR_AST_MISMATCH:{file}")
        except ERRORS as exc:
            blockers.append(f"VENDOR_UNREADABLE:{file}:{type(exc).__name__}")
    if not blockers:
        report.update(status="VERIFIED", source_subset_verified=True,
                      checked_projections=["watch._log", "sessions.session_mask",
                                           "sessions.current_session", "map_sessions_dependency"])
    return report
