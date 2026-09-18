"""Immutable Hermes invocation policy and deterministic invocation plan (WP175H).

This module freezes the exact first-runtime controls for one bounded, dormant-by-
default, one-shot Hermes research session against the pinned Hermes Agent v0.21.3
tagged contract. No caller may broaden the policy: the argv builder rejects any
executable path with shell metacharacters, never builds a command string, never
mounts the repository or a home/local_data path as the Hermes working directory,
and enables exactly the single permitted ``web`` toolset.

Pinned v0.21.3 contract (tag v2026.9.14, commit 345cd2b), verified against exact
tagged ``hermes_cli/_parser.py`` and ``hermes_cli/oneshot.py``: the supported
scripted one-shot path is top-level ``hermes -z <prompt>`` with the top-level flags
``--provider``, ``--model``, ``--toolsets``, ``--usage-file``,
``--ignore-user-config``, ``--ignore-rules``, and ``--safe-mode``; the version is
read from ``hermes --version``. ``--max-turns`` is NOT a top-level flag: it exists
only on the ``chat`` subparser, and the tagged ``-z`` implementation constructs the
agent with no ``max_iterations`` override, so an iteration cap is UNAVAILABLE on the
pinned one-shot path and WP175H claims none. v0.21.3 does NOT support
``--format stream-json`` or ``--input-file`` and emits no machine-readable runtime
tool-call event stream: the final research response is plain stdout and
machine-readable usage/cost evidence comes from the ``--usage-file`` JSON report.

Project code here never reads, stores, injects, logs, transforms, validates, or
echoes a provider secret or any trading credential. Provider/model labels are
non-secret audit strings only; this package does not select or activate a provider.
"""

from __future__ import annotations

import dataclasses
import re
import subprocess

from .models import (
    HermesResearchRunRequest,
    ITERATION_CAP_STATUS,
    MAX_TRANSPORT_RETRIES_ABSOLUTE,
    canonical_json_bytes,
    content_address,
    sha256_hex,
)

# ---------------------------------------------------------------------------
# Pinned external contract (section 3)
# ---------------------------------------------------------------------------

HERMES_RELEASE = "v0.21.3"
HERMES_RELEASE_TAG = "v2026.9.14"
HERMES_RELEASE_COMMIT = "345cd2b"

# The exact semantic version a real run must report from ``hermes --version``.
HERMES_EXPECTED_SEMVER = "0.21.3"

# The one permitted built-in toolset. ``web`` resolves to web_search + web_extract.
ALLOWED_TOOLSETS: tuple[str, ...] = ("web",)
ALLOWED_WEB_TOOLS: tuple[str, ...] = ("web_search", "web_extract")

# v0.21.3 has no machine-readable runtime tool-call telemetry; enforcement is by the
# statically pinned argv toolset only.
TOOL_ENFORCEMENT = "STATIC_EXACT_TOOLSET_POLICY"
RUNTIME_TOOL_TELEMETRY = "UNAVAILABLE_ON_PINNED_V0_21_3"

# v0.21.3 one-shot output: plain stdout final text plus a usage-file JSON report.
OUTPUT_MODE = "PLAIN_STDOUT_PLUS_USAGE_FILE"

# Exact tagged ``-z`` internally enables one-shot approval bypass; a project safety
# argument therefore cannot rest on approval prompts. It rests on the exact web-only
# toolset (web_search + web_extract), safe-mode, ignore-user-config, ignore-rules,
# no repo mount, no mutating tool family, and a deterministic no-authority validator.
APPROVAL_AUTHORITY = "APPROVAL_BYPASS_PRESENT_BUT_NO_MUTATING_TOOL_SURFACE"

# Pinned one-shot iteration-cap posture (see models.ITERATION_CAP_STATUS).
ITERATION_CAP = ITERATION_CAP_STATUS

POLICY_IDENTITY_PREFIX = "hermesinvocationpolicy:sha256:"
POLICY_SCHEMA_VERSION = "hermes-invocation-policy/1.2.0"

CWD_POLICY = "EPHEMERAL_EMPTY_DIRECTORY"

# The usage report file name written by Hermes inside the ephemeral cwd.
USAGE_FILE_NAME = "hermes_usage.json"

# Conservative cross-platform maximum for the ``-z`` prompt argv element. Windows
# assembles argv into a single command line bounded near 32767 bytes; this leaves
# generous headroom for the executable path and the other short flags.
MAX_PROMPT_BYTES = 24_000

# Conservative ceiling on the ASSEMBLED Windows command line. `CreateProcess`' hard
# limit is 32767 characters; quote/backslash-heavy prompt content expands under
# Windows argv quoting, so the raw prompt byte bound is not sufficient on its own.
# The assembled length is checked with Python's Windows quoting semantics
# (``subprocess.list2cmdline``) on every platform for a deterministic, testable guard.
MAX_COMMAND_LINE_CHARS = 30_000

# Forbidden characters/tokens in the supplied executable path (defence in depth even
# though invocation is always argv-only, never through a shell).
_SHELL_METACHARACTERS = re.compile(r"[;&|`$><\n\r\t\"'*?(){}\[\]!~^]")

# A stable semantic-version token, parsed leniently from ``hermes --version`` output.
_SEMVER_TOKEN = re.compile(r"\b(\d+\.\d+\.\d+)\b")


class PolicyBroadeningError(Exception):
    """Raised when a caller attempts to broaden the frozen invocation policy."""

    def __init__(self, code: str = "POLICY_BROADENING_FORBIDDEN") -> None:
        super().__init__(code)
        self.code = code


@dataclasses.dataclass(frozen=True)
class HermesInvocationPolicy:
    """Immutable frozen policy record. All controls are fixed for the first runtime."""

    schema_version: str = POLICY_SCHEMA_VERSION
    hermes_release: str = HERMES_RELEASE
    hermes_release_tag: str = HERMES_RELEASE_TAG
    allowed_toolsets: tuple[str, ...] = ALLOWED_TOOLSETS
    tool_enforcement: str = TOOL_ENFORCEMENT
    output_mode: str = OUTPUT_MODE
    iteration_cap: str = ITERATION_CAP
    approval_authority: str = APPROVAL_AUTHORITY
    ignore_user_config: bool = True
    ignore_rules: bool = True
    safe_mode: bool = True
    one_shot: bool = True
    shell: bool = False
    cwd_policy: str = CWD_POLICY
    repo_mount: bool = False
    persistent_memory: bool = False
    plugins: bool = False
    mcp: bool = False
    cron: bool = False
    delegation: bool = False
    browser: bool = False
    file_tools: bool = False
    terminal: bool = False
    code_execution: bool = False
    automatic_retry_on_content_failure: bool = False
    automatic_retry_on_schema_failure: bool = False
    max_transport_retries: int = MAX_TRANSPORT_RETRIES_ABSOLUTE
    max_concurrency: int = 1

    def __post_init__(self) -> None:
        # No instance may ever represent a broadened control.
        if self.allowed_toolsets != ALLOWED_TOOLSETS:
            raise PolicyBroadeningError()
        if self.tool_enforcement != TOOL_ENFORCEMENT:
            raise PolicyBroadeningError()
        if self.output_mode != OUTPUT_MODE:
            raise PolicyBroadeningError()
        if self.iteration_cap != ITERATION_CAP:
            raise PolicyBroadeningError()
        if self.approval_authority != APPROVAL_AUTHORITY:
            raise PolicyBroadeningError()
        forbidden_true = (
            self.shell,
            self.repo_mount,
            self.persistent_memory,
            self.plugins,
            self.mcp,
            self.cron,
            self.delegation,
            self.browser,
            self.file_tools,
            self.terminal,
            self.code_execution,
            self.automatic_retry_on_content_failure,
            self.automatic_retry_on_schema_failure,
        )
        if any(forbidden_true):
            raise PolicyBroadeningError()
        required_true = (
            self.ignore_user_config,
            self.ignore_rules,
            self.safe_mode,
            self.one_shot,
        )
        if not all(required_true):
            raise PolicyBroadeningError()
        if self.cwd_policy != CWD_POLICY:
            raise PolicyBroadeningError()
        if self.max_transport_retries > MAX_TRANSPORT_RETRIES_ABSOLUTE:
            raise PolicyBroadeningError()
        if self.max_concurrency != 1:
            raise PolicyBroadeningError()

    @property
    def policy_id(self) -> str:
        return content_address(POLICY_IDENTITY_PREFIX, self.identity_fields())

    def identity_fields(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "hermes_release": self.hermes_release,
            "hermes_release_tag": self.hermes_release_tag,
            "allowed_toolsets": list(self.allowed_toolsets),
            "tool_enforcement": self.tool_enforcement,
            "output_mode": self.output_mode,
            "iteration_cap": self.iteration_cap,
            "approval_authority": self.approval_authority,
            "ignore_user_config": self.ignore_user_config,
            "ignore_rules": self.ignore_rules,
            "safe_mode": self.safe_mode,
            "one_shot": self.one_shot,
            "shell": self.shell,
            "cwd_policy": self.cwd_policy,
            "repo_mount": self.repo_mount,
            "persistent_memory": self.persistent_memory,
            "plugins": self.plugins,
            "mcp": self.mcp,
            "cron": self.cron,
            "delegation": self.delegation,
            "browser": self.browser,
            "file_tools": self.file_tools,
            "terminal": self.terminal,
            "code_execution": self.code_execution,
            "automatic_retry_on_content_failure": self.automatic_retry_on_content_failure,
            "automatic_retry_on_schema_failure": self.automatic_retry_on_schema_failure,
            "max_transport_retries": self.max_transport_retries,
            "max_concurrency": self.max_concurrency,
        }


DEFAULT_HERMES_INVOCATION_POLICY = HermesInvocationPolicy()


def validate_executable_path(executable_path: str) -> str:
    """Reject a Hermes executable path that could enable shell execution."""
    if not isinstance(executable_path, str) or not executable_path.strip():
        raise PolicyBroadeningError("POLICY_EXECUTABLE_INVALID")
    if _SHELL_METACHARACTERS.search(executable_path):
        raise PolicyBroadeningError("POLICY_EXECUTABLE_INVALID")
    return executable_path


def build_version_argv(executable_path: str) -> tuple[str, ...]:
    """Build the bounded no-network version preflight argv (argv only)."""
    validate_executable_path(executable_path)
    return (executable_path, "--version")


def build_hermes_argv(
    executable_path: str,
    request: HermesResearchRunRequest,
    prompt_text: str,
    policy: HermesInvocationPolicy = DEFAULT_HERMES_INVOCATION_POLICY,
    usage_file_name: str = USAGE_FILE_NAME,
) -> tuple[str, ...]:
    """Build the exact pinned v0.21.3 one-shot argv list (never a shell string).

    The prompt is carried as one ``-z`` argv element and is bounded before spawn.
    The usage file name must be a bare relative name written inside the ephemeral
    temp working directory; a path separator or traversal marker is rejected.
    """
    validate_executable_path(executable_path)
    if not isinstance(usage_file_name, str) or not usage_file_name:
        raise PolicyBroadeningError("POLICY_USAGE_FILE_INVALID")
    if "/" in usage_file_name or "\\" in usage_file_name or ".." in usage_file_name:
        raise PolicyBroadeningError("POLICY_USAGE_FILE_INVALID")
    if not isinstance(prompt_text, str) or not prompt_text:
        raise PolicyBroadeningError("POLICY_PROMPT_INVALID")
    if len(prompt_text.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise PolicyBroadeningError("POLICY_PROMPT_TOO_LARGE")

    # Exact pinned v0.21.3 top-level flags only. ``--max-turns`` is NOT a top-level
    # flag on this release (it exists solely on the ``chat`` subparser), so it is
    # never passed: no iteration cap is available or claimed on the ``-z`` path.
    argv: list[str] = [
        executable_path,
        "--safe-mode",
        "--ignore-user-config",
        "--ignore-rules",
        "--provider",
        request.provider_label,
        "--model",
        request.model_label,
        "--toolsets",
        ",".join(policy.allowed_toolsets),
        "--usage-file",
        usage_file_name,
        "-z",
        prompt_text,
    ]
    # Fail closed before spawn if the assembled Windows command line (after argv
    # quoting) would approach the CreateProcess ceiling. Never shell-quote manually;
    # ``list2cmdline`` mirrors the exact Windows quoting the runtime would apply.
    if len(subprocess.list2cmdline(argv)) > MAX_COMMAND_LINE_CHARS:
        raise PolicyBroadeningError("POLICY_COMMAND_LINE_TOO_LARGE")
    return tuple(argv)


# ---------------------------------------------------------------------------
# Deterministic compact research envelope (section 9)
# ---------------------------------------------------------------------------

PERMANENT_SYSTEM_INSTRUCTION_VERSION = "hermes-research-system-instruction/1.0.0"

PERMANENT_SYSTEM_INSTRUCTION = (
    "You are a Polymarket public-research assistant. Your role is advisory and "
    "research-only; you have no execution, risk, credential, paper, or live "
    "authority. Use only public web evidence. Cite every source with a real URL "
    "and never fabricate a citation or claim source access that did not happen. "
    "Distinguish established fact from a source's claim and from your own "
    "inference. Actively search for evidence against the thesis and disclose "
    "uncertainty and missing data. Do not request credentials or private data. "
    "Do not produce execution, risk, order, or live instructions; do not place, "
    "cancel, sign, or submit any order. A human and deterministic review is "
    "required for every output. Return exactly one JSON object matching the "
    "provided research-draft schema as your final response."
)


@dataclasses.dataclass(frozen=True)
class HermesResearchEnvelope:
    """Deterministic compact prompt envelope passed as the one-shot ``-z`` prompt."""

    system_instruction_version: str
    system_instruction: str
    request_id: str
    research_question: str
    research_objective: str
    research_category: str
    public_market_context: str
    allowed_research_scope: tuple[str, ...]
    required_source_types: tuple[str, ...]
    max_sources: int
    draft_schema_version: str

    def to_query_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_mapping())

    def to_prompt_string(self) -> str:
        return self.to_query_bytes().decode("utf-8")

    def as_mapping(self) -> dict[str, object]:
        return {
            "system_instruction_version": self.system_instruction_version,
            "system_instruction": self.system_instruction,
            "request_id": self.request_id,
            "research_question": self.research_question,
            "research_objective": self.research_objective,
            "research_category": self.research_category,
            "public_market_context": self.public_market_context,
            "allowed_research_scope": list(self.allowed_research_scope),
            "required_source_types": list(self.required_source_types),
            "max_sources": self.max_sources,
            "draft_schema_version": self.draft_schema_version,
        }

    @property
    def envelope_digest(self) -> str:
        return sha256_hex(self.to_query_bytes())


def build_research_envelope(request: HermesResearchRunRequest) -> HermesResearchEnvelope:
    """Build the compact envelope. It never includes a repo mount, AGENTS.md, full
    project history, project memory, or the Alpha Factory database."""
    from .models import DRAFT_SCHEMA_VERSION

    return HermesResearchEnvelope(
        system_instruction_version=PERMANENT_SYSTEM_INSTRUCTION_VERSION,
        system_instruction=PERMANENT_SYSTEM_INSTRUCTION,
        request_id=request.request_id,
        research_question=request.research_question,
        research_objective=request.research_objective,
        research_category=request.research_category,
        public_market_context=request.public_market_context,
        allowed_research_scope=request.allowed_research_scope,
        required_source_types=request.required_source_types,
        max_sources=request.max_sources,
        draft_schema_version=DRAFT_SCHEMA_VERSION,
    )


def parse_hermes_version(reported: object) -> str | None:
    """Extract the stable semantic-version token from ``hermes --version`` output."""
    if isinstance(reported, bytes):
        try:
            reported = reported.decode("utf-8")
        except UnicodeError:
            return None
    if not isinstance(reported, str):
        return None
    match = _SEMVER_TOKEN.search(reported)
    return match.group(1) if match else None


def is_supported_hermes_version(reported: object) -> bool:
    """A real external run is invalid unless the reported version is exactly 0.21.3."""
    return parse_hermes_version(reported) == HERMES_EXPECTED_SEMVER
