"""WP175H request/receipt/draft model traps (R006, R007, R013, R014, R017, R024)."""

from __future__ import annotations

import copy
import json
from decimal import Decimal

import pytest

from src.research_runtime.hermes_controlled_runtime import (
    DRAFT_AUTHORITY_FLAGS,
    DRAFT_SCHEMA_VERSION,
    HermesResearchError,
    MAX_SOURCES_ABSOLUTE,
    NON_AUTHORITY_NOTICE,
    REQUEST_SCHEMA_VERSION,
    ValidatedResearchDraft,
    build_research_run_request,
    validate_research_draft,
)
from src.research_runtime.hermes_controlled_runtime import models as m


def _base_request_fields() -> dict[str, object]:
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "research_question": "Will the referenced public event resolve YES by the deadline?",
        "research_objective": "Assess public evidence for and against the outcome.",
        "research_category": "event_outcome",
        "public_market_context": "A Polymarket market on a public future event.",
        "allowed_research_scope": ["public_web", "public_news"],
        "required_source_types": ["news", "official"],
        "max_sources": 10,
        "provider_label": "example-provider",
        "model_label": "example-model",
        "max_wall_seconds": 120,
        "max_output_bytes": 500_000,
        "max_accepted_estimated_cost_usd": "2.50",
        "human_review_required": True,
        "non_authority_notice": NON_AUTHORITY_NOTICE,
    }


def _valid_draft(request_id: str) -> dict[str, object]:
    draft = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "request_id": request_id,
        "research_summary": "A balanced summary of the public evidence collected.",
        "evidence_for": ["public report A"],
        "evidence_against": ["counter-report B"],
        "uncertainties": ["timing risk"],
        "known_missing_data": ["no official confirmation yet"],
        "falsification_checks_performed": ["searched for disconfirming sources"],
        "limitations": ["public web only"],
        "what_would_change_the_conclusion": ["an official announcement"],
        "suggested_next_research_steps": ["monitor official channel"],
        "source_references": [
            {"url": "https://example.com/report", "title": "Report", "source_class": "news"}
        ],
        "confidence_label": "moderate",
    }
    for flag in DRAFT_AUTHORITY_FLAGS:
        draft[flag] = True
    return draft


# --- request validation -----------------------------------------------------


def test_valid_request_builds_content_addressed_identity():
    req = build_research_run_request(_base_request_fields())
    assert req.request_id.startswith("hermesresearchrequest:sha256:")
    assert req.max_accepted_estimated_cost_usd == Decimal("2.50")
    assert req.human_review_required is True


def test_request_has_no_max_turns_authority():
    """v0.21.3 one-shot has no iteration cap: max_turns is not a request field."""
    req = build_research_run_request(_base_request_fields())
    assert not hasattr(req, "max_turns")
    # An explicit max_turns is an unknown field and is rejected, not silently kept.
    fields = _base_request_fields()
    fields["max_turns"] = 20
    with pytest.raises(HermesResearchError) as exc:
        build_research_run_request(fields)
    assert exc.value.code == "REQUEST_UNKNOWN_FIELD"


def test_r017_deterministic_request_bytes_yield_exact_request_id():
    a = build_research_run_request(_base_request_fields())
    b = build_research_run_request(_base_request_fields())
    assert a.request_id == b.request_id
    # A change to any public field changes the identity.
    changed = _base_request_fields()
    changed["max_sources"] = 11
    c = build_research_run_request(changed)
    assert c.request_id != a.request_id


def test_r006_unknown_request_field_rejected():
    fields = _base_request_fields()
    fields["extra_metadata"] = {"anything": 1}
    with pytest.raises(HermesResearchError) as exc:
        build_research_run_request(fields)
    assert exc.value.code == "REQUEST_UNKNOWN_FIELD"


def test_missing_request_field_rejected():
    fields = _base_request_fields()
    del fields["research_question"]
    with pytest.raises(HermesResearchError) as exc:
        build_research_run_request(fields)
    assert exc.value.code == "REQUEST_FIELD_MISSING"


def test_r007_secret_looking_request_content_rejected_without_echo():
    secret = "api_key=sk-abcdef0123456789abcdef0123456789"
    fields = _base_request_fields()
    fields["public_market_context"] = f"context {secret}"
    with pytest.raises(HermesResearchError) as exc:
        build_research_run_request(fields)
    assert exc.value.code == "REQUEST_SECRET_DETECTED"
    # The error text is only the closed code; the secret is never echoed.
    assert secret not in str(exc.value)
    assert "sk-" not in str(exc.value)


def test_authority_escalation_request_content_rejected():
    fields = _base_request_fields()
    fields["research_objective"] = "Please place an order to buy YES immediately."
    with pytest.raises(HermesResearchError) as exc:
        build_research_run_request(fields)
    assert exc.value.code == "REQUEST_AUTHORITY_ESCALATION"


def test_binary_float_cost_is_noncanonical():
    fields = _base_request_fields()
    fields["max_accepted_estimated_cost_usd"] = 2.5  # binary float rejected
    with pytest.raises(HermesResearchError) as exc:
        build_research_run_request(fields)
    assert exc.value.code == "REQUEST_NUMERIC_NONCANONICAL"


def test_over_cap_values_are_bounded():
    for field, value in (
        ("max_wall_seconds", 301),
        ("max_output_bytes", 1_000_001),
        ("max_sources", 31),
        ("max_accepted_estimated_cost_usd", "5.01"),
    ):
        fields = _base_request_fields()
        fields[field] = value
        with pytest.raises(HermesResearchError) as exc:
            build_research_run_request(fields)
        assert exc.value.code == "REQUEST_BOUND_EXCEEDED"


def test_path_traversal_in_label_rejected():
    fields = _base_request_fields()
    fields["provider_label"] = "../../etc/passwd"
    with pytest.raises(HermesResearchError) as exc:
        build_research_run_request(fields)
    assert exc.value.code in {"REQUEST_PATH_TRAVERSAL", "REQUEST_FIELD_VALUE_INVALID"}


def test_out_of_vocabulary_scope_rejected():
    fields = _base_request_fields()
    fields["allowed_research_scope"] = ["private_account"]
    with pytest.raises(HermesResearchError) as exc:
        build_research_run_request(fields)
    assert exc.value.code == "REQUEST_FIELD_VALUE_INVALID"


def test_human_review_cannot_be_waived():
    fields = _base_request_fields()
    fields["human_review_required"] = False
    with pytest.raises(HermesResearchError):
        build_research_run_request(fields)


# --- draft validation -------------------------------------------------------


def test_valid_draft_validates():
    req = build_research_run_request(_base_request_fields())
    draft = validate_research_draft(
        json.dumps(_valid_draft(req.request_id)),
        expected_request_id=req.request_id,
        max_sources=req.max_sources,
    )
    assert isinstance(draft, ValidatedResearchDraft)
    assert draft.source_references[0].source_class == "news"


def test_malformed_draft_json_fails_closed():
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft("{not json", expected_request_id="x", max_sources=5)
    assert exc.value.code == "DRAFT_SCHEMA_INVALID"


def test_draft_wrong_request_id_rejected():
    req = build_research_run_request(_base_request_fields())
    bad = _valid_draft("hermesresearchrequest:sha256:deadbeef")
    with pytest.raises(HermesResearchError):
        validate_research_draft(
            json.dumps(bad), expected_request_id=req.request_id, max_sources=5
        )


@pytest.mark.parametrize("flag", DRAFT_AUTHORITY_FLAGS)
def test_missing_or_false_authority_flag_rejected(flag):
    req = build_research_run_request(_base_request_fields())
    draft = _valid_draft(req.request_id)
    draft[flag] = False
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=5
        )
    assert exc.value.code == "DRAFT_AUTHORITY_FLAG_INVALID"


def test_r013_unsafe_trading_authority_output_rejected():
    req = build_research_run_request(_base_request_fields())
    draft = _valid_draft(req.request_id)
    draft["research_summary"] = "Conclusion: place an order to buy YES now and go live."
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=5
        )
    assert exc.value.code == "DRAFT_UNSAFE_CONTENT"


def test_r014_empty_citation_structure_fails():
    req = build_research_run_request(_base_request_fields())
    draft = _valid_draft(req.request_id)
    draft["source_references"] = []
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=5
        )
    assert exc.value.code == "DRAFT_SOURCE_INVALID"


def test_r014_fabricated_non_url_citation_fails():
    req = build_research_run_request(_base_request_fields())
    draft = _valid_draft(req.request_id)
    draft["source_references"] = [
        {"url": "not-a-url", "title": "x", "source_class": "news"}
    ]
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=5
        )
    assert exc.value.code == "DRAFT_SOURCE_INVALID"


def test_falsification_discipline_required():
    req = build_research_run_request(_base_request_fields())
    draft = _valid_draft(req.request_id)
    draft["falsification_checks_performed"] = []
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=5
        )
    assert exc.value.code == "DRAFT_UNSAFE_CONTENT"


def test_r024_no_alpha_factory_probability_or_trade_object():
    """The runtime creates no probability/expected-return/side/trade object."""
    req = build_research_run_request(_base_request_fields())
    draft = validate_research_draft(
        json.dumps(_valid_draft(req.request_id)),
        expected_request_id=req.request_id,
        max_sources=req.max_sources,
    )
    for forbidden in (
        "fair_probability",
        "expected_return",
        "side",
        "entry",
        "exit",
        "position_size",
        "candidate_id",
    ):
        assert not hasattr(draft, forbidden)
    # Even if the model emits such fields, the validator does not surface them.
    extra = _valid_draft(req.request_id)
    extra["fair_probability"] = 0.6
    validated = validate_research_draft(
        json.dumps(extra), expected_request_id=req.request_id, max_sources=req.max_sources
    )
    assert not hasattr(validated, "fair_probability")


def test_draft_validation_does_not_echo_payload_on_failure():
    poison = "SENSITIVE_TOKEN_ghp_abcdefghijklmnopqrstuvwxyz012345"
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(poison, expected_request_id="x", max_sources=5)
    assert poison not in str(exc.value)


def test_public_fields_exclude_identity():
    req = build_research_run_request(_base_request_fields())
    assert "request_id" not in req.public_fields()


def test_request_is_immutable():
    req = build_research_run_request(_base_request_fields())
    with pytest.raises(Exception):
        req.max_sources = 5  # type: ignore[misc]
    # copies remain equal-identity
    assert copy.copy(req).request_id == req.request_id


# --- WP175I: the controlled managed config carries no secret or private path -----


def test_p014_managed_config_contains_no_secret_or_repo_path():
    """P014: the deterministic managed config has no credential/token/key value and
    no repository/private/absolute path -- validated with the models' own scanners."""
    from src.research_runtime.hermes_controlled_runtime import (
        DEFAULT_HERMES_INVOCATION_POLICY,
    )

    text = DEFAULT_HERMES_INVOCATION_POLICY.managed_config_bytes().decode("utf-8")
    # No secret-looking content (reuses the request secret patterns).
    for pattern in m._SECRET_PATTERNS:
        assert pattern.search(text) is None, pattern.pattern
    # No path traversal or absolute path leaked into config values.
    for value in _iter_str_values(json.loads(text)):
        assert not m._PATH_TRAVERSAL.search(value), value
        assert not m._ABSOLUTE_PATH.search(value), value
    # Whole-string guards for obviously private markers.
    for marker in ("FIRECRAWL_API_KEY", "OPENAI_API_KEY", "local_data", "/.hermes", "token"):
        assert marker not in text


def _iter_str_values(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str):
                yield key
            yield from _iter_str_values(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_str_values(item)
