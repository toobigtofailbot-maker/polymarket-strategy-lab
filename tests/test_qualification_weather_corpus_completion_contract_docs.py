"""S10-QUAL-DATA-02 contract drift protection: the contract, machine spec and operator constants agree."""

from __future__ import annotations

import json
from pathlib import Path

import tools.qualification.run_s10_qual_data_02 as operator
from src.data_layer.analytical_research import pendulumflow_v3 as v3
from src.data_layer.analytical_research import qualification_data_readiness as qd

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "qualification_weather_corpus_completion_contract.md"
SPEC = ROOT / "docs" / "wp_specs" / "S10-QUAL-DATA-02" / "wp_spec.json"
PROMPT = ROOT / "docs" / "wp_specs" / "S10-QUAL-DATA-02" / "wp_prompt.txt"


def _contract() -> str:
    return " ".join(CONTRACT.read_text(encoding="utf-8").split())


def test_corpus_completion_contract_doc_freezes_d011_retry_seed_and_budgets() -> None:
    text = _contract()
    # Seed identity and admission.
    for value in (operator.PREDECESSOR_HEAD, operator.BASE_SHA, operator.SEED_BUNDLE_ID, operator.SEED_DATASET_ID,
                  "QUAL_DATA_INSUFFICIENT", "FROZEN_BUDGET_EXHAUSTED", "SEED_EVIDENCE_MISSING", "SEED_EVIDENCE_CONFLICT",
                  "failed entries admitted: 0", "never enter any plan, report or bundle identity",
                  "Never seeded: rows, exclusions, bundle, ready manifests, scanned-hour decisions, label classifications or execution-evidence decisions",
                  "byte-identical bundle", "reports `CODE_DRIFT`"):
        assert value in text, value
    # D011 rules.
    for value in ("MARKET_HISTORY_SOURCE_INVALID", "its deeper walk-back stops", "not listed as searched",
                  operator.LTP_STATE_SEARCH_INCOMPLETE, "LABEL_V3_SOURCE_READ_FAILED", "LABEL_V3_RESOLUTION_MISSING",
                  "`CURRENT_ONLY` remains only on independent current Gamma metadata", "pendulumflow_failed_reads"):
        assert value in text, value
    for stage in operator.READ_STAGES:
        assert f"`{stage}`" in text, stage
    assert "LABEL_V3_SOURCE_READ_FAILED" in qd.MARKET_EXCLUSION_REASONS
    # Retry policy and caps match the operator constants.
    assert operator.THROTTLE_STATUSES == {429, 503} and operator.THROTTLE_DELAYS_SECONDS == (2, 8, 30)
    assert (operator.MAX_THROTTLE_RETRIES, operator.RETRY_AFTER_MAX_SECONDS, operator.MAX_TRANSPORT_RETRIES) == (3, 60, 1)
    for value in ("at most 3 retries after the frozen delays 2 s, 8 s, 30 s", "`max(frozen delay, Retry-After)`",
                  "No jitter, randomness or adaptive retry", "at most one immediate retry",
                  "never source absence", "no-sleep seam"):
        assert value in text, value
    for name in ("MAX_NETWORK_ATTEMPTS", "MAX_RESPONSE_BYTES", "MAX_SINGLE_RESPONSE", "MAX_DISTINCT_PENDULUM_HOURS"):
        assert f"`{name}={getattr(operator, name):_}`" in text, name
    assert "1 GiB" in text and operator.MEMORY_RANGE_BYTES == 1024 ** 3
    for host in sorted(operator.ALLOWED_HOSTS):
        assert host in text, host


def test_corpus_completion_contract_keeps_frozen_semantics_and_non_authority() -> None:
    text = _contract()
    for value in ("2026-08-18 through 2026-09-26 (40 dates)", qd.CHECKPOINT_A, qd.CHECKPOINT_B, "24 hours", "48 hours",
                  "±30-minute label window", "whole-object historical NDFD PoP12", v3.SOURCE_CLASS, v3.B0_SOURCE_AUTHORITY,
                  qd.B0_EXTERNAL_ONLY, "never canonical PIT"):
        assert value in text, value
    for policy in qd.FINALITY_POLICIES:
        assert policy in text, policy
    for phrase in ("DATA FORMATION / CORPUS COMPLETION ONLY", "No QualificationCandidate", "Gate C: NOT AUTHORIZED",
                   "Live: DISABLED", "Capital at risk: USD 0", "Merge: NOT AUTHORIZED", "This WP authorizes no successor"):
        assert phrase in text, phrase
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["identity"]["wp_id"] == "S10-QUAL-DATA-02"
    assert spec["identity"]["required_predecessor"] == {
        "pr_number": 202, "head_sha": operator.PREDECESSOR_HEAD, "merge_sha": operator.BASE_SHA}
    scope = spec["scope"]
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == scope["max_changed_files"] == 15
    for forbidden in ("pyproject.toml", ".github/workflows/ci.yml", "tools/qualification/run_s10_qual_data_01.py",
                      "src/data_layer/analytical_research/pendulumflow_v3.py", "src/data_layer/analytical_research/nws_ndfd_history.py",
                      "src/data_layer/analytical_research/qualification.py", "src/data_layer/analytical_research/qualification_gate.py",
                      "src/data_layer/point_in_time_market_research/research_provenance.py",
                      "src/data_layer/polymarket/public_client.py"):
        assert forbidden not in scope["required_changed_files"], forbidden
    authority = spec["authority"]
    for key in ("source_runtime", "network", "local_offline_tooling", "canonical_evidence_policy", "docs", "tests"):
        assert authority[key] is True, key
    for key in ("dependencies", "workflow_files", "credentials", "scheduler", "hermes_runtime", "strategy", "paper",
                "execution", "live", "workflow_governance"):
        assert authority[key] is False, key
    assert [item["requirement_id"] for item in spec["evidence_plan"]["items"]] == [f"R{i:03d}" for i in range(1, 36)]
    assert spec["successor_boundary"]["separately_gated"] is True
    assert "merge" in spec["successor_boundary"]["forbidden_in_this_wp"]
    prompt = PROMPT.read_text(encoding="utf-8")
    assert "Governance track expected: RUNTIME" in prompt and "**Do not merge.**" in prompt
    assert "BEGIN_NORMATIVE_RULE_MATRIX_V1" in prompt
