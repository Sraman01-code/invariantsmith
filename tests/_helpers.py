"""Shared gating and assertions for the sandbox attack tests.

Lives in tests/ as a plain module rather than conftest.py because the attack
tests import from it directly; pytest puts this directory on sys.path.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from sandbox.run import IMAGE

# Sentinels the attack payloads print. Asserting on STARTED is the positive
# control: without it, a typo in the payload would make an escape test "pass".
STARTED = "PAYLOAD_STARTED"
ESCAPED = "ESCAPED"


def _sandbox_blocker() -> str | None:
    """Return a reason the sandbox tests cannot run, or None if they can."""
    if shutil.which("docker") is None:
        return "docker is not on PATH"
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", IMAGE],
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "docker daemon is not responding"
    if proc.returncode != 0:
        return f"image {IMAGE} not built - run: make sandbox-build"
    return None


_BLOCKER = _sandbox_blocker()

requires_sandbox = pytest.mark.skipif(_BLOCKER is not None, reason=str(_BLOCKER))


def assert_contained(result, *, what: str) -> None:
    """Assert the payload actually ran and did not escape."""
    assert STARTED in result.stdout, (
        f"payload never ran, so this test proves nothing about {what}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert ESCAPED not in result.stdout, (
        f"SANDBOX ESCAPE: {what} succeeded. stdout={result.stdout!r}"
    )
