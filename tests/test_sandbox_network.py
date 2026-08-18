"""Attack test: untrusted code must not reach the network.

If these fail, a payload can exfiltrate anything it reads and call home.
Both payloads exit 0 either way on purpose - we assert on printed sentinels,
not on the exit code, so a crash for an unrelated reason cannot fake a pass.
"""

from __future__ import annotations

import pytest

from _helpers import assert_contained, requires_sandbox
from sandbox.run import run_source

TCP_PAYLOAD = """
import socket
print("PAYLOAD_STARTED", flush=True)
try:
    conn = socket.create_connection(("1.1.1.1", 53), timeout=5)
    conn.close()
except OSError as exc:
    print("BLOCKED:", type(exc).__name__, exc, flush=True)
else:
    print("ESCAPED", flush=True)
"""

DNS_PAYLOAD = """
import socket
print("PAYLOAD_STARTED", flush=True)
try:
    addr = socket.gethostbyname("example.com")
except OSError as exc:
    print("BLOCKED:", type(exc).__name__, exc, flush=True)
else:
    print("ESCAPED", addr, flush=True)
"""


@pytest.mark.docker
@requires_sandbox
def test_cannot_open_outbound_tcp_connection():
    """Direct connection to a known-reachable IP, bypassing DNS entirely."""
    result = run_source(TCP_PAYLOAD, timeout=60)
    assert_contained(result, what="outbound TCP connection")


@pytest.mark.docker
@requires_sandbox
def test_cannot_resolve_dns():
    """DNS is its own exfiltration channel: data can be smuggled in hostnames."""
    result = run_source(DNS_PAYLOAD, timeout=60)
    assert_contained(result, what="DNS resolution")
