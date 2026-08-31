from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FeatureEngine:
    engine_id: str
    engine_version: str
    deterministic: bool
    feature_ids: tuple[str, ...]


@dataclass(frozen=True)
class FeatureEngineRegistry:
    version: str
    engines: dict[str, FeatureEngine]


def load_feature_engine_registry(path: Path) -> FeatureEngineRegistry:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    engines = {
        engine["engine_id"]: FeatureEngine(
            engine_id=engine["engine_id"],
            engine_version=engine["engine_version"],
            deterministic=bool(engine["deterministic"]),
            feature_ids=tuple(engine["feature_ids"]),
        )
        for engine in data["engines"]
    }
    return FeatureEngineRegistry(version=data["version"], engines=engines)
