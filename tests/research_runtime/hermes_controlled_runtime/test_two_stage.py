"""TS02: native cold producer fixtures and exclusively offline callbacks."""
import copy
import json
from pathlib import Path
import runpy
import subprocess
from unittest.mock import patch

import pytest

from src.data_layer.polymarket import market_truth_data_api as api
from src.research_runtime.hermes_controlled_runtime import two_stage as ts
from tests.data_layer.polymarket.test_market_truth_data_api import _clock, _ts01_bodies
from tests.research_runtime.hermes_controlled_runtime.test_strategy_manager import _draft


def pair(tmp_path):
    path = tmp_path / "pair.sqlite3"
    gamma, book = _ts01_bodies()
    result = api.collect_trusted_research_pair(
        path, "42", clock=_clock(),
        transport=lambda url, *_: (200, {}, gamma if "/markets/" in url else book),
    )
    assert result["status"] == "ADMITTED"
    cold = api.export_trusted_research_pair(path)
    assert cold == result
    return path, cold


def kwargs(export):
    return dict(stage_a_text="Unverified prose https://example.org/not-a-source", trusted_pair=export,
                cutoff="2024-07-03T10:01:00Z", expected_request_id="offline.request.1",
                strategy_parameter_names=("lookback",))


def good(**request):
    assert request["tool_capabilities"] == ()
    assert set(request) == {"handoff", "output_contract", "expected_request_id",
                            "strategy_parameter_names", "tool_capabilities"}
    assert "strategy_assessment" in request["output_contract"]["properties"]
    return json.dumps(_draft(request["expected_request_id"])).encode()


def test_ts02_handoff_requires_cold_ts01_membership_and_cutoff(tmp_path):
    path, export = pair(tmp_path)
    options = kwargs(export)
    handoff = ts.build_handoff(**options)
    assert handoff["summary"]["proof_level"] == "SYNTHETIC_ONLY"
    assert handoff["UNTRUSTED_STAGE_A_TEXT"] == options["stage_a_text"]
    assert handoff["summary"]["token_id"] == "7"
    assert "raw_bytes" not in json.dumps(handoff)
    # Equivalent UTC clocks must produce the exact same identity.
    assert handoff == ts.build_handoff(**{**options, "cutoff": "2024-07-03T04:01:00-06:00"})
    bad = []
    for field, value in [("status", "NOT_ADMITTED"), ("proof_level", "MODEL_CLAIM"),
                         ("receipt_sha256", "0" * 64), ("selected", []), ("attempts", [])]:
        altered = copy.deepcopy(export); altered[field] = value; bad.append(altered)
    for field, value in [("raw_bytes", b"{}"), ("raw_sha256", "0" * 64),
                         ("occurrence_id", "forged"), ("received_at", "2025-01-01T00:00:00Z")]:
        altered = copy.deepcopy(export); altered["attempts"][0][field] = value; bad.append(altered)
    for altered in bad:
        calls = []
        result = ts.run_offline_two_stage(tmp_path / "reject", stage_b=lambda **r: calls.append(r),
                                           **kwargs(altered))
        assert result["status"] == "SOURCE_UNTRUSTED" and not calls
    for cutoff in [None, "", "2024-07-03T10:00:00Z", "2024-07-03T10:01:00",
                   "2024-07-03T10:00:06.0000009Z", "2024-07-03T10:00:06+00:00:00.0000019"]:
        with pytest.raises(ValueError): ts.build_handoff(**{**options, "cutoff": cutoff})
    with pytest.raises(ValueError): ts.build_handoff(**{**options, "stage_a_text": "é" * 10001})
    # Membership is checked by the unchanged producer's cold exporter, not model prose.
    receipt = path.with_suffix(".ts01.json")
    original = receipt.read_bytes(); receipt.write_bytes(b"{}")
    assert ts.run_offline_two_stage(tmp_path / "badreceipt", stage_b=good,
        **kwargs(api.export_trusted_research_pair(path)))["status"] == "SOURCE_UNTRUSTED"
    receipt.write_bytes(original)
    path.unlink()
    assert ts.run_offline_two_stage(tmp_path / "missing", stage_b=good,
        **kwargs(api.export_trusted_research_pair(path)))["status"] == "SOURCE_UNTRUSTED"


def test_ts02_stage_b_toolfree_contract_and_native_strategy_validator(tmp_path):
    _, export = pair(tmp_path)
    options = kwargs(export)
    assert ts.run_offline_two_stage(tmp_path / "valid", stage_b=good, **options)["status"] == "OFFLINE_SYNTHETIC_VALIDATED"
    drafts = [b"not-json", b"\xff", b"{}", None, b"x" * 65537]
    base = _draft(options["expected_request_id"])
    mutations = [dict(request_id="wrong"), dict(research_summary="PLACE AN ORDER now"),
                 dict(source_references=[]), dict(strategy_assessment={}),
                 dict(strategy_assessment={"lifecycle_action": "CONTINUE", "recommended_health_state": "HEALTHY",
                       "risk_direction": "INCREASE", "target_risk_band": None, "adaptation_recommendation": None})]
    mutations.append(dict(strategy_assessment={"lifecycle_action": "ADAPT", "recommended_health_state": "HEALTHY",
        "risk_direction": "UNCHANGED", "target_risk_band": None, "adaptation_recommendation": {
            "kind": "PARAMETER_UPDATE", "summary": "Change an unknown parameter", "parameter_updates": {"unknown": 5}}}))
    for mutation in mutations:
        drafts.append(json.dumps({**base, **mutation}).encode())
    from src.research_runtime.hermes_controlled_runtime.models import DRAFT_AUTHORITY_FLAGS
    for flag in DRAFT_AUTHORITY_FLAGS:
        for value in [False, None, "true"]:
            drafts.append(json.dumps({**base, flag: value}).encode())
        missing = dict(base); missing.pop(flag); drafts.append(json.dumps(missing).encode())
    for index, raw in enumerate(drafts):
        calls = []
        def invalid(**request):
            calls.append(request); return raw
        directory = tmp_path / f"invalid{index}"
        result = ts.run_offline_two_stage(directory, stage_b=invalid, **options)
        assert result["status"] == "INVALID_OUTPUT" and len(calls) == 1, index
        assert ts.run_offline_two_stage(directory, stage_b=invalid, **options) == result
        assert len(calls) == 1


def test_ts02_durable_reservation_zero_redispatch_and_tamper(tmp_path):
    _, export = pair(tmp_path); options = kwargs(export)
    directory = tmp_path / "journal"; calls = []
    def callback(**request):
        run_id = request["handoff"]["run_id"]
        assert (directory / (run_id + ".reserved")).is_file()
        assert (directory / run_id / "01_HANDOFF.json").is_file()
        calls.append(1)
        return good(**request)
    terminal = ts.run_offline_two_stage(directory, stage_b=callback, **options)
    assert terminal["status"] == "OFFLINE_SYNTHETIC_VALIDATED"
    assert ts.verify_offline_run(directory, terminal["run_id"]) == terminal
    assert ts.run_offline_two_stage(directory, stage_b=callback, **options) == terminal and calls == [1]
    record = directory / terminal["run_id"] / "02_B.json"
    original = record.read_bytes()
    for raw in [b"{", original.replace(b"OFFLINE_SYNTHETIC_VALIDATED", b"INVALID_OUTPUT")]:
        record.write_bytes(raw)
        assert ts.run_offline_two_stage(directory, stage_b=callback, **options)["status"] == "INCOMPLETE_BLOCKED"
    record.write_bytes(original); record.unlink()
    assert ts.run_offline_two_stage(directory, stage_b=callback, **options)["status"] == "INCOMPLETE_BLOCKED"
    assert calls == [1]
    # A surviving run directory is also a tombstone if the marker disappears.
    (directory / (terminal["run_id"] + ".reserved")).unlink()
    assert ts.run_offline_two_stage(directory, stage_b=callback, **options)["status"] == "INCOMPLETE_BLOCKED"
    assert calls == [1]
    interrupted = tmp_path / "crashed"; crash_calls = []
    def crash(**request):
        crash_calls.append(1); raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt): ts.run_offline_two_stage(interrupted, stage_b=crash, **options)
    assert ts.run_offline_two_stage(interrupted, stage_b=crash, **options)["status"] == "INCOMPLETE_BLOCKED"
    assert crash_calls == [1]
    def timeout(**request): raise TimeoutError("must not echo private path")
    result = ts.run_offline_two_stage(tmp_path / "timeout", stage_b=timeout, **options)
    assert result["status"] == "INTERRUPTED_BLOCKED" and "private" not in json.dumps(result)
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    entered, release = Event(), Event()
    concurrent_calls = []
    def blocked(**request):
        concurrent_calls.append(1); entered.set()
        assert release.wait(5)
        return good(**request)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(ts.run_offline_two_stage, tmp_path / "concurrent", stage_b=blocked, **options)
        assert entered.wait(5)
        try:
            second = ts.run_offline_two_stage(tmp_path / "concurrent", stage_b=blocked, **options)
            assert second["status"] == "INCOMPLETE_BLOCKED" and concurrent_calls == [1]
        finally:
            release.set()
        assert future.result()["status"] == "OFFLINE_SYNTHETIC_VALIDATED"


def test_ts02_terminal_proof_levels_and_usage_nonfabrication(tmp_path):
    _, export = pair(tmp_path)
    root = tmp_path / "proof"
    result = ts.run_offline_two_stage(root, stage_b=good, **kwargs(export))
    assert result["proof_level"] == "SYNTHETIC_ONLY"
    assert result["provider_toolfree"] == "UNPROVEN"
    assert set(result) == {"status", "run_id", "proof_level", "provider_toolfree", "handoff_sha256", "output_sha256"}
    text = "\n".join(p.read_text() for p in root.rglob("*") if p.is_file())
    assert "Unverified prose" not in text and "example.org" not in text
    for forbidden in ["estimated_cost", "input_tokens", "StrategyAssessment", "RESEARCH_DRAFT_VALIDATED"]:
        assert forbidden not in text
    assert not list(root.rglob("*usage*"))
    def mutate_request(**request):
        request["handoff"]["summary"]["expected_request_id"] = "wrong"
        return json.dumps(_draft("wrong")).encode()
    assert ts.run_offline_two_stage(tmp_path / "mutation", stage_b=mutate_request,
        **kwargs(export))["status"] == "INVALID_OUTPUT"


def test_ts02_existing_hermes_strategy_context_and_ts01_compatibility():
    # Actual unchanged family execution is also captured in the external pytest receipt.
    root = Path(__file__).resolve().parents[3]
    guard = runpy.run_path(str(root / "tests/test_hermes_input_output_contracts_and_validator_requirements_docs.py"))
    fn = guard["test_no_actual_hermes_implementation_artifacts_added"]
    fn()
    tracked = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout
    for extra, rejected in [("two_stage.py", False), ("unknown_new_module.py", True)]:
        value = tracked + "\nsrc/research_runtime/hermes_controlled_runtime/" + extra + "\n"
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, value, "")):
            if rejected:
                with pytest.raises(AssertionError): fn()
            else: fn()
