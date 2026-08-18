.PHONY: setup lint fmt test test-fast clean

# Install the project in editable mode plus dev tooling (pytest, ruff).
setup:
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

fmt:
	ruff format .

# Everything, including the Docker sandbox escape tests (slow, needs Docker running).
test:
	pytest

# Skip anything that needs a Docker daemon — for quick local loops.
test-fast:
	pytest -m "not docker"

clean:
	python -c "import shutil,pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil; [shutil.rmtree(d, ignore_errors=True) for d in ('.pytest_cache', '.ruff_cache', 'build')]"
