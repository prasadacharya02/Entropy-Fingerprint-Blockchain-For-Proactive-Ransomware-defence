"""Central configuration for the ENTROPY ransomware lab.

Values can be overridden through environment variables or a local ``.env``
file.  Paths supplied as relative values are resolved from the repository root.
The checked-in ``.env.example`` documents the supported runtime settings.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
BASE_DIR = str(BASE_PATH)  # Backwards-compatible string used by existing modules.

try:
    from dotenv import load_dotenv
except ImportError:  # The health check reports the missing optional loader.
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(BASE_PATH / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be one of: true, false, 1, 0, yes, no")


def _env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    value = default if raw is None else int(raw)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _env_float(name: str, default: float, *, minimum: float | None = None) -> float:
    raw = os.getenv(name)
    value = default if raw is None else float(raw)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _resolve_path(value: str | Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BASE_PATH / path
    return str(path.resolve())


def _env_path(name: str, default: Path) -> str:
    return _resolve_path(os.getenv(name) or default)


# Project folders
MONITORING_DIR = str(BASE_PATH / "monitoring")
ENTROPY_DIR = str(BASE_PATH / "entropy")
AI_DIR = str(BASE_PATH / "ai")
RESPONSE_DIR = str(BASE_PATH / "response")
BLOCKCHAIN_DIR = str(BASE_PATH / "blockchain")
DASHBOARD_DIR = str(BASE_PATH / "dashboard")
DATA_DIR = str(BASE_PATH / "data")
TRAINING_DATA_DIR = str(BASE_PATH / "data" / "training")
TESTING_DATA_DIR = str(BASE_PATH / "data" / "testing")
QUARANTINE_DIR = _env_path("ENTROPY_QUARANTINE_DIR", BASE_PATH / "quarantine_storage")
# Runtime files
LOG_FILE = _env_path("ENTROPY_LOG_FILE", BASE_PATH / "logs" / "entropy_system.log")
LOG_DIR = str(Path(LOG_FILE).parent)
DB_PATH = _env_path("ENTROPY_DB_PATH", BASE_PATH / "entropy.db")


def ensure_runtime_directories() -> None:
    """Create ignored runtime directories required by existing components."""
    directories = {
        Path(LOG_FILE).parent,
        Path(DB_PATH).parent,
        Path(QUARANTINE_DIR),
        Path(TRAINING_DATA_DIR),
        Path(TESTING_DATA_DIR),
    }
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Existing modules open log files while importing, so directory initialization is
# intentionally centralized here until the application factory work in Day 2.
ensure_runtime_directories()

# Folders to watch. Keep the default constrained to generated simulator data.
_watch_folders = os.getenv("ENTROPY_WATCH_FOLDERS")
if _watch_folders:
    WATCH_FOLDERS = [
        _resolve_path(item.strip())
        for item in _watch_folders.split(os.pathsep)
        if item.strip()
    ]
else:
    WATCH_FOLDERS = [TESTING_DATA_DIR]

# Processes that must never be terminated by the response layer.
WHITELISTED_PROCESSES = [
    "System",
    "Registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
]

# Detection thresholds
ENTROPY_THRESHOLD = _env_float("ENTROPY_THRESHOLD", 7.5, minimum=0.0)
ENTROPY_DELTA_THRESHOLD = _env_float("ENTROPY_DELTA_THRESHOLD", 2.0, minimum=0.0)
FILES_PER_SECOND_THRESHOLD = _env_float(
    "ENTROPY_FILES_PER_SECOND_THRESHOLD", 3.0, minimum=0.0
)
EVENT_DEDUP_WINDOW_SECONDS = _env_float(
    "ENTROPY_EVENT_DEDUP_WINDOW_SECONDS", 0.25, minimum=0.0
)
SAMPLE_SIZE_BYTES = _env_int("ENTROPY_SAMPLE_SIZE_BYTES", 65536, minimum=1)

# Blockchain settings
GANACHE_URL = os.getenv("ENTROPY_GANACHE_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS = os.getenv("ENTROPY_CONTRACT_ADDRESS", "").strip()
WALLET_ADDRESS = os.getenv("ENTROPY_WALLET_ADDRESS", "").strip()
ACCOUNT_INDEX = _env_int("ENTROPY_ACCOUNT_INDEX", 0, minimum=0)
BLOCKCHAIN_FALLBACK = _env_bool("ENTROPY_BLOCKCHAIN_FALLBACK", True)

# Dashboard settings
DASHBOARD_HOST = os.getenv("ENTROPY_DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = _env_int("ENTROPY_DASHBOARD_PORT", 5000, minimum=1)

# Victim read-only UI. Bind to all interfaces for containers/live previews;
# destructive attacker controls remain separately protected.
VICTIM_HOST = os.getenv("ENTROPY_VICTIM_HOST", "0.0.0.0")
VICTIM_PORT = _env_int("ENTROPY_VICTIM_PORT", 8002, minimum=1)
PUBLIC_VICTIM_URL = os.getenv("ENTROPY_PUBLIC_VICTIM_URL", "").strip()
PUBLIC_DASHBOARD_URL = os.getenv("ENTROPY_PUBLIC_DASHBOARD_URL", "").strip()
PUBLIC_ATTACKER_URL = os.getenv("ENTROPY_PUBLIC_ATTACKER_URL", "").strip()
DEBUG_MODE = _env_bool("ENTROPY_DEBUG", False)
FLASK_HOST = DASHBOARD_HOST
FLASK_PORT = DASHBOARD_PORT
SECRET_KEY = os.getenv("ENTROPY_SECRET_KEY", "entropy-local-development-only")
# Control routes are local-only by default. Set this token when the lab must be
# controlled remotely; clients must send Authorization: Bearer <token>.
CONTROL_TOKEN = os.getenv("ENTROPY_CONTROL_TOKEN", "").strip()

# DQN settings
STATE_SIZE = 10
ACTION_SIZE = 4
LEARNING_RATE = 0.001
GAMMA = 0.95
EPSILON_START = 1.0
EPSILON_END = 0.01
EPSILON_DECAY = 0.995
MEMORY_SIZE = 10000
BATCH_SIZE = 64
TARGET_UPDATE = 10

# Actions
ACTION_IGNORE = 0
ACTION_ALERT = 1
ACTION_TERMINATE = 2
ACTION_TERMINATE_QUARANTINE = 3

# Expected entropy ranges by file extension
NORMAL_ENTROPY_RANGES = {
    ".txt": (3.0, 5.5),
    ".doc": (6.0, 7.5),
    ".docx": (6.0, 7.5),
    ".pdf": (6.5, 7.8),
    ".jpg": (7.0, 7.8),
    ".jpeg": (7.0, 7.8),
    ".png": (6.5, 7.5),
    ".mp4": (7.0, 7.9),
    ".zip": (7.5, 8.0),
    ".exe": (5.0, 7.2),
    ".py": (4.0, 6.0),
    ".csv": (4.0, 6.0),
    ".xlsx": (6.0, 7.5),
    ".dat": (4.0, 6.5),
}
