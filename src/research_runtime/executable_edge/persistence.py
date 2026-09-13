"""Deterministic explicit-path persistence for WP172 research assessments."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import re

from .models import ExecutableEdgeAssessment, ExecutableEdgeError, canonical_bytes, validate_assessment

_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def serialize_assessment(assessment: ExecutableEdgeAssessment) -> bytes:
    validate_assessment(assessment)
    return canonical_bytes(asdict(assessment)) + b"\n"


def deserialize_assessment(data: bytes) -> ExecutableEdgeAssessment:
    try:
        if not isinstance(data, bytes) or len(data) > 1_048_576 or not data.endswith(b"\n"):
            raise ExecutableEdgeError("ASSESSMENT_SERIALIZATION_INVALID")
        value = json.loads(data.decode("utf-8"))
        if not isinstance(value, dict):
            raise ExecutableEdgeError("ASSESSMENT_SERIALIZATION_INVALID")
        value["assumptions"] = tuple(value.get("assumptions", ()))
        value["diagnostic_codes"] = tuple(value.get("diagnostic_codes", ()))
        assessment = ExecutableEdgeAssessment(**value)
        validate_assessment(assessment)
        if serialize_assessment(assessment) != data:
            raise ExecutableEdgeError("ASSESSMENT_SERIALIZATION_INVALID")
        return assessment
    except ExecutableEdgeError:
        raise
    except Exception as exc:
        raise ExecutableEdgeError("ASSESSMENT_SERIALIZATION_INVALID") from exc


def write_assessment(path: str | Path, assessment: ExecutableEdgeAssessment) -> str:
    target = Path(path)
    text = str(target).replace("\\", "/")
    allowed_storage = "local_data" in target.parts
    if (
        target.suffix != ".json"
        or target.name in {"", ".", ".."}
        or not target.parent.exists()
        or target.is_symlink()
        or not allowed_storage
        or (not target.is_absolute() and not (text == "local_data" or text.startswith("local_data/")))
        or (_DRIVE_RE.match(text) is not None and not target.is_absolute())
    ):
        raise ExecutableEdgeError("OUTPUT_PATH_INVALID")
    payload = serialize_assessment(assessment)
    if target.exists():
        if not target.is_file() or target.read_bytes() != payload:
            raise ExecutableEdgeError("OUTPUT_CONFLICT")
        return "ASSESSMENT_WRITE_IDEMPOTENT"
    try:
        fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if target.is_file() and target.read_bytes() == payload:
            return "ASSESSMENT_WRITE_IDEMPOTENT"
        raise ExecutableEdgeError("OUTPUT_CONFLICT")
    return "ASSESSMENT_WRITTEN"
