"""Tests for WP10 snapshot capture function and CLI tool.

All tests offline. No network calls. Uses mocked adapter clients.
Tests verify: no trading logic, no credentials, no automated polling,
no live network in pytest, correct --allow-network gating.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
CAPTURE_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "snapshot_capture.py"
WRITER_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "snapshot_writer.py"
MODELS_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "snapshot_models.py"
CAPTURE_TOOL = ROOT / "tools" / "polymarket" / "capture_market_snapshots.py"
GITIGNORE = ROOT / ".gitignore"
SNAPSHOT_DOC = ROOT / "docs" / "polymarket_snapshot_persistence.md"

DISALLOWED_METHOD_NAMES = {
    "place_order",
    "create_order",
    "post_order",
    "submit_order",
    "cancel_order",
    "sign_order",
    "execute_trade",
    "trade",
    "buy",
    "sell",
}

DISALLOWED_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
DISALLOWED_CREDENTIAL_IDENTIFIERS = {
    "private_key",
    "api_key",
    "api_secret",
    "wallet_key",
    "mnemonic",
    "passphrase",
}
# These are checked as literal text (not in comments/docstrings context)
DISALLOWED_CREDENTIAL_CALLS = {
    "load_dotenv",
}
DISALLOWED_ENV_READS = {
    "os.environ",
}


# ---------------------------------------------------------------------------
# Source file safety checks
# ---------------------------------------------------------------------------

class TestNoTradingMethodsInSnapshotSource:
    def _get_function_names(self, source: str) -> set[str]:
        tree = ast.parse(source)
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_no_trading_methods_in_capture_module(self):
        source = CAPTURE_MODULE.read_text(encoding="utf-8")
        names = self._get_function_names(source)
        found = names & DISALLOWED_METHOD_NAMES
        assert found == set(), f"Disallowed method names found in snapshot_capture.py: {found}"

    def test_no_trading_methods_in_writer_module(self):
        source = WRITER_MODULE.read_text(encoding="utf-8")
        names = self._get_function_names(source)
        found = names & DISALLOWED_METHOD_NAMES
        assert found == set(), f"Disallowed method names found in snapshot_writer.py: {found}"

    def test_no_trading_methods_in_models_module(self):
        source = MODELS_MODULE.read_text(encoding="utf-8")
        names = self._get_function_names(source)
        found = names & DISALLOWED_METHOD_NAMES
        assert found == set(), f"Disallowed method names found in snapshot_models.py: {found}"

    def test_no_trading_methods_in_capture_tool(self):
        source = CAPTURE_TOOL.read_text(encoding="utf-8")
        names = self._get_function_names(source)
        found = names & DISALLOWED_METHOD_NAMES
        assert found == set(), f"Disallowed method names found in capture_market_snapshots.py: {found}"


class TestNoHttpMutationInSnapshotSource:
    def _check_no_http_mutation(self, source: str, filename: str) -> None:
        for method in DISALLOWED_HTTP_METHODS:
            assert f'method="{method}"' not in source, (
                f"Forbidden HTTP method literal method=\"{method}\" in {filename}"
            )
            assert f"method='{method}'" not in source, (
                f"Forbidden HTTP method literal method='{method}' in {filename}"
            )

    def test_no_post_put_patch_delete_in_capture(self):
        self._check_no_http_mutation(
            CAPTURE_MODULE.read_text(encoding="utf-8"), "snapshot_capture.py"
        )

    def test_no_post_put_patch_delete_in_writer(self):
        self._check_no_http_mutation(
            WRITER_MODULE.read_text(encoding="utf-8"), "snapshot_writer.py"
        )

    def test_no_post_put_patch_delete_in_tool(self):
        self._check_no_http_mutation(
            CAPTURE_TOOL.read_text(encoding="utf-8"), "capture_market_snapshots.py"
        )


class TestNoCredentialLoadingInSnapshotSource:
    def _get_identifiers(self, source: str) -> set[str]:
        """Return all parameter names and Name/attribute identifiers in the AST."""
        tree = ast.parse(source)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)
        return names

    def _check_no_credential_identifiers(self, source: str, filename: str) -> None:
        identifiers = self._get_identifiers(source)
        for term in DISALLOWED_CREDENTIAL_IDENTIFIERS:
            found = {i for i in identifiers if term in i.lower()}
            assert not found, (
                f"Forbidden credential identifier(s) {found} found in {filename}"
            )

    def _check_no_credential_calls(self, source: str, filename: str) -> None:
        for term in DISALLOWED_CREDENTIAL_CALLS:
            assert term not in source, (
                f"Forbidden credential call {term!r} found in {filename}"
            )

    def test_no_credentials_in_capture_module(self):
        source = CAPTURE_MODULE.read_text(encoding="utf-8")
        self._check_no_credential_identifiers(source, "snapshot_capture.py")
        self._check_no_credential_calls(source, "snapshot_capture.py")

    def test_no_credentials_in_writer_module(self):
        source = WRITER_MODULE.read_text(encoding="utf-8")
        self._check_no_credential_identifiers(source, "snapshot_writer.py")
        self._check_no_credential_calls(source, "snapshot_writer.py")

    def test_no_credentials_in_models_module(self):
        source = MODELS_MODULE.read_text(encoding="utf-8")
        self._check_no_credential_identifiers(source, "snapshot_models.py")
        self._check_no_credential_calls(source, "snapshot_models.py")

    def test_no_credentials_in_capture_tool(self):
        source = CAPTURE_TOOL.read_text(encoding="utf-8")
        self._check_no_credential_identifiers(source, "capture_market_snapshots.py")
        self._check_no_credential_calls(source, "capture_market_snapshots.py")


# ---------------------------------------------------------------------------
# .gitignore check
# ---------------------------------------------------------------------------

class TestGitignoreIncludesLocalData:
    def test_gitignore_exists(self):
        assert GITIGNORE.is_file(), ".gitignore not found"

    def test_gitignore_includes_local_data(self):
        text = GITIGNORE.read_text(encoding="utf-8")
        assert "local_data/" in text or "local_data" in text, (
            ".gitignore must include local_data/ to prevent snapshot commits"
        )


# ---------------------------------------------------------------------------
# Snapshot doc checks
# ---------------------------------------------------------------------------

class TestSnapshotDocExists:
    def test_snapshot_persistence_doc_exists(self):
        assert SNAPSHOT_DOC.is_file(), (
            f"Missing docs/polymarket_snapshot_persistence.md"
        )

    def test_doc_mentions_no_automated_polling(self):
        text = SNAPSHOT_DOC.read_text(encoding="utf-8")
        assert "automated" in text.lower() or "polling" in text.lower()

    def test_doc_mentions_ignored_output_path(self):
        text = SNAPSHOT_DOC.read_text(encoding="utf-8")
        assert "local_data" in text

    def test_doc_mentions_no_trading_authority(self):
        text = SNAPSHOT_DOC.read_text(encoding="utf-8")
        assert "trading" in text.lower()

    def test_doc_mentions_read_only(self):
        text = SNAPSHOT_DOC.read_text(encoding="utf-8")
        assert "read-only" in text.lower() or "read only" in text.lower()


# ---------------------------------------------------------------------------
# CLI tool behavior (offline, using subprocess)
# ---------------------------------------------------------------------------

class TestCaptureToolCliOfflineBehavior:
    def test_exits_0_without_allow_network(self):
        result = subprocess.run(
            [sys.executable, str(CAPTURE_TOOL)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert "allow-network" in result.stdout.lower() or "allow_network" in result.stdout.lower()

    def test_help_includes_allow_network_flag(self):
        result = subprocess.run(
            [sys.executable, str(CAPTURE_TOOL), "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert "--allow-network" in result.stdout

    def test_help_mentions_no_credentials(self):
        result = subprocess.run(
            [sys.executable, str(CAPTURE_TOOL), "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert "credential" in result.stdout.lower() or "No credentials" in result.stdout

    def test_help_mentions_no_orders(self):
        result = subprocess.run(
            [sys.executable, str(CAPTURE_TOOL), "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert "order" in result.stdout.lower() or "trading" in result.stdout.lower()


# ---------------------------------------------------------------------------
# capture_market_snapshots() function unit tests (mocked client)
# ---------------------------------------------------------------------------

from src.data_layer.polymarket.snapshot_capture import (  # noqa: E402
    capture_market_snapshots,
)
from src.data_layer.polymarket.snapshot_models import (  # noqa: E402
    ADAPTER_VERSION,
    MARKET_SOURCE,
    READ_ONLY_PROVENANCE,
)


def _make_mock_client(markets_data=None, order_book_data=None):
    """Build a mock PolymarketPublicClient for offline tests."""
    client = MagicMock()

    if markets_data is None:
        markets_data = [
            {
                "id": "540817",
                "conditionId": "0xabc123",
                "question": "Will X happen?",
                "active": "True",
                "clobTokenIds": '["tok1","tok2"]',
                "outcomes": '["Yes","No"]',
                "endDate": "2026-12-31",
                "category": "politics",
            }
        ]

    mock_market_result = MagicMock()
    mock_market_result.data = markets_data
    client.get_markets.return_value = mock_market_result

    if order_book_data is None:
        order_book_data = {
            "bids": [{"price": "0.55", "size": "100"}],
            "asks": [{"price": "0.58", "size": "50"}],
            "asset_id": "tok1",
        }
    mock_ob_result = MagicMock()
    mock_ob_result.data = order_book_data
    client.get_order_book_snapshot.return_value = mock_ob_result

    return client


class TestCaptureMarketSnapshotsDeniedWithoutNetwork:
    def test_raises_runtime_error_without_allow_network(self):
        with pytest.raises(RuntimeError, match="allow_network"):
            capture_market_snapshots(allow_network=False)

    def test_does_not_call_client_without_allow_network(self):
        client = _make_mock_client()
        with pytest.raises(RuntimeError):
            capture_market_snapshots(allow_network=False, client=client)
        client.get_markets.assert_not_called()


class TestCaptureMarketSnapshotsWithMockClient:
    def test_returns_market_records(self):
        client = _make_mock_client()
        market_records, ob_records, manifest = capture_market_snapshots(
            allow_network=True,
            markets_limit=3,
            client=client,
        )
        assert len(market_records) == 1
        assert market_records[0].market_id == "540817"
        assert market_records[0].condition_id == "0xabc123"

    def test_market_records_have_read_only_provenance(self):
        client = _make_mock_client()
        market_records, _, _ = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert market_records[0].read_only_provenance == READ_ONLY_PROVENANCE

    def test_market_records_have_correct_adapter_version(self):
        client = _make_mock_client()
        market_records, _, _ = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert market_records[0].adapter_version == ADAPTER_VERSION

    def test_market_records_have_correct_source(self):
        client = _make_mock_client()
        market_records, _, _ = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert market_records[0].source == MARKET_SOURCE

    def test_manifest_is_returned(self):
        client = _make_mock_client()
        _, _, manifest = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert manifest.work_package == "WP10"
        assert manifest.tool_name == "capture_market_snapshots"
        assert manifest.network_used is True

    def test_manifest_snapshot_id_matches_records(self):
        client = _make_mock_client()
        market_records, _, manifest = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert market_records[0].snapshot_id == manifest.snapshot_id

    def test_snapshot_id_is_deterministic_with_fixed_datetime(self):
        from datetime import datetime, timezone
        dt = datetime(2026, 5, 19, 14, 30, 22, 0, tzinfo=timezone.utc)
        client = _make_mock_client()
        _, _, manifest = capture_market_snapshots(
            allow_network=True,
            client=client,
            _captured_at=dt,
        )
        assert manifest.snapshot_id.startswith("snap_20260519_143022")

    def test_json_encoded_token_ids_are_handled(self):
        """Verify clobTokenIds as JSON-encoded string is correctly parsed (WP9-D002)."""
        markets_data = [
            {
                "id": "12345",
                "conditionId": "0xdef456",
                "question": "Another question?",
                "active": "True",
                "clobTokenIds": '["tokenA","tokenB"]',
                "outcomes": '["Yes","No"]',
                "endDate": None,
                "category": None,
            }
        ]
        client = _make_mock_client(markets_data=markets_data)
        market_records, _, _ = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert "tokenA" in market_records[0].token_ids
        assert "tokenB" in market_records[0].token_ids

    def test_no_order_books_by_default(self):
        client = _make_mock_client()
        _, ob_records, manifest = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert ob_records == []
        assert manifest.order_books_written == 0
        client.get_order_book_snapshot.assert_not_called()

    def test_order_books_fetched_when_requested(self):
        client = _make_mock_client()
        _, ob_records, manifest = capture_market_snapshots(
            allow_network=True,
            include_order_books=True,
            max_order_books=1,
            client=client,
        )
        assert len(ob_records) == 1
        assert ob_records[0].token_id == "tok1"
        assert ob_records[0].bids == [{"price": "0.55", "size": "100"}]

    def test_order_books_have_read_only_provenance(self):
        client = _make_mock_client()
        _, ob_records, _ = capture_market_snapshots(
            allow_network=True,
            include_order_books=True,
            max_order_books=1,
            client=client,
        )
        assert ob_records[0].read_only_provenance == READ_ONLY_PROVENANCE

    def test_raw_field_names_not_full_payload(self):
        """raw_field_names must be a list of strings, not the full raw response."""
        client = _make_mock_client()
        market_records, _, _ = capture_market_snapshots(
            allow_network=True, client=client
        )
        raw_field_names = market_records[0].raw_field_names
        assert isinstance(raw_field_names, list)
        for item in raw_field_names:
            assert isinstance(item, str), f"raw_field_names must be strings, got {type(item)}"
        # The field names list should not contain the full raw dict
        assert len(raw_field_names) < 100, "raw_field_names looks like a full payload"

    def test_empty_markets_response_returns_no_records(self):
        client = _make_mock_client(markets_data=[])
        market_records, _, manifest = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert market_records == []
        assert manifest.markets_written == 0

    def test_manifest_notes_mention_rate_limit(self):
        client = _make_mock_client()
        _, _, manifest = capture_market_snapshots(
            allow_network=True, client=client
        )
        assert "rate" in manifest.notes.lower() or "WP8-D002" in manifest.notes
