"""S10-QUAL-DATA-03 contract drift protection: the contract, machine spec, prompt and code constants agree."""

from __future__ import annotations

import json
from pathlib import Path

import tools.qualification.run_s10_qual_data_03 as operator
from src.data_layer.analytical_research import qualification_oos_accrual as oa

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "qualification_weather_oos_accrual_contract.md"
SPEC = ROOT / "docs" / "wp_specs" / "S10-QUAL-DATA-03" / "wp_spec.json"
PROMPT = ROOT / "docs" / "wp_specs" / "S10-QUAL-DATA-03" / "wp_prompt.txt"


def _contract() -> str:
    return " ".join(CONTRACT.read_text(encoding="utf-8").split())


def test_oos_accrual_contract_binds_plan_census_and_seal() -> None:
    text = _contract()
    for value in (oa.PLAN_SHA256, oa.POWER_DOC_SHA256_LF, oa.PLAN_MERGE_SHA, oa.PLAN_MERGE_TIME, oa.FREEZE_DEADLINE,
                  oa.OOS_START, oa.EMBARGO_LOWER_BOUND, oa.CAP, oa.DATA02_BUNDLE_ID, oa.DATA02_DATASET_ID,
                  "HISTORICAL_NON_OOS", "`STOP PLAN_FREEZE_INVALID`", "2026-10-15 through 2027-02-11",
                  "11:00 and 12:00 UTC", "does not close the census", "STRUCTURAL_CLASSIFICATION_PENDING",
                  "PENDING_LABEL_FINALITY", "`LABEL_GAMMA_NOT_FINAL` is never emitted", "LABEL_V3_RESOLUTION_MISSING",
                  "LABEL_V3_SOURCE_READ_FAILED", "GAMMA_UNAVAILABLE", "never leapfrogs", "QUAL_OOS_INSUFFICIENT_AT_CAP",
                  "QUAL_OOS_ROWS_INSUFFICIENT", "DATA03_IMPLEMENTED_NOT_STARTED", oa.ROW_ID_PREFIX, oa.MEMBERSHIP_ID_PREFIX,
                  oa.BUNDLE_ID_PREFIX, oa.FEATURE_COLUMN_ID_PREFIX, oa.LABEL_STORE_ID_PREFIX, "EXTERNAL_PIT_MARKET_PROBABILITY_V1",
                  "`max_midpoint_spread = 0.1`", "`max_last_trade_age_seconds = 86400`", "B1/B2 forecasts are forbidden"):
        assert value in text, value
    for key in oa.MEMBERSHIP_PREIMAGE_KEYS:
        assert f"`{key}`" in text, key
    for checkpoint in oa.CHECKPOINT_IDS:
        assert checkpoint in text, checkpoint
    for stop in operator.HARD_STOPS:
        assert f"`{stop}`" in text or f"`STOP {stop}`" in text, stop


def test_oos_accrual_contract_freezes_network_budgets_and_firewall() -> None:
    text = _contract()
    assert operator.FEE_URL == oa.FEE_DOC_URL and oa.FEE_DOC_URL in text
    for host in sorted(operator.ALLOWED_HOSTS):
        assert host in text, host
    for name in ("RUN_MAX_ATTEMPTS", "RUN_MAX_BYTES", "MAX_SINGLE_RESPONSE", "RUN_MAX_PENDULUM_HOURS", "CUM_MAX_ATTEMPTS",
                 "CUM_MAX_BYTES", "CUM_MAX_PENDULUM_HOURS", "MAX_ACCRUE_RUNS", "MAX_CANDIDATES", "MAX_STATIONS",
                 "PROBE_MAX_ATTEMPTS", "PROBE_MAX_BYTES", "PROBE_MAX_SINGLE_RESPONSE", "PROBE_MAX_PENDULUM_HOURS"):
        assert f"`{name}={getattr(operator, name):_}`" in text, name
    assert (operator.RUN_MAX_ATTEMPTS, operator.CUM_MAX_ATTEMPTS, operator.MAX_ACCRUE_RUNS) == (12_288, 65_536, 64)
    assert (operator.PROBE_MAX_ATTEMPTS, operator.PROBE_MAX_BYTES, operator.PROBE_MAX_SINGLE_RESPONSE) == (32, 16 * 2 ** 20, 8 * 2 ** 20)
    for value in ("`MAX_QUALIFICATION_PROVENANCE_MANIFESTS = 256`", "`N2 + 150 > 256`", "no aggregation, substitution or omission",
                  "`VISIBLE_SCHEMA_VIOLATION`", "`STOP INTERNAL_ERROR:<ExceptionClass>`", "never backdated",
                  "`NOT_CAPTURED_NO_AUTHORIZED_EXACT_SOURCE`", "No scheduler, cron, delayed trigger, watcher or background task",
                  "Gate C: NOT AUTHORIZED", "Live: DISABLED", "Capital at risk: USD 0", "Orders: 0",
                  "This WP authorizes no successor", "never subclasses the DATA-02 completion pipeline"):
        assert value.lower() in text.lower(), value


def test_oos_accrual_machine_spec_and_prompt_agree() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    identity = spec["identity"]
    assert identity["wp_id"] == "S10-QUAL-DATA-03" and identity["risk_level"] == 3 and identity["package_size_class"] == "L"
    assert identity["package_class"] == "WEATHER_QUALIFICATION_PROSPECTIVE_OOS_ACCRUAL"
    assert identity["required_predecessor"] == {"pr_number": 205, "head_sha": "11244eed9686b01e29ede83ea6578bb0a781db6f",
                                                "merge_sha": oa.PLAN_MERGE_SHA}
    scope = spec["scope"]
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == scope["max_changed_files"] == 15
    for path in ("src/data_layer/analytical_research/qualification_oos_accrual.py", "tools/qualification/run_s10_qual_data_03.py",
                 "docs/qualification_weather_oos_accrual_contract.md", "docs/status_entries/S10-QUAL-DATA-03.md"):
        assert path in scope["required_changed_files"], path
    for forbidden in ("pyproject.toml", ".github/workflows/ci.yml", oa.PLAN_PATH, oa.POWER_DOC_PATH,
                      "tools/qualification/run_s10_qual_data_01.py", "tools/qualification/run_s10_qual_data_02.py",
                      "src/data_layer/analytical_research/qualification_data_readiness.py",
                      "src/data_layer/analytical_research/pendulumflow_v3.py", "src/data_layer/analytical_research/nws_ndfd_history.py",
                      "src/data_layer/analytical_research/qualification.py", "src/data_layer/analytical_research/qualification_gate.py",
                      "src/data_layer/analytical_research/experiment_os.py",
                      "tests/data_layer/analytical_research/test_qualification_weather_plan_freeze.py"):
        assert forbidden not in scope["required_changed_files"], forbidden
    authority = spec["authority"]
    for key in ("source_runtime", "network", "local_offline_tooling", "canonical_evidence_policy", "docs", "tests"):
        assert authority[key] is True, key
    for key in ("dependencies", "workflow_files", "credentials", "scheduler", "hermes_runtime", "strategy", "paper",
                "execution", "live", "workflow_governance"):
        assert authority[key] is False, key
    assert [item["requirement_id"] for item in spec["evidence_plan"]["items"]] == [f"R{i:03d}" for i in range(1, 51)]
    assert spec["successor_boundary"]["separately_gated"] is True and "merge" in spec["successor_boundary"]["forbidden_in_this_wp"]
    prompt = PROMPT.read_text(encoding="utf-8")
    for value in ("Governance track expected: RUNTIME", "**Do not merge.**", "BEGIN_NORMATIVE_RULE_MATRIX_V1",
                  "BEGIN_GOVERNANCE_AUTHORITY_V1", "SIDE14 — S10-QUAL-DATA-03 ONE-SHOT WP", oa.PLAN_SHA256, oa.FEE_DOC_URL):
        assert value in prompt, value
