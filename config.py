<<<<<<< HEAD
# config.py
# ============================================================
# ENTROPY - Central Configuration
# ============================================================

from __future__ import annotations
=======
"""Central configuration for the ENTROPY ransomware lab.

Values can be overridden through environment variables or a local ``.env``
file.  Paths supplied as relative values are resolved from the repository root.
The checked-in ``.env.example`` documents the supported runtime settings.
"""

from __future__ import annotations

>>>>>>> 85a04faf32325b1e508a3812f9a640202c9cea72
import os
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
<<<<<<< HEAD
BASE_DIR = str(BASE_PATH)

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_PATH / ".env")
except ImportError:
    pass

_TRUE_VALUES  = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}

def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(
        f"Invalid boolean value for {name}: {value!r} "
        f"(expected true/false, yes/no, 1/0, or on/off)"
    )

def _env_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    try:
        value = default if raw is None else int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {name}: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{name}={value} is below the minimum of {minimum}")
    return value

def _env_float(name: str, default: float, minimum: float | None = None) -> float:
    raw = os.getenv(name)
    try:
        value = default if raw is None else float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid float value for {name}: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{name}={value} is below the minimum of {minimum}")
    return value

def _resolve_path(value: str) -> str:
    """Resolve *value* against the repository root when it is relative."""
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return str(path)
    return str(BASE_PATH / path)

# ── Project Folders ──────────────────────────────────────────
MONITORING_DIR    = str(BASE_PATH / "monitoring")
ENTROPY_DIR       = str(BASE_PATH / "entropy")
AI_DIR            = str(BASE_PATH / "ai")
RESPONSE_DIR      = str(BASE_PATH / "response")
BLOCKCHAIN_DIR    = str(BASE_PATH / "blockchain")
DASHBOARD_DIR     = str(BASE_PATH / "dashboard")
DATA_DIR          = str(BASE_PATH / "data")
TRAINING_DATA_DIR = str(BASE_PATH / "data" / "training")
TESTING_DATA_DIR  = str(BASE_PATH / "data" / "testing")
VICTIM_USER_FILES = str(BASE_PATH / "victim_server" / "user_files")

# ── Install-time quarantine folder ───────────────────────────
# The quarantine store is created by the operator when the shield
# is installed: point ENTROPY_QUARANTINE_DIR at the folder you want
# protected files moved to (absolute or relative to the repo root).
# It is created automatically if it does not exist.
_quarantine_raw = os.getenv("ENTROPY_QUARANTINE_DIR", "").strip()
QUARANTINE_DIR    = (str(_resolve_path(_quarantine_raw))
                     if _quarantine_raw
                     else str(BASE_PATH / "quarantine_storage"))
BACKUP_DIR        = str(BASE_PATH / "backup_storage")
REPORTS_DIR       = str(BASE_PATH / "reports")

# ── Runtime Files & Directories ──────────────────────────────
LOG_FILE = str(BASE_PATH / "logs" / "entropy_system.log")
LOG_DIR  = str(Path(LOG_FILE).parent)
DB_PATH  = str(BASE_PATH / "entropy.db")

for d in [LOG_DIR, QUARANTINE_DIR, TRAINING_DATA_DIR, TESTING_DATA_DIR, VICTIM_USER_FILES, BACKUP_DIR, REPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Watch Folders ────────────────────────────────────────────
# By default the monitor only watches the sandboxed test-data folder.
# Set ENTROPY_WATCH_FOLDERS (comma-separated, relative to the repo root)
# to watch additional directories — lab.py uses this to point the
# detector at the controlled victim fixtures.

def _watch_folders() -> list[str]:
    raw = os.getenv("ENTROPY_WATCH_FOLDERS")
    if raw is None or not raw.strip():
        return [TESTING_DATA_DIR]
    folders = [
        _resolve_path(part.strip())
        for part in raw.split(",")
        if part.strip()
    ]
    return folders or [TESTING_DATA_DIR]

WATCH_FOLDERS = _watch_folders()

WHITELISTED_PROCESSES = [
    "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "svchost.exe", "systemd", "init", "kthreadd",
    "code.exe", "explorer.exe"
]

# ── Self-kill safety gate ────────────────────────────────────
# Command-line fragments that identify THIS software (defender
# pipeline, dashboards, lab services). The response layer refuses to
# terminate any process whose command line matches one of these, no
# matter what file-event attribution says. Real deployments should
# add their own product's module names here.
DEFENDER_TOOLING_MARKERS = (
    "pipeline_runner",
    "entropy_system",
    "lab.py",
    "victim_server",
    "attacker_server/app",
    "attacker_server\\app",
    "dashboard",
    "app.py",
    "main.py",
)

# ── Event Pipeline & Monitoring Config ───────────────────────
EVENT_DEDUP_WINDOW_SECONDS = _env_float("EVENT_DEDUP_WINDOW_SECONDS", 1.0, minimum=0.0)
EVENT_QUEUE_SIZE           = _env_int("EVENT_QUEUE_SIZE", 10000, minimum=1)
EVENT_BATCH_SIZE           = _env_int("EVENT_BATCH_SIZE", 50, minimum=1)

# ── Detection & Entropy Engine Thresholds ────────────────────
ENTROPY_THRESHOLD          = _env_float("ENTROPY_THRESHOLD", 6.8, minimum=0.0)
ENTROPY_DELTA_THRESHOLD    = _env_float("ENTROPY_DELTA_THRESHOLD", 2.0, minimum=0.0)
FILES_PER_SECOND_THRESHOLD = _env_float("ENTROPY_FILES_PER_SECOND_THRESHOLD", 3.0, minimum=0.0)

# ── Campaign (multi-file) escalation ───────────────────────
# A single high-entropy file is NOT proof of an attack — video
# writes, zip archives and photo imports are legitimately
# high-entropy. Ransomware, however, is by definition multi-file:
# one threat touches many files within seconds. The decision layer
# therefore tracks recent suspicious files (encrypted-data
# signature: entropy >= ENTROPY_THRESHOLD plus behavioural
# corroboration — an entropy jump >= ENTROPY_DELTA_THRESHOLD or a
# rename to a disguise extension) and confirms a CAMPAIGN when
# CAMPAIGN_MIN_FILES distinct files qualify within
# CAMPAIGN_WINDOW_SECONDS. On confirmation the response escalates
# to terminate + quarantine for the newest file, and a sweep
# quarantines + restores the remaining campaign files. This is what
# stops a slow, realistic attack within the first few files.
CAMPAIGN_ENABLED        = _env_bool("ENTROPY_CAMPAIGN_ENABLED", True)
CAMPAIGN_WINDOW_SECONDS = _env_float("ENTROPY_CAMPAIGN_WINDOW_SECONDS", 15.0, minimum=1.0)
CAMPAIGN_MIN_FILES      = _env_int("ENTROPY_CAMPAIGN_MIN_FILES", 2, minimum=2)
SAMPLE_SIZE_BYTES          = _env_int("ENTROPY_SAMPLE_SIZE_BYTES", 65536, minimum=1)

# ── Decision Engine Selection ────────────────────────────────
# "auto" / "rules" (default) = the deterministic rule engine — the
# measured 0-false-quarantine safety bar, and the default even when
# trained models exist. "rf" = the Random Forest second classifier
# (calibrated, SHAP-explained risk; opt-in high-recall mode).
# "dqn" = the trained DQN (opt-in). A requested engine that cannot
# load falls back to rules, always labelled as such.
AI_ENGINE = os.getenv("ENTROPY_AI_ENGINE", "auto").strip().lower()

# ── Backup & Recovery ────────────────────────────────────────
# Versions kept per file in the backup store (oldest evicted).
BACKUP_MAX_VERSIONS_PER_FILE = _env_int("ENTROPY_BACKUP_MAX_VERSIONS", 10, minimum=1)

# ── Blockchain Settings ──────────────────────────────────────
GANACHE_URL         = os.getenv("ENTROPY_GANACHE_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS    = os.getenv("ENTROPY_CONTRACT_ADDRESS", "0x7d5fd3ad0ffbeaAf9df76d1CF74058b5E14ddC1D").strip()
WALLET_ADDRESS      = os.getenv("ENTROPY_WALLET_ADDRESS", "0x4769fFb50b3bE30331056C2f174A0eaa64436E5d").strip()
ACCOUNT_INDEX         = _env_int("ENTROPY_ACCOUNT_INDEX", 0, minimum=0)
BLOCKCHAIN_FALLBACK = _env_bool("ENTROPY_BLOCKCHAIN_FALLBACK", True)

# ── Federated Threat-Fingerprint Exchange ─────────────────────
# Shared registry of confirmed threat fingerprints — the "have we seen
# this before?" layer the pitch claims. Every node writes the SHA-256 of
# each file it contains as a confirmed threat and can query prior
# sightings of any fingerprint. In this lab it is one SQLite file opened
# by several simulated nodes; in a deployment it is the network. A
# fingerprint seen by >= EXCHANGE_CONFIRM_THRESHOLD *independent* nodes
# counts as a known threat (see blockchain/fingerprint_exchange.py).
THREAT_EXCHANGE_DB         = str(BASE_PATH / "blockchain" / "exchange.db")
EXCHANGE_NODE_ID           = os.getenv("ENTROPY_NODE_ID", "").strip()
EXCHANGE_CONFIRM_THRESHOLD = _env_int("ENTROPY_EXCHANGE_CONFIRM_THRESHOLD", 2, minimum=2)
# Master switch (tests and single-node offline use disable it).
EXCHANGE_ENABLED           = _env_bool("ENTROPY_EXCHANGE", True)

# ── Web Servers & Hosts ──────────────────────────────────────
DASHBOARD_HOST      = os.getenv("ENTROPY_DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT      = _env_int("ENTROPY_DASHBOARD_PORT", 5000, minimum=1)
FLASK_HOST          = DASHBOARD_HOST
FLASK_PORT          = DASHBOARD_PORT
PUBLIC_DASHBOARD_URL= f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"

# The victim explorer is a normal web app; bind it wherever the operator
# wants to reach it. Default is loopback (safe); the lab launcher sets
# 0.0.0.0 so a remote browser can open "This PC".
VICTIM_HOST         = os.getenv("ENTROPY_VICTIM_HOST", "127.0.0.1")
VICTIM_PORT         = _env_int("ENTROPY_VICTIM_PORT", 5001)
PUBLIC_VICTIM_URL   = f"http://{VICTIM_HOST}:{VICTIM_PORT}"

ATTACKER_HOST       = "0.0.0.0"
ATTACKER_PORT       = 8001
PUBLIC_ATTACKER_URL = f"http://127.0.0.1:{ATTACKER_PORT}"

DEBUG_MODE          = False
SECRET_KEY          = os.getenv("ENTROPY_SECRET_KEY", "entropy-local-development-only")
DRY_RUN             = _env_bool("ENTROPY_DRY_RUN", False)
# The lab UI (attacker console) authenticates control routes with this
# bearer token. lab.py sets ENTROPY_CONTROL_TOKEN; CONTROL_TOKEN is kept
# as a legacy alias. Leave both unset to fall back to loopback-only.
CONTROL_TOKEN       = (os.getenv("ENTROPY_CONTROL_TOKEN")
                       or os.getenv("CONTROL_TOKEN")
                       or "").strip()

# ── Privileged Vault Access (Victim UI) ──────────────────────
VAULT_USER          = os.getenv("ENTROPY_VAULT_USER", "victim_user")
VAULT_PIN           = os.getenv("ENTROPY_VAULT_PIN", "1234")
VAULT_SESSION_HOURS = _env_int("ENTROPY_VAULT_SESSION_HOURS", 8, minimum=0)

# ── Reinforcement Learning (DQN) ─────────────────────────────
STATE_SIZE     = 10
ACTION_SIZE    = 4
LEARNING_RATE  = 0.001
GAMMA          = 0.95
EPSILON_START  = 1.0
EPSILON_END    = 0.01
EPSILON_DECAY  = 0.995
MEMORY_SIZE    = 10000
BATCH_SIZE     = 64
TARGET_UPDATE  = 10

ACTION_IGNORE               = 0
ACTION_ALERT                = 1
ACTION_TERMINATE            = 2
ACTION_TERMINATE_QUARANTINE = 3

NORMAL_ENTROPY_RANGES = {
    ".txt": (3.0, 5.5),   ".doc": (6.0, 7.5),   ".docx": (6.0, 7.5),
    ".pdf": (6.5, 7.8),   ".jpg": (7.0, 7.8),   ".jpeg": (7.0, 7.8),
    ".png": (6.5, 7.5),   ".mp4": (7.0, 7.9),   ".zip": (7.5, 8.0),
    ".exe": (5.0, 7.2),   ".py": (4.0, 6.0),    ".csv": (4.0, 6.0),
    ".xlsx": (6.0, 7.5),  ".dat": (4.0, 6.5),
}
=======
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
    "systemd",
    "init",
    "kthreadd",
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
# Destructive terminate/quarantine is simulated unless explicitly disabled.
DRY_RUN = _env_bool("ENTROPY_DRY_RUN", True)

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
>>>>>>> 85a04faf32325b1e508a3812f9a640202c9cea72
