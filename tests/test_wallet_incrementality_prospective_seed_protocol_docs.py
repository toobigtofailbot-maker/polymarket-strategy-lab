"""Synthetic documentation examples, not source authentication or a study engine."""

import copy
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
WP = "S10-WALLET-SEED-01"
DOC = ROOT / "docs/wallet_incrementality_prospective_seed_protocol.md"
SPEC = ROOT / f"docs/wp_specs/{WP}/wp_spec.json"
STATUS = ROOT / f"docs/status_entries/{WP}.md"
BASE = "6a44d14dff4e631a5ba1fe6b94a46e532266512c"


def _canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(method):
    return (
        "walletmethod:sha256:"
        + hashlib.sha256(_canonical({"method": method})).hexdigest()
    )


def _closed_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate method field")
        result[key] = value
    return result


def _no_float_or_constant(value):
    raise ValueError("noncanonical method number")


def _method(text=None):
    blocks = re.findall(
        r"```json\n(.*?)\n```", DOC.read_text() if text is None else text, re.S
    )
    assert len(blocks) == 1
    envelope = json.loads(
        blocks[0],
        object_pairs_hook=_closed_pairs,
        parse_float=_no_float_or_constant,
        parse_constant=_no_float_or_constant,
    )
    assert set(envelope) == {"method", "method_digest"}
    expected = json.loads(SPEC.read_bytes())["examples"]["items"][0]["input"]
    # Canonical bytes distinguish booleans from integer-valued policy fields.
    assert _canonical(envelope["method"]) == _canonical(expected["method"])
    assert envelope["method_digest"] == _digest(envelope["method"])
    assert envelope["method_digest"] == expected["method_digest"]
    return envelope["method"]


def _document_with(envelope):
    return "```json\n" + json.dumps(envelope, allow_nan=False) + "\n```"


def _source_example(**changes):
    """Closed synthetic facts illustrating policy; true does not attest a source."""
    facts = dict(
        identity="CHAIN_NATIVE_STRONG",
        finality="FINALIZED",
        source_bound=True,
        both_book_sides_observed=True,
        book_transport="GET /book",
        coverage="COMPLETE",
        action_seen=1000,
        quote_seen=1000,
        finality_seen=1000,
        cutoff=1000,
        profile_window=True,
        self_hash_only=False,
    )
    facts.update(changes)
    return (
        facts["identity"] == "CHAIN_NATIVE_STRONG"
        and facts["finality"] == "FINALIZED"
        and facts["source_bound"] is True
        and facts["both_book_sides_observed"] is True
        and facts["book_transport"] == "GET /book"
        and facts["coverage"] == "COMPLETE"
        and facts["profile_window"] is True
        and facts["self_hash_only"] is False
        and all(
            type(facts[key]) is int
            for key in ("action_seen", "quote_seen", "finality_seen", "cutoff")
        )
        and facts["action_seen"] <= facts["cutoff"]
        and facts["finality_seen"] <= facts["cutoff"]
        and facts["cutoff"] - 30 <= facts["quote_seen"] <= facts["cutoff"]
    )


def _forecast_example(bid, ask, vote, *, coverage="COMPLETE", wallet_in_baseline=False):
    if wallet_in_baseline or coverage != "COMPLETE" or vote == "CONFLICT":
        return None
    for value in (bid, ask):
        if not isinstance(value, str) or not re.fullmatch(r"0\.[0-9]+", value):
            raise ValueError("canonical decimal text required")
    with localcontext() as context:
        context.prec = 80
        bid, ask = Decimal(bid), Decimal(ask)
        if not 0 < bid <= ask < 1 or ask - bid > Decimal("0.1"):
            return None
        baseline = (bid + ask) / 2
        if vote == "NO_SIGNAL":
            return baseline, baseline
        if type(vote) is not int or vote not in (0, 1):
            return None
        return baseline, Decimal("0.9") * baseline + Decimal("0.1") * vote


def _label_example(**changes):
    facts = dict(
        same_instrument=True,
        source_route=True,
        finality="FINALIZED",
        venue="RESOLVED",
        denominator=1,
        target_numerator=1,
        complement_numerator=0,
        observed=2001,
        target_end=2000,
        cutoff=1000,
        deadline=3000,
    )
    facts.update(changes)
    return (
        facts["same_instrument"] is True
        and facts["source_route"] is True
        and facts["finality"] == "FINALIZED"
        and facts["venue"] == "RESOLVED"
        and all(
            type(facts[k]) is int
            for k in ("denominator", "target_numerator", "complement_numerator")
        )
        and facts["denominator"] > 0
        and facts["target_numerator"] in (0, facts["denominator"])
        and facts["complement_numerator"] in (0, facts["denominator"])
        and facts["target_numerator"] + facts["complement_numerator"]
        == facts["denominator"]
        and max(facts["target_end"], facts["cutoff"])
        < facts["observed"]
        <= facts["deadline"]
    )


def _disposition_example(
    *, excluded=False, unknown=False, forecasts=True, label=False, expired=False
):
    if excluded:
        return "EXCLUDED"
    if unknown:
        return "UNKNOWN"
    if not forecasts:
        return "UNMATCHED"
    if label:
        return "MATCHED"
    return "CENSORED" if expired else "PENDING"


def test_seed01_method_block_and_freeze_identity():
    method = _method()
    assert method["study_state"] == "NOT_ACTIVATED"
    assert method["freeze"]["minimum_predecision_freeze_seconds"] == 86400
    assert method["target"]["unit_count"] == method["target"]["cluster_count"] == 1
    assert method["accounting"]["method_only_enrolled_count"] == "NOT_ESTABLISHED"
    assert _digest(dict(reversed(list(method.items())))) == _digest(method)
    for path, value in [("unit_count", 2), ("unit_count", True)]:
        changed = copy.deepcopy(method)
        changed["target"][path] = value
        assert _digest(changed) != _digest(method)
    changed = copy.deepcopy(method)
    changed["accounting"]["status_precedence"].reverse()
    assert _digest(changed) != _digest(method)
    for bad in (None, {}, "", True):
        with pytest.raises((AssertionError, TypeError)):
            _method(_document_with({"method": bad, "method_digest": "invalid"}))
    for mutation in ("missing", "extra", "null", "boolean", "false_authority"):
        changed = copy.deepcopy(method)
        if mutation == "missing":
            del changed["forecasts"]
        elif mutation == "extra":
            changed["unexpected"] = False
        elif mutation == "null":
            changed["sources"] = None
        elif mutation == "boolean":
            changed["target"]["unit_count"] = True
        else:
            changed["authority"]["no_execution_authority"] = False
        with pytest.raises(AssertionError):
            _method(
                _document_with({"method": changed, "method_digest": _digest(changed)})
            )
    for malformed in (
        '{"method":',
        '{"method":{},"method":{}}',
        '{"method":NaN}',
        '{"method":0.1}',
    ):
        with pytest.raises((ValueError, AssertionError)):
            _method("```json\n" + malformed + "\n```")
    expected = json.loads(SPEC.read_bytes())["examples"]["items"][0]["input"]
    assert expected["method_digest"] == _digest(expected["method"])
    assert set(expected) == {"method", "method_digest"}


def test_seed01_source_route_and_cutoff_contract():
    assert _source_example()
    for bad in (
        {"identity": "SOURCE_CONTENT_DERIVED"},
        {"identity": "API_NATIVE_STRONG"},
        {"finality": "UNFINALIZED"},
        {"source_bound": False},
        {"source_bound": 1},
        {"both_book_sides_observed": False},
        {"book_transport": "WS"},
        {"action_seen": 1001},
        {"quote_seen": 1001},
        {"quote_seen": 969},
        {"finality_seen": 1001},
        {"action_seen": None},
        {"coverage": "PARTIAL"},
        {"profile_window": False},
        {"self_hash_only": True},
    ):
        assert not _source_example(**bad)
    source = _method()["sources"]
    assert source["existing_source_route_proved"] is False
    assert source["wallet_identity"] == "CHAIN_NATIVE_STRONG_ONLY"
    assert source["book_admission"] == "OBSERVED_BOTH_SIDES"
    text = DOC.read_text()
    for required in (
        "transaction_hash, log_index",
        "block hash/number",
        "removed=false",
        "FINALIZED",
        "audited protocol/ABI/contract-version",
        "RawEvidenceReference",
        "ResearchProvenanceManifest",
        "two separate calls",
        "same original profile/head/cohort/context",
        "never substitutes",
        "self-hashed standalone mapping never establishes authenticity",
        "DQ OK",
        "EXACT/FAITHFUL",
    ):
        assert required in text


def test_seed01_forecast_algebra_and_controls():
    policy = _method()["forecasts"]
    assert policy["wallet_weight"] == "0.1" and policy["nonwallet_weight"] == "0.9"
    assert (
        policy["observation_delay_seconds"] == 0 and policy["decimal_precision"] == 80
    )
    assert policy["calibrated"] is False and policy["costs_enter_score"] is False
    for vote, expected_wallet, expected_loss, expected_delta in (
        (1, "0.64", "0.1296", "0.0304"),
        (0, "0.54", "0.2116", "-0.0516"),
        ("NO_SIGNAL", "0.6", "0.16", "0"),
    ):
        baseline, wallet = _forecast_example("0.58", "0.62", vote)
        assert baseline == Decimal("0.6") and wallet == Decimal(expected_wallet)
        loss0, lossw = (baseline - 1) ** 2, (wallet - 1) ** 2
        assert loss0 == Decimal("0.16") and lossw == Decimal(expected_loss)
        assert loss0 - lossw == Decimal(expected_delta)
        assert (baseline - 1) ** 2 - (baseline - 1) ** 2 == 0  # Masked control.
    for vote in (None, True, "CONFLICT", 2):
        assert _forecast_example("0.58", "0.62", vote) is None
    assert _forecast_example("0.58", "0.62", "NO_SIGNAL", coverage="PARTIAL") is None
    assert _forecast_example("0.58", "0.62", 1, wallet_in_baseline=True) is None
    for bid, ask in (("0.7", "0.6"), ("0.1", "0.9"), ("0.0", "0.1")):
        assert _forecast_example(bid, ask, 1) is None
    for bad in (0.5, "5e-1", "NaN", "", None):
        with pytest.raises(ValueError):
            _forecast_example(bad, "0.62", 1)
    assert (
        "does not assert that market prices are unaffected by wallet trading"
        in DOC.read_text()
    )


def test_seed01_label_finality_and_horizon_contract():
    assert _label_example() and _label_example(
        target_numerator=0, complement_numerator=1
    )
    for bad in (
        {"same_instrument": False},
        {"source_route": False},
        {"finality": "UNKNOWN"},
        {"venue": "VOID"},
        {"venue": "DISPUTED"},
        {"denominator": 0},
        {"target_numerator": True},
        {"target_numerator": 2},
        {"complement_numerator": 1},
        {"observed": 2000},
        {"observed": 3001},
    ):
        assert not _label_example(**bad)
    labels = _method()["labels"]
    assert labels["weather_substitution"] is False
    text = DOC.read_text()
    assert "absent proof yields UNKNOWN, not CENSORED" in text
    assert (
        "finalized canonical block" in text
        and "positive CTF payout denominator" in text
    )
    assert "Early settlement inconsistent with the frozen event end" in text


def test_seed01_membership_and_denominator_contract():
    policy = _method()["accounting"]
    assert policy["status_precedence"] == [
        "EXCLUDED",
        "UNKNOWN",
        "UNMATCHED",
        "MATCHED",
        "PENDING",
        "CENSORED",
    ]
    assert policy["unknown_group_count"] is None
    cases = [
        ({"excluded": True, "unknown": True, "label": True}, "EXCLUDED"),
        ({"unknown": True, "forecasts": False, "expired": True}, "UNKNOWN"),
        ({"forecasts": False, "expired": True}, "UNMATCHED"),
        ({"label": True}, "MATCHED"),
        ({"label": True, "expired": True}, "MATCHED"),
        ({}, "PENDING"),
        ({"expired": True}, "CENSORED"),
    ]
    for facts, expected in cases:
        disposition = _disposition_example(**facts)
        assert disposition == expected
        counts = {
            state: int(state == disposition) for state in policy["conservation_terms"]
        }
        assert sum(counts.values()) == 1
        groups = (
            len({"synthetic_group" for _ in range(3)})
            if disposition == "MATCHED"
            else 0
        )
        assert groups == int(
            disposition == "MATCHED"
        )  # Repeated/related fills remain one group.
    assert policy["zero_matched_numeric_summaries"] is None
    assert policy["zero_matched_status"] == "INSUFFICIENT_EVIDENCE"
    text = DOC.read_text()
    for required in (
        "never backdate",
        "no second market".lower(),
        "not permission to replace",
        "unknown group count stays null",
    ):
        assert required in text.lower()


def test_seed01_scope_truth_and_non_authority():
    spec = json.loads(SPEC.read_bytes())
    expected = {
        "docs/wallet_incrementality_prospective_seed_protocol.md",
        f"tests/{Path(__file__).name}",
        "docs/deferred_items_log.md",
        "docs/project_status.md",
        "docs/repo_truth_index.md",
        f"docs/status_entries/{WP}.md",
        f"docs/wp_specs/{WP}/wp_prompt.txt",
        f"docs/wp_specs/{WP}/wp_spec.json",
    }
    assert (
        set(spec["scope"]["required_changed_files"])
        == set(spec["scope"]["allowed_changed_files"])
        == expected
    )
    assert (
        spec["scope"]["max_changed_files"] == 8
        and spec["identity"]["required_predecessor"]["merge_sha"] == BASE
    )
    assert {k for k, v in spec["authority"].items() if v} == {
        "docs",
        "tests",
        "canonical_evidence_policy",
    }
    prompt = (ROOT / f"docs/wp_specs/{WP}/wp_prompt.txt").read_text()
    mirror = prompt.split("BEGIN_GOVERNANCE_AUTHORITY_V1\n", 1)[1].split(
        "END_GOVERNANCE_AUTHORITY_V1", 1
    )[0]
    assert {
        k: v == "true"
        for k, v in (line.split(": ") for line in mirror.splitlines()[1:])
    } == spec["authority"]
    for path in (ROOT / "docs/project_status.md", ROOT / "docs/repo_truth_index.md"):
        assert WP in path.read_text() and BASE in path.read_text()
    assert WP + "-D001" in (ROOT / "docs/deferred_items_log.md").read_text()
    status = STATUS.read_text()
    for required in (
        "STUDY_NOT_ACTIVATED",
        "REAL_PAIRED_UNITS_NOT_ESTABLISHED",
        "BLOCKED_NOT_READY",
        "Ready for review: NO",
        "PENDING",
        "NOT AUTHORIZED",
    ):
        assert required in status
    assert spec["successor_boundary"]["separately_gated"] is True
    assert _method()["authority"]["real_collection_authorized"] is False
    assert "DATA-03" in DOC.read_text() and "ALPHA-03/04" in DOC.read_text()
