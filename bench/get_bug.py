"""Fetch one BugsInPy bug so we can look at it by hand.

Deliberately fetch-only. This script never installs dependencies and never runs
a project's tests: `pip install -r requirements.txt` executes that project's
setup.py as you, on your machine. Running downloaded code belongs in the
container (see sandbox/run.py), not here.

    python -m bench.get_bug --list
    python -m bench.get_bug --project PySnooper --bug 1
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BUGSINPY_URL = "https://github.com/soarsmu/BugsInPy.git"
DATA = Path(__file__).resolve().parent / "_data"
CATALOGUE = DATA / "BugsInPy"
CHECKOUTS = DATA / "checkouts"

DEFAULT_PROJECT = "PySnooper"  # small, few dependencies: the easiest first repro
DEFAULT_BUG = "1"


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=True,
    )


def _parse_info(path: Path) -> dict[str, str]:
    """BugsInPy metadata files are shell-style key="value" lines."""
    info: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            info[key.strip()] = value.strip().strip('"')
    return info


def ensure_catalogue() -> Path:
    """Shallow-clone the BugsInPy metadata repo once."""
    if CATALOGUE.exists():
        return CATALOGUE
    DATA.mkdir(parents=True, exist_ok=True)
    print(f"Cloning BugsInPy catalogue into {CATALOGUE} ...")
    _git("clone", "--depth", "1", BUGSINPY_URL, str(CATALOGUE))
    return CATALOGUE


def list_projects() -> None:
    projects = sorted(p for p in (ensure_catalogue() / "projects").iterdir() if p.is_dir())
    for project in projects:
        bugs = list((project / "bugs").glob("*"))
        print(f"{project.name:<16} {len(bugs):>3} bugs")


def checkout_bug(project: str, bug_id: str) -> None:
    catalogue = ensure_catalogue()
    bug_dir = catalogue / "projects" / project / "bugs" / bug_id
    if not bug_dir.is_dir():
        sys.exit(f"No such bug: {project}/{bug_id}. Try --list.")

    info = _parse_info(bug_dir / "bug.info")
    # Note the inconsistent naming in BugsInPy: bug.info but project.info.
    project_info = _parse_info(catalogue / "projects" / project / "project.info")
    url = project_info["github_url"]
    buggy = info["buggy_commit_id"]

    target = CHECKOUTS / f"{project}-{bug_id}"
    if not target.exists():
        target.mkdir(parents=True)
        print(f"Fetching {project} at buggy commit {buggy[:10]} ...")
        _git("init", "-q", cwd=target)
        _git("remote", "add", "origin", url, cwd=target)
        try:
            # Fetch just the one commit rather than the project's whole history.
            _git("fetch", "-q", "--depth", "1", "origin", buggy, cwd=target)
        except subprocess.CalledProcessError:
            print("  single-commit fetch refused by server, falling back to full history")
            _git("fetch", "-q", "origin", cwd=target)
        _git("checkout", "-q", buggy, cwd=target)

    run_test = (bug_dir / "run_test.sh").read_text(encoding="utf-8").strip()

    print(f"\nBug:            {project}/{bug_id}")
    print(f"Buggy commit:   {buggy}")
    print(f"Fixed commit:   {info.get('fixed_commit_id', '?')}")
    print(f"Needs Python:   {info.get('python_version', '?')}")
    print(f"Failing test:   {info.get('test_file', '?')}")
    print(f"Checked out at: {target}")
    print(f"\nThe failing test is:\n    {run_test}")
    print(
        "\nNOT run for you. This project's requirements.txt executes arbitrary\n"
        "code on install. Use a throwaway environment, or wait for the sandboxed\n"
        "runner. See the module docstring."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch one BugsInPy bug.")
    parser.add_argument("--list", action="store_true", help="list projects and bug counts")
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--bug", default=DEFAULT_BUG)
    args = parser.parse_args(argv)

    if args.list:
        list_projects()
    else:
        checkout_bug(args.project, args.bug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
