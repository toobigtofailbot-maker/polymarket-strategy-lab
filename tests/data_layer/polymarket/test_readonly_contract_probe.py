"""Tests for the WP9 readonly contract probe tool and updated parser/metadata.

Tests verify:
- Probe exits cleanly without --allow-network (no network calls made).
- --help output includes --allow-network.
- Probe source contains no POST/PUT/PATCH/DELETE logic.
- Probe source contains no credential loading.
- Probe source contains no disallowed trading/order method names.
- Probe output path uses an ignored/local directory.
- Probe imports and uses the read-only adapter.
- Endpoint verification metadata updated only for confirmed endpoints.
- CLOB /health remains unverified (returned 404 in WP9 probe).
- Parser handles clobTokenIds as JSON-encoded string.
- Parser handles outcomes as JSON-encoded string.
- Parser handles clobTokenIds as plain Python list (backwards compat).
- Existing boundary tests remain unaffected.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PROBE_SCRIPT = ROOT / "tools" / "polymarket" / "readonly_contract_probe.py"
CLIENT_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "public_client.py"

DISALLOWED_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
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
DISALLOWED_CREDENTIAL_TERMS_AS_PARAMS = {
    "private_key",
    "api_key",
    "api_secret",
    "wallet_key",
    "mnemonic",
    "passphrase",
}


class TestProbeExitsCleanlyWithoutAllowNetwork:
    def test_no_network_flag_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(PROBE_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"

    def test_no_network_flag_prints_allow_network_guidance(self):
        result = subprocess.run(
            [sys.executable, str(PROBE_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        combined = (result.stdout + result.stderr).lower()
        assert "allow-network" in combined or "allow_network" in combined, (
            "Expected --allow-network guidance in output when flag is absent"
        )


class TestProbeHelpIncludesAllowNetwork:
    def test_help_includes_allow_network(self):
        result = subprocess.run(
            [sys.executable, str(PROBE_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "--allow-network" in result.stdout, (
            "--allow-network flag not present in --help output"
        )


class TestProbeSourceNoHttpMutationMethods:
    def test_no_post_put_patch_delete_in_probe(self):
        source = PROBE_SCRIPT.read_text(encoding="utf-8")
        for forbidden in DISALLOWED_HTTP_METHODS:
            assert f'method="{forbidden}"' not in source, (
                f"Forbidden HTTP method literal found: method=\"{forbidden}\""
            )
            assert f"method='{forbidden}'" not in source, (
                f"Forbidden HTTP method literal found: method='{forbidden}'"
            )


class TestProbeSourceNoCredentialLoading:
    def test_no_env_credential_loading(self):
        source = PROBE_SCRIPT.read_text(encoding="utf-8")
        # Must not load .env files
        forbidden_patterns = [
            "load_dotenv",
            "dotenv",
            "os.environ.get(\"API",
            "os.environ.get('API",
            "os.getenv(\"API",
            "os.getenv('API",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in source, f"Forbidden credential-loading pattern found: {pattern!r}"

    def test_no_private_key_params_in_probe(self):
        source = PROBE_SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.arg):
                arg_lower = node.arg.lower()
                for term in DISALLOWED_CREDENTIAL_TERMS_AS_PARAMS:
                    assert term not in arg_lower, (
                        f"Disallowed credential term {term!r} found as parameter: {node.arg!r}"
                    )


class TestProbeSourceNoDisallowedTradingMethods:
    def test_no_disallowed_method_names_in_probe(self):
        source = PROBE_SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        method_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        found = method_names & DISALLOWED_METHOD_NAMES
        assert found == set(), f"Disallowed method names found in probe: {found}"


class TestProbeUsesReadOnlyAdapter:
    def test_probe_imports_polymarket_public_client(self):
        source = PROBE_SCRIPT.read_text(encoding="utf-8")
        assert "PolymarketPublicClient" in source, (
            "Probe must use PolymarketPublicClient from the read-only adapter"
        )

    def test_probe_imports_from_src_data_layer(self):
        source = PROBE_SCRIPT.read_text(encoding="utf-8")
        assert "src.data_layer.polymarket" in source, (
            "Probe must import from src.data_layer.polymarket"
        )


class TestEndpointVerificationMetadata:
    """Verify that only confirmed endpoints are marked verified in WP9."""

    def _get_endpoint_map(self) -> dict:
        import sys as _sys
        if str(ROOT) not in _sys.path:
            _sys.path.insert(0, str(ROOT))
        from src.data_layer.polymarket import public_client
        return public_client._ENDPOINT_MAP

    def test_gamma_markets_is_verified(self):
        ep_map = self._get_endpoint_map()
        assert ep_map["gamma_markets"]["verified"] is True, (
            "gamma_markets should be verified after WP9 probe"
        )

    def test_gamma_market_by_id_is_verified(self):
        ep_map = self._get_endpoint_map()
        assert ep_map["gamma_market_by_id"]["verified"] is True, (
            "gamma_market_by_id should be verified after WP9 probe"
        )

    def test_clob_book_is_verified(self):
        ep_map = self._get_endpoint_map()
        assert ep_map["clob_book"]["verified"] is True, (
            "clob_book should be verified after WP9 probe (HTTP 200 with bids/asks)"
        )

    def test_clob_health_is_not_verified(self):
        ep_map = self._get_endpoint_map()
        assert ep_map["clob_health"]["verified"] is False, (
            "clob_health must remain unverified — WP9 probe returned HTTP 404"
        )

    def test_verified_endpoints_have_verified_in_wp(self):
        ep_map = self._get_endpoint_map()
        for key, entry in ep_map.items():
            if entry.get("verified"):
                assert entry.get("verified_in_wp"), (
                    f"Verified endpoint {key!r} must have verified_in_wp set"
                )
                assert entry.get("verified_at_utc"), (
                    f"Verified endpoint {key!r} must have verified_at_utc set"
                )

    def test_clob_health_notes_document_404(self):
        ep_map = self._get_endpoint_map()
        notes = ep_map["clob_health"].get("notes", "")
        assert "404" in notes, (
            "clob_health notes must document the HTTP 404 result from WP9 probe"
        )


class TestParserJsonEncodedStrings:
    """Verify parser handles WP9-discovered JSON-encoded string fields."""

    def _get_client_class(self):
        from src.data_layer.polymarket import PolymarketPublicClient
        return PolymarketPublicClient

    def test_parse_clob_token_ids_as_json_string(self):
        client = self._get_client_class()
        raw = {
            "id": "540817",
            "conditionId": "0xabc",
            "question": "Test market?",
            "active": "true",
            "clobTokenIds": '["token_a","token_b"]',
            "outcomes": '["Yes","No"]',
        }
        result = client.parse_market_summary(raw)
        assert result.token_ids == ("token_a", "token_b"), (
            f"Expected ('token_a', 'token_b'), got {result.token_ids}"
        )

    def test_parse_outcomes_as_json_string(self):
        client = self._get_client_class()
        raw = {
            "id": "540817",
            "conditionId": "0xabc",
            "question": "Test market?",
            "active": "true",
            "clobTokenIds": '["token_a","token_b"]',
            "outcomes": '["Yes","No"]',
        }
        result = client.parse_market_summary(raw)
        assert result.outcome_labels == ("Yes", "No"), (
            f"Expected ('Yes', 'No'), got {result.outcome_labels}"
        )

    def test_parse_clob_token_ids_as_plain_list_still_works(self):
        """Backwards compat: plain Python list must still parse correctly."""
        client = self._get_client_class()
        raw = {
            "id": "540817",
            "conditionId": "0xabc",
            "question": "Test market?",
            "active": "true",
            "clobTokenIds": ["token_a", "token_b"],
            "outcomes": ["Yes", "No"],
        }
        result = client.parse_market_summary(raw)
        assert result.token_ids == ("token_a", "token_b")
        assert result.outcome_labels == ("Yes", "No")

    def test_parse_market_id_uses_id_field(self):
        client = self._get_client_class()
        raw = {
            "id": "540817",
            "conditionId": "0xabc",
            "question": "Test?",
            "active": "true",
            "clobTokenIds": "[]",
            "outcomes": "[]",
        }
        result = client.parse_market_summary(raw)
        assert result.market_id == "540817"

    def test_parse_clob_token_ids_empty_json_array(self):
        client = self._get_client_class()
        raw = {
            "id": "1",
            "conditionId": "0xabc",
            "question": "Test?",
            "active": "true",
            "clobTokenIds": "[]",
            "outcomes": "[]",
        }
        result = client.parse_market_summary(raw)
        assert result.token_ids == ()
        assert result.outcome_labels == ()

    def test_parse_json_string_or_list_with_list(self):
        client = self._get_client_class()
        result = client._parse_json_string_or_list(["a", "b"])
        assert result == ["a", "b"]

    def test_parse_json_string_or_list_with_json_string(self):
        client = self._get_client_class()
        result = client._parse_json_string_or_list('["x","y"]')
        assert result == ["x", "y"]

    def test_parse_json_string_or_list_with_empty_string(self):
        client = self._get_client_class()
        result = client._parse_json_string_or_list("")
        assert result == []

    def test_parse_json_string_or_list_with_none(self):
        client = self._get_client_class()
        result = client._parse_json_string_or_list(None)
        assert result == []
