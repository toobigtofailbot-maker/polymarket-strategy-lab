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


# ===========================================================================
# WP175M: canonical draft output contract, prompt envelope, and H1 #3 replay
# ===========================================================================

from src.research_runtime.hermes_controlled_runtime import (  # noqa: E402
    CONFIDENCE_LABELS,
    CONFIDENCE_LABELS_SORTED,
    DRAFT_LIST_FIELDS,
    DRAFT_OUTPUT_CONTRACT_ID,
    DRAFT_REQUIRED_TOP_LEVEL_FIELDS,
    DraftStructureDiagnostics,
    HermesResearchEnvelope,
    MAX_COMMAND_LINE_CHARS,
    PolicyBroadeningError,
    SOURCE_CLASSES_SORTED,
    build_hermes_argv,
    build_research_draft_output_schema,
    build_research_envelope,
    inspect_research_draft_structure,
    research_draft_output_schema_digest,
)
from src.research_runtime.hermes_controlled_runtime import policy as pol  # noqa: E402


# The exact H1 #3 ALTERNATIVE structured shape (structural NAMES ONLY; harmless
# synthetic values -- never raw H1 research content). It carries the two canonical
# fields Hermes did include plus the alternative top-level keys it improvised.
_H1_3_ALTERNATIVE_KEYS = (
    "as_of",
    "completeness",
    "cross_category_assessment",
    "evidence_map",
    "generated_at",
    "research_category",
    "research_question",
    "scope",
    "sources",
)


def _h1_3_shape_document(request_id: str) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "request_id": request_id,
    }
    for key in _H1_3_ALTERNATIVE_KEYS:
        doc[key] = "synthetic-placeholder"
    return doc


def _contract_compliant_draft(request_id: str, max_sources: int) -> dict[str, object]:
    draft: dict[str, object] = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "request_id": request_id,
        "research_summary": "A synthetic balanced summary of dummy public evidence.",
        "confidence_label": "moderate",
        "evidence_for": ["dummy supporting note"],
        "evidence_against": ["dummy counter note"],
        "uncertainties": ["dummy uncertainty"],
        "known_missing_data": ["dummy missing datum"],
        "falsification_checks_performed": ["searched for dummy disconfirming evidence"],
        "limitations": ["public web only"],
        "what_would_change_the_conclusion": ["a dummy official confirmation"],
        "suggested_next_research_steps": ["monitor the dummy official channel"],
        "source_references": [
            {
                "url": "https://docs.example.com/reference",
                "title": "Documentation reference",
                "source_class": "reference",
            }
        ],
    }
    for flag in DRAFT_AUTHORITY_FLAGS:
        draft[flag] = True
    return draft


# --- M01-M12: contract derives from validator constants ----------------------


def test_m01_required_top_level_field_set_is_deterministic():
    assert DRAFT_REQUIRED_TOP_LEVEL_FIELDS[0:2] == ("schema_version", "request_id")
    # advisory_only must be the first missing authority/governance field.
    assert DRAFT_REQUIRED_TOP_LEVEL_FIELDS[2] == "advisory_only"
    expected = (
        ("schema_version", "request_id")
        + tuple(DRAFT_AUTHORITY_FLAGS)
        + ("research_summary", "confidence_label")
        + tuple(DRAFT_LIST_FIELDS)
        + ("source_references",)
    )
    assert DRAFT_REQUIRED_TOP_LEVEL_FIELDS == expected


def _schema(request_id="hermesresearchrequest:sha256:deadbeef", max_sources=8):
    return build_research_draft_output_schema(
        expected_request_id=request_id, max_sources=max_sources
    )


def test_m02_authority_flags_derive_from_constant():
    schema = _schema()
    for flag in DRAFT_AUTHORITY_FLAGS:
        assert schema["properties"][flag] == {"type": "boolean", "const": True}


def test_m03_list_fields_derive_from_constant():
    schema = _schema()
    for field in DRAFT_LIST_FIELDS:
        spec = schema["properties"][field]
        assert spec["type"] == "array"
        assert spec["items"]["type"] == "string"
        assert spec["maxItems"] == m.DRAFT_LIST_MAX_ITEMS
        assert spec["items"]["maxLength"] == m.DRAFT_LIST_ITEM_MAX_LEN


def test_m04_confidence_enum_derives_from_labels():
    schema = _schema()
    assert schema["properties"]["confidence_label"]["enum"] == list(CONFIDENCE_LABELS_SORTED)
    assert set(CONFIDENCE_LABELS_SORTED) == set(CONFIDENCE_LABELS)


def test_m05_source_class_enum_derives_from_source_classes():
    schema = _schema()
    enum = schema["properties"]["source_references"]["items"]["properties"]["source_class"]["enum"]
    assert enum == list(SOURCE_CLASSES_SORTED)


def test_m06_source_max_derives_from_request_and_absolute_cap():
    assert _schema(max_sources=5)["properties"]["source_references"]["maxItems"] == 5
    # capped at the absolute maximum
    assert _schema(max_sources=999)["properties"]["source_references"]["maxItems"] == MAX_SOURCES_ABSOLUTE


def test_m07_falsification_list_schema_is_non_empty():
    schema = _schema()
    assert schema["properties"]["falsification_checks_performed"]["minItems"] == 1
    # other list fields are not forced non-empty (validator allows empty there)
    assert "minItems" not in schema["properties"]["evidence_for"]


def test_m08_source_references_schema_is_non_empty():
    assert _schema()["properties"]["source_references"]["minItems"] == 1


def test_m09_output_contract_canonical_serialization_stable():
    a = m.canonical_json_bytes(_schema())
    b = m.canonical_json_bytes(_schema())
    assert a == b


def test_m10_output_contract_digest_stable_for_identical_inputs():
    assert research_draft_output_schema_digest(_schema()) == research_draft_output_schema_digest(_schema())
    # a different request id changes the digest
    assert research_draft_output_schema_digest(_schema(request_id="hermesresearchrequest:sha256:abc")) != \
        research_draft_output_schema_digest(_schema())


def test_m11_exact_request_id_embedded_as_const():
    schema = _schema(request_id="hermesresearchrequest:sha256:d977")
    assert schema["properties"]["request_id"] == {"type": "string", "const": "hermesresearchrequest:sha256:d977"}


def test_m12_exact_draft_schema_version_embedded_as_const():
    schema = _schema()
    assert schema["properties"]["schema_version"] == {"type": "string", "const": DRAFT_SCHEMA_VERSION}
    assert schema["draft_schema_version"] == DRAFT_SCHEMA_VERSION
    assert schema["schema_id"] == DRAFT_OUTPUT_CONTRACT_ID


def test_contract_required_set_equals_validator_required_set():
    """STOP CONTRACT_VALIDATOR_DRIFT: generated + validator share one required set."""
    schema = _schema()
    assert schema["required"] == list(DRAFT_REQUIRED_TOP_LEVEL_FIELDS)


# --- M13-M18: H1 #3 alternative-shape structural failure ---------------------


def test_m13_h1_3_alternative_shape_fails_draft_field_missing():
    req = build_research_run_request(_base_request_fields())
    doc = _h1_3_shape_document(req.request_id)
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(doc), expected_request_id=req.request_id, max_sources=req.max_sources
        )
    assert exc.value.code == "DRAFT_FIELD_MISSING"


def test_m14_m15_m16_diagnostics_present_missing_first():
    req = build_research_run_request(_base_request_fields())
    doc = _h1_3_shape_document(req.request_id)
    diag = inspect_research_draft_structure(json.dumps(doc))
    assert isinstance(diag, DraftStructureDiagnostics)
    assert diag.status == "AVAILABLE"
    assert diag.present_required_fields == ("schema_version", "request_id")
    assert diag.first_missing_field == "advisory_only"
    # missing set is exactly the remaining canonical required fields
    assert set(diag.missing_required_fields) == set(DRAFT_REQUIRED_TOP_LEVEL_FIELDS) - {
        "schema_version",
        "request_id",
    }


def test_m17_m18_diagnostics_contain_no_raw_or_arbitrary_values():
    req = build_research_run_request(_base_request_fields())
    doc = _h1_3_shape_document(req.request_id)
    diag = inspect_research_draft_structure(json.dumps(doc))
    all_tokens = set(diag.present_required_fields) | set(diag.missing_required_fields)
    if diag.first_missing_field is not None:
        all_tokens.add(diag.first_missing_field)
    # every emitted token is a canonical required field name; no alternative model key
    assert all_tokens.issubset(set(DRAFT_REQUIRED_TOP_LEVEL_FIELDS))
    for alt_key in _H1_3_ALTERNATIVE_KEYS:
        assert alt_key not in all_tokens
    assert "synthetic-placeholder" not in all_tokens


def test_diagnostics_invalid_output_status():
    diag = inspect_research_draft_structure("{not json")
    assert diag.status == "UNAVAILABLE_INVALID_OUTPUT"
    assert diag.present_required_fields == ()
    assert set(diag.missing_required_fields) == set(DRAFT_REQUIRED_TOP_LEVEL_FIELDS)


# --- M19-M24: valid synthetic contract-compliant draft -----------------------


def test_m19_synthetic_contract_compliant_draft_passes():
    req = build_research_run_request(_base_request_fields())
    draft = _contract_compliant_draft(req.request_id, req.max_sources)
    validated = validate_research_draft(
        json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
    )
    assert isinstance(validated, ValidatedResearchDraft)
    # generated schema and validator required-field sets are identical
    schema = build_research_draft_output_schema(
        expected_request_id=req.request_id, max_sources=req.max_sources
    )
    assert set(schema["required"]) == set(DRAFT_REQUIRED_TOP_LEVEL_FIELDS)
    diag = inspect_research_draft_structure(json.dumps(draft))
    assert diag.missing_required_fields == ()


@pytest.mark.parametrize("flag", DRAFT_AUTHORITY_FLAGS)
def test_m20_all_authority_flags_required_true(flag):
    req = build_research_run_request(_base_request_fields())
    draft = _contract_compliant_draft(req.request_id, req.max_sources)
    draft[flag] = False
    with pytest.raises(HermesResearchError):
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
        )


def test_m21_non_empty_falsification_required():
    req = build_research_run_request(_base_request_fields())
    draft = _contract_compliant_draft(req.request_id, req.max_sources)
    draft["falsification_checks_performed"] = []
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
        )
    assert exc.value.code == "DRAFT_UNSAFE_CONTENT"


def test_m22_non_empty_valid_source_references_required():
    req = build_research_run_request(_base_request_fields())
    draft = _contract_compliant_draft(req.request_id, req.max_sources)
    draft["source_references"] = []
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
        )
    assert exc.value.code == "DRAFT_SOURCE_INVALID"


def test_m23_confidence_closed_vocabulary_preserved():
    req = build_research_run_request(_base_request_fields())
    draft = _contract_compliant_draft(req.request_id, req.max_sources)
    draft["confidence_label"] = "certain"  # not in vocabulary
    with pytest.raises(HermesResearchError):
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
        )


def test_m24_source_class_closed_vocabulary_preserved():
    req = build_research_run_request(_base_request_fields())
    draft = _contract_compliant_draft(req.request_id, req.max_sources)
    draft["source_references"][0]["source_class"] = "blog"  # not in vocabulary
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
        )
    assert exc.value.code == "DRAFT_SOURCE_INVALID"


# --- P01-P08: prompt envelope --------------------------------------------------


def test_p01_permanent_system_instruction_version_is_1_1_0():
    assert pol.PERMANENT_SYSTEM_INSTRUCTION_VERSION == "hermes-research-system-instruction/1.1.0"


def test_p02_envelope_includes_draft_output_schema():
    req = build_research_run_request(_base_request_fields())
    env = build_research_envelope(req)
    assert isinstance(env, HermesResearchEnvelope)
    assert "draft_output_schema" in env.as_mapping()
    assert env.as_mapping()["draft_output_schema"]["type"] == "object"


def test_p03_envelope_schema_contains_every_canonical_required_field():
    req = build_research_run_request(_base_request_fields())
    env = build_research_envelope(req)
    schema = env.as_mapping()["draft_output_schema"]
    for field in DRAFT_REQUIRED_TOP_LEVEL_FIELDS:
        assert field in schema["properties"]
    assert schema["required"] == list(DRAFT_REQUIRED_TOP_LEVEL_FIELDS)
    # exact request id + draft schema version embedded as constants
    assert schema["properties"]["request_id"]["const"] == req.request_id
    assert schema["properties"]["schema_version"]["const"] == DRAFT_SCHEMA_VERSION
    # confidence + source-class enums present
    assert schema["properties"]["confidence_label"]["enum"] == list(CONFIDENCE_LABELS_SORTED)
    assert schema["properties"]["source_references"]["items"]["properties"]["source_class"]["enum"] == list(SOURCE_CLASSES_SORTED)
    # source cap aligned to request max_sources
    assert schema["properties"]["source_references"]["maxItems"] == req.max_sources


def test_p04_instruction_forbids_renaming_canonical_fields():
    instr = pol.PERMANENT_SYSTEM_INSTRUCTION
    assert "draft_output_schema" in instr
    assert "EXACTLY" in instr
    for alias in ("sources", "evidence_map", "completeness", "cross_category_assessment"):
        assert alias in instr
    assert "exactly one JSON object" in instr


def test_p05_request_identity_independent_of_output_schema():
    """The frozen H1 request id (d977...) reproduces because request identity derives
    ONLY from public_fields(); the new draft_output_schema lives in the envelope and
    never touches request identity."""
    a = build_research_run_request(_base_request_fields())
    b = build_research_run_request(_base_request_fields())
    assert a.request_id == b.request_id
    env = build_research_envelope(a)
    # envelope carries the request id verbatim; building the envelope does not mutate it
    assert env.request_id == a.request_id
    assert "draft_output_schema" not in a.public_fields()


def _request_for_argv() -> dict[str, object]:
    # A representative controlled request in the exact frozen H1 provider/model shape.
    fields = _base_request_fields()
    fields["provider_label"] = "openai-codex"
    fields["model_label"] = "gpt-5.6-sol"
    return fields


def _max_legal_request_fields() -> dict[str, object]:
    fields = _base_request_fields()
    fields["research_question"] = "a" * m._MAX_LONG_TEXT
    fields["research_objective"] = "b" * m._MAX_LONG_TEXT
    fields["public_market_context"] = "c" * m._MAX_LONG_TEXT
    fields["allowed_research_scope"] = sorted(m.ALLOWED_RESEARCH_SCOPE_TOKENS)
    fields["required_source_types"] = sorted(m.REQUIRED_SOURCE_TYPES)
    fields["max_sources"] = MAX_SOURCES_ABSOLUTE
    return fields


def test_p06_frozen_shape_request_argv_fits_command_line_guard():
    req = build_research_run_request(_request_for_argv())
    env = build_research_envelope(req)
    prompt = env.to_prompt_string()
    argv = build_hermes_argv("hermes", req, prompt)
    assert argv[-2] == "-z" and argv[-1] == prompt
    import subprocess as _sp
    assert len(_sp.list2cmdline(list(argv))) <= MAX_COMMAND_LINE_CHARS


def test_p07_max_legal_request_preserves_command_line_guard():
    req = build_research_run_request(_max_legal_request_fields())
    env = build_research_envelope(req)
    prompt = env.to_prompt_string()
    # the max legal request still fits after schema embedding
    argv = build_hermes_argv("hermes", req, prompt)
    assert len(argv) >= 1
    # the CreateProcess guard is not weakened: an oversized prompt still fails closed
    with pytest.raises(PolicyBroadeningError) as exc:
        build_hermes_argv("hermes", req, "x" * (pol.MAX_PROMPT_BYTES + 1))
    assert exc.value.code in {"POLICY_PROMPT_TOO_LARGE", "POLICY_COMMAND_LINE_TOO_LARGE"}


def test_p08_envelope_has_no_repo_path_or_credentials():
    req = build_research_run_request(_base_request_fields())
    env = build_research_envelope(req)
    text = env.to_prompt_string()
    for pattern in m._SECRET_PATTERNS:
        assert pattern.search(text) is None, pattern.pattern
    for marker in ("FIRECRAWL_API_KEY", "OPENAI_API_KEY", "local_data", "HERMES_HOME", "C:\\\\", "/home/"):
        assert marker not in text


# --- Section 22: offline H1 #3 contract replay (no provider/Hermes/Firecrawl) --


def test_offline_h1_3_contract_replay():
    req = build_research_run_request(_request_for_argv())
    # OLD failure shape: alternative top-level schema fails DRAFT_FIELD_MISSING, first
    # missing canonical field is advisory_only.
    old = _h1_3_shape_document(req.request_id)
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(old), expected_request_id=req.request_id, max_sources=req.max_sources
        )
    assert exc.value.code == "DRAFT_FIELD_MISSING"
    assert inspect_research_draft_structure(json.dumps(old)).first_missing_field == "advisory_only"
    # NEW prompt: explicitly embeds the canonical schema guidance.
    env = build_research_envelope(req)
    schema = env.as_mapping()["draft_output_schema"]
    assert schema["required"] == list(DRAFT_REQUIRED_TOP_LEVEL_FIELDS)
    assert schema["properties"]["request_id"]["const"] == req.request_id
    # SYNTHETIC compliant output validates without any post-generation repair.
    good = _contract_compliant_draft(req.request_id, req.max_sources)
    validate_research_draft(
        json.dumps(good), expected_request_id=req.request_id, max_sources=req.max_sources
    )


# ===========================================================================
# WP175M Finding G: exact contract/validator alignment (whitespace + URL regex)
# ===========================================================================

import re as _re_g


def _src_schema():
    return build_research_draft_output_schema(
        expected_request_id="hermesresearchrequest:sha256:deadbeef", max_sources=8
    )


def test_g01_research_summary_non_whitespace_pattern_matches_validator():
    schema = _src_schema()
    assert schema["properties"]["research_summary"]["pattern"] == m.DRAFT_NON_WHITESPACE_PATTERN
    req = build_research_run_request(_base_request_fields())
    # whitespace-only summary rejected by the validator
    ws = _contract_compliant_draft(req.request_id, req.max_sources)
    ws["research_summary"] = "   \t  "
    with pytest.raises(HermesResearchError):
        validate_research_draft(
            json.dumps(ws), expected_request_id=req.request_id, max_sources=req.max_sources
        )
    # a normal summary passes that specific requirement
    ok = _contract_compliant_draft(req.request_id, req.max_sources)
    validate_research_draft(
        json.dumps(ok), expected_request_id=req.request_id, max_sources=req.max_sources
    )


def test_g02_source_title_non_whitespace_pattern_matches_validator():
    schema = _src_schema()
    title_schema = schema["properties"]["source_references"]["items"]["properties"]["title"]
    assert title_schema["pattern"] == m.DRAFT_NON_WHITESPACE_PATTERN
    req = build_research_run_request(_base_request_fields())
    bad = _contract_compliant_draft(req.request_id, req.max_sources)
    bad["source_references"][0]["title"] = "   "
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(bad), expected_request_id=req.request_id, max_sources=req.max_sources
        )
    assert exc.value.code == "DRAFT_SOURCE_INVALID"


def test_g03_url_pattern_is_single_source_of_truth():
    schema = _src_schema()
    url_schema = schema["properties"]["source_references"]["items"]["properties"]["url"]
    assert url_schema["pattern"] == m.DRAFT_SOURCE_URL_PATTERN
    assert m._URL_RE.pattern == m.DRAFT_SOURCE_URL_PATTERN


def test_g04_no_invented_uri_format_constraint():
    url_schema = _src_schema()["properties"]["source_references"]["items"]["properties"]["url"]
    assert "format" not in url_schema


def test_g05_url_behavior_parity_generated_regex_vs_validator():
    req = build_research_run_request(_base_request_fields())
    gen = _re_g.compile(m.DRAFT_SOURCE_URL_PATTERN)

    def validator_accepts(url: str) -> bool:
        draft = _contract_compliant_draft(req.request_id, req.max_sources)
        draft["source_references"][0]["url"] = url
        try:
            validate_research_draft(
                json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
            )
            return True
        except HermesResearchError:
            return False

    over_length = "https://example.com/" + ("a" * (m.DRAFT_SOURCE_URL_MAX_LEN + 10))
    matrix = [
        ("https://example.com/report", True, True),
        ("HTTPS://EXAMPLE.COM/report", True, True),
        ("https://exa mple.com/report", False, False),   # whitespace
        ("http://example.com/report", False, False),      # missing https
        ("https://.example.com", False, False),           # malformed first char
        # over-length: the regex matches (no length bound) but validator length-rejects
        (over_length, True, False),
    ]
    for url, regex_expected, validator_expected in matrix:
        assert bool(gen.match(url)) is regex_expected, url
        assert validator_accepts(url) is validator_expected, url


def test_g06_valid_synthetic_contract_fixture_still_passes():
    req = build_research_run_request(_base_request_fields())
    draft = _contract_compliant_draft(req.request_id, req.max_sources)
    validate_research_draft(
        json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
    )


def test_g07_h1_3_alternative_shape_fixture_still_fails():
    req = build_research_run_request(_base_request_fields())
    doc = _h1_3_shape_document(req.request_id)
    with pytest.raises(HermesResearchError) as exc:
        validate_research_draft(
            json.dumps(doc), expected_request_id=req.request_id, max_sources=req.max_sources
        )
    assert exc.value.code == "DRAFT_FIELD_MISSING"
    assert inspect_research_draft_structure(json.dumps(doc)).first_missing_field == "advisory_only"


def test_g08_required_field_set_unchanged():
    expected = (
        ("schema_version", "request_id")
        + tuple(DRAFT_AUTHORITY_FLAGS)
        + ("research_summary", "confidence_label")
        + tuple(DRAFT_LIST_FIELDS)
        + ("source_references",)
    )
    assert DRAFT_REQUIRED_TOP_LEVEL_FIELDS == expected
    assert _src_schema()["required"] == list(DRAFT_REQUIRED_TOP_LEVEL_FIELDS)


def test_g09_receipt_1_3_fields_unchanged():
    from src.research_runtime.hermes_controlled_runtime import RECEIPT_SCHEMA_VERSION
    assert RECEIPT_SCHEMA_VERSION == "hermes-research-run-receipt/1.3.0"
    fields = {f.name for f in m.dataclasses.fields(m.HermesResearchRunReceipt)}
    for field in (
        "prompt_envelope_sha256",
        "draft_output_contract_sha256",
        "draft_diagnostics_status",
        "draft_present_required_fields",
        "draft_missing_required_fields",
        "draft_first_missing_field",
        "usage_session_id_digest",
    ):
        assert field in fields


def test_g10_provider_model_evidence_semantics_unchanged():
    # The validator still binds nothing about provider/model; that stays in the
    # controller. Here we assert the draft validator is unchanged in what it returns.
    req = build_research_run_request(_base_request_fields())
    draft = _contract_compliant_draft(req.request_id, req.max_sources)
    validated = validate_research_draft(
        json.dumps(draft), expected_request_id=req.request_id, max_sources=req.max_sources
    )
    assert isinstance(validated, ValidatedResearchDraft)
    for forbidden in ("provider", "model", "verified_provider"):
        assert not hasattr(validated, forbidden)


# S10-HERMES-CTX-01: explicit context-mode contract / validator lockstep.
from src.research_runtime.hermes_controlled_runtime import (  # noqa: E402
    CONTEXT_CLAIM_DIRECTIONS,
    CONTEXT_CLAIM_FIELDS,
    CONTEXT_CLAIM_KINDS,
    CONTEXT_REQUIRED_TOP_LEVEL_FIELDS,
    build_context_research_draft_output_schema,
    validate_context_research_draft,
)


def _context_doc(request_id: str) -> dict[str, object]:
    doc = _contract_compliant_draft(request_id, 8)
    doc["context_claims"] = [{
        "claim_statement": "The source bears on the synthetic subject.",
        "claim_kind": "INFERENCE", "subject_refs": ["subject:one"],
        "direction": "SUPPORTING", "source_reference_indices": [0],
        "assumptions": ["the source is accurate"],
        "uncertainty_note": "The public record may be incomplete.",
    }]
    return doc


def test_context_contract_is_additive_and_ordinary_h1_required_set_is_unchanged():
    request_id = "hermesresearchrequest:sha256:" + "a" * 64
    ordinary = build_research_draft_output_schema(expected_request_id=request_id, max_sources=8)
    context = build_context_research_draft_output_schema(
        expected_request_id=request_id, max_sources=8,
        allowed_subject_refs=("subject:one",),
    )
    assert ordinary["required"] == list(DRAFT_REQUIRED_TOP_LEVEL_FIELDS)
    assert "context_claims" not in ordinary["required"]
    assert context["required"] == list(CONTEXT_REQUIRED_TOP_LEVEL_FIELDS)
    claim_schema = context["properties"]["context_claims"]["items"]
    assert claim_schema["required"] == list(CONTEXT_CLAIM_FIELDS)
    assert tuple(claim_schema["properties"]["claim_kind"]["enum"]) == CONTEXT_CLAIM_KINDS
    assert tuple(claim_schema["properties"]["direction"]["enum"]) == CONTEXT_CLAIM_DIRECTIONS
    assert claim_schema["properties"]["subject_refs"]["items"]["enum"] == ["subject:one"]
    assert validate_research_draft(
        json.dumps(_contract_compliant_draft(request_id, 8)),
        expected_request_id=request_id, max_sources=8,
    ).context_claims == ()


def test_context_validator_requires_claims_and_retains_falsification_values():
    request_id = "hermesresearchrequest:sha256:" + "b" * 64
    with pytest.raises(HermesResearchError, match="CONTEXT_CLAIM_INVALID"):
        validate_context_research_draft(
            json.dumps(_contract_compliant_draft(request_id, 8)),
            expected_request_id=request_id, max_sources=8,
            allowed_subject_refs=("subject:one",),
        )
    validated = validate_context_research_draft(
        json.dumps(_context_doc(request_id)), expected_request_id=request_id,
        max_sources=8, allowed_subject_refs=("subject:one",),
    )
    assert validated.falsification_checks_performed == ("searched for dummy disconfirming evidence",)
    assert validated.context_claims[0].claim_id.startswith("hermescontextclaim:sha256:")


@pytest.mark.parametrize("mutation", [
    lambda claim: claim.update(extra="not allowed"),
    lambda claim: claim.pop("uncertainty_note"),
    lambda claim: claim.update(claim_kind="COMMAND"),
    lambda claim: claim.update(source_reference_indices=[99]),
    lambda claim: claim.update(subject_refs=["other"]),
    lambda claim: claim.update(claim_statement="place an order"),
])
def test_context_schema_negative_matrix_fails_closed(mutation):
    request_id = "hermesresearchrequest:sha256:" + "c" * 64
    doc = _context_doc(request_id)
    mutation(doc["context_claims"][0])
    with pytest.raises(HermesResearchError):
        validate_context_research_draft(
            json.dumps(doc), expected_request_id=request_id, max_sources=8,
            allowed_subject_refs=("subject:one",),
        )


def test_context_validator_rejects_extra_top_level_field():
    request_id = "hermesresearchrequest:sha256:" + "d" * 64
    doc = _context_doc(request_id)
    doc["extra"] = "not allowed"
    with pytest.raises(HermesResearchError, match="CONTEXT_CLAIM_INVALID"):
        validate_context_research_draft(
            json.dumps(doc), expected_request_id=request_id, max_sources=8,
            allowed_subject_refs=("subject:one",),
        )


# --- S10-HERMES-CTX-03: canonical public Polymarket ids in public_market_context --
#
# Live-shaped canonical PUBLIC identifiers (synthetic values with the real shapes: a
# 0x + 64 lowercase-hex condition id and a 77-digit CLOB token id). No network.

_CTX03_CONDITION = "0x3f5a9c1e7b2d4a6c8e0f1b3d5a7c9e2f4b6d8a0c2e4f6a8b0d2c4e6f8a1b3c5d"
_CTX03_EVENT_ID = "event:polymarket:" + _CTX03_CONDITION
_CTX03_MARKET_ID = "market:polymarket:512345"
_CTX03_TOKEN_ID = (
    "token:polymarket:"
    "71321045679252212594626385532706912750332728571942532289631379312455583992563"
)
_CTX03_WALLET = "0x" + "ab12cd34ef" * 4
_CTX03_CREDENTIALS = (
    "api_key=abc",
    "secret key here",
    "password",
    "private_key",
    "Bearer abcdefgh12345678",
    "Authorization: Basic abc",
    "sk-abcdef0123456789abcdef",
    "ghp_abcdefghijklmnopqrstuvwx",
    "-----BEGIN RSA " + "PRIVATE KEY-----",
    "access token",
)


def _ctx03_build(public_market_context: str, **overrides: object):
    fields = _base_request_fields()
    fields["public_market_context"] = public_market_context
    fields.update(overrides)
    return build_research_run_request(fields)


def _ctx03_rejected_code(public_market_context: str, **overrides: object) -> str:
    with pytest.raises(HermesResearchError) as exc:
        _ctx03_build(public_market_context, **overrides)
    assert str(exc.value) == exc.value.code
    return exc.value.code


def _ctx03_live_context() -> str:
    exact_scope = {
        "event_id": _CTX03_EVENT_ID,
        "market_id": _CTX03_MARKET_ID,
        "token_ids": [_CTX03_TOKEN_ID],
    }
    scope = {
        "alpha_context_present": False,
        "campaign_id": "contextcampaign:sha256:" + "1" * 64,
        "exact_scope_json": m.canonical_json_bytes(exact_scope).decode("utf-8"),
        "exact_scope_sha256": "2" * 64,
        "information_cutoff": "2026-09-27T00:00:00Z",
        "scope_key": "af1-market-scope:" + "3" * 64,
        "subject_refs": sorted([_CTX03_EVENT_ID, _CTX03_MARKET_ID, _CTX03_TOKEN_ID]),
    }
    return m.canonical_json_bytes(scope).decode("utf-8")


def test_ctx03_t01_existing_secret_controls_preserved():
    test_r007_secret_looking_request_content_rejected_without_echo()
    for credential in _CTX03_CREDENTIALS:
        for field in ("public_market_context", "research_question"):
            fields = _base_request_fields()
            fields[field] = f"context {credential}"
            with pytest.raises(HermesResearchError) as exc:
                build_research_run_request(fields)
            assert exc.value.code == "REQUEST_SECRET_DETECTED", credential
            assert credential not in str(exc.value)


def test_ctx03_t02_bare_64_hex_rejected():
    for value in (
        _CTX03_CONDITION,
        f"condition {_CTX03_CONDITION} is public",
        '{"condition_id":"' + _CTX03_CONDITION + '"}',
        _CTX03_CONDITION.upper().replace("0X", "0x"),
    ):
        assert _ctx03_rejected_code(value) == "REQUEST_SECRET_DETECTED"


def test_ctx03_t03_bare_wallet_shaped_40_hex_rejected():
    for value in (
        _CTX03_WALLET,
        f"wallet {_CTX03_WALLET}",
        "0x" + "AbCdEf0123" * 4,
        f"{_CTX03_EVENT_ID} {_CTX03_WALLET}",
    ):
        assert _ctx03_rejected_code(value) == "REQUEST_SECRET_DETECTED"


def test_ctx03_t04_canonical_event_id_accepted_in_public_market_context():
    for value in (
        _CTX03_EVENT_ID,
        f"Subject {_CTX03_EVENT_ID} is a public Polymarket event.",
        '{"subject_refs":["' + _CTX03_EVENT_ID + '"]}',
        "event:polymarket:market-512345",
    ):
        req = _ctx03_build(value)
        assert req.public_market_context == value
        assert req.request_id.startswith("hermesresearchrequest:sha256:")


def test_ctx03_t05_same_hex_rejected_in_other_request_fields():
    for field in ("research_question", "research_objective"):
        for value in (
            f"About {_CTX03_EVENT_ID}?",
            f"About {_CTX03_EVENT_ID} today",
            _CTX03_EVENT_ID,
            f"About {_CTX03_CONDITION} today",
        ):
            fields = _base_request_fields()
            fields["public_market_context"] = _CTX03_EVENT_ID  # valid here
            fields[field] = value
            with pytest.raises(HermesResearchError) as exc:
                build_research_run_request(fields)
            assert exc.value.code == "REQUEST_SECRET_DETECTED"


def test_ctx03_t06_wrong_namespace_rejected():
    hex64 = _CTX03_CONDITION
    for value in (
        "event:other:" + hex64,
        "foo:polymarket:" + hex64,
        "market:polymarket:" + hex64,
        "token:polymarket:" + hex64,
        "Event:Polymarket:" + hex64,
        "EVENT:POLYMARKET:" + hex64,
        "event:kalshi:" + hex64,
        "polymarket:" + hex64,
        "event:polymarket-x:" + hex64,
        "xevent:polymarket:" + hex64,
        "prefix:event:polymarket:" + hex64,
        "wallet.event:polymarket:" + hex64,
        "polymarket " + hex64,
    ):
        assert _ctx03_rejected_code(value) == "REQUEST_SECRET_DETECTED", value


def test_ctx03_t07_malformed_canonical_near_matches_rejected():
    hexdigits = _CTX03_CONDITION[2:]
    mixed = hexdigits[:32] + hexdigits[32:].upper()
    malformed_events = (
        "event:polymarket:0x" + hexdigits[:40],
        "event:polymarket:0x" + hexdigits[:63],
        "event:polymarket:0x" + hexdigits + "a",
        "event:polymarket:0x" + hexdigits + "g",
        "event:polymarket:0x" + hexdigits + "_x",
        "event:polymarket:0x" + hexdigits + _CTX03_WALLET,
        "event:polymarket:0x" + hexdigits + "12345",
        "event:polymarket:0X" + hexdigits,
        "event:polymarket:0x" + hexdigits.upper(),
        "event:polymarket:0x" + mixed,
        "event:polymarket:0x" + hexdigits + ".1",
        "event:polymarket:0x" + hexdigits + "-a",
        "event:polymarket:0x" + hexdigits + ":x",
        "event:polymarket:0x" + hexdigits + "/x",
        "event:polymarket:",
        "event:polymarket: ",
        "event:polymarket:market-",
        "event:polymarket:market-0123",
        "event:polymarket:market-12x",
        "event:polymarket:" + _CTX03_EVENT_ID,
        "event:polymarket:sk-abcdef0123456789abcdef",
    )
    rejected = malformed_events + (
        "event:polymarket:0x" + hexdigits + " " + _CTX03_WALLET,
        "token:polymarket:sk-abcdef0123456789abcdef",
    )
    for value in rejected:
        assert _ctx03_rejected_code(value) == "REQUEST_SECRET_DETECTED", value
        # Rejected in prose and JSON too, even beside a valid canonical event id.
        assert _ctx03_rejected_code(f"{_CTX03_EVENT_ID} and {value} here") == (
            "REQUEST_SECRET_DETECTED"
        ), value
        assert _ctx03_rejected_code('{"ref":"' + value + '"}') == "REQUEST_SECRET_DETECTED"
    # No malformed event near-match is recognized, so nothing is partially masked.
    for value in malformed_events + (
        "market:polymarket:0512345",
        "market:polymarket:",
        "token:polymarket:1.5",
    ):
        assert m._CANONICAL_PUBLIC_POLYMARKET_ID.search(value) is None, value
        assert m._CANONICAL_PUBLIC_POLYMARKET_ID.sub(" ", value) == value
    # The field-aware guard is stricter than the unchanged global rule, which still
    # misses word-glued hex; that global behavior is not broadened here.
    for value in ("event:polymarket:0x" + hexdigits + "g", "event:polymarket:0X" + hexdigits):
        m._scan_secret(value)


def test_ctx03_t07b_malformed_event_guard_is_load_bearing(monkeypatch):
    """Bypassing the namespace guard re-opens the word-glued acceptance (mutation check)."""
    glued = "event:polymarket:" + _CTX03_CONDITION + "g"
    assert _ctx03_rejected_code(glued) == "REQUEST_SECRET_DETECTED"
    monkeypatch.setattr(m, "_CANONICAL_EVENT_NAMESPACE", "\x00never-present\x00")
    assert _ctx03_build(glued).public_market_context == glued
    monkeypatch.undo()
    assert _ctx03_rejected_code(glued) == "REQUEST_SECRET_DETECTED"


def test_ctx03_t08_valid_id_plus_real_secret_rejected():
    for credential in _CTX03_CREDENTIALS:
        for value in (
            f"{_CTX03_EVENT_ID} {credential}",
            f"{credential} {_CTX03_EVENT_ID}",
            _ctx03_live_context()[:-1] + ',"note":"' + credential + '"}',
        ):
            assert _ctx03_rejected_code(value) == "REQUEST_SECRET_DETECTED", credential
    # Credential markers that overlap or abut an identifier are checked on the original.
    for value in (
        f"access {_CTX03_TOKEN_ID}",
        f"authorization: {_CTX03_EVENT_ID}",
        f"secret {_CTX03_TOKEN_ID.replace('token:', 'key:')}",
    ):
        assert _ctx03_rejected_code(value) == "REQUEST_SECRET_DETECTED", value


def test_ctx03_t09_live_shaped_token_id_accepted():
    assert len(_CTX03_TOKEN_ID) - len("token:polymarket:") == 77
    for value in (_CTX03_TOKEN_ID, f"Outcome token {_CTX03_TOKEN_ID} (public CLOB id)."):
        req = _ctx03_build(value)
        assert req.public_market_context == value


def test_ctx03_t10_live_shaped_market_event_token_context_accepted():
    context = _ctx03_live_context()
    # The exact scope is embedded as an escaped JSON string as well as in subject_refs.
    assert context.count(_CTX03_CONDITION) == 2
    req = _ctx03_build(context)
    assert req.public_market_context == context
    assert req.request_id == m.content_address(
        m.REQUEST_IDENTITY_PREFIX, req.public_fields()
    )


def test_ctx03_t11_original_bytes_drive_request_id():
    context = _ctx03_live_context()
    req = _ctx03_build(context)
    assert req.public_market_context == context
    assert req.public_fields()["public_market_context"] == context
    assert _CTX03_CONDITION in req.public_market_context
    assert req == _ctx03_build(context)
    changed_condition = _CTX03_CONDITION[:-1] + "e"
    changed = _ctx03_build(context.replace(_CTX03_CONDITION, changed_condition))
    assert changed.request_id != req.request_id
    changed_token = _ctx03_build(context.replace("992563", "992564"))
    assert changed_token.request_id != req.request_id
    # A masked copy would be identity-colliding across different identifiers.
    masked = m._CANONICAL_PUBLIC_POLYMARKET_ID.sub(" ", context)
    assert masked != context
    assert m._CANONICAL_PUBLIC_POLYMARKET_ID.sub(
        " ", context.replace(_CTX03_CONDITION, changed_condition)
    ) == masked


def test_ctx03_t12_mixed_rejection_never_echoes():
    secret = "sk-abcdef0123456789abcdef0123456789"
    context = f"{_CTX03_EVENT_ID} {_CTX03_TOKEN_ID} {secret} {_CTX03_WALLET}"
    with pytest.raises(HermesResearchError) as exc:
        _ctx03_build(context)
    assert exc.value.code == "REQUEST_SECRET_DETECTED"
    assert str(exc.value) == "REQUEST_SECRET_DETECTED"
    assert exc.value.args == ("REQUEST_SECRET_DETECTED",)
    for fragment in (secret, "sk-", _CTX03_CONDITION, _CTX03_WALLET, "polymarket"):
        assert fragment not in str(exc.value)
        assert fragment not in repr(exc.value)


def test_ctx03_t15_no_broad_global_allowlist(monkeypatch):
    import ast
    import inspect

    # The generic long-hex rule is still a global secret rule, unchanged.
    assert m._LONG_HEX_SECRET_PATTERN in m._SECRET_PATTERNS
    assert m._LONG_HEX_SECRET_PATTERN.pattern == r"\b0x[a-fA-F0-9]{40,}\b"
    assert m._LONG_HEX_SECRET_PATTERN.flags == m.re.compile("").flags
    assert len(m._SECRET_PATTERNS) == 11
    # The global scanner still rejects canonical event ids outside the narrow path.
    with pytest.raises(HermesResearchError):
        m._scan_secret(_CTX03_EVENT_ID)
    # Private fixed-signature helpers: no caller-supplied allowlist or digest hook.
    assert list(inspect.signature(m._scan_public_market_context_secret).parameters) == ["text"]
    assert list(inspect.signature(m._require_public_market_context).parameters) == [
        "value", "max_len"
    ]
    for name in dir(m):
        lowered = name.lower()
        assert "allowlist" not in lowered and "whitelist" not in lowered, name
        assert "safe_digest" not in lowered, name
    import src.research_runtime.hermes_controlled_runtime as package

    for name in ("_CANONICAL_PUBLIC_POLYMARKET_ID", "_scan_public_market_context_secret",
                 "_require_public_market_context", "_LONG_HEX_SECRET_PATTERN"):
        assert name not in getattr(package, "__all__", ())
    # Exactly one call site, bound to the public_market_context field only.
    tree = ast.parse(inspect.getsource(m))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id in {"_require_public_market_context",
                             "_scan_public_market_context_secret"}
    ]
    assert len(calls) == 2
    pmc_call = next(c for c in calls if c.func.id == "_require_public_market_context")
    assert ast.unparse(pmc_call.args[0]) == "fields['public_market_context']"
    # Runtime spy: every other string field still takes the ordinary strict path.
    strict_values: list[object] = []
    narrow_values: list[object] = []
    real_strict = m._require_str
    real_narrow = m._require_public_market_context

    def strict_spy(value, **kwargs):
        strict_values.append(value)
        return real_strict(value, **kwargs)

    def narrow_spy(value, **kwargs):
        narrow_values.append(value)
        return real_narrow(value, **kwargs)

    monkeypatch.setattr(m, "_require_str", strict_spy)
    monkeypatch.setattr(m, "_require_public_market_context", narrow_spy)
    fields = _base_request_fields()
    fields["public_market_context"] = _ctx03_live_context()
    build_research_run_request(fields)
    assert narrow_values == [fields["public_market_context"]]
    assert fields["public_market_context"] not in strict_values
    for field in ("schema_version", "research_question", "research_objective",
                  "research_category", "provider_label", "model_label",
                  "non_authority_notice"):
        assert fields[field] in strict_values, field
