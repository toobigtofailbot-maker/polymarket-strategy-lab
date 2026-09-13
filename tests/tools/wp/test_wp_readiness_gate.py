"""Focused and adversarial tests for the pre-implementation readiness gate.

These node names are referenced verbatim by docs/wp_specs/WP168G/wp_spec.json
evidence_plan (R002-R010, R026, R027); each carries a reachable assertion so the
gate's own post-implementation assertion-adequacy check accepts them.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
GATE_PATH = ROOT / "tools" / "wp" / "wp_readiness_gate.py"
PACKAGE = ROOT / "docs" / "wp_specs" / "WP168G"

_MODULE_SPEC = importlib.util.spec_from_file_location("wp_readiness_gate", GATE_PATH)
assert _MODULE_SPEC is not None and _MODULE_SPEC.loader is not None
gate = importlib.util.module_from_spec(_MODULE_SPEC)
sys.modules["wp_readiness_gate"] = gate  # required before exec so dataclasses resolves
_MODULE_SPEC.loader.exec_module(gate)
guard = gate.wp_spec_guard

REAL_PROMPT = (PACKAGE / "wp_prompt.txt").read_text(encoding="utf-8")
REAL_SPEC = json.loads((PACKAGE / "wp_spec.json").read_text(encoding="utf-8"))
REAL_CERT = json.loads((PACKAGE / "draftability_certificate.json").read_text(encoding="utf-8"))


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build(tmp_path: pathlib.Path, *, prompt: str | None = None, spec: dict | None = None):
    """Materialize a package whose PASS certificate is bound to the written bytes."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    wp = tmp_path / "wp_prompt.txt"
    wp.write_text(REAL_PROMPT if prompt is None else prompt, encoding="utf-8")
    sp = tmp_path / "wp_spec.json"
    sp.write_text(json.dumps(REAL_SPEC if spec is None else spec), encoding="utf-8")
    cert = copy.deepcopy(REAL_CERT)
    cert["wp_text_sha256"] = _sha(wp)
    cert["wp_spec_sha256"] = _sha(sp)
    cp = tmp_path / "draftability_certificate.json"
    cp.write_text(json.dumps(cert), encoding="utf-8")
    return str(wp), str(sp), str(cp)


def _matrix(rows: list[str]) -> str:
    body = "\n".join(rows)
    block = f"{gate.MATRIX_BEGIN}\n{gate.MATRIX_HEADER}\n{body}\n{gate.MATRIX_END}"
    idx = REAL_PROMPT.rfind(gate.MATRIX_BEGIN)
    end = REAL_PROMPT.find(gate.MATRIX_END, idx) + len(gate.MATRIX_END)
    return REAL_PROMPT[:idx] + block + REAL_PROMPT[end:]


def _evaluate(tmp_path, **kwargs):
    wp, sp, cp = _build(tmp_path, **{k: kwargs.pop(k) for k in ("prompt", "spec") if k in kwargs})
    return gate.evaluate_readiness(wp, sp, cp, str(ROOT), **kwargs)


def _authority_mirror(spec: dict, **overrides: object) -> str:
    values = {"risk_level": spec["identity"]["risk_level"]}
    values.update({key: spec["authority"][key] for key in guard.AUTHORITY_KEYS})
    values.update(overrides)
    lines = [gate.AUTHORITY_MIRROR_BEGIN]
    for key in gate.AUTHORITY_MIRROR_KEYS:
        value = values[key]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{key}: {rendered}")
    lines.append(gate.AUTHORITY_MIRROR_END)
    return "\n".join(lines)


def _prompt_for_track(track: str, spec: dict | None = None, **mirror_overrides: object) -> str:
    package_spec = REAL_SPEC if spec is None else spec
    return (
        REAL_PROMPT
        + "\n"
        + _authority_mirror(package_spec, **mirror_overrides)
        + f"\nGovernance track expected: {track}\n"
    )


def _evaluate_uncertified(
    tmp_path, track: str, *, mutate_spec=None, mirror_overrides=None, **kwargs
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    spec = copy.deepcopy(REAL_SPEC)
    if mutate_spec is not None:
        mutate_spec(spec)
    wp = tmp_path / "wp_prompt.txt"
    wp.write_text(
        _prompt_for_track(track, spec, **(mirror_overrides or {})), encoding="utf-8"
    )
    sp = tmp_path / "wp_spec.json"
    sp.write_text(json.dumps(spec), encoding="utf-8")
    return gate.evaluate_readiness(str(wp), str(sp), None, str(ROOT), **kwargs)


def test_prompt_structure_accepts_negative_test_hyphenation() -> None:
    prompt = REAL_PROMPT.replace("NEGATIVE TEST MATRIX", "NEGATIVE-TEST MATRIX")
    assert prompt != REAL_PROMPT
    assert "READINESS_PROMPT_STRUCTURE_INVALID" not in gate._prompt_structure_errors(prompt)


# --------------------------------------------------------------------------- R002
def test_valid_independently_certified_package_is_implementation_ready(tmp_path):
    result = _evaluate(tmp_path)
    assert result.is_ready is True
    assert result.status == "IMPLEMENTATION_READY"
    assert result.error_codes == ()
    assert result.package_guard_passed is True
    assert result.certificate_hash_bound is True
    assert result.normative_rule_count == 16
    # Readiness is not authorization: the closed result carries no AUTHORIZED grant.
    assert "AUTHORIZED" not in json.dumps(result.to_public_dict())


# --------------------------------------------------------------------------- R003
def test_wp168_same_domain_normalize_reject_contradiction_fails(tmp_path):
    prompt = _matrix(
        [
            "NR001|source_row|market|alt_hex_case|NORMALIZE_LOWERCASE|lowercase|NONE|NONE",
            "NR002|source_row|market|alt_hex_case|REJECT|reject_alt_case|NONE|NONE",
        ]
    )
    result = _evaluate(tmp_path, prompt=prompt)
    assert "READINESS_SEMANTIC_CONTRADICTION" in result.error_codes
    assert result.is_ready is False


# --------------------------------------------------------------------------- R004
def test_wp168_two_domain_case_policy_is_not_a_contradiction(tmp_path):
    prompt = _matrix(
        [
            "NR001|source_row|market|alt_hex_case|NORMALIZE_LOWERCASE|lowercase|NONE|NONE",
            "NR002|context|condition_id|alt_hex_case|REJECT|reject_alt_case|NONE|NONE",
        ]
    )
    result = _evaluate(tmp_path, prompt=prompt)
    assert "READINESS_SEMANTIC_CONTRADICTION" not in result.error_codes


# --------------------------------------------------------------------------- R005
def test_rule_matrix_missing_domain_or_duplicate_rule_id_fails_closed(tmp_path):
    # Missing DOMAIN column -> 7 fields -> not well-formed -> RULE_MATRIX_INVALID.
    missing = _matrix(["NR001|market|alt_hex_case|NORMALIZE_LOWERCASE|lowercase|NONE|NONE"])
    (tmp_path / "a").mkdir()
    r_missing = _evaluate(tmp_path / "a", prompt=missing)
    assert "READINESS_RULE_MATRIX_INVALID" in r_missing.error_codes

    # Duplicate RULE_ID -> RULE_MATRIX_INVALID.
    dup = _matrix(
        [
            "NR001|source_row|market|alt_hex_case|NORMALIZE_LOWERCASE|lowercase|NONE|NONE",
            "NR001|context|condition_id|alt_hex_case|REJECT|reject_alt_case|NONE|NONE",
        ]
    )
    (tmp_path / "b").mkdir()
    r_dup = _evaluate(tmp_path / "b", prompt=dup)
    assert "READINESS_RULE_MATRIX_INVALID" in r_dup.error_codes
    # No raw prompt content is echoed in the sanitized result.
    assert "source_row" not in json.dumps(r_dup.to_public_dict())


# --------------------------------------------------------------------------- R006
def test_preimplementation_missing_node_is_planned_only_when_target_file_is_in_scope():
    target = "tests/test_project_status_docs.py"  # exists on base
    absent_node = "test_this_node_does_not_exist_zzz"
    in_scope = gate._evidence_item_errors(
        absent_node, [target], {target}, ROOT, post_implementation=False
    )
    assert "READINESS_EVIDENCE_NODE_MISSING" not in in_scope
    out_of_scope = gate._evidence_item_errors(
        absent_node, [target], set(), ROOT, post_implementation=False
    )
    assert "READINESS_EVIDENCE_NODE_MISSING" in out_of_scope


# --------------------------------------------------------------------------- R007
def test_postimplementation_assertionless_evidence_node_is_rejected(tmp_path):
    module = tmp_path / "mod.py"
    module.write_text("def test_no_assert():\n    value = 1 + 1\n", encoding="utf-8")
    rel = module.relative_to(tmp_path).as_posix()
    codes = gate._evidence_item_errors(
        "test_no_assert", [rel], {rel}, tmp_path, post_implementation=True
    )
    assert "READINESS_EVIDENCE_ASSERTION_INADEQUATE" in codes


# --------------------------------------------------------------------------- R008
def test_postimplementation_same_module_asserting_helper_is_adequate(tmp_path):
    module = tmp_path / "mod.py"
    module.write_text(
        "def _check(x):\n    assert x == x\n\n"
        "def test_uses_helper():\n    _check(5)\n",
        encoding="utf-8",
    )
    rel = module.relative_to(tmp_path).as_posix()
    codes = gate._evidence_item_errors(
        "test_uses_helper", [rel], {rel}, tmp_path, post_implementation=True
    )
    assert "READINESS_EVIDENCE_ASSERTION_INADEQUATE" not in codes


# --------------------------------------------------------------------------- R009
def test_exact_scope_policy_and_optional_diff_check(tmp_path):
    bad = copy.deepcopy(REAL_SPEC)
    bad["scope"]["allowed_changed_files"] = bad["scope"]["allowed_changed_files"][:-1]
    assert "READINESS_SCOPE_INVALID" in gate._scope_errors(bad)
    assert gate._scope_errors(REAL_SPEC) == []
    # Optional diff verification: an empty diff (HEAD..HEAD) never equals the 20-file
    # required scope, so it fails closed.
    result = _evaluate(tmp_path, check_diff=True, base="HEAD", head="HEAD")
    assert "READINESS_DIFF_SCOPE_MISMATCH" in result.error_codes


# --------------------------------------------------------------------------- R010
def test_readiness_result_field_coverage_and_no_echo(tmp_path):
    marker = "ZZ_HOSTILE_MARKER_ZZ"
    prompt = REAL_PROMPT + f"\n\n{marker} intentionally injected prose.\n"
    result = _evaluate(tmp_path, prompt=prompt)
    public = result.to_public_dict()
    expected_keys = {
        "schema_id", "schema_version", "is_ready", "status", "wp_id",
        "error_codes", "checked_sections", "scope_file_count",
        "evidence_item_count", "normative_rule_count", "package_guard_passed",
        "certificate_hash_bound",
        "governance_track", "minimum_governance_track", "readiness_basis",
        "certificate_required",
    }
    assert set(public.keys()) == expected_keys
    assert public["schema_version"] == "1.2.0"
    assert marker not in json.dumps(public)


# --------------------------------------------------------------------------- WP171G R001 / N04-N06 / N11
def test_track_derivation_authority_mirror_and_stricter_selection(tmp_path):
    fast = _evaluate_uncertified(tmp_path / "fast", "FAST")
    assert fast.is_ready is True
    assert fast.minimum_governance_track == "FAST"

    stricter = _evaluate_uncertified(tmp_path / "stricter", "RUNTIME")
    assert stricter.is_ready is True
    assert stricter.minimum_governance_track == "FAST"

    def runtime(spec):
        spec["identity"]["risk_level"] = 3

    weak = _evaluate_uncertified(tmp_path / "weak", "FAST", mutate_spec=runtime)
    assert weak.is_ready is False
    assert "READINESS_GOVERNANCE_TRACK_INVALID" in weak.error_codes


def test_new_package_requires_exactly_one_governance_track_line(tmp_path):
    spec = copy.deepcopy(REAL_SPEC)
    sp = tmp_path / "wp_spec.json"
    sp.write_text(json.dumps(spec), encoding="utf-8")
    prompts = (
        REAL_PROMPT,
        _prompt_for_track("FAST", spec) + "Governance track expected: RUNTIME\n",
        REAL_PROMPT + "\n" + _authority_mirror(spec) + "\nGovernance track expected: fast\n",
    )
    for index, prompt in enumerate(prompts):
        wp = tmp_path / f"wp_{index}.txt"
        wp.write_text(prompt, encoding="utf-8")
        result = gate.evaluate_readiness(str(wp), str(sp), None, str(ROOT))
        assert result.is_ready is False
        assert "READINESS_GOVERNANCE_TRACK_INVALID" in result.error_codes


# --------------------------------------------------------------------------- WP171G N01
def test_fast_without_certificate_is_ready(tmp_path):
    result = _evaluate_uncertified(tmp_path, "FAST")
    assert result.is_ready is True
    assert result.governance_track == "FAST"
    assert result.readiness_basis == "DETERMINISTIC"
    assert result.certificate_required is False
    assert result.certificate_hash_bound is False
    assert result.package_guard_passed is None
    assert "package_guard" not in result.checked_sections
    assert "spec_validation" in result.checked_sections


# --------------------------------------------------------------------------- WP171G N02
def test_runtime_without_certificate_is_ready(tmp_path):
    def runtime(spec):
        spec["authority"]["network"] = True

    result = _evaluate_uncertified(tmp_path, "RUNTIME", mutate_spec=runtime)
    assert result.is_ready is True
    assert result.minimum_governance_track == "RUNTIME"
    assert result.readiness_basis == "DETERMINISTIC"


# --------------------------------------------------------------------------- WP171G N03
def test_protected_without_certificate_fails_closed(tmp_path):
    def protected(spec):
        spec["authority"]["credentials"] = True

    result = _evaluate_uncertified(tmp_path, "PROTECTED", mutate_spec=protected)
    assert result.is_ready is False
    assert result.error_codes == ("READINESS_CERTIFICATE_NOT_PASS",)
    assert result.certificate_required is True


# --------------------------------------------------------------------------- WP171G N04-N06 / N11
def test_weaker_governance_tracks_are_rejected(tmp_path):
    mutations = (
        ("FAST", lambda s: s["authority"].__setitem__("credentials", True)),
        ("RUNTIME", lambda s: s["authority"].__setitem__("execution", True)),
        ("FAST", lambda s: s["authority"].__setitem__("live", True)),
        ("RUNTIME", lambda s: s["authority"].__setitem__("live", True)),
        ("FAST", lambda s: s["authority"].__setitem__("paper", True)),
        ("FAST", lambda s: s["authority"].__setitem__("scheduler", True)),
        ("FAST", lambda s: s["authority"].__setitem__("hermes_runtime", True)),
        ("FAST", lambda s: s["authority"].__setitem__("network", True)),
        ("FAST", lambda s: s["identity"].__setitem__("risk_level", 3)),
        ("RUNTIME", lambda s: s["identity"].__setitem__("risk_level", 4)),
    )
    for index, (track, mutate) in enumerate(mutations):
        case = tmp_path / str(index)
        case.mkdir()
        result = _evaluate_uncertified(case, track, mutate_spec=mutate)
        assert result.is_ready is False
        assert "READINESS_GOVERNANCE_TRACK_INVALID" in result.error_codes


def test_authority_mirror_rejects_understatement_and_invalid_blocks(tmp_path):
    mismatch_cases = (
        {"credentials": True},
        {"network": True},
        {"execution": True},
        {"live": True},
        {"risk_level": 4},
    )
    for index, overrides in enumerate(mismatch_cases):
        result = _evaluate_uncertified(
            tmp_path / f"mismatch_{index}", "FAST", mirror_overrides=overrides
        )
        assert result.is_ready is False
        assert result.error_codes == ("READINESS_AUTHORITY_MIRROR_INVALID",)

    spec = copy.deepcopy(REAL_SPEC)
    sp = tmp_path / "invalid_wp_spec.json"
    sp.write_text(json.dumps(spec), encoding="utf-8")
    valid_block = _authority_mirror(spec)
    malformed_block = valid_block.replace("credentials: false", "credentials: FALSE")
    prompts = (
        REAL_PROMPT + "\nGovernance track expected: FAST\n",
        REAL_PROMPT + "\n" + valid_block + "\n" + valid_block
        + "\nGovernance track expected: FAST\n",
        REAL_PROMPT + "\n" + malformed_block + "\nGovernance track expected: FAST\n",
    )
    for index, prompt in enumerate(prompts):
        wp = tmp_path / f"invalid_prompt_{index}.txt"
        wp.write_text(prompt, encoding="utf-8")
        result = gate.evaluate_readiness(str(wp), str(sp), None, str(ROOT))
        assert result.is_ready is False
        assert "READINESS_AUTHORITY_MIRROR_INVALID" in result.error_codes


# --------------------------------------------------------------------------- WP171G N07
def test_historical_certified_package_remains_ready(tmp_path):
    result = _evaluate(tmp_path)
    assert result.is_ready is True
    assert result.governance_track == "PROTECTED"
    assert result.minimum_governance_track == "FAST"
    assert result.readiness_basis == "INDEPENDENT_CERTIFICATE"
    assert result.package_guard_passed is True
    assert "package_guard" in result.checked_sections


# --------------------------------------------------------------------------- WP171G N09
def test_certificate_hash_change_invalidates_protected(tmp_path):
    wp, sp, cp = _build(tmp_path)
    pathlib.Path(wp).write_text(REAL_PROMPT + "\nsemantic change\n", encoding="utf-8")
    result = gate.evaluate_readiness(wp, sp, cp, str(ROOT))
    assert result.is_ready is False
    assert "READINESS_CERTIFICATE_NOT_PASS" in result.error_codes


# --------------------------------------------------------------------------- WP171G N10
def test_check_diff_rejects_scope_mismatch(tmp_path):
    result = _evaluate_uncertified(
        tmp_path, "FAST", check_diff=True, base="HEAD", head="HEAD"
    )
    assert result.is_ready is False
    assert "READINESS_DIFF_SCOPE_MISMATCH" in result.error_codes


# --------------------------------------------------------------------------- WP171G R002
def test_certificate_policy_and_historical_compatibility(tmp_path):
    cases = (
        ("fast", test_fast_without_certificate_is_ready),
        ("runtime", test_runtime_without_certificate_is_ready),
        ("protected", test_protected_without_certificate_fails_closed),
        ("historical", test_historical_certified_package_remains_ready),
        ("hash", test_certificate_hash_change_invalidates_protected),
    )
    for name, test in cases:
        case = tmp_path / name
        case.mkdir()
        test(case)
    assert {name for name, _test in cases} == {
        "fast", "runtime", "protected", "historical", "hash"
    }


# --------------------------------------------------------------------------- WP171G R003
def test_readiness_result_tracks_draftability_basis(tmp_path):
    deterministic = _evaluate_uncertified(tmp_path / "deterministic", "FAST")
    certified = _evaluate(tmp_path / "certified")
    assert deterministic.to_public_dict()["readiness_basis"] == "DETERMINISTIC"
    assert certified.to_public_dict()["readiness_basis"] == "INDEPENDENT_CERTIFICATE"
    assert deterministic.governance_track == "FAST"
    assert certified.governance_track == "PROTECTED"
    assert deterministic.package_guard_passed is None
    assert certified.package_guard_passed is True


# --------------------------------------------------------------------------- WP171G R004 / N08
def test_fast_same_envelope_correction_without_certificate(tmp_path):
    before = _evaluate_uncertified(tmp_path / "before", "FAST")

    def correction(spec):
        spec["identity"]["objective"] += " Same-authority wording correction."

    after = _evaluate_uncertified(
        tmp_path / "after", "FAST", mutate_spec=correction
    )
    assert before.is_ready is True
    assert after.is_ready is True
    assert after.certificate_hash_bound is False


# --------------------------------------------------------------------------- WP171G N12
def test_track_choice_cannot_bypass_failed_required_evidence(tmp_path):
    def inadequate(spec):
        item = next(
            item for item in spec["evidence_plan"]["items"]
            if item["source"] == "pytest"
        )
        item["expected_result"] = "passes"

    result = _evaluate_uncertified(tmp_path, "FAST", mutate_spec=inadequate)
    assert result.is_ready is False
    assert "READINESS_EVIDENCE_ASSERTION_INADEQUATE" in result.error_codes


# --------------------------------------------------------------------------- R026
def test_preimplementation_planned_new_node_in_existing_in_scope_file_is_allowed():
    existing_file = "tests/tools/wp/test_wp_spec_guard.py"  # already exists on base
    assert (ROOT / existing_file).is_file()
    planned_node = "test_a_brand_new_node_not_yet_written"
    allowed = gate._evidence_item_errors(
        planned_node, [existing_file], {existing_file}, ROOT, post_implementation=False
    )
    assert "READINESS_EVIDENCE_NODE_MISSING" not in allowed
    rejected = gate._evidence_item_errors(
        planned_node, [existing_file], set(), ROOT, post_implementation=False
    )
    assert "READINESS_EVIDENCE_NODE_MISSING" in rejected


# --------------------------------------------------------------------------- R027
def test_wp_spec_guard_authorizes_only_exact_pr_template_governance_path():
    template = ".github/pull_request_template.md"
    assert guard._authority_requirements(template, "WP168G") == (
        "workflow_governance",
        "canonical_evidence_policy",
    )
    # Arbitrary non-workflow .github path stays unauthorized.
    assert guard._authority_requirements(".github/other_notes.md", "WP168G") is None
    # .github/workflows semantics unchanged.
    assert guard._authority_requirements(".github/workflows/ci.yml", "WP168G") == (
        "workflow_files",
    )
    # Either required flag false -> the path cannot be authorized.
    needs = guard._authority_requirements(template, "WP168G")
    for missing in ("workflow_governance", "canonical_evidence_policy"):
        authority = {n: True for n in needs}
        authority[missing] = False
        assert any(authority[n] is not True for n in needs)
