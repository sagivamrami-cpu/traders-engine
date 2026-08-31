from pathlib import Path

from tools.validate_phase0 import (
    load_yaml,
    validate_feature_catalog,
    validate_label_contracts,
    validate_node_registry,
    validate_priority_register,
    validate_required_files,
)

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


def test_feature_catalog_has_null_semantics_and_required_families():
    path = ROOT / "configs/features/feature-catalog.yaml"
    validate_feature_catalog(path)
    catalog = load_yaml(path)
    assert catalog["null_semantics"] == [
        "zero",
        "false",
        "missing",
        "unknown",
        "unavailable",
        "not_applicable",
        "stale",
    ]
    family_ids = {family["id"] for family in catalog["feature_families"]}
    assert {
        "data.provenance",
        "shared.context",
        "tr.location",
        "tr.pattern",
        "tr.vector",
        "tr.retest",
        "order_flow.master",
        "options.prior",
        "regime.market",
        "risk.geometry",
    }.issubset(family_ids)


def test_label_contracts_define_candidate_snapshot_and_ambiguous_policy():
    path = ROOT / "configs/contracts/label-contracts.yaml"
    validate_label_contracts(path)
    contracts = load_yaml(path)
    assert contracts["candidate_snapshot"]["granularity"] == [
        "observation_time",
        "symbol",
        "producer",
        "graph_id",
        "candidate_direction",
        "contract_version",
    ]
    label = contracts["outcome_labels"][0]
    assert "AMBIGUOUS" in label["outcome_classes"]
    assert label["same_bar_target_and_stop_policy"] == "AMBIGUOUS_EXCLUDED_FROM_TRAINING"


def test_phase0_required_policy_files_exist():
    validate_required_files()


def test_priority_register_keeps_research_parameters_open():
    path = ROOT / "research/priority-register.yaml"
    validate_priority_register(path)
    register = load_yaml(path)
    statuses = {p["status"] for p in register["research_parameters"]}
    assert statuses == {"OPEN"}
    priorities = {p["priority"] for p in register["research_parameters"]}
    assert "P0_BLOCKS_DATASET" in priorities
    assert "P0_BLOCKS_LIVE" in priorities
