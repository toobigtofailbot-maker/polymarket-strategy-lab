"""External-process boundary for the controlled Hermes research runtime (WP175H/WP175I).

Two backends implement one protocol:

  * :class:`FakeHermesBackend` -- deterministic, makes no process and no network
    call; used by every unit/CI test.
  * :class:`ExternalHermesCliBackend` -- runs a caller-supplied Hermes v0.21.3
    executable with an argv list only (never a shell, never a command string), from
    a fresh empty temporary working directory that never mounts the repository, a
    ``local_data`` path, or a user home path; captures stdout/stderr under hard byte
    caps; reads the bounded ``--usage-file`` report Hermes writes into that temp dir;
    enforces a hard wall-clock timeout that kills the child process tree where
    platform mechanics permit; and deletes the temporary directory on teardown.

WP175I controlled research profile. For every external research invocation the backend
creates a SECOND ephemeral directory -- the managed scope -- separate from the cwd, the
repository, ``local_data``, and the research HERMES_HOME. It writes exactly one
non-secret ``config.yaml`` (the caller-supplied deterministic managed-config bytes) into
that directory and sets ``HERMES_MANAGED_DIR`` on the child to it. The child never
inherits an ambient ``HERMES_MANAGED_DIR``, ``HERMES_SAFE_MODE``, or
``HERMES_ENABLE_PROJECT_PLUGINS``. Both ephemeral directories are removed on every path
(success, failure, timeout). For an H1-grade research home, a fail-closed preflight
rejects unexpected control-plane material -- a present ``config.yaml`` or a non-empty
user ``plugins/`` directory -- BEFORE spawn, inspecting directory/file NAMES only and
never reading a credential value.

Pinned v0.21.3 carries the prompt as the ``-z`` argv element, so no prompt file is
written into the working directory. The backend records no secret-bearing
environment or raw stderr in evidence and does not discover, read, validate,
inject, or log provider credentials. Only an explicit NON-SECRET research
Hermes-home locator may be forwarded so Hermes can find its own credential store,
configured out-of-repo by S10-GATE-H1.
"""

from __future__ import annotations

import dataclasses
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Protocol, Sequence


@dataclasses.dataclass(frozen=True)
class HermesVersionProbe:
    """Sanitized result of a bounded, update-check-disabled ``hermes --version`` probe.

    Raw ``hermes --version`` is NOT intrinsically offline: exact tagged
    ``hermes_cli/_startup_fast.py::print_fast_version_info(check_updates=True)`` calls
    ``banner.check_for_updates(passive=True)``, which can reach GitHub. The probe is
    isolated in a throwaway ``HERMES_HOME`` whose ``config.yaml`` sets
    ``updates.check: false``; the tagged ``check_for_updates`` returns before any
    network access when that opt-out is set.
    """

    launched: bool
    timed_out: bool
    version_text: str | None
    exit_code: int | None = None
    stdout_truncated: bool = False


@dataclasses.dataclass(frozen=True)
class HermesInvocationOutcome:
    """Sanitized outcome of one backend invocation. Carries no raw stderr text."""

    stdout: bytes
    stdout_truncated: bool
    stderr_byte_len: int
    stderr_truncated: bool
    usage_file_bytes: bytes | None
    usage_file_truncated: bool
    exit_code: int | None
    timed_out: bool
    launch_failed: bool
    duration_ms: int | None

    @property
    def transport_retry_eligible(self) -> bool:
        """Retry is permitted only for transport failure or timeout (section 12)."""
        return self.timed_out or self.launch_failed


class HermesInvocationBackend(Protocol):
    """One bounded invocation. Implementations must never raise on process error."""

    def probe_version(
        self, *, version_argv: Sequence[str], max_output_bytes: int, max_wall_seconds: int
    ) -> HermesVersionProbe: ...

    def invoke(
        self,
        *,
        argv: Sequence[str],
        usage_file_name: str,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        max_usage_bytes: int,
        max_wall_seconds: int,
        hermes_home: str | None = None,
        managed_config_bytes: bytes | None = None,
    ) -> HermesInvocationOutcome: ...


# ---------------------------------------------------------------------------
# Fake backend
# ---------------------------------------------------------------------------


class FakeHermesBackend:
    """Deterministic backend that performs zero process and zero network calls."""

    def __init__(
        self,
        outcomes: Sequence[HermesInvocationOutcome],
        *,
        version_text: str | None = "hermes-agent 0.21.3",
        version_timed_out: bool = False,
        version_launched: bool = True,
        version_exit_code: int | None = 0,
        version_stdout_truncated: bool = False,
    ) -> None:
        if not outcomes:
            raise ValueError("FakeHermesBackend requires at least one outcome")
        self._outcomes = tuple(outcomes)
        self._version = HermesVersionProbe(
            launched=version_launched,
            timed_out=version_timed_out,
            version_text=version_text,
            exit_code=version_exit_code,
            stdout_truncated=version_stdout_truncated,
        )
        self.call_count = 0
        self.version_probe_count = 0
        self.recorded_argv: list[tuple[str, ...]] = []
        self.recorded_usage_file_names: list[str] = []
        self.recorded_hermes_home: list[str | None] = []
        # Deterministic record of the controlled managed-config bytes the controller
        # supplied -- the fake performs ZERO process/network calls and never writes
        # the config to disk or sets an environment variable.
        self.recorded_managed_config_bytes: list[bytes | None] = []

    @classmethod
    def from_transcript(
        cls,
        response_stdout: bytes,
        *,
        usage_file_bytes: bytes | None = None,
        exit_code: int = 0,
        stderr_byte_len: int = 0,
        version_text: str | None = "hermes-agent 0.21.3",
    ) -> "FakeHermesBackend":
        return cls(
            [
                HermesInvocationOutcome(
                    stdout=response_stdout,
                    stdout_truncated=False,
                    stderr_byte_len=stderr_byte_len,
                    stderr_truncated=False,
                    usage_file_bytes=usage_file_bytes,
                    usage_file_truncated=False,
                    exit_code=exit_code,
                    timed_out=False,
                    launch_failed=False,
                    duration_ms=0,
                )
            ],
            version_text=version_text,
        )

    def probe_version(
        self, *, version_argv: Sequence[str], max_output_bytes: int, max_wall_seconds: int
    ) -> HermesVersionProbe:
        self.version_probe_count += 1
        return self._version

    def invoke(
        self,
        *,
        argv: Sequence[str],
        usage_file_name: str,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        max_usage_bytes: int,
        max_wall_seconds: int,
        hermes_home: str | None = None,
        managed_config_bytes: bytes | None = None,
    ) -> HermesInvocationOutcome:
        index = min(self.call_count, len(self._outcomes) - 1)
        self.call_count += 1
        self.recorded_argv.append(tuple(argv))
        self.recorded_usage_file_names.append(usage_file_name)
        self.recorded_hermes_home.append(hermes_home)
        self.recorded_managed_config_bytes.append(managed_config_bytes)
        outcome = self._outcomes[index]
        if len(outcome.stdout) > max_stdout_bytes:
            return dataclasses.replace(
                outcome, stdout=outcome.stdout[:max_stdout_bytes], stdout_truncated=True
            )
        return outcome


# ---------------------------------------------------------------------------
# External CLI backend
# ---------------------------------------------------------------------------

# Working-directory / home prefixes that must never be supplied to Hermes.
_FORBIDDEN_PATH_MARKERS = ("local_data",)

# Provider-secret-bearing environment variable name fragments that are never
# forwarded to the child process.
_SECRET_ENV_FRAGMENTS = (
    "KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "CREDENTIAL",
    "AUTH",
    "PRIVATE",
)

# Only these neutral variables are ever forwarded (plus an explicit HERMES_HOME and the
# backend-created HERMES_MANAGED_DIR set in ``invoke``).
_NEUTRAL_ENV_KEYS = ("PATH", "SystemRoot", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL")

# Control-plane variables that must NEVER be inherited from the parent process. The
# minimal-env whitelist already excludes everything not in ``_NEUTRAL_ENV_KEYS``; these
# are named so the boundary is explicit and testable. ``HERMES_MANAGED_DIR`` is set by
# the backend itself (to its ephemeral managed dir), never inherited; ``HERMES_SAFE_MODE``
# is never set (safe mode would suppress the bundled Firecrawl backend);
# ``HERMES_ENABLE_PROJECT_PLUGINS`` is never forwarded (project plugins stay disabled).
_NEVER_FORWARD_ENV = (
    "HERMES_SAFE_MODE",
    "HERMES_ENABLE_PROJECT_PLUGINS",
    "HERMES_MANAGED_DIR",
)

# A dedicated H1 research home must NOT carry these control-plane files (names only).
_RESEARCH_HOME_FORBIDDEN_CONFIG = "config.yaml"
_RESEARCH_HOME_USER_PLUGINS_DIR = "plugins"


class ExternalHermesCliBackend:
    """Runs an external Hermes v0.21.3 CLI via argv only from an ephemeral empty cwd."""

    def probe_version(
        self, *, version_argv: Sequence[str], max_output_bytes: int, max_wall_seconds: int
    ) -> HermesVersionProbe:
        version_argv = list(version_argv)
        if not version_argv:
            return HermesVersionProbe(launched=False, timed_out=False, version_text=None)

        # Isolated throwaway HERMES_HOME whose config disables the passive update
        # check, so ``hermes --version`` performs no GitHub/network access. It never
        # reuses the real credential-bearing research home and forwards no secrets.
        probe_home = tempfile.mkdtemp(prefix="hermes_verprobe_")
        try:
            _write_update_disabled_config(probe_home)
            env = _minimal_env(None)
            env["HERMES_HOME"] = probe_home
            try:
                proc = subprocess.run(  # noqa: S603
                    version_argv,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=probe_home,
                    env=env,
                    timeout=max_wall_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return HermesVersionProbe(
                    launched=True, timed_out=True, version_text=None, exit_code=None
                )
            except (OSError, ValueError):
                return HermesVersionProbe(launched=False, timed_out=False, version_text=None)
            raw_all = proc.stdout or b""
            raw = raw_all[:max_output_bytes]
            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover - defensive
                text = None
            return HermesVersionProbe(
                launched=True,
                timed_out=False,
                version_text=text,
                exit_code=proc.returncode,
                stdout_truncated=len(raw_all) > max_output_bytes,
            )
        finally:
            shutil.rmtree(probe_home, ignore_errors=True)

    def invoke(
        self,
        *,
        argv: Sequence[str],
        usage_file_name: str,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        max_usage_bytes: int,
        max_wall_seconds: int,
        hermes_home: str | None = None,
        managed_config_bytes: bytes | None = None,
    ) -> HermesInvocationOutcome:
        argv = list(argv)
        if not argv:
            return _launch_failure()
        if "/" in usage_file_name or "\\" in usage_file_name or ".." in usage_file_name:
            return _launch_failure()

        env = _minimal_env(hermes_home)
        if hermes_home is not None and "HERMES_HOME" not in env:
            # An unsafe research-home locator fails closed rather than running.
            return _launch_failure()
        # WP175I H1 control-plane preflight: a dedicated research home must not carry a
        # ``config.yaml`` or a non-empty user ``plugins/`` directory, so the controlled
        # managed scope is the only non-default runtime policy layer. Names only; no
        # credential value is read.
        if hermes_home is not None and not is_clean_research_home_control_plane(hermes_home):
            return _launch_failure()

        temp_dir = tempfile.mkdtemp(prefix="hermes_oneshot_")
        # A distinct ephemeral managed-scope directory (never the cwd, repo, local_data,
        # research home, or a caller-supplied path). The child receives it through
        # ``HERMES_MANAGED_DIR``; the parent never inherits or forwards that variable.
        managed_dir: str | None = None
        start = time.monotonic()
        try:
            resolved = os.path.realpath(temp_dir)
            home = os.path.realpath(os.path.expanduser("~"))
            if resolved == home or any(marker in resolved for marker in _FORBIDDEN_PATH_MARKERS):
                return _launch_failure()

            if managed_config_bytes is not None:
                managed_dir = tempfile.mkdtemp(prefix="hermes_managed_")
                if os.path.realpath(managed_dir) == resolved:  # pragma: no cover - defensive
                    return _launch_failure()
                try:
                    with open(os.path.join(managed_dir, "config.yaml"), "wb") as handle:
                        handle.write(managed_config_bytes)
                except OSError:
                    return _launch_failure(_elapsed_ms(start))
                # The backend itself sets HERMES_MANAGED_DIR; it is never inherited or
                # caller-supplied. ``get_managed_dir()`` honors it only when the dir exists.
                env["HERMES_MANAGED_DIR"] = managed_dir

            popen_kwargs: dict[str, object] = {
                "cwd": temp_dir,
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "env": env,
            }
            if os.name == "posix":
                popen_kwargs["start_new_session"] = True
            else:  # pragma: no cover - Windows-only branch
                popen_kwargs["creationflags"] = getattr(
                    subprocess, "CREATE_NEW_PROCESS_GROUP", 0
                )

            try:
                process = subprocess.Popen(argv, **popen_kwargs)  # noqa: S603
            except (OSError, ValueError):
                return _launch_failure(_elapsed_ms(start))

            timed_out = False
            try:
                stdout, stderr = process.communicate(timeout=max_wall_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_tree(process)
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except (subprocess.TimeoutExpired, ValueError, OSError):
                    stdout, stderr = b"", b""

            stdout = stdout or b""
            stderr = stderr or b""
            usage_bytes, usage_truncated = _read_usage_file(
                os.path.join(temp_dir, usage_file_name), max_usage_bytes
            )
            return HermesInvocationOutcome(
                stdout=stdout[:max_stdout_bytes],
                stdout_truncated=len(stdout) > max_stdout_bytes,
                stderr_byte_len=min(len(stderr), max_stderr_bytes),
                stderr_truncated=len(stderr) > max_stderr_bytes,
                usage_file_bytes=usage_bytes,
                usage_file_truncated=usage_truncated,
                exit_code=None if timed_out else process.returncode,
                timed_out=timed_out,
                launch_failed=False,
                duration_ms=_elapsed_ms(start),
            )
        finally:
            # Both ephemeral directories are removed on success, failure, and timeout.
            shutil.rmtree(temp_dir, ignore_errors=True)
            if managed_dir is not None:
                shutil.rmtree(managed_dir, ignore_errors=True)


def _read_usage_file(path: str, max_bytes: int) -> tuple[bytes | None, bool]:
    try:
        with open(path, "rb") as handle:
            data = handle.read(max_bytes + 1)
    except (OSError, ValueError):
        return None, False
    if len(data) > max_bytes:
        return data[:max_bytes], True
    return data, False


def _launch_failure(duration_ms: int | None = None) -> HermesInvocationOutcome:
    return HermesInvocationOutcome(
        stdout=b"",
        stdout_truncated=False,
        stderr_byte_len=0,
        stderr_truncated=False,
        usage_file_bytes=None,
        usage_file_truncated=False,
        exit_code=None,
        timed_out=False,
        launch_failed=True,
        duration_ms=duration_ms,
    )


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


# Stable repository root derived from THIS module's install location, independent of
# the caller's working directory: src/research_runtime/hermes_controlled_runtime/ ->
# three parents up is the repository root.
_REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir)
)


def is_safe_research_home(hermes_home: str) -> bool:
    """A NON-SECRET research Hermes-home locator that is safe to forward.

    Rejects a home inside the repository tree, a ``local_data`` tree, a traversal
    marker, or a relative path. The repository boundary is derived from this module's
    install location (``_REPO_ROOT``), NOT from ``os.getcwd()``, so a home inside the
    repository is rejected regardless of where the caller launched. Never inspects or
    reads any credential.
    """
    if not isinstance(hermes_home, str) or not hermes_home.strip():
        return False
    if ".." in hermes_home:
        return False
    if not os.path.isabs(hermes_home):
        return False
    resolved = os.path.realpath(hermes_home)
    if any(marker in resolved for marker in _FORBIDDEN_PATH_MARKERS):
        return False
    # Case-normalized comparison so the boundary holds on case-insensitive filesystems.
    resolved_nc = os.path.normcase(resolved)
    repo_nc = os.path.normcase(_REPO_ROOT)
    if resolved_nc == repo_nc or resolved_nc.startswith(repo_nc + os.sep):
        return False
    return True


def is_clean_research_home_control_plane(hermes_home: str) -> bool:
    """Fail-closed H1 preflight for the dedicated research HERMES_HOME (WP175I §5.5).

    Rejects a home that carries unexpected control-plane material so the ephemeral
    managed scope stays the ONLY non-default runtime policy layer for H1:

    * the home must be a safe research home (outside repo/local_data, absolute, no
      traversal) -- reuses :func:`is_safe_research_home`;
    * ``config.yaml`` must be ABSENT (exact tagged ``load_config`` reads
      ``$HERMES_HOME/config.yaml`` regardless of ``--ignore-user-config``);
    * a user ``plugins/`` directory must be absent or empty (opt-in user plugins).

    An ``.env`` / ``auth.json`` / session / cache file is permitted -- Hermes loads its
    own out-of-repo credential store from there. This inspects directory/file NAMES
    only and never reads or echoes a credential value.
    """
    if not is_safe_research_home(hermes_home):
        return False
    root = os.path.realpath(hermes_home)
    # A dedicated research home is expected to exist; a missing home cannot host a
    # credential store, so it is not a usable H1 profile.
    if not os.path.isdir(root):
        return False
    if os.path.exists(os.path.join(root, _RESEARCH_HOME_FORBIDDEN_CONFIG)):
        return False
    plugins_dir = os.path.join(root, _RESEARCH_HOME_USER_PLUGINS_DIR)
    try:
        if os.path.isdir(plugins_dir) and any(os.scandir(plugins_dir)):
            return False
    except OSError:
        return False
    return True


# Config written into the throwaway version-probe HERMES_HOME. Exact tagged
# ``hermes_cli/banner.check_for_updates(passive=True)`` reads
# ``load_config().get("updates", {}).get("check", True) is False`` and returns before
# any network access when this opt-out is present.
_UPDATE_DISABLED_CONFIG_YAML = "updates:\n  check: false\n"


def _write_update_disabled_config(hermes_home: str) -> None:
    """Write only the update-check opt-out into the probe home's ``config.yaml``."""
    with open(os.path.join(hermes_home, "config.yaml"), "w", encoding="utf-8") as handle:
        handle.write(_UPDATE_DISABLED_CONFIG_YAML)


def _minimal_env(hermes_home: str | None) -> dict[str, str]:
    """A minimal environment with no forwarded provider secrets.

    Only neutral variables are kept, and an explicit safe non-secret HERMES_HOME may
    be added so Hermes can locate its own out-of-repo credential store. No variable
    whose name looks secret-bearing is ever forwarded, and no full environment dump
    occurs.
    """
    env: dict[str, str] = {}
    for key in _NEUTRAL_ENV_KEYS:
        if key in _NEVER_FORWARD_ENV:  # pragma: no cover - defensive invariant
            continue
        value = os.environ.get(key)
        if value is not None and not _looks_secret(key):
            env[key] = value
    if hermes_home is not None and is_safe_research_home(hermes_home):
        env["HERMES_HOME"] = hermes_home
    # Defensive: a control-plane variable is never inherited even if it were somehow
    # whitelisted. HERMES_MANAGED_DIR is set later by the backend to its own ephemeral
    # managed scope; HERMES_SAFE_MODE / HERMES_ENABLE_PROJECT_PLUGINS are never set.
    for name in _NEVER_FORWARD_ENV:
        env.pop(name, None)
    return env


def _looks_secret(name: str) -> bool:
    upper = name.upper()
    return any(fragment in upper for fragment in _SECRET_ENV_FRAGMENTS)


def _kill_tree(process: "subprocess.Popen[bytes]") -> None:
    """Best-effort termination of the child process tree on timeout."""
    try:
        if os.name == "posix":
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                return
            except (ProcessLookupError, PermissionError, OSError):
                pass
        else:  # pragma: no cover - Windows-only branch
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=False,
                )
                return
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
        process.kill()
    except (OSError, ValueError):
        pass


# Retained so the external backend can be exercised in a test harness using the
# current interpreter as a harmless fake executable, never a provider process.
FAKE_EXECUTABLE_INTERPRETER = sys.executable
