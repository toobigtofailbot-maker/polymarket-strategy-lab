import json
from pathlib import Path

from src.paper_trading.cli import _parser, main

from conftest import make_engine


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
