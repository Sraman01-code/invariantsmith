"""Execute untrusted Python inside a locked-down container.

Every flag in DOCKER_SECURITY_FLAGS stops a specific attack; see README/CLAUDE
notes for the threat table. Nothing here should be relaxed without a test in
tests/ proving the corresponding attack is still blocked.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

IMAGE = "invariantsmith-sandbox:latest"
DEFAULT_TIMEOUT = 10.0
DEFAULT_MEMORY = "256m"
DEFAULT_PIDS = 64
DEFAULT_CPUS = "1.0"


@dataclass(frozen=True)
class SandboxResult:
    """Outcome of one sandboxed execution."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def _security_flags(memory: str, pids: int, cpus: str) -> list[str]:
    # Formatting is suppressed deliberately: one line per flag keeps each flag
    # next to the attack it stops, which is the whole point of this function.
    # fmt: off
    return [
        "--network", "none",                    # no interface at all: no exfiltration, no C2
        "--read-only",                          # immutable rootfs: nothing persists
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",  # the only writable spot
        "--user", "10001:10001",                # unprivileged UID
        "--cap-drop", "ALL",                    # no mount, no raw sockets, no chown
        "--security-opt", "no-new-privileges",  # no setuid escalation back up
        "--memory", memory,
        "--memory-swap", memory,                # equal to --memory => swap disabled
        "--pids-limit", str(pids),              # fork bombs die here
        "--cpus", cpus,
        "--ulimit", "fsize=1048576",            # 1 MiB max file write
        "--ulimit", "nofile=256:256",
    ]
    # fmt: on


def _kill(name: str) -> None:
    """Best-effort removal of a container we gave up waiting on."""
    subprocess.run(
        ["docker", "kill", name],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _make_container_readable(directory: Path) -> None:
    """Let the container's unprivileged UID traverse a staging directory.

    tempfile.mkdtemp() creates directories at 0700 - searchable only by the
    creating user - so UID 10001 inside the container cannot even open the
    payload, and fails with EACCES before any sandbox behaviour is exercised.
    Widening to 0755 is safe: the mount is read-only and the directory is
    discarded straight after the run. On Windows this is close to a no-op,
    which is precisely why the problem only shows up on Linux.
    """
    directory.chmod(0o755)
    for child in directory.iterdir():
        if child.is_file():
            child.chmod(0o644)


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else value.decode("utf-8", "replace")


def run_file(
    script: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    memory: str = DEFAULT_MEMORY,
    pids: int = DEFAULT_PIDS,
    cpus: str = DEFAULT_CPUS,
    image: str = IMAGE,
) -> SandboxResult:
    """Run one .py file in the sandbox. Its parent directory is mounted read-only.

    The directory must be traversable by UID 10001 (mode 0755 or wider). We do
    not widen it here, because silently changing permissions on a caller's
    directory is a nasty side effect; run_source handles its own staging dir.
    """
    script = Path(script).resolve()
    if not script.is_file():
        raise FileNotFoundError(script)

    # Named so we can kill it ourselves: killing the `docker run` client on the
    # host does NOT stop the container, it only detaches us from it.
    name = f"invsmith-{uuid.uuid4().hex[:12]}"

    # fmt: off
    cmd = [
        "docker", "run", "--rm", "--name", name,
        *_security_flags(memory, pids, cpus),
        # as_posix() keeps Docker Desktop happy with Windows paths (C:/Users/...).
        "--volume", f"{script.parent.as_posix()}:/work:ro",
        "--workdir", "/work",
        image,
        f"/work/{script.name}",
    ]
    # fmt: on

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill(name)
        return SandboxResult(-1, _as_text(exc.stdout), _as_text(exc.stderr), True)

    return SandboxResult(proc.returncode, proc.stdout, proc.stderr, False)


def run_source(code: str, **kwargs) -> SandboxResult:
    """Run a snippet by writing it to a throwaway directory first."""
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        script = staging / "payload.py"
        script.write_text(code, encoding="utf-8")
        _make_container_readable(staging)
        return run_file(script, **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run untrusted Python in a container.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("script", nargs="?", type=Path, help="path to a .py file")
    source.add_argument("-c", "--code", help="inline source to execute")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--memory", default=DEFAULT_MEMORY)
    parser.add_argument("--pids", type=int, default=DEFAULT_PIDS)
    parser.add_argument("--image", default=IMAGE)
    args = parser.parse_args(argv)

    opts = {
        "timeout": args.timeout,
        "memory": args.memory,
        "pids": args.pids,
        "image": args.image,
    }
    result = run_source(args.code, **opts) if args.code else run_file(args.script, **opts)

    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.timed_out:
        sys.stderr.write(f"\n[sandbox] killed after {args.timeout}s\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
