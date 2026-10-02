import json
from dataclasses import asdict
from pathlib import Path

from src.paper_trading.cli import _parser, main

from tests.paper_trading.conftest import make_engine
from tests.paper_trading.conftest import generous_limits
from tests.paper_trading.test_models import _research_binding
from src.paper_trading import PaperStore


def test_wp173_paper_runtime_has_no_live_credential_or_external_network_surface(
    tmp_path, capsys
) -> None:
    path = tmp_path / "paper.sqlite3"
    store, _engine = make_engine(path)
    store.close()
    assert main(["status", "--paper-store", str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["simulated_paper_only"] is True
    assert "path" not in output
    parser = _parser()
    assert (
        "LIVE_STORE" in parser.format_help()
        or parser.parse_args(
            [
                "run",
                "--paper-store",
                str(path),
                "--mode",
                "LIVE_STORE",
                "--max-polls",
                "1",
            ]
        ).mode
        == "LIVE_STORE"
    )
    source = "\n".join(
        file.read_text(encoding="utf-8").lower()
        for file in Path("src/paper_trading").glob("*.py")
    )
    for forbidden in (
        "import requests",
        "import httpx",
        "import websockets",
        "py_clob_client",
        "api_key",
        "private_key",
        "signing",
        "def submit_order",
        "def place_order",
        ".submit_order(",
        ".place_order(",
        "execution_gateway",
        "hermes",
    ):
        assert forbidden not in source
    assert "mode=ro" in source
    assert 'choices=("replay", "live_store")' in source


def _write_json(path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _binding_input():
    value = asdict(_research_binding())
    for key in (
        "schema_version", "binding_id", "binding_kind", "research_paper_only",
        "simulated_paper_only", "qualification_claim", "executable_edge_claim",
        "wp173_qualified_evaluation_eligible", "gate_c_eligible",
        "live_promotion_eligible", "real_capital_usd",
    ):
        value.pop(key)
    return value


def test_research_init_is_finite_and_offline(tmp_path, capsys) -> None:
    store_path = tmp_path / "research.sqlite3"
    binding_path = tmp_path / "binding.json"
    limits_path = tmp_path / "limits.json"
    _write_json(binding_path, _binding_input())
    _write_json(limits_path, asdict(generous_limits()))
    assert main([
        "research-init", "--paper-store", str(store_path), "--binding", str(binding_path),
        "--limits", str(limits_path), "--session-label", "research", "--event-time-ns", "100",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["binding_kind"] == "RESEARCH_PAPER"
    assert output["research_paper_only"] is True


def test_research_snapshot_is_deterministic_read_only_and_sanitized(tmp_path, capsys) -> None:
    store_path = tmp_path / "research.sqlite3"
    binding_path = tmp_path / "binding.json"
    limits_path = tmp_path / "limits.json"
    _write_json(binding_path, _binding_input())
    _write_json(limits_path, asdict(generous_limits()))
    assert main([
        "research-init", "--paper-store", str(store_path), "--binding", str(binding_path),
        "--limits", str(limits_path), "--session-label", "research", "--event-time-ns", "100",
    ]) == 0
    capsys.readouterr()
    with PaperStore(store_path) as store:
        before = store.current_head()
    assert main(["research-snapshot", "--paper-store", str(store_path)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(["research-snapshot", "--paper-store", str(store_path)]) == 0
    second = json.loads(capsys.readouterr().out)
    with PaperStore(store_path) as store:
        after = store.current_head()
    assert first == second and before == after
    assert "path" not in first
    assert first["no_live_authority"] is True


def test_existing_paper_cli_commands_remain_compatible(tmp_path, capsys) -> None:
    path = tmp_path / "paper.sqlite3"
    store, _engine = make_engine(path)
    store.close()
    assert main(["status", "--paper-store", str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["binding_kind"] == "QUALIFIED_PAPER"
    assert output["research_paper_only"] is False
