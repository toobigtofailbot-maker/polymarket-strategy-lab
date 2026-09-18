"""External-process boundary for the controlled Hermes research runtime (WP175H).

Two backends implement one protocol:

  * :class:`FakeHermesBackend` -- deterministic, makes no process and no network
    call; used by every unit/CI test.
  * :class:`ExternalHermesCliBackend` -- runs a caller-supplied Hermes executable
    with an argv list only (never a shell, never a command string), from a fresh
    empty temporary working directory that never mounts the repository, a
    ``local_data`` path, or a user home path; captures stdout/stderr under hard
    byte caps; enforces a hard wall-clock timeout that kills the child process tree
    where platform mechanics permit; and deletes the temporary directory on
    teardown. It records no secret-bearing environment or raw stderr in evidence
    and does not discover, read, validate, inject, or log provider credentials.
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
class HermesInvocationOutcome:
    """Sanitized outcome of one backend invocation. Carries no raw stderr text."""

    stdout: bytes
    stdout_truncated: bool
    stderr_byte_len: int
    stderr_truncated: bool
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

    def invoke(
        self,
        *,
        argv: Sequence[str],
        query_bytes: bytes,
        query_file_name: str,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        max_wall_seconds: int,
    ) -> HermesInvocationOutcome: ...


# ---------------------------------------------------------------------------
# Fake backend
# ---------------------------------------------------------------------------


class FakeHermesBackend:
    """Deterministic backend that performs zero process and zero network calls."""

    def __init__(self, outcomes: Sequence[HermesInvocationOutcome]) -> None:
        if not outcomes:
            raise ValueError("FakeHermesBackend requires at least one outcome")
        self._outcomes = tuple(outcomes)
        self.call_count = 0
        self.recorded_argv: list[tuple[str, ...]] = []
        self.recorded_query_bytes: list[bytes] = []
        self.recorded_query_file_names: list[str] = []

    @classmethod
    def from_transcript(
        cls,
        transcript: bytes,
        *,
        exit_code: int = 0,
        stderr_byte_len: int = 0,
    ) -> "FakeHermesBackend":
        return cls(
            [
                HermesInvocationOutcome(
                    stdout=transcript,
                    stdout_truncated=False,
                    stderr_byte_len=stderr_byte_len,
                    stderr_truncated=False,
                    exit_code=exit_code,
                    timed_out=False,
                    launch_failed=False,
                    duration_ms=0,
                )
            ]
        )

    def invoke(
        self,
        *,
        argv: Sequence[str],
        query_bytes: bytes,
        query_file_name: str,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        max_wall_seconds: int,
    ) -> HermesInvocationOutcome:
        index = min(self.call_count, len(self._outcomes) - 1)
        self.call_count += 1
        self.recorded_argv.append(tuple(argv))
        self.recorded_query_bytes.append(bytes(query_bytes))
        self.recorded_query_file_names.append(query_file_name)
        outcome = self._outcomes[index]
        # Enforce the caller's stdout cap deterministically even for the fake.
        if len(outcome.stdout) > max_stdout_bytes:
            return dataclasses.replace(
                outcome, stdout=outcome.stdout[:max_stdout_bytes], stdout_truncated=True
            )
        return outcome


# ---------------------------------------------------------------------------
# External CLI backend
# ---------------------------------------------------------------------------

# Working-directory prefixes that must never be supplied to Hermes as its cwd.
_FORBIDDEN_CWD_MARKERS = ("local_data",)


class ExternalHermesCliBackend:
    """Runs an external Hermes CLI via argv only from an ephemeral empty cwd."""

    def invoke(
        self,
        *,
        argv: Sequence[str],
        query_bytes: bytes,
        query_file_name: str,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        max_wall_seconds: int,
    ) -> HermesInvocationOutcome:
        argv = list(argv)
        if not argv:
            return _launch_failure()
        if "/" in query_file_name or "\\" in query_file_name or ".." in query_file_name:
            return _launch_failure()

        temp_dir = tempfile.mkdtemp(prefix="hermes_oneshot_")
        # Structural isolation: an ephemeral mkdtemp cwd never mounts the repo, a
        # local_data path, or a user home path.
        resolved = os.path.realpath(temp_dir)
        home = os.path.realpath(os.path.expanduser("~"))
        if resolved == home or any(marker in resolved for marker in _FORBIDDEN_CWD_MARKERS):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return _launch_failure()

        start = time.monotonic()
        try:
            query_path = os.path.join(temp_dir, query_file_name)
            with open(query_path, "wb") as handle:
                handle.write(query_bytes)

            popen_kwargs: dict[str, object] = {
                "cwd": temp_dir,
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                # A minimal, secret-free environment: no provider secrets are
                # discovered, injected, or forwarded by this project code.
                "env": _minimal_env(),
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
            stdout_truncated = len(stdout) > max_stdout_bytes
            stderr_truncated = len(stderr) > max_stderr_bytes
            return HermesInvocationOutcome(
                stdout=stdout[:max_stdout_bytes],
                stdout_truncated=stdout_truncated,
                stderr_byte_len=min(len(stderr), max_stderr_bytes),
                stderr_truncated=stderr_truncated,
                exit_code=None if timed_out else process.returncode,
                timed_out=timed_out,
                launch_failed=False,
                duration_ms=_elapsed_ms(start),
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def _launch_failure(duration_ms: int | None = None) -> HermesInvocationOutcome:
    return HermesInvocationOutcome(
        stdout=b"",
        stdout_truncated=False,
        stderr_byte_len=0,
        stderr_truncated=False,
        exit_code=None,
        timed_out=False,
        launch_failed=True,
        duration_ms=duration_ms,
    )


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _minimal_env() -> dict[str, str]:
    """A minimal environment with no forwarded secrets.

    Only PATH (to locate the executable) and a small set of neutral locale/temp
    variables are kept. No provider secret or trading credential is forwarded.
    """
    env: dict[str, str] = {}
    for key in ("PATH", "SystemRoot", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"):
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    return env


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
