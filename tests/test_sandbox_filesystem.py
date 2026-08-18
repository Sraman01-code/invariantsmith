"""Attack test: untrusted code must not write anywhere that persists.

The second test is the one that matters most for correctness of our results:
if a payload can write into the mounted source directory, it can rewrite the
very function we are analysing, and every number we report becomes a lie.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from _helpers import assert_contained, requires_sandbox
from sandbox.run import run_file, run_source

ROOTFS_PAYLOAD = """
print("PAYLOAD_STARTED", flush=True)
try:
    with open("/escaped.txt", "w") as handle:
        handle.write("pwned")
except OSError as exc:
    print("BLOCKED:", type(exc).__name__, exc, flush=True)
else:
    print("ESCAPED", flush=True)
"""

MOUNT_PAYLOAD = """
print("PAYLOAD_STARTED", flush=True)
try:
    with open("/work/escaped.txt", "w") as handle:
        handle.write("pwned")
except OSError as exc:
    print("BLOCKED:", type(exc).__name__, exc, flush=True)
else:
    print("ESCAPED", flush=True)
"""


@pytest.mark.docker
@requires_sandbox
def test_cannot_write_to_container_root_filesystem():
    """--read-only makes the whole rootfs immutable, so nothing persists."""
    result = run_source(ROOTFS_PAYLOAD, timeout=60)
    assert_contained(result, what="write to container rootfs")


@pytest.mark.docker
@requires_sandbox
def test_cannot_write_into_mounted_host_directory():
    """The :ro bind mount must hold: check the host filesystem, not just stdout."""
    # Not pytest's tmp_path: it lives under /tmp/pytest-of-<user>, which pytest
    # creates at 0700. The container's UID needs execute permission on every
    # ancestor, so we stage directly under /tmp (1777) and widen our own dir.
    with tempfile.TemporaryDirectory() as tmp:
        host_dir = Path(tmp)
        script = host_dir / "payload.py"
        script.write_text(MOUNT_PAYLOAD, encoding="utf-8")
        host_dir.chmod(0o755)
        script.chmod(0o644)

        result = run_file(script, timeout=60)

        assert_contained(result, what="write into the mounted host directory")
        # The strongest assertion available: the file is genuinely not on the host.
        assert not (host_dir / "escaped.txt").exists(), (
            "SANDBOX ESCAPE: payload created a file on the host filesystem"
        )
        assert script.read_text(encoding="utf-8") == MOUNT_PAYLOAD, (
            "SANDBOX ESCAPE: payload modified the source file under analysis"
        )
