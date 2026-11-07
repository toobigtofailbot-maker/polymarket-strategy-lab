"""Finite manual official SDK public search probe (S10-R3-REAL-PUBLIC-GET-01, Phase A: live sealed).

  check                                              envelope + SDK identity + activation state, offline
  live   --scratch-dir DIR --activation-record FILE  one attempted GET; refuses while activation is sealed
  verify --scratch-dir DIR [--grounding-scratch DIR] cold offline replay through the real SDK

``live`` stops with LIVE_ACTIVATION_SEALED before reading any input or building any transport until a
separately reviewed, owner-merged change pins the SHA-256 of one exact owner activation record. A
pinned record binds the exact URL, envelope, one attempt, one absolute scratch directory and a UTC
window. The attempt is claimed on disk before dialing, so it is spent even if it fails and is never
repeated; an identical repeat over a verified receipt is returned without network.
``verify`` blocks every socket entry point, replays the frozen bytes through the real SDK on
``httpx.MockTransport`` and recomputes the content-addressed receipt. With ``--grounding-scratch`` it
cold-verifies a caller-named S10-R3-SRC-01 scratch and crosses SDK markets with native identities,
read-only; without it the crosscheck is NATIVE_PIT_CROSSCHECK_NOT_RUN.
Writes only inside one empty absolute scratch directory outside the repository.
No tradable side, order, strategy, paper, capital or live-trading authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import official_sdk_public_probe as PROBE  # noqa: E402
from src.data_layer.analytical_research import official_sdk_search_bridge as OSB  # noqa: E402
from src.data_layer.analytical_research import public_market_contract_parity as PMC  # noqa: E402
from src.data_layer.analytical_research import source_grounding as SG  # noqa: E402
from tools.alpha import run_public_market_contract_parity as PMCCLI  # noqa: E402
from tools.alpha import run_related_market_alpha as REL  # noqa: E402  (reused path/size/hardlink guards)
from tools.alpha import run_source_grounding as SGCLI  # noqa: E402

CODE_FILES = (Path(OSB.__file__), Path(PROBE.__file__), Path(__file__))
MAX_RECORD_BYTES = 4096
MAX_RECEIPT_BYTES = 1 << 20
ATTEMPT_MARKER, RAW, RECEIPT = "attempt_claimed.json", "raw_response.bin", "receipt.json"
OK_STATUSES = ("CHECKED", "ACQUIRED", "VERIFIED", "IDEMPOTENT_VERIFIED")


def code_identity() -> str:
    digest = hashlib.sha256()
    for path in CODE_FILES:
        digest.update(path.resolve().read_bytes())
    return "code:sha256:" + digest.hexdigest()


def check() -> dict:
    with SGCLI.no_network() as attempts:
        identity = OSB.sdk_identity()
    OSB._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "CHECKED", "envelope": PROBE.envelope(), "envelope_sha256": PROBE.envelope_sha256(),
            "sdk_installed_blobs_match_tag": identity["installed_blobs_match_tag"], "code_identity": code_identity(),
            "live_activation": "SEALED" if PROBE.OWNER_ACTIVATION_SHA256 is None else "PINNED",
            "actual_live_get_executed": False, "network_attempts": 0}


def _write_once(path: Path, data: bytes) -> None:
    with open(path, "xb") as handle:
        handle.write(data)


def live(scratch_dir: Path, record_path: Path, inner=None, now_utc: str | None = None) -> dict:
    """``inner`` is a test seam only; argparse never supplies it, so the CLI always uses the real egress."""
    OSB._require(PROBE.OWNER_ACTIVATION_SHA256 is not None, "LIVE_ACTIVATION_SEALED")  # before any input or transport
    scratch = REL._check_scratch(Path(scratch_dir))
    record_raw = REL._read_capped(REL._caller_path(str(record_path), directory=False, scratch=scratch), MAX_RECORD_BYTES)
    if scratch.exists() and any(scratch.iterdir()):
        return _repeat(scratch, record_raw)
    PROBE.authorize_live(record_raw, str(scratch), now_utc or PROBE._utc_now(), SGCLI._strict_json)
    OSB.sdk_identity()  # SDK drift stops before the attempt is claimed
    scratch.mkdir(parents=True, exist_ok=True)
    activation = SG.sha256_hex(record_raw)
    _write_once(scratch / ATTEMPT_MARKER, SG.canonical_bytes({"activation_record_sha256": activation,
                                                              "envelope_sha256": PROBE.envelope_sha256()}))
    attempt = PROBE.acquire(inner)
    if attempt["body"] is not None:
        _write_once(scratch / RAW, attempt["body"])
    receipt = PROBE.finalize(PROBE.build_core(attempt, activation, code_identity(), SGCLI._strict_json))
    _write_once(scratch / RECEIPT, PROBE.receipt_bytes(receipt))
    core = receipt["core"]
    return {"status": "ACQUIRED", "receipt_id": receipt["receipt_id"], "outcome": core["attempt"]["outcome"],
            "http_status": core["attempt"]["http_status"], "byte_count": core["attempt"]["byte_count"],
            "sdk_status": core["sdk_replay"]["sdk_status"], "transport_origin": core["transport_origin"],
            "network_attempts": core["attempt"]["network_dials"]}


def _repeat(scratch: Path, record_raw: bytes) -> dict:
    """A claimed attempt is never repeated: identical activation over a verified receipt is idempotent."""
    OSB._require((scratch / RECEIPT).is_file(), "ATTEMPT_ALREADY_CONSUMED" if (scratch / ATTEMPT_MARKER).exists()
                 else "SCRATCH_NOT_EMPTY")
    checked = verify(scratch)
    OSB._require(checked["status"] == "VERIFIED", "ATTEMPT_ALREADY_CONSUMED")
    receipt = SGCLI._strict_json((scratch / RECEIPT).read_bytes(), "RECEIPT_UNREADABLE")
    OSB._require(receipt["core"]["activation_record_sha256"] == SG.sha256_hex(record_raw), "ATTEMPT_ALREADY_CONSUMED")
    return {"status": "IDEMPOTENT_VERIFIED", "receipt_id": checked["receipt_id"], "network_attempts": 0}


def _attempt_from(core: dict, scratch: Path) -> dict:
    facts = core["attempt"]
    OSB._require(isinstance(facts, dict) and set(facts) == PROBE.ATTEMPT_KEYS, "RECEIPT_SHAPE_INVALID")
    raw_path = scratch / RAW
    body = REL._read_capped(raw_path, PROBE.MAX_BODY_BYTES) if raw_path.is_file() else None
    if body is not None and len(body) == 0 and raw_path.stat().st_size > 0:
        OSB._stop("RAW_RESPONSE_OVERSIZE")
    return {**{k: facts[k] for k in PROBE.ATTEMPT_KEYS - {"byte_count", "body_sha256"}}, "body": body,
            "transport_origin": core["transport_origin"]}


def _native_crosscheck(grounding_dir: Path | None, scratch: Path, receipt_core: dict, attempt: dict) -> dict:
    if grounding_dir is None:
        return {"status": "NATIVE_PIT_CROSSCHECK_NOT_RUN"}
    grounding = REL._caller_path(str(grounding_dir), directory=True, scratch=scratch)
    if grounding is None:
        return {"status": "NOT_CROSSED", "reason": "GROUNDING_SCRATCH_UNUSABLE"}
    try:
        verification = PMCCLI._verify_grounding(grounding)  # cold, read-only; no canonical write
        case = SGCLI._strict_json((grounding / "frozen_case.json").read_bytes(), "GROUNDING_SCRATCH_INVALID")
        as_of = PMC.RP.canonicalize_utc_timestamp(case["as_of"])
        end = attempt["acquired_end_utc"]
        if end is None or PMC._key(as_of) > PMC._key(end):
            return {"status": "NOT_CROSSED", "reason": "SOURCE_TIME_CONFLICT"}

        def read(rel) -> bytes:
            path = grounding / "inputs" / rel if type(rel) is str else None
            return path.read_bytes() if path is not None and path.is_file() and not path.is_symlink() else b""
        _policy, universe = SG.load_corpus(grounding / "inputs" / "pit.sqlite3", case["policy"], as_of)
        rules, _ = SG.bind_rule_texts(universe, case["rule_texts"], read)
        native = PMC.normalize_native(universe, rules)
    except (SG.GroundingStop, OSError, KeyError, TypeError, ValueError):
        return {"status": "NOT_CROSSED", "reason": "GROUNDING_NOT_VERIFIED"}
    replayed = PROBE.replay(attempt["body"], attempt["http_status"], attempt["content_type"], SGCLI._strict_json, native)
    projection = replayed["projection"]
    if projection is None:
        return {"status": "NOT_CROSSED", "reason": replayed["sdk_status"] if replayed["sdk_status"] != "SDK_TYPED_PAGE"
                else replayed["strict_json"]}
    return {"status": "CROSSED", "grounding_receipt_id": verification["receipt_id"], "pit_as_of": as_of,
            "market_status_counts": projection["market_status_counts"], "ranked_native_ids": projection["ranked"],
            "orientation": "ORIENTATION_UNPROVEN", "tradable_side": None, "settlement_equivalence": "NOT_CLAIMED",
            "real_value": "NOT_VERIFIED", "canonical_writes": 0}


def verify(scratch_dir: Path, grounding_dir: Path | None = None) -> dict:
    scratch = Path(scratch_dir)
    OSB._require(scratch.is_absolute() and scratch.is_dir() and not REL._inside(scratch.resolve(), REPO_ROOT)
                 and not REL._unsafe_entry(scratch, directory=True), "SCRATCH_INVALID")
    scratch = scratch.resolve()
    with SGCLI.no_network() as attempts:
        raw = REL._read_capped(scratch / RECEIPT, MAX_RECEIPT_BYTES) if (scratch / RECEIPT).is_file() else b""
        receipt = SGCLI._strict_json(raw, "RECEIPT_UNREADABLE")
        failures = []
        if not isinstance(receipt, dict) or set(receipt) != {"core", "receipt_id"} or not isinstance(receipt["core"], dict):
            return {"status": "TAMPER_DETECTED", "failures": ["RECEIPT_SHAPE_INVALID"], "receipt_id": None,
                    "network_attempts": 0}
        core = receipt["core"]
        if receipt["receipt_id"] != PROBE.finalize(core)["receipt_id"]:
            failures.append("RECEIPT_ID_MISMATCH")
        try:
            attempt = _attempt_from(core, scratch)
            recomputed = PROBE.build_core(attempt, core.get("activation_record_sha256"), code_identity(), SGCLI._strict_json)
        except (SG.GroundingStop, KeyError, TypeError) as stop:
            reason = str(stop) if isinstance(stop, SG.GroundingStop) else "RECEIPT_SHAPE_INVALID"
            return {"status": "TAMPER_DETECTED", "failures": failures + [f"RECOMPUTE_REFUSED:{reason}"],
                    "receipt_id": receipt["receipt_id"], "network_attempts": 0}
        failures.extend(f"OUTPUT_MISMATCH:{k}" for k in sorted(set(core) | set(recomputed)) if core.get(k) != recomputed.get(k))
        start, end = PMC._utc(attempt["acquired_start_utc"]), PMC._utc(attempt["acquired_end_utc"])
        if start is not None and (end is None or PMC._key(start) > PMC._key(end)):
            failures.append("ACQUISITION_TIME_CONFLICT")
        crosscheck = _native_crosscheck(grounding_dir, scratch, core, attempt) if not failures else {"status": "NOT_CROSSED",
                                                                                                    "reason": "RECEIPT_NOT_VERIFIED"}
    OSB._require(not attempts, "NETWORK_ATTEMPT_BLOCKED")
    return {"status": "VERIFIED" if not failures else "TAMPER_DETECTED", "failures": failures,
            "receipt_id": receipt["receipt_id"], "transport_origin": core.get("transport_origin"),
            "native_pit_crosscheck": crosscheck, "network_attempts": 0}


def run_safe(command: str, args) -> dict:
    """Closed result for every outcome; refusals carry a stable code and never echo input, headers or paths."""
    try:
        if command == "check":
            return check()
        if command == "live":
            return live(args.scratch_dir, args.activation_record)
        return verify(args.scratch_dir, args.grounding_scratch)
    except SG.GroundingStop as stop:
        return {"status": "STOPPED", "reason_code": str(stop)}
    except FileExistsError:
        return {"status": "STOPPED", "reason_code": "WRITE_ONCE_CONFLICT"}
    except Exception:  # noqa: BLE001 - sanitized: no exception text or path is echoed
        return {"status": "STOPPED", "reason_code": "INTERNAL_REFUSAL"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    first = sub.add_parser("live")
    first.add_argument("--scratch-dir", required=True, type=Path)
    first.add_argument("--activation-record", required=True, type=Path)
    second = sub.add_parser("verify")
    second.add_argument("--scratch-dir", required=True, type=Path)
    second.add_argument("--grounding-scratch", type=Path, default=None)
    args = parser.parse_args(argv)
    started = time.monotonic()
    result = run_safe(args.command, args)
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
