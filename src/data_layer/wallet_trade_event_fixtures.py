"""Local/offline/read-only wallet trade event fixture validation and loading.

Validates wallet trade event snapshot records from explicit local JSON fixture
paths only. A wallet trade event snapshot is a historical advisory observation,
not a trade signal, copy instruction, order request, wallet skill claim, or
execution input.

Does not fetch wallet data.
Does not monitor wallets.
Does not compute wallet skill, copyability, research priority, strategy output,
paper PnL, or live PnL.
Does not write files.
Does not scan directories recursively.
Stdlib-only. No network access. No credentials.

Added in WP78.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


VALID_ADVISORY_LABEL = "WALLET_TRADE_EVENT_FIXTURE_VALID"
INVALID_ADVISORY_LABEL = "WALLET_TRADE_EVENT_FIXTURE_INVALID"
LOAD_ADVISORY_LABEL = (
    "ADVISORY_ONLY_WALLET_TRADE_EVENT_FIXTURE_LOADER — This loader reads "
    "explicit local JSON wallet trade event observation fixtures for structural "
    "validation only. It does not fetch wallet data, monitor wallets, copy "
    "wallets, rank wallet skill, calculate copyability, propose strategy output, "
    "place orders, size positions, override risk, or trade."
)

EXPECTED_NOTICE = "ADVISORY_ONLY_WALLET_TRADE_EVENT_SNAPSHOT"
EXPECTED_SCHEMA_VERSION = "WALLET_TRADE_EVENT_SNAPSHOT_V1"

ALLOWED_SOURCE_TYPES: frozenset[str] = frozenset({
    "LOCAL_FIXTURE",
    "MANUAL_RESEARCH_ENTRY",
    "SANITIZED_EXPORT",
    "SYNTHETIC_TEST_FIXTURE",
})

FORBIDDEN_SOURCE_TYPES: frozenset[str] = frozenset({
    "LIVE_API",
    "AUTHENTICATED_API",
    "WALLET_MONITOR",
    "ORDER_FEED",
    "EXECUTION_FEED",
})

ALLOWED_DIRECTIONS: frozenset[str] = frozenset({
    "YES_OBSERVED",
    "NO_OBSERVED",
    "UNKNOWN_OBSERVED",
    "HISTORICAL_OBSERVATION_ONLY",
})

FORBIDDEN_DIRECTION_VALUES: frozenset[str] = frozenset({
    "BUY",
    "SELL",
    "LONG",
    "SHORT",
    "ENTER",
    "EXIT",
    "TRADE",
})

REQUIRED_TOP_LEVEL_SECTIONS: tuple[str, ...] = (
    "_notice",
    "_schema_version",
    "_status",
    "event",
    "wallet_reference",
    "market_reference",
    "observation",
    "context",
    "review",
    "safety",
)

REQUIRED_EVENT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "event_id",
    "source_type",
    "source_id",
    "observed_at_utc",
)

REQUIRED_WALLET_FIELDS: tuple[str, ...] = ("wallet_id_or_address",)

REQUIRED_MARKET_FIELDS: tuple[str, ...] = (
    "market_id",
    "condition_id",
    "market_category",
    "asset_id",
    "outcome_label",
)

REQUIRED_OBSERVATION_FIELDS: tuple[str, ...] = (
    "direction_observed",
    "price_observed",
    "size_observed",
)

REQUIRED_CONTEXT_FIELDS: tuple[str, ...] = (
    "liquidity_context_available",
    "orderbook_context_available",
    "copyability_context_available",
)

REQUIRED_REVIEW_FIELDS: tuple[str, ...] = (
    "suspicious_flow_flag",
    "human_review_required",
    "advisory_only_notice",
)

REQUIRED_SAFETY_FLAGS: tuple[str, ...] = (
    "manual_research_only",
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
    "no_risk_override",
    "no_parameter_auto_change",
)

FORBIDDEN_EXACT_KEYS: frozenset[str] = frozenset({
    "buy",
    "sell",
    "entry",
    "exit",
    "position_size",
    "expected_return",
    "profit_target",
    "stop_loss",
    "take_profit",
    "live_signal",
    "execute",
    "auto_copy",
})

FORBIDDEN_SECRET_KEYS: frozenset[str] = frozenset({
    "api_key",
    "apikey",
    "secret",
    "secret_key",
    "private_key",
    "wallet_private_key",
    "seed_phrase",
    "passphrase",
    "auth_token",
    "bearer_token",
    "access_token",
})

FORBIDDEN_COMPUTATION_TERMS: tuple[str, ...] = (
    "wallet_skill",
    "wallet_rank",
    "copyability_pnl",
    "delayed_copy_outcome",
    "research_priority_boost",
    "trade_edge",
    "expected_return",
    "position_size",
    "win_rate",
    "strategy_result",
    "paper_pnl",
    "live_pnl",
)

_URL_PREFIXES: tuple[str, ...] = (
    "http://",
    "https://",
    "ws://",
    "wss://",
    "ftp://",
)
_UTC_SUFFIX_RE = re.compile(r"(Z|[+-]00:00)$")


@dataclass(frozen=True)
class WalletTradeEventValidationResult:
    is_valid: bool
    invalid_fields: tuple[str, ...]
    warnings: tuple[str, ...]
    advisory_label: str


@dataclass(frozen=True)
class LoadedWalletTradeEventRecord:
    source_path: str
    record_index: int | None
    record: Mapping[str, object]
    validation: WalletTradeEventValidationResult


@dataclass(frozen=True)
class WalletTradeEventFixtureLoadResult:
    source_path: str
    loaded_count: int
    valid_count: int
    invalid_count: int
    warning_count: int
    records: tuple[LoadedWalletTradeEventRecord, ...]
    errors: tuple[str, ...]
    advisory_label: str


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_utc_timestamp(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and bool(_UTC_SUFFIX_RE.search(value))


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _looks_like_url(path_str: str) -> bool:
    low = path_str.strip().lower()
    return any(low.startswith(prefix) for prefix in _URL_PREFIXES)


def _as_mapping(record: Mapping[str, object], section: str) -> Mapping[str, object] | None:
    value = record.get(section)
    return value if isinstance(value, Mapping) else None


def _collect_forbidden_key_paths(obj: object, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            key_str = str(key)
            full_path = f"{path}.{key_str}" if path else key_str
            normalized = key_str.lower()
            if normalized in FORBIDDEN_EXACT_KEYS or normalized in FORBIDDEN_SECRET_KEYS:
                found.append(full_path)
            found.extend(_collect_forbidden_key_paths(value, full_path))
    elif isinstance(obj, (list, tuple)):
        for index, item in enumerate(obj):
            found.extend(_collect_forbidden_key_paths(item, f"{path}[{index}]"))
    return found


def _collect_forbidden_string_paths(obj: object, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            key_str = str(key)
            full_path = f"{path}.{key_str}" if path else key_str
            found.extend(_collect_forbidden_string_paths(value, full_path))
    elif isinstance(obj, (list, tuple)):
        for index, item in enumerate(obj):
            found.extend(_collect_forbidden_string_paths(item, f"{path}[{index}]"))
    elif isinstance(obj, str):
        normalized = obj.strip().upper()
        if normalized in FORBIDDEN_SOURCE_TYPES or normalized in FORBIDDEN_DIRECTION_VALUES:
            found.append(f"{path}={obj}")
    return found


def _require_mapping_section(
    record: Mapping[str, object],
    section: str,
    invalid: list[str],
) -> Mapping[str, object] | None:
    if section not in record:
        invalid.append(section)
        return None
    section_value = record[section]
    if not isinstance(section_value, Mapping):
        invalid.append(section)
        return None
    if not section_value:
        invalid.append(section)
    return section_value


def _check_required_string_fields(
    section: Mapping[str, object],
    section_name: str,
    fields: tuple[str, ...],
    invalid: list[str],
) -> None:
    for field in fields:
        field_path = f"{section_name}.{field}"
        if field not in section:
            invalid.append(field_path)
        elif not _is_nonempty_string(section[field]):
            invalid.append(field_path)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def validate_wallet_trade_event_snapshot(
    record: Mapping[str, object],
) -> WalletTradeEventValidationResult:
    """Validate one wallet trade event snapshot mapping.

    Returns a frozen deterministic result. The validator checks structural
    shape, allowed source type, allowed historical direction value, required
    safety flags, and forbidden trade/credential-like keys. It does not raise on
    invalid records, fetch data, write files, compute skill, compute copyability,
    or produce any trade signal.
    """
    invalid: list[str] = []
    warnings: list[str] = []

    for section in REQUIRED_TOP_LEVEL_SECTIONS:
        if section not in record:
            _add_unique(invalid, section)

    notice = record.get("_notice")
    if notice != EXPECTED_NOTICE:
        _add_unique(invalid, "_notice")

    schema_version = record.get("_schema_version")
    if schema_version != EXPECTED_SCHEMA_VERSION:
        _add_unique(invalid, "_schema_version")

    for key_path in _collect_forbidden_key_paths(record):
        _add_unique(invalid, key_path)
        warnings.append(
            f"Forbidden trade-like or credential-like key found: '{key_path}'. "
            "Wallet trade event fixtures are advisory observations only."
        )

    for string_path in _collect_forbidden_string_paths(record):
        warnings.append(
            f"Forbidden source, direction, or trade-like value found: '{string_path}'."
        )

    event = _require_mapping_section(record, "event", invalid)
    wallet = _require_mapping_section(record, "wallet_reference", invalid)
    market = _require_mapping_section(record, "market_reference", invalid)
    observation = _require_mapping_section(record, "observation", invalid)
    context = _require_mapping_section(record, "context", invalid)
    review = _require_mapping_section(record, "review", invalid)
    safety = _require_mapping_section(record, "safety", invalid)

    if event is not None:
        _check_required_string_fields(event, "event", REQUIRED_EVENT_FIELDS, invalid)
        if event.get("schema_version") != EXPECTED_SCHEMA_VERSION:
            _add_unique(invalid, "event.schema_version")
        source_type = event.get("source_type")
        if source_type in FORBIDDEN_SOURCE_TYPES:
            _add_unique(invalid, "event.source_type")
            warnings.append(
                f"Forbidden source_type '{source_type}' is not allowed for local fixtures."
            )
        elif source_type not in ALLOWED_SOURCE_TYPES:
            _add_unique(invalid, "event.source_type")
        if "observed_at_utc" in event and not _is_utc_timestamp(event["observed_at_utc"]):
            _add_unique(invalid, "event.observed_at_utc")

    if wallet is not None:
        _check_required_string_fields(wallet, "wallet_reference", REQUIRED_WALLET_FIELDS, invalid)

    if market is not None:
        _check_required_string_fields(market, "market_reference", REQUIRED_MARKET_FIELDS, invalid)

    if observation is not None:
        _check_required_string_fields(
            observation,
            "observation",
            ("direction_observed",),
            invalid,
        )
        direction = observation.get("direction_observed")
        if direction in FORBIDDEN_DIRECTION_VALUES:
            _add_unique(invalid, "observation.direction_observed")
            warnings.append(
                f"Forbidden direction_observed '{direction}': wallet events are "
                "historical observations only, not buy/sell or trade instructions."
            )
        elif direction not in ALLOWED_DIRECTIONS:
            _add_unique(invalid, "observation.direction_observed")
        for numeric_field in ("price_observed", "size_observed"):
            field_path = f"observation.{numeric_field}"
            if numeric_field not in observation:
                _add_unique(invalid, field_path)
            elif not _is_number(observation[numeric_field]):
                _add_unique(invalid, field_path)

    if context is not None:
        for field in REQUIRED_CONTEXT_FIELDS:
            field_path = f"context.{field}"
            if field not in context:
                _add_unique(invalid, field_path)
            elif not isinstance(context[field], bool):
                _add_unique(invalid, field_path)

    if review is not None:
        for field in ("suspicious_flow_flag", "human_review_required"):
            field_path = f"review.{field}"
            if field not in review:
                _add_unique(invalid, field_path)
            elif not isinstance(review[field], bool):
                _add_unique(invalid, field_path)
        if "advisory_only_notice" not in review:
            _add_unique(invalid, "review.advisory_only_notice")
        elif not _is_nonempty_string(review["advisory_only_notice"]):
            _add_unique(invalid, "review.advisory_only_notice")

    if safety is not None:
        for flag in REQUIRED_SAFETY_FLAGS:
            field_path = f"safety.{flag}"
            if flag not in safety:
                _add_unique(invalid, field_path)
            elif safety[flag] is not True:
                _add_unique(invalid, field_path)

    is_valid = not invalid
    return WalletTradeEventValidationResult(
        is_valid=is_valid,
        invalid_fields=tuple(invalid),
        warnings=tuple(warnings),
        advisory_label=VALID_ADVISORY_LABEL if is_valid else INVALID_ADVISORY_LABEL,
    )


def _load_single_file(
    file_path: Path,
) -> tuple[list[LoadedWalletTradeEventRecord], list[str]]:
    records: list[LoadedWalletTradeEventRecord] = []
    errors: list[str] = []

    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"Cannot read file '{file_path}': {exc}")
        return records, errors

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in '{file_path}': {exc}")
        return records, errors

    if isinstance(data, dict):
        validation = validate_wallet_trade_event_snapshot(data)
        records.append(
            LoadedWalletTradeEventRecord(
                source_path=str(file_path),
                record_index=None,
                record=data,
                validation=validation,
            )
        )
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(
                    f"JSON list entry at index {i} in '{file_path}' is not an object "
                    f"(got {type(item).__name__}); skipping."
                )
                continue
            validation = validate_wallet_trade_event_snapshot(item)
            records.append(
                LoadedWalletTradeEventRecord(
                    source_path=str(file_path),
                    record_index=i,
                    record=item,
                    validation=validation,
                )
            )
    else:
        errors.append(
            f"JSON root in '{file_path}' is neither an object nor a list "
            f"(got {type(data).__name__})."
        )

    return records, errors


def load_wallet_trade_event_fixtures(
    path: str | Path,
) -> WalletTradeEventFixtureLoadResult:
    """Load wallet trade event fixtures from an explicit local path.

    Accepts:
    - A single JSON object file containing one wallet trade event snapshot.
    - A single JSON list file containing wallet trade event snapshot objects.
    - A directory: loads direct-child *.json files sorted by filename.

    Non-json files in directories are ignored. Subdirectories are not scanned.
    URL-like inputs are rejected. Invalid event records are returned with their
    validation result instead of raising.
    """
    path_str = str(path).strip()

    if _looks_like_url(path_str):
        return WalletTradeEventFixtureLoadResult(
            source_path=path_str,
            loaded_count=0,
            valid_count=0,
            invalid_count=0,
            warning_count=0,
            records=(),
            errors=(f"URL-like path rejected: '{path_str}'. Only explicit local paths are accepted.",),
            advisory_label=LOAD_ADVISORY_LABEL,
        )

    resolved = Path(path_str)

    if not resolved.exists():
        return WalletTradeEventFixtureLoadResult(
            source_path=path_str,
            loaded_count=0,
            valid_count=0,
            invalid_count=0,
            warning_count=0,
            records=(),
            errors=(f"Path does not exist: '{path_str}'.",),
            advisory_label=LOAD_ADVISORY_LABEL,
        )

    all_records: list[LoadedWalletTradeEventRecord] = []
    all_errors: list[str] = []

    if resolved.is_dir():
        json_files = sorted(
            child for child in resolved.iterdir() if child.is_file() and child.suffix.lower() == ".json"
        )
        if not json_files:
            all_errors.append(
                f"Directory '{path_str}' contains no direct-child *.json files."
            )
        for json_file in json_files:
            records, errors = _load_single_file(json_file)
            all_records.extend(records)
            all_errors.extend(errors)
    elif resolved.is_file():
        if resolved.suffix.lower() != ".json":
            return WalletTradeEventFixtureLoadResult(
                source_path=path_str,
                loaded_count=0,
                valid_count=0,
                invalid_count=0,
                warning_count=0,
                records=(),
                errors=(
                    f"Unsupported file extension '{resolved.suffix}' for '{path_str}'. "
                    "Only .json files are accepted.",
                ),
                advisory_label=LOAD_ADVISORY_LABEL,
            )
        records, errors = _load_single_file(resolved)
        all_records.extend(records)
        all_errors.extend(errors)
    else:
        return WalletTradeEventFixtureLoadResult(
            source_path=path_str,
            loaded_count=0,
            valid_count=0,
            invalid_count=0,
            warning_count=0,
            records=(),
            errors=(f"Path is neither a file nor a directory: '{path_str}'.",),
            advisory_label=LOAD_ADVISORY_LABEL,
        )

    valid_count = sum(1 for record in all_records if record.validation.is_valid)
    invalid_count = sum(1 for record in all_records if not record.validation.is_valid)
    warning_count = sum(len(record.validation.warnings) for record in all_records)

    return WalletTradeEventFixtureLoadResult(
        source_path=path_str,
        loaded_count=len(all_records),
        valid_count=valid_count,
        invalid_count=invalid_count,
        warning_count=warning_count,
        records=tuple(all_records),
        errors=tuple(all_errors),
        advisory_label=LOAD_ADVISORY_LABEL,
    )
