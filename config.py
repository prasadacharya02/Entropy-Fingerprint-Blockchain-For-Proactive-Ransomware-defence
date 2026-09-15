# config.py
# ============================================================
# ENTROPY - Central Configuration
# ============================================================

from __future__ import annotations
import os
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
BASE_DIR = str(BASE_PATH)

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_PATH / ".env")
except ImportError:
    pass

def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None: return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw is None else int(raw)

def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw is None else float(raw)

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
QUARANTINE_DIR    = str(BASE_PATH / "quarantine_storage")

# ── Runtime Files & Directories ──────────────────────────────
LOG_FILE = str(BASE_PATH / "logs" / "entropy_system.log")
LOG_DIR  = str(Path(LOG_FILE).parent)
DB_PATH  = str(BASE_PATH / "entropy.db")

for d in [LOG_DIR, QUARANTINE_DIR, TRAINING_DATA_DIR, TESTING_DATA_DIR, VICTIM_USER_FILES]:
    os.makedirs(d, exist_ok=True)

# ── Watch Folders ────────────────────────────────────────────
WATCH_FOLDERS = [
    os.path.join(BASE_DIR, "victim_server", "user_files"),
    os.path.join(BASE_DIR, "data", "testing")
]

WHITELISTED_PROCESSES = [
    "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "svchost.exe", "systemd", "init", "kthreadd",
    "code.exe", "explorer.exe"
]

# ── Event Pipeline & Monitoring Config ───────────────────────
EVENT_DEDUP_WINDOW_SECONDS = _env_float("EVENT_DEDUP_WINDOW_SECONDS", 1.0)
EVENT_QUEUE_SIZE           = _env_int("EVENT_QUEUE_SIZE", 10000)
EVENT_BATCH_SIZE           = _env_int("EVENT_BATCH_SIZE", 50)

# ── Detection & Entropy Engine Thresholds ────────────────────
ENTROPY_THRESHOLD          = _env_float("ENTROPY_THRESHOLD", 6.8)
ENTROPY_DELTA_THRESHOLD    = _env_float("ENTROPY_DELTA_THRESHOLD", 2.0)
FILES_PER_SECOND_THRESHOLD = _env_float("ENTROPY_FILES_PER_SECOND_THRESHOLD", 3.0)
SAMPLE_SIZE_BYTES          = _env_int("ENTROPY_SAMPLE_SIZE_BYTES", 65536)

# ── Blockchain Settings ──────────────────────────────────────
GANACHE_URL         = os.getenv("ENTROPY_GANACHE_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS    = os.getenv("ENTROPY_CONTRACT_ADDRESS", "0x7d5fd3ad0ffbeaAf9df76d1CF74058b5E14ddC1D").strip()
WALLET_ADDRESS      = os.getenv("ENTROPY_WALLET_ADDRESS", "0x4769fFb50b3bE30331056C2f174A0eaa64436E5d").strip()
ACCOUNT_INDEX       = _env_int("ENTROPY_ACCOUNT_INDEX", 0)
BLOCKCHAIN_FALLBACK = _env_bool("ENTROPY_BLOCKCHAIN_FALLBACK", False)

# ── Web Servers & Hosts ──────────────────────────────────────
DASHBOARD_HOST      = os.getenv("ENTROPY_DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT      = _env_int("ENTROPY_DASHBOARD_PORT", 5000)
FLASK_HOST          = DASHBOARD_HOST
FLASK_PORT          = DASHBOARD_PORT
PUBLIC_DASHBOARD_URL= f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"

VICTIM_HOST         = "127.0.0.1"
VICTIM_PORT         = 5001
PUBLIC_VICTIM_URL   = f"http://{VICTIM_HOST}:{VICTIM_PORT}"

ATTACKER_HOST       = "0.0.0.0"
ATTACKER_PORT       = 8001
PUBLIC_ATTACKER_URL = f"http://127.0.0.1:{ATTACKER_PORT}"

DEBUG_MODE          = False
SECRET_KEY          = os.getenv("ENTROPY_SECRET_KEY", "entropy-local-development-only")
DRY_RUN             = _env_bool("ENTROPY_DRY_RUN", False)
CONTROL_TOKEN       = os.getenv("CONTROL_TOKEN", "demo_secret_token_123")

# ── Privileged Vault Access (Victim UI) ──────────────────────
VAULT_USER          = os.getenv("ENTROPY_VAULT_USER", "victim_user")
VAULT_PIN           = os.getenv("ENTROPY_VAULT_PIN", "1234")
VAULT_SESSION_HOURS = _env_int("ENTROPY_VAULT_SESSION_HOURS", 8)

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