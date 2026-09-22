"""Read a pinned HTML guide as data; never evaluate its JavaScript.

This deliberately supports one source format. A changed format must be reviewed,
not accepted by a permissive parser that silently loses trading requirements.
Graph drawing code is preserved in the artifact but is not interpreted here.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


SECTION_SHAPES = {
    "layers": (22, 6),
    "trRows": (14, 5),
    "trKnowledgeRows": (12, 4),
    "sharedRows": (8, 4),
    "ofRows": (18, 4),
    "optionsRows": (19, 4),
    "runtimeRows": (15, 4),
    "governanceRows": (8, 4),
}
LAYER_KEYS = ("title", "kind", "ask", "checks", "output", "next")
JSON_STRING = r'"(?:[^"\\]|\\.)*"'
LAYER_PATTERN = re.compile(
    r"\{\s*"
    + r"\s*,\s*".join(key + r"\s*:\s*(" + JSON_STRING + ")" for key in LAYER_KEYS)
    + r"\s*\}",
    re.DOTALL,
)


@dataclass(frozen=True)
class SourceUnit:
    unit_id: str
    section: str
    title: str
    question: str
    checks: str
    output: str
    note: str
    kind: str
    line_start: int
    line_end: int


@dataclass(frozen=True)
class SourceCatalog:
    source_sha256: str
    units: tuple[SourceUnit, ...]
    open_parameters: tuple[str, ...]

    def readiness(self, *, include_units: bool = False) -> dict:
        report = {
            "import_version": "tr-hybrid-html-guide-v1",
            "source_sha256": self.source_sha256,
            "scope": "GUIDE_SOURCE_INVENTORY_ONLY",
            "section_counts": dict(Counter(unit.section for unit in self.units)),
            "source_unit_count": len(self.units),
            "open_parameters": list(self.open_parameters),
            "atomic_feature_coverage_verified": False,
            "graph_semantics_verified": False,
            "ready_for_replay": False,
            "ready_for_training": False,
            "blockers": [
                "OPEN_RESEARCH_PARAMETERS",
                "ATOMIC_CONTRACTS_NOT_VALIDATED",
                "GRAPH_SEMANTICS_NOT_VALIDATED",
                "EXECUTABLE_TREE_NOT_IMPLEMENTED",
                "REPLAY_FIDELITY_NOT_VALIDATED",
            ],
        }
        if include_units:
            report["units"] = [asdict(unit) for unit in self.units]
        return report


def _array_span(source: str, name: str) -> tuple[int, int]:
    declarations = list(re.finditer(r"\bvar\s+" + re.escape(name) + r"\s*=", source))
    if len(declarations) != 1:
        raise ValueError(f"expected exactly one declaration of {name}")
    start = declarations[0].end()
    while start < len(source) and source[start].isspace():
        start += 1
    if start == len(source) or source[start] != "[":
        raise ValueError(f"{name} must contain an inert data array")
    depth, quoted, escaped = 0, False, False
    for pos in range(start, len(source)):
        char = source[pos]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                if not source[pos + 1:].lstrip().startswith(";"):
                    raise ValueError(f"unsupported expression after {name}")
                return start + 1, pos
    raise ValueError(f"unterminated array {name}")


def _section_units(source: str, name: str) -> list[SourceUnit]:
    start, end = _array_span(source, name)
    pos = start
    units: list[SourceUnit] = []
    expected_count, expected_width = SECTION_SHAPES[name]
    decoder = json.JSONDecoder()
    while pos < end:
        while pos < end and source[pos].isspace():
            pos += 1
        if pos == end:
            break
        row_start = pos
        if name == "layers":
            match = LAYER_PATTERN.match(source, pos, end)
            if match is None:
                raise ValueError("unsupported layers object; expected six ordered string fields")
            row = [json.loads(value) for value in match.groups()]
            pos = match.end()
        else:
            try:
                row, pos = decoder.raw_decode(source, pos)
            except json.JSONDecodeError as exc:
                raise ValueError(f"unsupported data in {name}") from exc
        if pos > end or not isinstance(row, list) or len(row) != expected_width:
            raise ValueError(f"wrong row shape in {name}")
        if any(not isinstance(value, str) or not value.strip() for value in row):
            raise ValueError(f"only nonempty string fields are supported in {name}")
        if name == "layers":
            title, kind, question, checks, output, note = row
        else:
            title, question, checks, output = row[:4]
            note = row[4] if expected_width == 5 else ""
            kind = "SOURCE_EVIDENCE_UNCLASSIFIED"
        units.append(SourceUnit(
            unit_id=f"guide:{name}:{len(units)}", section=name,
            title=title, question=question, checks=checks, output=output,
            note=note, kind=kind,
            line_start=source.count("\n", 0, row_start) + 1,
            line_end=source.count("\n", 0, pos) + 1,
        ))
        while pos < end and source[pos].isspace():
            pos += 1
        if pos < end:
            if source[pos] != ",":
                raise ValueError(f"unsupported separator in {name}")
            pos += 1
    if len(units) != expected_count:
        raise ValueError(f"expected {expected_count} source units in {name}, got {len(units)}")
    if len({unit.title for unit in units}) != len(units):
        raise ValueError(f"duplicate source titles in {name}")
    if name in {"layers", "trRows", "ofRows", "optionsRows"}:
        for index, unit in enumerate(units):
            label = f"L{index}" if name == "layers" else str(index + (name != "trRows"))
            if not unit.title.startswith(label + " · "):
                raise ValueError(f"unexpected source sequence in {name}: {unit.title}")
    return units


def _open_parameters(source: str) -> tuple[str, ...]:
    pattern = re.compile(
        r'paramField\.appendChild\(node\("p",\s*"",\s*(' + JSON_STRING + r')\)\);'
    )
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError("expected exactly one explicit open parameter list")
    value = json.loads(matches[0].group(1))
    parameters = tuple(part.strip().rstrip(".") for part in value.split(";"))
    if len(parameters) != 13 or len(set(parameters)) != 13 or not all(parameters):
        raise ValueError("incomplete or unsupported open parameter list")
    return parameters


def load_catalog(path: Path, expected_sha256: str | None = None) -> SourceCatalog:
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise ValueError("source hash differs from pinned artifact")
    source = raw.decode("utf-8")
    units = tuple(unit for name in SECTION_SHAPES for unit in _section_units(source, name))
    return SourceCatalog(digest, units, _open_parameters(source))
