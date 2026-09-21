"""Contract tests for the canonical public wallet event model (S10-WALLET-01)."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

import pytest

from src.data_layer.wallet_intelligence import contracts as c


def _oracle_id(prefix: str, preimage: object) -> str:
    raw = json.dumps(preimage, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return prefix + hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public error vocabulary (19) - R-V2-11 / E01-E06.
# ---------------------------------------------------------------------------
def test_public_error_set_is_exact():
    assert c.WALLET_PUBLIC_ERROR_CODES == (
        "FIELD_TYPE_INVALID",
        "FIELD_VALUE_INVALID",
        "SCHEMA_UNSUPPORTED",
        "ADDRESS_INVALID",
        "DECIMAL_INVALID",
        "IDENTITY_DERIVATION_MISMATCH",
        "REFERENCE_INVALID",
        "REFERENCE_TYPE_INVALID",
        "REFERENCE_CYCLE",
        "PIT_NOT_ADMISSIBLE",
        "PROVENANCE_INCOMPLETE",
        "DQ_STATE_INVALID",
        "CURSOR_INVALID",
        "CURSOR_GAP",
        "SOURCE_DISAGREEMENT",
        "SOURCE_UNAVAILABLE",
        "SOURCE_RESPONSE_INVALID",
        "RATE_LIMIT_GUARD_DENIED",
        "NETWORK_DISABLED",
        "NETWORK_HOST_FORBIDDEN",
        "NETWORK_SCHEME_FORBIDDEN",
        "RECONCILIATION_INVALID",
        "LEDGER_IDENTITY_CONFLICT",
        "LEDGER_INTEGRITY_TAMPER",
        "LIMIT_EXCEEDED",
        "INTERNAL_VALIDATION_FAILED",
    )


def test_internal_to_public_total_mapping_and_closure():
    expected_internal = {
        "SCHEMA_VERSION_UNSUPPORTED", "FIELD_MISSING", "FIELD_TYPE", "FIELD_VALUE",
        "ADDRESS", "DECIMAL", "IDENTITY", "REFERENCE_MISSING", "REFERENCE_WRONG_TYPE",
        "REFERENCE_CYCLE", "PIT_INADMISSIBLE", "PROVENANCE", "DQ", "CURSOR", "GAP",
        "DISAGREEMENT", "SOURCE_UNAVAILABLE", "RESPONSE", "GUARD", "NETWORK_OFF",
        "HOST", "SCHEME", "RECONCILIATION", "LEDGER_IDENTITY", "LEDGER_TAMPER",
        "LIMIT", "UNEXPECTED",
    }
    assert set(c.WALLET_INTERNAL_TO_PUBLIC_ERROR) == expected_internal
    for internal, public in c.WALLET_INTERNAL_TO_PUBLIC_ERROR.items():
        assert public in c.WALLET_PUBLIC_ERROR_CODES
    # Unknown/future internal codes collapse to the closed fallback.
    assert c.map_internal_failure_to_public("SOMETHING_NEW") == "INTERNAL_VALIDATION_FAILED"
    assert c.map_internal_failure_to_public(None) == "INTERNAL_VALIDATION_FAILED"


def test_error_message_is_only_the_public_code():
    err = c.WalletContractError("ADDRESS")
    assert str(err) == "ADDRESS_INVALID"
    assert err.public_code == "ADDRESS_INVALID"


# ---------------------------------------------------------------------------
# Address normalization (10.1) - R-W02 / R-F02 / R-F04.
# ---------------------------------------------------------------------------
def test_address_lowercases_mixed_case_without_eip55():
    assert c.canonicalize_evm_address("0x" + "Ab" * 20) == "0x" + "ab" * 20


def test_address_strips_surrounding_ascii_whitespace():
    assert c.canonicalize_evm_address("  0x" + "1" * 40 + "\n") == "0x" + "1" * 40


def test_address_rejects_full_width_prefix():
    with pytest.raises(c.WalletContractError) as e:
        c.canonicalize_evm_address("０ｘ" + "0" * 40)
    assert e.value.public_code == "ADDRESS_INVALID"


def test_address_rejects_wrong_length_and_non_hex():
    for bad in ("0x123", "0x" + "1" * 41, "0x" + "g" * 40, "1" * 42):
        with pytest.raises(c.WalletContractError):
            c.canonicalize_evm_address(bad)


# ---------------------------------------------------------------------------
# Generic role vs Polymarket wallet type independence (10.1) - R-F02.
# ---------------------------------------------------------------------------
def test_generic_role_and_wallet_type_exact_sets():
    assert c.GENERIC_ACCOUNT_ROLES == ("ACCOUNT_WALLET", "SIGNER", "PROTOCOL_CONTRACT", "OTHER_CONTRACT", "UNKNOWN")
    assert c.POLYMARKET_WALLET_TYPES == ("EOA", "POLY_PROXY", "GNOSIS_SAFE", "DEPOSIT_WALLET", "UNKNOWN")


def test_role_and_type_vary_independently_and_survive_roundtrip():
    a = c.build_wallet_account_identity_evidence(
        canonical_wallet="0x" + "1" * 40,
        generic_account_role="ACCOUNT_WALLET",
        polymarket_wallet_type="DEPOSIT_WALLET",
        evidence_link_class="PROTOCOL_DECLARED",
        source_reference="doc:1",
    )
    b = c.build_wallet_account_identity_evidence(
        canonical_wallet="0x" + "1" * 40,
        generic_account_role="SIGNER",
        polymarket_wallet_type="UNKNOWN",
        evidence_link_class="PROTOCOL_DECLARED",
        source_reference="doc:1",
    )
    # ACCOUNT_WALLET + DEPOSIT_WALLET and SIGNER + UNKNOWN are both valid.
    assert a.generic_account_role == "ACCOUNT_WALLET" and a.polymarket_wallet_type == "DEPOSIT_WALLET"
    assert b.generic_account_role == "SIGNER" and b.polymarket_wallet_type == "UNKNOWN"
    # Changing one dimension does not mutate the other; ids differ.
    assert a.wallet_account_identity_evidence_id != b.wallet_account_identity_evidence_id


def test_wallet_type_rejects_unknown_enum_value():
    with pytest.raises(c.WalletContractError):
        c.build_wallet_account_identity_evidence(
            canonical_wallet="0x" + "1" * 40,
            generic_account_role="ACCOUNT_WALLET",
            polymarket_wallet_type="MULTISIG_BOGUS",
            evidence_link_class="PROTOCOL_DECLARED",
            source_reference="doc:1",
        )


def test_no_deanonymization_fields_present():
    fields = set(c.WalletAccountIdentityEvidence.__dataclass_fields__)
    for forbidden in ("beneficial_owner", "real_person", "insider_probability", "deanonymized_identity"):
        assert forbidden not in fields


# ---------------------------------------------------------------------------
# Context-typed identifiers (10.3) - R-B03 / R-D04 / R-F04.
# ---------------------------------------------------------------------------
def test_bytes32_context_lowercases_and_validates():
    assert c.canonicalize_identifier("TRANSACTION_HASH", "0x" + "AB" * 32) == "0x" + "ab" * 32
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("TRANSACTION_HASH", "0x" + "ab" * 31)  # wrong length


def test_data_api_response_condition_id_uses_response_grammar_not_protocol():
    # A short hex id valid under the response grammar but rejected by the 31/32-byte
    # protocol structural helper still passes in the response context.
    short = "0xabc"
    assert c.canonicalize_identifier("DATA_API_RESPONSE_CONDITION_ID", short) == "0xabc"
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("PROTOCOL_STANDARD_CONDITION_ID", short)


def test_protocol_standard_condition_id_lengths():
    assert c.canonicalize_identifier("PROTOCOL_STANDARD_CONDITION_ID", "0x" + "AB" * 31) == "0x" + "ab" * 31
    assert c.canonicalize_identifier("PROTOCOL_STANDARD_CONDITION_ID", "0x" + "ab" * 32) == "0x" + "ab" * 32
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("PROTOCOL_STANDARD_CONDITION_ID", "0x" + "ab" * 30)


def test_market_selector_transform_only_in_its_context():
    src = "0x01" + "cc" * 30  # length 64
    assert c.canonicalize_identifier("MARKET_SELECTOR_CONDITION_ID", src) == src.lower() + "00"
    # The same 64-length value is NOT auto-transformed in the response context.
    assert c.canonicalize_identifier("DATA_API_RESPONSE_CONDITION_ID", src) == src.lower()


def test_combo_condition_id_grammar():
    canon = "0x03" + "bb" * 30  # length 64
    assert c.canonicalize_identifier("COMBO_CONDITION_ID", canon) == canon
    src = "0x03" + "aa" * 30 + "00"  # length 66
    assert c.canonicalize_identifier("COMBO_CONDITION_ID", src) == "0x03" + "aa" * 30
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("COMBO_CONDITION_ID", "0x01" + "aa" * 30)  # wrong prefix


def test_unsigned_integer_context_canonicalizes():
    assert c.canonicalize_identifier("GAMMA_MARKET_ID", "00123") == "123"
    assert c.canonicalize_identifier("CLOB_TOKEN_ID", 0) == "0"
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("GAMMA_MARKET_ID", "+5")
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("GAMMA_MARKET_ID", True)


def test_opaque_source_native_id_preserved_no_case_fold():
    assert c.canonicalize_identifier("SOURCE_NATIVE_EVENT_ID", "AbC-123") == "AbC-123"
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("SOURCE_NATIVE_EVENT_ID", " leading")
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("SOURCE_NATIVE_EVENT_ID", "a\x00b")


def test_unknown_identifier_context_rejects():
    with pytest.raises(c.WalletContractError):
        c.canonicalize_identifier("NOT_A_CONTEXT", "0xabc")


# ---------------------------------------------------------------------------
# Decimal canonicalization (10.4) - R-V2-08 / R-F04.
# ---------------------------------------------------------------------------
def test_decimal_equivalent_spellings_identical():
    for value in ("1", "1.0", "1.000", Decimal("1.000"), 1):
        assert c.canonicalize_decimal(value) == "1"
    assert c.canonicalize_decimal("-0") == "0"
    assert c.canonicalize_decimal("0.00") == "0"
    assert c.canonicalize_decimal(Decimal("-0.0")) == "0"


def test_decimal_no_exponent_and_range():
    assert c.canonicalize_decimal("100") == "100"
    assert c.canonicalize_decimal(Decimal("1E+2")) == "100"
    assert c.canonicalize_price("0.5") == "0.5"
    with pytest.raises(c.WalletContractError):
        c.canonicalize_price("1.5")  # price out of range
    with pytest.raises(c.WalletContractError):
        c.canonicalize_quantity("0")  # size must be > 0


def test_decimal_rejects_float_nan_inf():
    for bad in (1.5, float("nan"), float("inf"), True, "1e5", "abc"):
        with pytest.raises(c.WalletContractError):
            c.canonicalize_decimal(bad)


# ---------------------------------------------------------------------------
# Event type table (10.2) - R-W03 / R-V2-04.
# ---------------------------------------------------------------------------
def test_canonical_event_type_set_exact():
    assert set(c.CANONICAL_EVENT_TYPES) == {
        "TRADE_FILL", "TRANSFER_IN", "TRANSFER_OUT", "SPLIT", "MERGE", "CONVERSION",
        "REDEEM_SETTLEMENT", "DEPOSIT", "WITHDRAWAL", "REWARD", "MAKER_REBATE",
        "TAKER_REBATE", "REFERRAL_REWARD", "YIELD", "MIGRATION", "TIP",
        "COMBO_COMPRESS", "COMBO_WRAP", "COMBO_UNWRAP", "FEE", "UNKNOWN_PUBLIC_ACTIVITY",
    }


def test_standard_activity_type_map_exact():
    assert set(c.STANDARD_ACTIVITY_TYPE_MAP) == {
        "TRADE", "SPLIT", "MERGE", "REDEEM", "REWARD", "CONVERSION", "MIGRATION",
        "DEPOSIT", "WITHDRAWAL", "YIELD", "MAKER_REBATE", "TAKER_REBATE",
        "REFERRAL_REWARD", "TIP",
    }
    assert c.map_standard_activity_type("TRADE") == "TRADE_FILL"
    assert c.map_standard_activity_type("REDEEM") == "REDEEM_SETTLEMENT"


def test_combo_activity_type_map_exact():
    assert set(c.COMBO_ACTIVITY_TYPE_MAP) == {
        "SPLIT", "MERGE", "CONVERT", "COMPRESS", "WRAP", "UNWRAP", "REDEEM",
    }
    assert c.map_combo_activity_type("CONVERT") == "CONVERSION"
    assert c.map_combo_activity_type("COMPRESS") == "COMBO_COMPRESS"


def test_unknown_future_source_type_maps_unknown_public_activity():
    assert c.map_standard_activity_type("BRAND_NEW_TYPE") == "UNKNOWN_PUBLIC_ACTIVITY"
    assert c.map_combo_activity_type("BRAND_NEW_TYPE") == "UNKNOWN_PUBLIC_ACTIVITY"


# ---------------------------------------------------------------------------
# Event identity (10.6) - R-W01 / R-V2-02 / R-B04.
# ---------------------------------------------------------------------------
def _trade_event(**overrides):
    params = dict(
        identity_strength="SOURCE_CONTENT_DERIVED",
        canonical_event_type="TRADE_FILL",
        canonical_wallet="0x" + "1" * 40,
        combo_state="UNKNOWN",
        source_system_family="POLYMARKET_DATA_API_V2",
        condition_context="DATA_API_RESPONSE_CONDITION_ID",
        condition_value="0xabc",
        token_context="CLOB_TOKEN_ID",
        token_value="111",
        side="BUY",
        price="0.5",
        size="10",
        event_time="2026-01-01T00:00:00Z",
        transaction_hash="0x" + "a" * 64,
    )
    params.update(overrides)
    return c.build_wallet_evidence_event(**params)


def test_event_identity_matches_independent_oracle():
    ev = _trade_event()
    expected = _oracle_id("walletevent:sha256:", ev.identity_preimage())
    assert ev.wallet_event_id == expected


def test_event_identity_changes_on_one_semantic_field():
    a = _trade_event()
    b = _trade_event(price="0.6")
    assert a.wallet_event_id != b.wallet_event_id


def test_event_identity_equivalent_decimal_spellings_same_id():
    a = _trade_event(price="0.5", size="10")
    b = _trade_event(price="0.50", size="10.0")
    assert a.wallet_event_id == b.wallet_event_id


def test_combo_state_unknown_is_not_false():
    unknown = _trade_event(combo_state="UNKNOWN")
    false_state = _trade_event(combo_state="FALSE")
    assert unknown.wallet_event_id != false_state.wallet_event_id
    assert unknown.combo_state == "UNKNOWN"


def test_trade_fill_content_derived_requires_combo_state():
    with pytest.raises(c.WalletContractError):
        c.build_wallet_evidence_event(
            identity_strength="SOURCE_CONTENT_DERIVED",
            canonical_event_type="TRADE_FILL",
            canonical_wallet="0x" + "1" * 40,
            combo_state=None,
            source_system_family="POLYMARKET_DATA_API_V2",
        )


def test_chain_native_strong_identity_excludes_acquisition_fields():
    ev = c.build_wallet_evidence_event(
        identity_strength="CHAIN_NATIVE_STRONG",
        canonical_event_type="TRADE_FILL",
        canonical_wallet="0x" + "1" * 40,
        chain_id=137,
        transaction_hash="0x" + "a" * 64,
        log_index=3,
        combo_state="FALSE",
    )
    preimage = ev.identity_preimage()
    for absent in ("price", "size", "event_time", "condition_value"):
        assert absent not in preimage


def test_run_key_carrier_invariant_r_b01():
    # RawEvidenceReference / WalletEvidenceEvent must have no ingest_run_key field.
    assert "ingest_run_key" not in c.WalletEvidenceEvent.__dataclass_fields__
    # Page / observation / receipt must require it.
    assert "ingest_run_key" in c.WalletFeedPageEvidence.__dataclass_fields__
    assert "ingest_run_key" in c.WalletEventObservation.__dataclass_fields__
    assert "ingest_run_key" in c.WalletIngestRunReceipt.__dataclass_fields__


# ---------------------------------------------------------------------------
# Economic object key + combo receipt shape (15.6).
# ---------------------------------------------------------------------------
def test_economic_object_key_is_sorted_namespaced():
    key = c.build_economic_object_key(
        [("token", "CLOB_TOKEN_ID", "222"), ("condition", "DATA_API_RESPONSE_CONDITION_ID", "0xabc")]
    )
    assert key == (
        ("condition", "DATA_API_RESPONSE_CONDITION_ID", "0xabc"),
        ("token", "CLOB_TOKEN_ID", "222"),
    )


def test_combo_feed_receipt_requires_not_supported_time_filter():
    with pytest.raises(c.WalletContractError):
        c.build_feed_acquisition_receipt(
            feed_key="COMBO_ACTIVITY",
            endpoint="/v2/activity/combos",
            source_contract_version="1.0.0",
            canonical_wallet="0x" + "1" * 40,
            time_filter_capability="NOT_SUPPORTED",
            acquisition_scope="ALL_AVAILABLE_AS_OF_RUN",
            requested_page_size=100,
            feed_completion_state="COMPLETE",
            feed_replay_fidelity="FAITHFUL",
            requested_start="2026-01-01T00:00:00Z",  # illegal for NOT_SUPPORTED
        )
    ok = c.build_feed_acquisition_receipt(
        feed_key="COMBO_ACTIVITY",
        endpoint="/v2/activity/combos",
        source_contract_version="1.0.0",
        canonical_wallet="0x" + "1" * 40,
        time_filter_capability="NOT_SUPPORTED",
        acquisition_scope="ALL_AVAILABLE_AS_OF_RUN",
        requested_page_size=100,
        feed_completion_state="COMPLETE",
        feed_replay_fidelity="FAITHFUL",
    )
    assert ok.requested_start is None and ok.requested_end is None
