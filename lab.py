"""Single-process launcher for the ENTROPY ransomware lab.

Starts the detection pipeline, SOC dashboard, victim explorer, and attacker
console together, then shuts them down on Ctrl+C.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

SERVICES = (
    ("pipeline", [PYTHON, str(ROOT / "monitoring" / "pipeline_runner.py")]),
    ("dashboard", [PYTHON, str(ROOT / "app.py")]),
    ("victim", [PYTHON, str(ROOT / "victim_server" / "app.py")]),
    ("attacker", [PYTHON, str(ROOT / "attacker_server" / "app.py")]),
)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("ENTROPY_WATCH_FOLDERS", "victim_server/user_files")
    env.setdefault("ENTROPY_DASHBOARD_HOST", "0.0.0.0")
    env.setdefault("ENTROPY_DRY_RUN", "true")
    env.setdefault("ENTROPY_CONTROL_TOKEN", "entropy-lab")
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def main() -> int:
    fixtures = ROOT / "victim_server" / "create_fake_files.py"
    if not (ROOT / "victim_server" / "user_files").exists():
        subprocess.check_call([PYTHON, str(fixtures), "--clean"], cwd=ROOT)

    print("=" * 60)
    print("  ENTROPY Command Platform")
    print("  SOC       : http://127.0.0.1:5000")
    print("  Attacker  : http://127.0.0.1:8001")
    print("  Victim PC : http://127.0.0.1:8002")
    print("  Watching  : victim_server/user_files")
    print("  Dry-run   : on  |  control token set for remote lab UI")
    print("=" * 60)

    env = _env()
    processes: list[subprocess.Popen] = []
    try:
        for name, command in SERVICES:
            proc = subprocess.Popen(command, cwd=ROOT, env=env)
            processes.append(proc)
            print(f"[lab] started {name} pid={proc.pid}")

        while True:
            for name, proc in zip((s[0] for s in SERVICES), processes):
                code = proc.poll()
                if code is not None:
                    print(f"[lab] {name} exited with {code}")
                    return code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[lab] shutting down...")
        return 0
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
        deadline = time.time() + 8
        for proc in processes:
            remaining = max(0.1, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[lab] stopped")


if __name__ == "__main__":
    raise SystemExit(main())
