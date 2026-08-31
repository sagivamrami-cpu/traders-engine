from pathlib import Path

from tools.validate_phase0 import load_yaml, validate_node_registry

ROOT = Path(__file__).resolve().parents[2]


def test_node_registry_has_required_layers_and_runtime_stages():
    path = ROOT / "configs/graphs/node-registry.yaml"
    validate_node_registry(path)
    registry = load_yaml(path)
    assert [layer["id"] for layer in registry["layers"]] == [f"L{i}" for i in range(22)]
    assert registry["tr_runtime_stages"] == [
        "DATA",
        "POSITION",
        "SESSION",
        "LOCATION",
        "CYCLE",
        "CONTEXT",
        "PATTERN",
        "VECTOR",
        "TRAP",
        "RETEST",
        "TARGET_RISK",
        "TRIGGER",
        "SCALE_IN",
        "INVALIDATION",
    ]


def test_node_registry_keeps_hard_gates_deterministic():
    registry = load_yaml(ROOT / "configs/graphs/node-registry.yaml")
    hard_gate_types = {"GLOBAL_HARD_GATE", "GRAPH_ELIGIBILITY_GATE"}
    for node in registry["nodes"]:
        if node["type"] in hard_gate_types:
            assert node["learned"] is False
