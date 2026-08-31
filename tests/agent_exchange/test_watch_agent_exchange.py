from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.watch_agent_exchange import (
    detect_events,
    load_state,
    snapshot_exchange,
    write_state,
)


def write_exchange_file(root: Path, relative_path: str, text: str = "content") -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_snapshot_exchange_tracks_result_markdown_files(tmp_path: Path):
    write_exchange_file(tmp_path, "agent-exchange/status/2026-status.md")
    write_exchange_file(tmp_path, "agent-exchange/reviews/2026-review.md")
    write_exchange_file(tmp_path, "agent-exchange/decisions/2026-decision.md")
    write_exchange_file(tmp_path, "agent-exchange/inbox/codex/2026-request.md")

    snapshot = snapshot_exchange(tmp_path)

    assert set(snapshot) == {
        "agent-exchange/decisions/2026-decision.md",
        "agent-exchange/reviews/2026-review.md",
        "agent-exchange/status/2026-status.md",
    }


def test_detect_events_reports_new_and_modified_result_files(tmp_path: Path):
    status_file = write_exchange_file(
        tmp_path,
        "agent-exchange/status/2026-claude-status.md",
        "initial",
    )
    before = snapshot_exchange(tmp_path)
    status_file.write_text("updated content", encoding="utf-8")
    write_exchange_file(tmp_path, "agent-exchange/reviews/2026-groq-review.md")
    after = snapshot_exchange(tmp_path)

    events = detect_events(before, after)

    assert [(event.kind, event.path) for event in events] == [
        ("new", "agent-exchange/reviews/2026-groq-review.md"),
        ("modified", "agent-exchange/status/2026-claude-status.md"),
    ]


def test_state_file_round_trip(tmp_path: Path):
    write_exchange_file(tmp_path, "agent-exchange/status/2026-status.md")
    snapshot = snapshot_exchange(tmp_path)
    state_file = tmp_path / "agent-exchange/.watch-state.json"

    write_state(state_file, snapshot)

    assert load_state(state_file) == snapshot
    assert json.loads(state_file.read_text(encoding="utf-8"))["files"] == snapshot


def test_cli_once_prints_current_result_files(tmp_path: Path):
    write_exchange_file(
        tmp_path,
        "agent-exchange/status/2026-claude-status.md",
        "# Status\n\nStatus:\nIMPLEMENTED_AWAITING_CODEX_REVIEW\n",
    )

    result = subprocess.run(
        [
            sys.executable,
            "tools/watch_agent_exchange.py",
            "--root",
            str(tmp_path),
            "--once",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Agent Exchange Watch" in result.stdout
    assert "agent-exchange/status/2026-claude-status.md" in result.stdout
    assert "IMPLEMENTED_AWAITING_CODEX_REVIEW" in result.stdout
