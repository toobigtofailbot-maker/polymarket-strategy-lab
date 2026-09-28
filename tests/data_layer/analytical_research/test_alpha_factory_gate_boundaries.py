from pathlib import Path

import pytest

from src.data_layer.analytical_research.alpha_factory_gate import AF1SeededCaseResult, af1_record_from_mapping


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src" / "data_layer" / "analytical_research" / "alpha_factory_gate.py"
OPERATOR = ROOT / "tools" / "alpha" / "run_s10_gate_af1.py"


def test_gate_source_is_local_evaluator_and_operator_is_only_runtime_boundary():
    source = SOURCE.read_text(encoding="utf-8").lower()
    for token in ("requests", "websocket", "subprocess", "time.sleep", "while true"):
        assert token not in source
    assert "polymarket_public_population" not in source
    assert "hermes_controlled_runtime" not in source
    assert OPERATOR.is_file()


def test_closed_schema_rejects_generic_undeclared_authority_key():
    mapping = {field: None for field in AF1SeededCaseResult.__dataclass_fields__}
    mapping["undeclared_authority"] = True
    with pytest.raises(ValueError, match="CLOSED_SCHEMA"):
        af1_record_from_mapping(AF1SeededCaseResult, mapping)


def test_no_blacklist_reconstruction_or_guard_exemption():
    source = SOURCE.read_text(encoding="utf-8")
    assert "exemption" not in source.lower()
    assert "join(chr" not in source.lower()
    assert "decode(" not in source.lower()


def test_af1_source_and_tool_authority_boundaries():
    source = SOURCE.read_text(encoding="utf-8").lower()
    operator = OPERATOR.read_text(encoding="utf-8").lower()
    assert "polymarket_public_population" not in source
    assert "run_blind_phase" not in source
    assert "run_blind_phase" in operator
    assert "while true" not in operator and "time.sleep" not in operator


def test_af1_closed_schema_is_lexical_guard_compatible():
    source = SOURCE.read_text(encoding="utf-8").lower()
    assert "af1_closed_schema_invalid" in source
    assert "exemption" not in source and "join(chr" not in source


def test_operator_has_no_direct_network_subprocess_credential_or_env_surface():
    operator = OPERATOR.read_text(encoding="utf-8")
    lowered = operator.lower()
    for token in (
        "import requests", "import httpx", "import socket", "urllib", "websocket",
        "subprocess", "os.environ", "getenv", "time.sleep", "while true",
    ):
        assert token not in lowered, token
    # Exactly one coordinator call site and one controller call site; no loop retries.
    assert operator.count("populate_initial_polymarket_public_data(") == 1
    assert operator.count("run_blind_phase(") == 1
    assert "retry" not in "".join(
        line for line in lowered.splitlines() if line.strip().startswith(("for ", "while "))
    )


def test_context_store_is_only_built_from_the_absolute_workspace_root():
    operator = OPERATOR.read_text(encoding="utf-8")
    assert operator.count("ContextArtifactStore(") == 1
    assert "ContextArtifactStore(context_store_root(workspace, ordinal))" in operator


def test_operator_binds_current_certified_base_and_predecessor():
    operator = OPERATOR.read_text(encoding="utf-8")
    assert 'BASE_SHA = "1ccf42df0e95586b98c79a0bf912343f9c34df31"' in operator
    assert "PREDECESSOR_PR = 195" in operator
    assert 'PREDECESSOR_HEAD_SHA = "ddc25d189359b6e365edcf08c762cb0552b7170a"' in operator
    assert 'CONSUMED_ATTEMPT_DIRECTORIES = frozenset({"attempt-01", "attempt-02", "attempt-03"})' in operator
    assert 'AUTHORIZED_ATTEMPT_DIRECTORY = "attempt-04"' in operator
    assert "46bc862018208b30971228ed719c7e9337142b41" not in operator
    assert "CURRENT_BUILD_ANALYSIS" not in operator
