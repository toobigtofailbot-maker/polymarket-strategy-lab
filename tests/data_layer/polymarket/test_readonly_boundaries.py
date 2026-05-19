"""Tests verifying read-only boundary enforcement for the Polymarket adapter.

These tests confirm that:
- No POST/PUT/PATCH/DELETE methods exist on the client.
- No credential, private-key, wallet, or signing fields exist.
- No disallowed method names exist.
- Timeout is configurable.
- Base URL is configurable.
- Smoke test requires --allow-network.
- Docs mention read-only limitations.
"""

from __future__ import annotations

import ast
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLIENT_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "public_client.py"
MODELS_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "models.py"
ERRORS_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "errors.py"
INIT_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "__init__.py"
README_MODULE = ROOT / "src" / "data_layer" / "polymarket" / "README.md"
SMOKE_TEST = ROOT / "tools" / "polymarket" / "readonly_smoke_test.py"
EVAL_DOC = ROOT / "docs" / "polymarket_readonly_adapter_evaluation.md"
SEMANTICS_DOC = ROOT / "docs" / "polymarket_data_semantics.md"


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

DISALLOWED_CREDENTIAL_TERMS = {
    "private_key",
    "api_key",
    "api_secret",
    "wallet_key",
    "mnemonic",
    "passphrase",
    "bearer",
    "secret",
}

DISALLOWED_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class TestNoDisallowedMethodNames:
    def _get_method_names(self, source: str) -> set[str]:
        tree = ast.parse(source)
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_no_disallowed_method_names_in_client(self):
        source = CLIENT_MODULE.read_text(encoding="utf-8")
        method_names = self._get_method_names(source)
        found = method_names & DISALLOWED_METHOD_NAMES
        assert found == set(), f"Disallowed method names found: {found}"

    def test_no_disallowed_method_names_in_models(self):
        source = MODELS_MODULE.read_text(encoding="utf-8")
        method_names = self._get_method_names(source)
        found = method_names & DISALLOWED_METHOD_NAMES
        assert found == set(), f"Disallowed method names found: {found}"


class TestNoHttpMutationMethods:
    def test_no_post_put_patch_delete_in_client(self):
        source = CLIENT_MODULE.read_text(encoding="utf-8")
        for forbidden in DISALLOWED_HTTP_METHODS:
            # Check for method= strings (case-sensitive literals)
            assert f'method="{forbidden}"' not in source, (
                f"Found forbidden HTTP method literal: method=\"{forbidden}\""
            )
            assert f"method='{forbidden}'" not in source, (
                f"Found forbidden HTTP method literal: method='{forbidden}'"
            )


class TestNoCredentialFields:
    def _combined_source(self) -> str:
        return "\n".join(
            f.read_text(encoding="utf-8")
            for f in [CLIENT_MODULE, MODELS_MODULE, ERRORS_MODULE, INIT_MODULE]
        )

    def test_no_private_key_field(self):
        source = self._combined_source()
        # Allow "private_key" in comments/docs as a forbidden term mention,
        # but not as a Python identifier assignment or parameter.
        tree = ast.parse(CLIENT_MODULE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.arg):
                assert "private_key" not in node.arg, "private_key found as parameter"
                assert "api_key" not in node.arg, "api_key found as parameter"
                assert "secret" not in node.arg.lower(), "secret found as parameter"
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    assert "private_key" not in arg.arg
                    assert "api_key" not in arg.arg
                    assert "wallet_key" not in arg.arg
                    assert "mnemonic" not in arg.arg

    def test_no_signing_import(self):
        source = CLIENT_MODULE.read_text(encoding="utf-8")
        forbidden_imports = ["eth_account", "web3", "cryptography.hazmat.primitives.asymmetric"]
        for imp in forbidden_imports:
            assert imp not in source, f"Forbidden import found: {imp}"


class TestTimeoutConfigurable:
    def test_client_has_timeout_parameter(self):
        from src.data_layer.polymarket import PolymarketPublicClient
        sig = inspect.signature(PolymarketPublicClient.__init__)
        assert "timeout_seconds" in sig.parameters

    def test_client_stores_timeout(self):
        from src.data_layer.polymarket import PolymarketPublicClient
        client = PolymarketPublicClient(timeout_seconds=7.5)
        assert client._timeout == 7.5


class TestBaseUrlConfigurable:
    def test_client_has_gamma_base_url_parameter(self):
        from src.data_layer.polymarket import PolymarketPublicClient
        sig = inspect.signature(PolymarketPublicClient.__init__)
        assert "gamma_base_url" in sig.parameters

    def test_client_has_clob_base_url_parameter(self):
        from src.data_layer.polymarket import PolymarketPublicClient
        sig = inspect.signature(PolymarketPublicClient.__init__)
        assert "clob_base_url" in sig.parameters

    def test_client_stores_custom_urls(self):
        from src.data_layer.polymarket import PolymarketPublicClient
        client = PolymarketPublicClient(
            gamma_base_url="http://gamma-test",
            clob_base_url="http://clob-test",
        )
        assert "gamma-test" in client._gamma_base_url
        assert "clob-test" in client._clob_base_url


class TestSmokeTestRequiresAllowNetwork:
    def test_smoke_test_exits_cleanly_without_allow_network(self):
        result = subprocess.run(
            [sys.executable, str(SMOKE_TEST)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "allow-network" in result.stdout.lower() or "allow_network" in result.stdout.lower()

    def test_smoke_test_has_allow_network_flag(self):
        result = subprocess.run(
            [sys.executable, str(SMOKE_TEST), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "--allow-network" in result.stdout

    def test_smoke_test_source_contains_allow_network_guard(self):
        source = SMOKE_TEST.read_text(encoding="utf-8")
        assert "allow_network" in source or "allow-network" in source


class TestDocsReadOnlyLimitations:
    def test_eval_doc_exists(self):
        assert EVAL_DOC.is_file(), f"Missing: {EVAL_DOC}"

    def test_semantics_doc_exists(self):
        assert SEMANTICS_DOC.is_file(), f"Missing: {SEMANTICS_DOC}"

    def test_eval_doc_mentions_no_credentials(self):
        text = EVAL_DOC.read_text(encoding="utf-8")
        assert "credential" in text.lower() or "No credentials" in text

    def test_eval_doc_mentions_read_only(self):
        text = EVAL_DOC.read_text(encoding="utf-8")
        assert "read-only" in text.lower() or "read only" in text.lower()

    def test_eval_doc_mentions_no_order_placement(self):
        text = EVAL_DOC.read_text(encoding="utf-8")
        assert "order placement" in text.lower() or "order_placement" in text.lower()

    def test_readme_mentions_no_trading_authority(self):
        text = README_MODULE.read_text(encoding="utf-8")
        assert "trading authority" in text.lower() or "No trading authority" in text

    def test_readme_mentions_no_credentials(self):
        text = README_MODULE.read_text(encoding="utf-8")
        assert "credential" in text.lower() or "No credentials" in text
