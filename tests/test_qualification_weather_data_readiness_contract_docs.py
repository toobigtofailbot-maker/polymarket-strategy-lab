"""S10-QUAL-DATA-01 contract drift protection: the contract, machine spec and code constants agree."""

from __future__ import annotations

import json
from pathlib import Path

from src.data_layer.analytical_research import nws_ndfd_history as ndfd
from src.data_layer.analytical_research import pendulumflow_v3 as v3
from src.data_layer.analytical_research import qualification_data_readiness as qd

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "qualification_weather_data_readiness_contract.md"
SPEC = ROOT / "docs" / "wp_specs" / "S10-QUAL-DATA-01" / "wp_spec.json"
PROMPT = ROOT / "docs" / "wp_specs" / "S10-QUAL-DATA-01" / "wp_prompt.txt"


def _contract() -> str:
    return " ".join(CONTRACT.read_text(encoding="utf-8").split())


def test_contract_freezes_lineage_corpus_checkpoints_and_windows() -> None:
    text = _contract()
    for value in (qd.ALPHA_CANDIDATE_ID, qd.ALPHA_FAMILY_ID, qd.ALPHA_EPISODE_ID, qd.ALPHA_REGISTRY_HEAD, qd.AF1_RECEIPT_ID,
                  "2026-08-18 through 2026-09-26 inclusive (40 dates)", qd.CHECKPOINT_A, qd.CHECKPOINT_B,
                  "exactly 24 hours", "[checkpoint - 48 hours, checkpoint]", "ALPHA_LINEAGE_EVIDENCE_MISSING",
                  "ALPHA_LINEAGE_CONFLICT", "AF1_EVIDENCE_DRIFT", "never reconstructed"):
        assert value in text, value
    assert qd.target_dates()[0] == "2026-08-18" and qd.target_dates()[-1] == "2026-09-26" and len(qd.target_dates()) == 40
    assert qd.MARKET_HISTORY_LOOKBACK.total_seconds() == 24 * 3600
    assert qd.NDFD_VINTAGE_LOOKBACK.total_seconds() == 48 * 3600


def test_contract_source_authority_matches_code() -> None:
    text = _contract()
    for value in (v3.SOURCE_CLASS, v3.B0_SOURCE_AUTHORITY, ndfd.SOURCE_CLASS, qd.B0_EXTERNAL_ONLY, qd.B0_CANONICAL,
                  "never canonical PIT", "Never `SOURCE_KIND_CANONICAL_PIT`", "PIT_MARKET_PROBABILITY_V1",
                  "FULL and SINGLE-BY-DESIGN are admissible", "PARTIAL and SINGLE-BY-DEFECT are diagnostic only",
                  "`eccodes==2.48.0`", "`eccodeslib==2.48.0.26`", "Four clocks stay separate"):
        assert value in text, value
    for policy in qd.FINALITY_POLICIES:
        assert policy in text, policy
    for state in qd.EXECUTION_STATES:
        assert state in text, state
    for terminal in qd.TERMINALS:
        assert terminal in text, terminal
    assert ndfd.EXPECTED_ECCODES_VERSION == "2.48.0" and ndfd.EXPECTED_ECCODESLIB_VERSION == "2.48.0.26"


def test_contract_network_budget_matches_operator_constants() -> None:
    import tools.qualification.run_s10_qual_data_01 as operator

    text = _contract()
    for host in sorted(operator.ALLOWED_HOSTS):
        assert host in text, host
    assert operator.ALLOWED_HOSTS == {"archive.pendulumflow.com", "noaa-ndfd-pds.s3.amazonaws.com",
                                      "gamma-api.polymarket.com", "api.weather.gov"}
    assert operator.ALLOWED_METHODS == {"GET", "HEAD"}
    budgets = (operator.MAX_TARGET_DATES, operator.MAX_CANDIDATES, operator.MAX_STATIONS, operator.MAX_PENDULUM_HOURS,
               operator.MAX_ATTEMPTS, operator.MAX_TOTAL_BYTES, operator.MAX_SINGLE_RESPONSE, operator.MAX_RETRIES_PER_REQUEST)
    assert budgets == (40, 1024, 128, 2000, 8192, 2 * 1024 ** 3, 256 * 1024 ** 2, 1)
    for phrase in ("<=40 target dates", "<=1024 candidates", "<=128 stations", "<=2000 PendulumFlow hours",
                   "<=8192 transport attempts including retries", "<=2 GiB total bytes including retries",
                   "<=256 MiB per response", "at most one immediate retry"):
        assert phrase in text, phrase


def test_contract_and_spec_keep_non_authority_and_successor_boundary() -> None:
    text = _contract()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    for phrase in ("DATA FORMATION / READINESS ONLY", "No QualificationCandidate", "Gate C: NOT AUTHORIZED",
                   "Live: DISABLED", "Capital at risk: USD 0", "This WP authorizes no successor"):
        assert phrase in text, phrase
    assert spec["identity"]["wp_id"] == "S10-QUAL-DATA-01"
    assert spec["identity"]["required_predecessor"] == {
        "pr_number": 201, "head_sha": "cd70800d40f60f4ec20f5b17e107cc56643562a2",
        "merge_sha": "77738717fee422fe83d8bb2b7765c36dfbe6b283"}
    scope = spec["scope"]
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == scope["max_changed_files"] == 20
    for forbidden in ("pyproject.toml", ".github/workflows/ci.yml", "src/data_layer/analytical_research/__init__.py",
                      "src/data_layer/analytical_research/qualification.py", "src/data_layer/analytical_research/qualification_gate.py",
                      "src/data_layer/point_in_time_market_research/research_provenance.py",
                      "src/data_layer/analytical_research/external_dataset.py", "src/data_layer/polymarket/public_client.py"):
        assert forbidden not in scope["required_changed_files"], forbidden
    authority = spec["authority"]
    for key in ("source_runtime", "network", "local_offline_tooling", "canonical_evidence_policy", "docs", "tests"):
        assert authority[key] is True, key
    for key in ("dependencies", "workflow_files", "credentials", "scheduler", "hermes_runtime", "strategy", "paper",
                "execution", "live", "workflow_governance"):
        assert authority[key] is False, key
    assert [item["requirement_id"] for item in spec["evidence_plan"]["items"]] == [f"R{i:03d}" for i in range(1, 35)]
    assert spec["successor_boundary"]["separately_gated"] is True
    assert "merge" in spec["successor_boundary"]["forbidden_in_this_wp"]
    prompt = PROMPT.read_text(encoding="utf-8")
    assert "Governance track expected: RUNTIME" in prompt and "Do not merge." in prompt
