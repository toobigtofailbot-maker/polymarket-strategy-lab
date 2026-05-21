from __future__ import annotations

import json
from pathlib import Path

from tools.polymarket.export_agent_context import main


def test_cli_default_exits_zero_writes_no_file_and_prints_safety_summary(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = main([], repo_root=tmp_path)

    out = capsys.readouterr().out
    assert result == 0
    assert "output written: no" in out
    assert "no network, no credentials, no orders" in out
    assert not (tmp_path / "local_data").exists()


def test_cli_help_exits_zero(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "--include-local-report-metadata" in capsys.readouterr().out


def test_cli_explicit_output_writes_json_under_agent_context_exports(tmp_path):
    out = tmp_path / "repo" / "local_data" / "agent_context_exports" / "wp23_context.local.json"

    result = main(["--out", str(out)], repo_root=tmp_path / "repo")

    assert result == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "agent-context-export.v1"
    assert data["export_mode"] == "local_offline_read_only"
    assert "safety_boundaries" in data


def test_cli_rejects_output_outside_allowed_dir(tmp_path, capsys):
    result = main(["--out", str(tmp_path / "bad.local.json")], repo_root=tmp_path)

    assert result == 1
    assert "local_data/agent_context_exports" in capsys.readouterr().err


def test_cli_does_not_accept_network_or_credential_flags(capsys):
    for flag in ("--allow-network", "--credential", "--account", "--private-endpoint"):
        try:
            main([flag])
        except SystemExit as exc:
            assert exc.code != 0
        assert flag in capsys.readouterr().err
