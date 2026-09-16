"""WP174 persistent audit, restart, corruption, and stale-writer tests."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from src.execution_gateway import (
    FixtureAuthenticatedReadAdapter,
    GateASecretReferenceLoader,
    GatewayError,
    GatewayStore,
    GatewayStoreError,
    ProtectedExecutionGateway,
    build_fixture_account_snapshot,
    read_gateway_projection,
)
from src.execution_gateway.gateway import _GATE_C_EVENT_ISSUER


def _empty_snapshot():
    return build_fixture_account_snapshot(
        signer="0x" + "1" * 40,
        funder="0x" + "2" * 40,
        observed_time_ns=2,
        access_state="ELIGIBLE",
        venue_mode="NORMAL",
        balances_hash="balances:sha256:" + "8" * 64,
        positions_hash="positions:sha256:" + "9" * 64,
    )


def test_store_restart_hash_chain_and_disabled_state_fail_closed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "gateway.sqlite3"
    gateway = ProtectedExecutionGateway.create(path, created_time_ns=1)
    gateway.configure_credentials(
        GateASecretReferenceLoader(
            {"secret-ref:fixture-one": ("0x" + "1" * 40, "0x" + "2" * 40)}
        ),
        "secret-ref:fixture-one",
        event_time_ns=2,
    )
    gateway.reconcile(
        adapter=FixtureAuthenticatedReadAdapter(_empty_snapshot()), event_time_ns=3
    )
    gateway.set_authority("A2_SHADOW", actor="fixture-operator", event_time_ns=4)
    gateway.disable(reason="operator-kill", actor="fixture-operator", event_time_ns=5)
    gateway.close()

    with ProtectedExecutionGateway.open(path, opened_time_ns=6) as restarted:
        assert restarted.state.authority_state == "A0_DISABLED"
        assert restarted.state.reconciliation_state == "REQUIRED"
        assert restarted.state.disable_reason == "RESTART_RECONCILIATION_REQUIRED"
        with pytest.raises(GatewayError, match="SHADOW_AUTHORITY_REQUIRED"):
            restarted.prepare_limit_order(
                None,  # type: ignore[arg-type]
                "paperintent:sha256:" + "0" * 64,
                None,  # type: ignore[arg-type]
                session_identity="fixture-session",
                worst_acceptable_price="0.5",
                time_in_force="GTC",
                post_only=False,
                expiration=None,
                nonce=0,
                signing_time_ns=7,
            )

    projection = read_gateway_projection(path, limit=100)
    assert projection["state"]["authority_state"] == "A0_DISABLED"
    assert projection["state"]["reconciliation_state"] == "REQUIRED"
    assert len(projection["audit"]) == 6
    rendered = json.dumps(projection)
    for forbidden in ("private_key", "api_secret", "passphrase", "signed_payload"):
        assert forbidden not in rendered

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE gateway_journal SET event_hash=? WHERE sequence=2", ("0" * 64,)
    )
    connection.commit()
    connection.close()
    with pytest.raises(GatewayStoreError, match="STORE_CORRUPT"):
        read_gateway_projection(path, limit=10)


def test_stale_writer_and_sensitive_audit_data_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "gateway.sqlite3"
    first = ProtectedExecutionGateway.create(path, created_time_ns=1)
    second_store = GatewayStore(path)
    mapping, head, _events = second_store.load()
    assert mapping is not None and head is not None
    second_store.append(
        "EXTERNAL_FIXTURE_EVENT",
        2,
        {"fixture": True},
        mapping,
        expected_head=head,
    )
    with pytest.raises(GatewayError, match="STALE_GATEWAY_STATE"):
        first.record_access("ELIGIBLE", event_time_ns=3)
    assert first.state.authority_state == "A0_DISABLED"
    assert first.state.reconciliation_state == "BLOCKED"
    first.close()
    second_store.close()

    safe_path = tmp_path / "safe.sqlite3"
    with GatewayStore(safe_path, create=True) as store:
        with pytest.raises(GatewayStoreError, match="SENSITIVE_DATA_FORBIDDEN"):
            store.append(
                "BAD_EVENT",
                1,
                {"passphrase": "SENSITIVE_FIXTURE_VALUE"},
                {},
                expected_head=None,
            )
        safe = store.append(
            "PUBLIC_IDS",
            1,
            {
                "condition_id": "0x" + "a" * 64,
                "token_id": "1" * 70,
            },
            {},
            expected_head=None,
        )
        assert safe.sequence == 1
        with pytest.raises(GatewayStoreError, match="SENSITIVE_DATA_FORBIDDEN"):
            store.append(
                "BAD_EVENT",
                1,
                {"note": "QWxhZGRpbjpvcGVuIHNlc2FtZSBmaXh0dXJlIHZhbHVl"},
                {},
                expected_head=None,
            )
        with pytest.raises(GatewayStoreError, match="SENSITIVE_DATA_FORBIDDEN"):
            store.append(
                "BAD_EVENT",
                1,
                {"note": "a" * 64},
                {},
                expected_head=None,
            )


def test_store_rejects_foreign_schema_symlink_and_non_lowercase_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    foreign = tmp_path / "foreign.sqlite3"
    sqlite3.connect(foreign).close()
    with pytest.raises(GatewayStoreError, match="STORE_SCHEMA_INVALID"):
        GatewayStore(foreign)
    with pytest.raises(GatewayStoreError, match="STORE_PATH_INVALID"):
        GatewayStore(tmp_path / "Gateway.sqlite3", create=True)
    link = tmp_path / "linked.sqlite3"
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: True if self == link else original(self),
    )
    with pytest.raises(GatewayStoreError, match="STORE_PATH_INVALID"):
        GatewayStore(link)


def test_hash_consistent_invalid_authority_state_is_never_projected_or_restored(
    tmp_path: Path,
) -> None:
    path = tmp_path / "invalid-state.sqlite3"
    gateway = ProtectedExecutionGateway.create(path, created_time_ns=1)
    gateway.close()
    with GatewayStore(path) as store:
        mapping, head, _ = store.load()
        assert mapping is not None and head is not None
        invalid = dict(mapping)
        invalid["authority_state"] = "A3_RESTRICTED_LIVE"
        store.append(
            "EXTERNAL_FIXTURE_EVENT", 2, {"fixture": True}, invalid, expected_head=head
        )
    with pytest.raises(GatewayStoreError, match="STORE_REPLAY_INVALID"):
        read_gateway_projection(path, limit=10)
    with pytest.raises(GatewayError, match="STATE_REPLAY_INVALID"):
        ProtectedExecutionGateway.open(path, opened_time_ns=3)


def test_gate_c_checkpoint_is_visible_only_as_sanitized_projection(tmp_path: Path) -> None:
    path = tmp_path / "gateway.sqlite3"
    with ProtectedExecutionGateway.create(path, created_time_ns=1) as gateway:
        with pytest.raises(GatewayError, match="SENSITIVE_DATA_FORBIDDEN"):
            gateway.record_gate_c_event(
                "GATE_C_DISABLED",
                {
                    "armed": False,
                    "halted": True,
                    "authority_state": "A0_DISABLED",
                    "disable_reason": "OPERATOR_KILL",
                    "reconciliation_state": "BLOCKED",
                    "access_state": "UNKNOWN",
                    "private_key": "must-not-enter",
                },
                issuer=_GATE_C_EVENT_ISSUER,
                event_time_ns=2,
            )
    projection = read_gateway_projection(path, limit=1)
    assert projection["state"]["restricted_live_available"] is False


def test_hash_consistent_a2_with_ineligible_access_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid-cross-state.sqlite3"
    gateway = ProtectedExecutionGateway.create(path, created_time_ns=1)
    gateway.close()
    with GatewayStore(path) as store:
        mapping, head, _ = store.load()
        assert mapping is not None and head is not None
        invalid = dict(mapping)
        invalid.update(
            authority_state="A2_SHADOW",
            credential_configured=True,
            public_signer="0x" + "1" * 40,
            public_funder="0x" + "2" * 40,
            reconciliation_state="HEALTHY",
            access_state="GEOBLOCKED",
            last_event_time_ns=2,
        )
        store.append(
            "AUTHORITY_CHANGED", 2, {"fixture": True}, invalid, expected_head=head
        )
    with pytest.raises(GatewayStoreError, match="STORE_REPLAY_INVALID"):
        read_gateway_projection(path, limit=10)
    with pytest.raises(GatewayError, match="STATE_INVALID"):
        ProtectedExecutionGateway.open(path, opened_time_ns=3)


def test_event_data_state_mismatch_rejects_and_closes_store(tmp_path: Path) -> None:
    path = tmp_path / "mismatched-event.sqlite3"
    gateway = ProtectedExecutionGateway.create(path, created_time_ns=1)
    gateway.close()
    with GatewayStore(path) as store:
        mapping, head, _ = store.load()
        assert mapping is not None and head is not None
        invalid = dict(mapping)
        invalid.update(
            credential_configured=True,
            public_signer="0x" + "1" * 40,
            public_funder="0x" + "2" * 40,
            last_event_time_ns=2,
        )
        store.append(
            "CREDENTIAL_REFERENCE_CONFIGURED",
            2,
            {"configured": False},
            invalid,
            expected_head=head,
        )
    with pytest.raises(GatewayError, match="STATE_REPLAY_INVALID"):
        ProtectedExecutionGateway.open(path, opened_time_ns=3)
    with pytest.raises(GatewayStoreError, match="STORE_REPLAY_INVALID"):
        read_gateway_projection(path, limit=10)
    path.unlink()
    assert not path.exists()


def test_rate_limit_event_deadline_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "mismatched-rate.sqlite3"
    gateway = ProtectedExecutionGateway.create(path, created_time_ns=1)
    gateway.close()
    with GatewayStore(path) as store:
        mapping, head, _ = store.load()
        assert mapping is not None and head is not None
        invalid = dict(mapping)
        invalid.update(rate_limit_until_ns=1, last_event_time_ns=2)
        store.append(
            "RATE_LIMITED",
            2,
            {"now_ns": 1, "retry_after_seconds": 60, "until_ns": 1},
            invalid,
            expected_head=head,
        )
    with pytest.raises(GatewayError, match="STATE_REPLAY_INVALID"):
        ProtectedExecutionGateway.open(path, opened_time_ns=3)
