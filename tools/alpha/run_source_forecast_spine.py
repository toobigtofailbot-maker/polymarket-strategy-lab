"""B1-A source/PIT -> A1/A2 -> W01 A3/A4 + forecast diagnostic spine operator (S10-CAP-B1-SOURCE-FORECAST-01).

  run    --case SPINE.json --grounding-scratch DIR --forecast-cases CASES.json --registry ALPHA.sqlite3
         --scratch-dir DIR --pin-root DIR
  verify --scratch-dir DIR --registry ALPHA.sqlite3

One finite, manual, offline pass. Call path: native ``run_source_grounding.verify`` (cold) ->
``source_forecast_spine.scout`` (A1) -> ``.research`` (A2: pinned Metaculus leaves, official SDK on
MockTransport) -> unmodified ``run_forecast_evaluation.run`` + ``.verify`` -> ``.bind_forecast`` ->
unmodified ``run_hermes_delegated_specialists.run`` + ``.verify`` (pinned Hermes, scripted provider
boundary, advisory Alpha append + cold read) -> one write-once spine receipt. A1/A2/forecast refusal never
dispatches W01 and never appends. A non-empty scratch is never re-run: it must cold-verify (IDEMPOTENT).

Exit codes: 0 RUN_COMPLETE / VERIFIED / IDEMPOTENT_VERIFIED, 1 refusal or tamper, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import forecast_evaluation as FE  # noqa: E402
from src.data_layer.analytical_research import metaculus_source_archive_bridge as MSA  # noqa: E402
from src.data_layer.analytical_research import research_cooperation as HC  # noqa: E402
from src.data_layer.analytical_research import source_forecast_spine as SP  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_forecast_evaluation as FCLI  # noqa: E402
from tools.alpha import run_hermes_delegated_specialists as W01  # noqa: E402
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

MAX_CASE_BYTES = 1 << 20
OK_STATUSES = ("RUN_COMPLETE", "VERIFIED", "IDEMPOTENT_VERIFIED")
STOPS = (SP.SpineStop, SG.GroundingStop, FE.EvaluationStop, HC.CoopStop, MSA.MetaculusStop)


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(SP.__file__)):
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def _read(path: Path) -> bytes:
    path = Path(path)
    SP._require(path.is_absolute() and path.is_file() and not path.is_symlink()
                and not SGCLI._inside(path.resolve(), REPO_ROOT) and 0 < path.stat().st_size <= MAX_CASE_BYTES,
                "CASE_UNREADABLE")
    return path.read_bytes()


def parse_case(raw: bytes) -> dict:
    SP._require(SG.SECRET_RE.search(raw.decode("utf-8", "replace")) is None, "SECRET_MATERIAL_REJECTED")
    case = SGCLI._strict_json(raw, "CASE_JSON_INVALID")
    SP.validate_case(case)
    return case


def _stages(case: dict, grounding_dir: Path) -> tuple[dict, dict, dict]:
    grounding = SP.load_grounding(grounding_dir)
    scouted = SP.scout(grounding, case["target_market_id"])
    SP._require(scouted["status"] == "ADMITTED", "A1_REFUSED:" + str(scouted["reason"]))
    researched = SP.research(grounding, scouted, case["sdk_pages"])
    SP._require(researched["status"] == "ADMITTED", "A2_REFUSED:" + str(researched["reason"]))
    return grounding, scouted, researched


def _scratch(scratch_dir: Path) -> Path:
    scratch = Path(scratch_dir)
    SP._require(scratch.is_absolute() and not SGCLI._inside(scratch.resolve(), REPO_ROOT) and not scratch.is_symlink(),
                "SCRATCH_INVALID")
    return scratch.resolve()


def run(case_path: Path, grounding_dir: Path, forecast_cases: Path, registry: Path, scratch_dir: Path, pin_root: Path) -> dict:
    scratch = _scratch(scratch_dir)
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(Path(case_path), scratch, Path(registry))
    with SGCLI.no_network() as attempts:
        raw = _read(case_path)
        case = parse_case(raw)
        _, scouted, researched = _stages(case, Path(grounding_dir))
        handoff = SP.w01_case(case, scouted, researched)
        W01.parse_case(SG.canonical_bytes(handoff))  # the W01 parser itself must accept the handoff
        SP.check_lineage(Path(registry), case, scouted["target"]["candidate_id"])
        inputs = scratch / "inputs"
        inputs.mkdir(parents=True)
        (inputs / "spine_case.json").write_bytes(raw)
        fc = FCLI.run(Path(grounding_dir), Path(forecast_cases), scratch / "forecast")
        SP._require(fc["status"] == "RUN_COMPLETE" and FCLI.verify(scratch / "forecast")["status"] == "VERIFIED",
                    "FORECAST_NOT_VERIFIED")
        forecast = SP.bind_forecast(json.loads((scratch / "forecast" / "receipt.json").read_bytes()), scouted, researched)
        (inputs / "w01_case.json").write_bytes(SG.canonical_bytes(handoff))
        w01 = W01.run(inputs / "w01_case.json", Path(grounding_dir), Path(registry), scratch / "w01", Path(pin_root))
        SP._require(w01["status"] == "RUN_COMPLETE", "W01_NOT_COMPLETE")
        checked = W01.verify(scratch / "w01", Path(registry))
        SP._require(checked["status"] == "VERIFIED", "W01_NOT_VERIFIED")
        summary = _w01_summary(scratch, w01["receipt_id"])
        SP._require(summary["grounding_receipt_id"] == scouted["grounding_receipt_id"], "W01_GROUNDING_MISMATCH")
        core = SP.build_core(case, scouted, researched, forecast, summary, code_identity())
    SP._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    receipt = SP.finalize(core)
    with open(scratch / "receipt.json", "xb") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8"))
    return {"status": "RUN_COMPLETE", "receipt_id": receipt["receipt_id"], "w01_receipt_id": w01["receipt_id"],
            "episode_id": w01["episode_id"], "forecast_receipt_id": forecast["receipt_id"],
            "native_vs_upstream": researched["native_vs_upstream"], "network_attempts": 0}


def _w01_summary(scratch: Path, receipt_id: str) -> dict:
    receipt = json.loads((scratch / "w01" / "receipt.json").read_bytes())
    core = receipt["core"]
    SP._require(receipt["receipt_id"] == receipt_id, "W01_RECEIPT_MISMATCH")
    return {"receipt_id": receipt_id, "grounding_receipt_id": core["grounding_receipt_id"], "witness_id": core["witness_id"],
            "episode_id": core["episode_id"], "append_status": core["append_status"],
            "cooperation_outcome": core["cooperation"]["cooperation"]["outcome"],
            "evidence_class": core["evidence_class"], "acceptance_status": core["acceptance_status"],
            "provider_invocations": core["provider_invocations"],
            "children": [{"task_index": c["task_index"], "role": c["role"], "status": c["status"]}
                         for c in core["witness_body"]["children"]]}


def _repeat(case_path: Path, scratch: Path, registry: Path) -> dict:
    SP._require((scratch / "receipt.json").is_file(), "SCRATCH_NOT_EMPTY")  # partial scratch: refuse, no hidden retry
    checked = verify(scratch, registry)
    SP._require(checked["status"] == "VERIFIED" and _read(case_path) == (scratch / "inputs" / "spine_case.json").read_bytes(),
                "SCRATCH_NOT_EMPTY")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def verify(scratch_dir: Path, registry: Path) -> dict:
    """Cold: re-verify the frozen forecast + W01 scratches and recompute A1/A2/bindings from frozen copies."""
    scratch = _scratch(scratch_dir)
    SP._require(scratch.is_dir(), "SCRATCH_INVALID")
    with SGCLI.no_network() as attempts:
        receipt = SGCLI._strict_json((scratch / "receipt.json").read_bytes() if (scratch / "receipt.json").is_file() else b"",
                                     "RECEIPT_UNREADABLE")
        failures = []
        try:
            case = parse_case((scratch / "inputs" / "spine_case.json").read_bytes())
            if FCLI.verify(scratch / "forecast")["status"] != "VERIFIED":
                failures.append("FORECAST_NOT_VERIFIED")
            if W01.verify(scratch / "w01", Path(registry))["status"] != "VERIFIED":
                failures.append("W01_NOT_VERIFIED")
            _, scouted, researched = _stages(case, scratch / "forecast" / "inputs" / "grounding")
            handoff = SP.w01_case(case, scouted, researched)
            if SG.canonical_bytes(handoff) != (scratch / "inputs" / "w01_case.json").read_bytes() \
                    or SG.canonical_bytes(handoff) != (scratch / "w01" / "inputs" / "case.json").read_bytes():
                failures.append("W01_HANDOFF_MISMATCH")
            forecast = SP.bind_forecast(json.loads((scratch / "forecast" / "receipt.json").read_bytes()), scouted, researched)
            summary = _w01_summary(scratch, receipt["core"]["w01"]["receipt_id"])
            if summary["grounding_receipt_id"] != scouted["grounding_receipt_id"]:
                failures.append("W01_GROUNDING_MISMATCH")
            core = SP.build_core(case, scouted, researched, forecast, summary, code_identity())
            if core != receipt["core"]:
                failures.append("CORE_MISMATCH")
            if receipt.get("receipt_id") != SP.finalize(core)["receipt_id"]:
                failures.append("RECEIPT_ID_MISMATCH")
        except STOPS as stop:
            failures.append("RECOMPUTE_REFUSED:" + str(stop).split(":")[0])
        except (KeyError, TypeError, AttributeError, OSError, ValueError):
            failures.append("RECEIPT_FIELDS_INVALID")
    SP._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) and not failures else None,
            "network_attempts": 0}


def run_safe(args) -> dict:
    """Closed result for every outcome; never echoes input text, paths or tracebacks."""
    try:
        if args.command == "run":
            return run(args.case, args.grounding_scratch, args.forecast_cases, args.registry, args.scratch_dir, args.pin_root)
        return verify(args.scratch_dir, args.registry)
    except STOPS as stop:
        return {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        return {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - sanitized
        return {"status": "STOPPED", "reason_code": "INTERNAL_REFUSAL"}


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # never echo caller arguments
        print(json.dumps({"status": "USAGE_ERROR", "reason_code": "USAGE_INVALID"}, sort_keys=True))
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    first = sub.add_parser("run")
    for flag in ("--case", "--grounding-scratch", "--forecast-cases", "--registry", "--scratch-dir", "--pin-root"):
        first.add_argument(flag, required=True, type=Path)
    second = sub.add_parser("verify")
    for flag in ("--scratch-dir", "--registry"):
        second.add_argument(flag, required=True, type=Path)
    result = run_safe(parser.parse_args(argv))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
