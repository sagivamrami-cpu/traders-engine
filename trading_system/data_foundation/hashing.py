from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _stable_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_stable_value(item) for item in value]
    if isinstance(value, str):
        return value.replace("\r\n", "\n")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def stable_json_dumps(value: Any) -> str:
    return json.dumps(
        _stable_value(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = stable_json_dumps(list(rows)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
