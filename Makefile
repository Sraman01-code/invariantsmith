.PHONY: setup lint fmt test test-fast sandbox-build clean

SANDBOX_IMAGE := invariantsmith-sandbox:latest

# Always go through `python -m`: the interpreter is on PATH on every machine,
# but its Scripts/bin directory frequently is not (notably on Windows).
PY := python

# Install the project in editable mode plus dev tooling (pytest, ruff).
setup:
	$(PY) -m pip install -e ".[dev]"

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

fmt:
	$(PY) -m ruff format .

# Build the execution image. Required before the escape tests will run.
sandbox-build:
	docker build -t $(SANDBOX_IMAGE) sandbox/

# Everything, including the Docker sandbox escape tests (slow, needs Docker running).
test:
	$(PY) -m pytest

# Skip anything that needs a Docker daemon — for quick local loops.
test-fast:
	$(PY) -m pytest -m "not docker"

clean:
	python -c "import shutil,pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil; [shutil.rmtree(d, ignore_errors=True) for d in ('.pytest_cache', '.ruff_cache', 'build')]"
