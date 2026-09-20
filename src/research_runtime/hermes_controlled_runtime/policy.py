"""Immutable Hermes invocation policy and deterministic invocation plan (WP175H/WP175I).

This module freezes the exact first-runtime controls for one bounded, dormant-by-
default, one-shot Hermes research session against the pinned Hermes Agent v0.21.3
tagged contract. No caller may broaden the policy: the argv builder rejects any
executable path with shell metacharacters, never builds a command string, never
mounts the repository or a home/local_data path as the Hermes working directory,
and enables exactly the single permitted ``web`` toolset.

WP175I CONTROLLED RESEARCH PROFILE. The merged WP175H research invocation carried
``--safe-mode``, which on exact tagged v0.21.3 sets ``HERMES_SAFE_MODE=1`` and makes
``hermes_cli/plugins.py`` skip ALL plugin discovery -- including the pinned bundled
``plugins/web/firecrawl`` backend (``kind: backend``) that H1 requires. WP175I
therefore REMOVES ``--safe-mode`` from the real research argv (retaining
``--ignore-user-config`` and ``--ignore-rules``) and replaces the lost isolation with
a deterministic, repo-owned, non-secret managed-scope ``config.yaml`` injected through
``HERMES_MANAGED_DIR``. Verified against exact commit 345cd2b:
``hermes_cli/oneshot.py`` (the ``-z`` handler) calls ``hermes_cli.config.load_config()``,
whose ``_merge_managed_overlay`` deep-merges the managed config leaf-over-leaf ON TOP of
defaults/user config (``hermes_cli/managed_scope.py``), so the managed layer survives the
one-shot path. The managed layer pins Firecrawl for both web_search and web_extract,
forces the keyless fallback/rescue rings OFF, empties the provider fallback chain, sets
one ordinary provider attempt (``agent.api_max_retries: 1``), and forbids the
custom/user/project plugin allow-list (``plugins.enabled: []``) while pinned bundled
backend discovery still registers Firecrawl. Removing safe mode is safe ONLY with the
full compensating-control set (dedicated research home with ``config.yaml`` absent and no
user plugins, empty ephemeral cwd, no forwarded ``HERMES_ENABLE_PROJECT_PLUGINS`` /
``HERMES_MANAGED_DIR`` / secrets, ``--toolsets web`` only, no MCP/custom toolset, no repo
mount). ``CUSTOM_USER_PROJECT_PLUGIN_LOADING = FORBIDDEN``;
``PINNED_BUNDLED_BACKEND_DISCOVERY = ALLOWED_FOR_WEB_PROVIDER_REGISTRATION``;
``EXPOSED_AGENT_TOOLSET = WEB_ONLY``.

Pinned v0.21.3 contract (tag v2026.9.14, commit 345cd2b), verified against exact
tagged ``hermes_cli/_parser.py`` and ``hermes_cli/oneshot.py``: the supported
scripted one-shot path is top-level ``hermes -z <prompt>`` with the top-level flags
``--provider``, ``--model``, ``--toolsets``, ``--usage-file``,
``--ignore-user-config``, and ``--ignore-rules``; the version is read from
``hermes --version``. ``--max-turns`` is NOT a top-level flag: it exists only on the
``chat`` subparser, and the tagged ``-z`` implementation constructs the agent with no
``max_iterations`` override, so an iteration cap is UNAVAILABLE on the pinned one-shot
path and WP175H claims none. v0.21.3 does NOT support ``--format stream-json`` or
``--input-file`` and emits no machine-readable runtime tool-call event stream: the final
research response is plain stdout and machine-readable usage/cost evidence comes from the
``--usage-file`` JSON report.

Retry posture (exact tagged, commit 345cd2b): ``agent.api_max_retries: 1`` clamps to one
ordinary provider attempt (``agent/agent_init.py`` ``max(...,1)``,
``agent/conversation_loop.py`` ``while retry_count < max_retries``); the primary OpenAI
client is created with SDK ``max_retries=0`` (``_create_openai_client``, proven by tagged
``tests/agent/test_create_openai_client_disables_sdk_retries.py``); one bounded
same-provider primary-transport recovery (``agent/agent_runtime_helpers.py``
``try_recover_primary_transport``) may rebuild the primary client once after that attempt
exhausts on a transient transport error -- same provider, same model, same web backend,
no second controller invocation. No provider/model fallback; no web backend
fallback/rescue.

Project code here never reads, stores, injects, logs, transforms, validates, or
echoes a provider secret or any trading credential. Provider/model labels are
non-secret audit strings only; this package does not select or activate a provider.
The managed config carries no secret, token, key, path, or private data.
"""

from __future__ import annotations

import dataclasses
import re
import subprocess
from typing import Mapping

from .models import (
    HermesResearchRunRequest,
    ITERATION_CAP_STATUS,
    MAX_TRANSPORT_RETRIES_ABSOLUTE,
    build_research_draft_output_schema,
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
# toolset (web_search + web_extract), the controlled managed-scope profile,
# ignore-user-config, ignore-rules, no repo mount, no mutating tool family, and a
# deterministic no-authority validator. Safe mode is NOT used on the research
# invocation (it would suppress the bundled Firecrawl backend H1 requires).
APPROVAL_AUTHORITY = "APPROVAL_BYPASS_PRESENT_BUT_NO_MUTATING_TOOL_SURFACE"

# Pinned one-shot iteration-cap posture (see models.ITERATION_CAP_STATUS).
ITERATION_CAP = ITERATION_CAP_STATUS

POLICY_IDENTITY_PREFIX = "hermesinvocationpolicy:sha256:"
# Bumped from 1.2.0 (WP175H) to 2.0.0 (WP175I): the security posture materially changed
# -- safe mode removed from the research invocation, replaced by the controlled
# managed-scope profile.
POLICY_SCHEMA_VERSION = "hermes-invocation-policy/2.0.0"

# ---------------------------------------------------------------------------
# WP175I controlled research profile (section 5)
# ---------------------------------------------------------------------------

# The controlled managed-profile version. A change here changes policy identity.
CONTROLLED_PROFILE_VERSION = "hermes-controlled-research-profile/1.0.0"

# Deterministic managed-scope config VALUES pinned for every external research
# invocation. Written verbatim (as JSON, which is valid YAML) into an ephemeral
# ``HERMES_MANAGED_DIR/config.yaml`` and deep-merged leaf-over-leaf on top of exact
# tagged v0.21.3 defaults by ``hermes_cli.config.load_config`` /
# ``_merge_managed_overlay``. NO secret, token, key, path, or private value here.
MANAGED_UPDATES_CHECK = False
MANAGED_AGENT_API_MAX_RETRIES = 1
MANAGED_FALLBACK_PROVIDERS: tuple[str, ...] = ()
MANAGED_WEB_BACKEND = "firecrawl"
MANAGED_WEB_SEARCH_BACKEND = "firecrawl"
MANAGED_WEB_EXTRACT_BACKEND = "firecrawl"
MANAGED_WEB_KEYLESS_FALLBACK = False
MANAGED_WEB_KEYLESS_RESCUE = False
MANAGED_WEB_CACHE_ENABLED = False
MANAGED_WEB_PROVIDER_TIER_FIRECRAWL = "paid"
MANAGED_PLUGINS_ENABLED: tuple[str, ...] = ()

# Truthful post-correction profile wording (safe mode removed; bundled discovery on).
CUSTOM_USER_PROJECT_PLUGIN_LOADING = "FORBIDDEN"
BUNDLED_BACKEND_DISCOVERY = "ALLOWED_FOR_WEB_PROVIDER_REGISTRATION"
EXPOSED_AGENT_TOOLSET = "WEB_ONLY"
SAME_PROVIDER_PRIMARY_TRANSPORT_RECOVERY = "ALLOWED_BOUNDED"
PROVIDER_MODEL_FALLBACK = "NONE"
WEB_BACKEND_FALLBACK_RESCUE = "NONE"

CWD_POLICY = "EPHEMERAL_EMPTY_DIRECTORY"

# Managed-scope directory policy: a backend-created ephemeral directory, never the
# repository, ``local_data``, the research HERMES_HOME, or the empty cwd, and never
# inherited from or supplied by the caller.
MANAGED_SCOPE_MODE = "EPHEMERAL_REPO_OWNED_NON_SECRET_MANAGED_DIR"

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

# Bind package-version identity to the Hermes-branded ``--version`` label.  The
# exact tagged banner also contains a release date shaped like a semantic version;
# an unbranded first-token search can therefore select the wrong value.
_HERMES_VERSION_TOKEN = re.compile(
    r"\bhermes(?:\s+agent|-agent)\s+v?(\d+\.\d+\.\d+)\b",
    re.IGNORECASE,
)


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
    # WP175I: safe mode is REMOVED from the research invocation (it suppresses the
    # bundled Firecrawl backend on exact v0.21.3). It is frozen False and the
    # controlled managed scope replaces the lost isolation.
    safe_mode: bool = False
    controlled_managed_scope: bool = True
    controlled_profile_version: str = CONTROLLED_PROFILE_VERSION
    managed_scope_mode: str = MANAGED_SCOPE_MODE
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
    # --- controlled managed-profile pinned values (drive the managed config bytes) ---
    updates_check: bool = MANAGED_UPDATES_CHECK
    api_max_retries: int = MANAGED_AGENT_API_MAX_RETRIES
    managed_fallback_providers: tuple[str, ...] = MANAGED_FALLBACK_PROVIDERS
    web_backend: str = MANAGED_WEB_BACKEND
    web_search_backend: str = MANAGED_WEB_SEARCH_BACKEND
    web_extract_backend: str = MANAGED_WEB_EXTRACT_BACKEND
    keyless_fallback: bool = MANAGED_WEB_KEYLESS_FALLBACK
    keyless_rescue: bool = MANAGED_WEB_KEYLESS_RESCUE
    web_cache_enabled: bool = MANAGED_WEB_CACHE_ENABLED
    web_provider_tier_firecrawl: str = MANAGED_WEB_PROVIDER_TIER_FIRECRAWL
    managed_plugins_enabled: tuple[str, ...] = MANAGED_PLUGINS_ENABLED
    # --- truthful profile posture strings ---
    custom_user_project_plugin_loading: str = CUSTOM_USER_PROJECT_PLUGIN_LOADING
    bundled_backend_discovery: str = BUNDLED_BACKEND_DISCOVERY
    exposed_agent_toolset: str = EXPOSED_AGENT_TOOLSET
    same_provider_primary_transport_recovery: str = SAME_PROVIDER_PRIMARY_TRANSPORT_RECOVERY
    provider_model_fallback: str = PROVIDER_MODEL_FALLBACK
    web_backend_fallback_rescue: str = WEB_BACKEND_FALLBACK_RESCUE
    research_home_config_allowed: bool = False
    research_home_user_plugins_allowed: bool = False

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
            # WP175I: safe mode must NOT be re-enabled as the supposed H1 safety
            # mechanism; the controlled managed scope is the H1 isolation layer.
            self.safe_mode,
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
            self.keyless_fallback,
            self.keyless_rescue,
            self.web_cache_enabled,
            self.updates_check,
            self.research_home_config_allowed,
            self.research_home_user_plugins_allowed,
        )
        if any(forbidden_true):
            raise PolicyBroadeningError()
        required_true = (
            self.ignore_user_config,
            self.ignore_rules,
            self.controlled_managed_scope,
            self.one_shot,
        )
        if not all(required_true):
            raise PolicyBroadeningError()
        # Controlled managed-profile values are pinned exactly. Any deviation either
        # fails construction here or changes policy identity via the managed digest.
        pinned = (
            (self.controlled_profile_version, CONTROLLED_PROFILE_VERSION),
            (self.managed_scope_mode, MANAGED_SCOPE_MODE),
            (self.api_max_retries, MANAGED_AGENT_API_MAX_RETRIES),
            (self.managed_fallback_providers, MANAGED_FALLBACK_PROVIDERS),
            (self.web_backend, MANAGED_WEB_BACKEND),
            (self.web_search_backend, MANAGED_WEB_SEARCH_BACKEND),
            (self.web_extract_backend, MANAGED_WEB_EXTRACT_BACKEND),
            (self.web_provider_tier_firecrawl, MANAGED_WEB_PROVIDER_TIER_FIRECRAWL),
            (self.managed_plugins_enabled, MANAGED_PLUGINS_ENABLED),
            (self.custom_user_project_plugin_loading, CUSTOM_USER_PROJECT_PLUGIN_LOADING),
            (self.bundled_backend_discovery, BUNDLED_BACKEND_DISCOVERY),
            (self.exposed_agent_toolset, EXPOSED_AGENT_TOOLSET),
            (self.same_provider_primary_transport_recovery, SAME_PROVIDER_PRIMARY_TRANSPORT_RECOVERY),
            (self.provider_model_fallback, PROVIDER_MODEL_FALLBACK),
            (self.web_backend_fallback_rescue, WEB_BACKEND_FALLBACK_RESCUE),
        )
        for actual, expected in pinned:
            if actual != expected:
                raise PolicyBroadeningError()
        if self.cwd_policy != CWD_POLICY:
            raise PolicyBroadeningError()
        if self.max_transport_retries > MAX_TRANSPORT_RETRIES_ABSOLUTE:
            raise PolicyBroadeningError()
        if self.max_concurrency != 1:
            raise PolicyBroadeningError()

    def managed_config_mapping(self) -> dict[str, object]:
        """The deterministic non-secret managed-scope config for this policy.

        The keys are exact tagged v0.21.3 config keys (verified at commit 345cd2b):
        ``updates.check``, ``fallback_providers``, ``agent.api_max_retries``,
        ``web.{backend,search_backend,extract_backend,keyless_fallback,keyless_rescue,
        cache_enabled,provider_tier}``, ``plugins.enabled``, ``hooks``. Values are
        literals only -- never a secret, token, key, path, or private value.
        """
        return {
            "updates": {"check": self.updates_check},
            "fallback_providers": list(self.managed_fallback_providers),
            "agent": {"api_max_retries": self.api_max_retries},
            "web": {
                "backend": self.web_backend,
                "search_backend": self.web_search_backend,
                "extract_backend": self.web_extract_backend,
                "keyless_fallback": self.keyless_fallback,
                "keyless_rescue": self.keyless_rescue,
                "cache_enabled": self.web_cache_enabled,
                "provider_tier": {"firecrawl": self.web_provider_tier_firecrawl},
            },
            "plugins": {"enabled": list(self.managed_plugins_enabled)},
            "hooks": {},
        }

    def managed_config_bytes(self) -> bytes:
        """Deterministic managed ``config.yaml`` bytes (canonical JSON, valid YAML)."""
        return canonical_json_bytes(self.managed_config_mapping())

    @property
    def managed_config_sha256(self) -> str:
        return sha256_hex(self.managed_config_bytes())

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
            "controlled_managed_scope": self.controlled_managed_scope,
            "controlled_profile_version": self.controlled_profile_version,
            "managed_scope_mode": self.managed_scope_mode,
            # The deterministic managed-config bytes are committed into the policy
            # identity by their SHA-256 (section 5.4): a one-field broadening of any
            # managed control changes this digest and therefore the policy id.
            "managed_config_sha256": self.managed_config_sha256,
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
            "custom_user_project_plugin_loading": self.custom_user_project_plugin_loading,
            "bundled_backend_discovery": self.bundled_backend_discovery,
            "exposed_agent_toolset": self.exposed_agent_toolset,
            "same_provider_primary_transport_recovery": self.same_provider_primary_transport_recovery,
            "provider_model_fallback": self.provider_model_fallback,
            "web_backend_fallback_rescue": self.web_backend_fallback_rescue,
            "research_home_config_allowed": self.research_home_config_allowed,
            "research_home_user_plugins_allowed": self.research_home_user_plugins_allowed,
        }


DEFAULT_HERMES_INVOCATION_POLICY = HermesInvocationPolicy()

# Deterministic managed-config bytes / digest for the default controlled profile.
CONTROLLED_MANAGED_CONFIG_BYTES = DEFAULT_HERMES_INVOCATION_POLICY.managed_config_bytes()
CONTROLLED_MANAGED_CONFIG_SHA256 = DEFAULT_HERMES_INVOCATION_POLICY.managed_config_sha256


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
    # WP175I: ``--safe-mode`` is NOT passed -- it sets HERMES_SAFE_MODE=1 which makes
    # exact tagged ``hermes_cli/plugins.py`` skip plugin discovery, suppressing the
    # bundled Firecrawl backend H1 needs. Isolation is enforced by the controlled
    # managed-scope profile plus ``--ignore-user-config`` / ``--ignore-rules``.
    argv: list[str] = [
        executable_path,
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

# WP175M: bumped 1.0.0 -> 1.1.0. The permanent instruction now states that the
# envelope's ``draft_output_schema`` is the authoritative response contract and that
# canonical field names must be used exactly (never renamed/substituted). The full
# field list is NOT duplicated in prose -- the machine-generated schema is the source
# of truth.
PERMANENT_SYSTEM_INSTRUCTION_VERSION = "hermes-research-system-instruction/1.1.0"

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
    "required for every output. "
    "Your final response MUST be exactly one JSON object that conforms to the "
    "`draft_output_schema` provided in this envelope; that schema is authoritative. "
    "Use the field names EXACTLY as specified there and include EVERY required field. "
    "Do not rename or substitute canonical fields with aliases such as `sources`, "
    "`evidence_map`, `completeness`, or `cross_category_assessment`. Every authority "
    "flag must be present and exactly the boolean true. The substantive research "
    "fields must reflect real research you actually performed and must never be "
    "fabricated placeholders: `source_references` must contain the real sources you "
    "used and `falsification_checks_performed` must record the actual disconfirming "
    "work you did."
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
    # WP175M: the authoritative deterministic draft output contract, generated from the
    # validator's canonical constants. It supplies the actual field-name contract the
    # H1 #3 prompt only referenced by version string. Included in the canonical query
    # bytes, prompt string, and envelope digest.
    draft_output_schema: Mapping[str, object]

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
            "draft_output_schema": dict(self.draft_output_schema),
        }

    @property
    def envelope_digest(self) -> str:
        return sha256_hex(self.to_query_bytes())

    @property
    def draft_output_contract_digest(self) -> str:
        """SHA-256 of the canonical serialization of the embedded output contract."""
        return sha256_hex(canonical_json_bytes(dict(self.draft_output_schema)))


def build_research_envelope(request: HermesResearchRunRequest) -> HermesResearchEnvelope:
    """Build the compact envelope. It never includes a repo mount, AGENTS.md, full
    project history, project memory, or the Alpha Factory database."""
    from .models import DRAFT_SCHEMA_VERSION

    draft_output_schema = build_research_draft_output_schema(
        expected_request_id=request.request_id,
        max_sources=request.max_sources,
    )
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
        draft_output_schema=draft_output_schema,
    )


def parse_hermes_version(reported: object) -> str | None:
    """Extract only the package version attached to a Hermes-branded label."""
    if isinstance(reported, bytes):
        try:
            reported = reported.decode("utf-8")
        except UnicodeError:
            return None
    if not isinstance(reported, str):
        return None
    match = _HERMES_VERSION_TOKEN.search(reported)
    return match.group(1) if match else None


def is_supported_hermes_version(reported: object) -> bool:
    """A real external run is invalid unless the reported version is exactly 0.21.3."""
    return parse_hermes_version(reported) == HERMES_EXPECTED_SEMVER
