"""Dependency health check for the ENTROPY ransomware lab.

This command intentionally does not start any service.  It verifies that the
packages needed by the current multi-process demo are importable and returns a
non-zero exit code when setup is incomplete.
"""

from __future__ import annotations

from importlib import metadata, util
from typing import NamedTuple


class Dependency(NamedTuple):
    distribution: str
    module: str
    purpose: str
    required: bool


DEPENDENCIES = (
    Dependency("watchdog", "watchdog", "filesystem monitoring", True),
    Dependency("psutil", "psutil", "process inspection and response", True),
    Dependency("numpy", "numpy", "feature extraction and model training", True),
    Dependency("flask", "flask", "dashboard and victim web applications", True),
    Dependency("python-dotenv", "dotenv", ".env configuration loading", True),
    Dependency("flask-socketio", "flask_socketio", "dashboard live updates", True),
    Dependency("torch", "torch", "optional DQN inference and training", False),
    Dependency("web3", "web3", "optional Ganache integration; SQLite fallback is available", False),
    Dependency("eventlet", "eventlet", "optional Socket.IO server runtime", False),
    Dependency("colorama", "colorama", "optional cross-platform terminal output", False),
)


def inspect_dependencies() -> list[tuple[Dependency, str | None]]:
    """Return each dependency and its installed version, or ``None``."""
    results = []
    for dependency in DEPENDENCIES:
        if util.find_spec(dependency.module) is None:
            results.append((dependency, None))
            continue
        try:
            version = metadata.version(dependency.distribution)
        except metadata.PackageNotFoundError:
            version = "installed"
        results.append((dependency, version))
    return results


def main() -> int:
    print("=" * 62)
    print("  ENTROPY - environment health check")
    print("=" * 62)

    results = inspect_dependencies()
    missing_required = []
    optional_missing = []
    for dependency, version in results:
        if version is None:
            if dependency.required:
                missing_required.append(dependency)
                label = "MISSING"
            else:
                optional_missing.append(dependency)
                label = "OPTIONAL"
            print(f"[{label}] {dependency.distribution:<18} {dependency.purpose}")
        else:
            print(f"[OK]      {dependency.distribution:<18} {version}")

    print("-" * 62)
    if missing_required:
        print(
            f"Environment incomplete: {len(missing_required)} required package(s) missing."
        )
        print("Install them with:  python -m pip install -r requirements.txt")
        return 1

    if optional_missing:
        print(
            f"Environment ready with {len(optional_missing)} optional package(s) unavailable."
        )
        print("Fallbacks remain active where supported (rules/local ledger).")
    else:
        print("Environment ready. See README.md for the lab startup commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
