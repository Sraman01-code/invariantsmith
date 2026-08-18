# Execution environment for untrusted Python.
#
# Deliberately boring: a stock interpreter, no build tools, no package manager
# use at runtime, no third-party packages. Every capability we do not install is
# one a payload cannot abuse. Runtime isolation lives in sandbox/run.py — this
# image only has to be a small, non-root, dependency-free place to land.
FROM python:3.12-slim

# An unprivileged identity baked into the image, so the image is safe by default
# even if someone forgets --user on the command line. nologin shell: this account
# is for running a script, never for an interactive session.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin runner

# HOME points at /tmp because the root filesystem is mounted read-only at runtime
# and /tmp is the only writable location (a small, noexec tmpfs). Libraries that
# insist on a cache directory land there and get discarded when the container dies.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    HOME=/tmp

# Payload is bind-mounted read-only at /work by sandbox/run.py.
WORKDIR /work

USER runner

ENTRYPOINT ["python"]
