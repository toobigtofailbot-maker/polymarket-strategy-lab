"""Local append-only content-addressed store for context protocol evidence."""

from __future__ import annotations

import os
from pathlib import Path

from .context_protocol import artifact_id, artifact_mapping
from .models import canonical_json_bytes, sha256_hex

MAX_CONTEXT_ARTIFACTS_PER_CAMPAIGN = 512
MAX_CONTEXT_ARTIFACT_BYTES = 2_000_000
MAX_CONTEXT_CAMPAIGN_BYTES = 32_000_000


class ContextStoreError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ContextArtifactStore:
    """Caller-rooted store with exclusive create and no mutable alias/update API."""

    def __init__(self, root: object) -> None:
        if not isinstance(root, (str, os.PathLike)):
            raise ContextStoreError("ARTIFACT_PATH_INVALID")
        path = Path(root)
        if not path.is_absolute() or ".." in path.parts:
            raise ContextStoreError("ARTIFACT_PATH_INVALID")
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise ContextStoreError("ARTIFACT_PATH_ESCAPE")
        self._root = path.resolve()

    @property
    def root(self) -> Path:
        return self._root

    @staticmethod
    def _safe_name(value: str) -> str:
        return sha256_hex(value.encode("utf-8"))

    def _campaign_dir(self, campaign_id: str, *, create: bool) -> Path:
        if not isinstance(campaign_id, str) or not campaign_id:
            raise ContextStoreError("ARTIFACT_PATH_INVALID")
        target = self._root / self._safe_name(campaign_id)
        if create:
            target.mkdir(exist_ok=True)
        if target.is_symlink():
            raise ContextStoreError("ARTIFACT_PATH_ESCAPE")
        try:
            resolved = target.resolve(strict=create)
        except OSError:
            raise ContextStoreError("ARTIFACT_PATH_INVALID") from None
        if resolved.parent != self._root:
            raise ContextStoreError("ARTIFACT_PATH_ESCAPE")
        return resolved

    def _path(self, campaign_id: str, identity: str, *, create_dir: bool) -> Path:
        return self._campaign_dir(campaign_id, create=create_dir) / f"{self._safe_name(identity)}.json"

    def append(self, record: object) -> str:
        identity = artifact_id(record)
        mapping = artifact_mapping(record)
        campaign_id = mapping.get("campaign_id")
        if not isinstance(campaign_id, str):
            raise ContextStoreError("ARTIFACT_PAYLOAD_INVALID")
        wrapper = {
            "artifact_type": type(record).__name__,
            "artifact_id": identity,
            "payload": mapping,
            "payload_sha256": sha256_hex(canonical_json_bytes(mapping)),
        }
        raw = canonical_json_bytes(wrapper)
        if len(raw) > MAX_CONTEXT_ARTIFACT_BYTES:
            raise ContextStoreError("ARTIFACT_LIMIT_EXCEEDED")
        directory = self._campaign_dir(campaign_id, create=True)
        files = tuple(directory.glob("*.json"))
        if len(files) >= MAX_CONTEXT_ARTIFACTS_PER_CAMPAIGN and not self._path(campaign_id, identity, create_dir=True).exists():
            raise ContextStoreError("ARTIFACT_LIMIT_EXCEEDED")
        total = sum(item.stat().st_size for item in files if item.is_file())
        if total + len(raw) > MAX_CONTEXT_CAMPAIGN_BYTES:
            raise ContextStoreError("ARTIFACT_LIMIT_EXCEEDED")
        target = self._path(campaign_id, identity, create_dir=True)
        if target.exists():
            try:
                existing = target.read_bytes()
            except OSError:
                raise ContextStoreError("ARTIFACT_TAMPERED") from None
            if existing == raw:
                self.load(campaign_id, identity)
                return identity
            raise ContextStoreError("ARTIFACT_IDENTITY_CONFLICT")
        try:
            with target.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            return self.append(record)
        except OSError:
            raise ContextStoreError("ARTIFACT_APPEND_FAILED") from None
        self.load(campaign_id, identity)
        return identity

    def contains(self, campaign_id: str, identity: str) -> bool:
        target = self._path(campaign_id, identity, create_dir=False)
        return target.is_file() and not target.is_symlink()

    def load(self, campaign_id: str, identity: str) -> dict[str, object]:
        target = self._path(campaign_id, identity, create_dir=False)
        if target.is_symlink() or not target.is_file():
            raise ContextStoreError("ARTIFACT_NOT_FOUND")
        try:
            raw = target.read_bytes()
            if len(raw) > MAX_CONTEXT_ARTIFACT_BYTES:
                raise ValueError
            import json
            wrapper = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, ValueError, TypeError):
            raise ContextStoreError("ARTIFACT_TAMPERED") from None
        if not isinstance(wrapper, dict) or set(wrapper) != {"artifact_type", "artifact_id", "payload", "payload_sha256"}:
            raise ContextStoreError("ARTIFACT_TAMPERED")
        payload = wrapper.get("payload")
        if (
            wrapper.get("artifact_id") != identity or not isinstance(payload, dict)
            or payload.get("campaign_id") != campaign_id
            or wrapper.get("payload_sha256") != sha256_hex(canonical_json_bytes(payload))
            or canonical_json_bytes(wrapper) != raw
        ):
            raise ContextStoreError("ARTIFACT_TAMPERED")
        return payload
