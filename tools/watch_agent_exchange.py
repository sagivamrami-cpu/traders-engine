from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_RESULT_DIRS = ("status", "reviews", "decisions")


@dataclass(frozen=True)
class ExchangeEvent:
    kind: str
    path: str
    status: str | None = None


Snapshot = dict[str, dict[str, Any]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_exchange_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "agent-exchange").is_dir():
            return candidate
    raise FileNotFoundError(f"agent-exchange directory not found from {start}")


def extract_field(text: str, name: str) -> str | None:
    lines = text.splitlines()
    inline = re.compile(rf"^{re.escape(name)}:\s*(.+)$")
    label = f"{name}:"
    for index, line in enumerate(lines):
        inline_match = inline.match(line)
        if inline_match:
            return inline_match.group(1).strip()
        if line.strip() == label:
            for next_line in lines[index + 1 :]:
                stripped = next_line.strip()
                if stripped:
                    return stripped
    return None


def snapshot_exchange(root: Path, result_dirs: tuple[str, ...] = DEFAULT_RESULT_DIRS) -> Snapshot:
    project_root = find_exchange_root(root)
    exchange = project_root / "agent-exchange"
    snapshot: Snapshot = {}
    for directory_name in result_dirs:
        directory = exchange / directory_name
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            stat = path.stat()
            relative_path = path.relative_to(project_root).as_posix()
            text = path.read_text(encoding="utf-8")
            snapshot[relative_path] = {
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
                "sha256": sha256_file(path),
                "status": extract_field(text, "Status"),
                "sender": extract_field(text, "Sender"),
                "target": extract_field(text, "Target"),
            }
    return snapshot


def detect_events(before: Snapshot, after: Snapshot) -> list[ExchangeEvent]:
    events: list[ExchangeEvent] = []
    for path in sorted(set(after) - set(before)):
        events.append(ExchangeEvent("new", path, after[path].get("status")))
    for path in sorted(set(before) & set(after)):
        if before[path].get("sha256") != after[path].get("sha256"):
            events.append(ExchangeEvent("modified", path, after[path].get("status")))
    for path in sorted(set(before) - set(after)):
        events.append(ExchangeEvent("deleted", path, before[path].get("status")))
    return events


def load_state(path: Path) -> Snapshot:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    files = payload.get("files", {})
    if not isinstance(files, dict):
        raise ValueError(f"invalid watch state file: {path}")
    return files


def write_state(path: Path, snapshot: Snapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": "agent-exchange-watch-state-0.1.0", "files": snapshot}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_snapshot(snapshot: Snapshot) -> None:
    print("# Agent Exchange Watch")
    print(f"\nResult files: {len(snapshot)}")
    if not snapshot:
        return
    print()
    for path, metadata in sorted(snapshot.items()):
        status = metadata.get("status") or "UNKNOWN"
        sender = metadata.get("sender") or "UNKNOWN"
        target = metadata.get("target") or "UNKNOWN"
        print(f"- `{path}` status={status} sender={sender} target={target}")


def print_events(events: list[ExchangeEvent]) -> None:
    print("# Agent Exchange Events")
    print(f"\nEvents: {len(events)}")
    if not events:
        return
    print()
    for event in events:
        status = event.status or "UNKNOWN"
        print(f"- {event.kind}: `{event.path}` status={status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch agent-exchange result folders for new or updated agent outputs.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root or child directory.")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="Watch state JSON path. Defaults to the system temp directory.",
    )
    parser.add_argument("--once", action="store_true", help="Print the current result snapshot and exit.")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Seconds between polls while waiting.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3600.0,
        help="Maximum seconds to wait for an event.",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Keep watching after each detected event.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = find_exchange_root(args.root)
    root_hash = hashlib.sha256(str(project_root).encode("utf-8")).hexdigest()[:12]
    state_file = args.state_file or Path(tempfile.gettempdir()) / f"agent-exchange-watch-{root_hash}.json"
    current = snapshot_exchange(project_root)

    if args.once:
        print_snapshot(current)
        return 0

    previous = load_state(state_file)
    if not previous:
        write_state(state_file, current)
        previous = current
        print(f"Initialized watch state at `{state_file}` with {len(previous)} result files.")

    deadline = time.monotonic() + args.timeout
    while True:
        latest = snapshot_exchange(project_root)
        events = detect_events(previous, latest)
        if events:
            print_events(events)
            write_state(state_file, latest)
            if not args.continuous:
                return 0
            previous = latest
        if time.monotonic() >= deadline:
            print("No agent-exchange result events detected before timeout.")
            return 1
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    sys.exit(main())
