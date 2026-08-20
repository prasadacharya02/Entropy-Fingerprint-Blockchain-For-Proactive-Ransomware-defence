# monitoring/pipeline_runner.py
# ============================================================
# ENTROPY - Full Pipeline Runner
#
# FLOW:
# FileMonitor → EventPipeline → AI Decision → Response
#                                    ↓
#                             Blockchain Log
#                                    ↓
#                             Dashboard DB
# ============================================================

import os
import sys
import time
import json
import hashlib
import logging
from datetime import datetime
from threading import Thread

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from monitoring.event_pipeline   import EventPipeline
from blockchain.connector        import BlockchainConnector
from response.response_module     import ProcessTerminator
from storage.database             import init_db as initialize_database
from storage.hashing               import sha256_file

# Logger must exist before the optional DQN import: the fallback path logs
# missing PyTorch/model errors during module import.
log = logging.getLogger("PipelineRunner")

# ── Optional DQN decision engine ────────────────────────
# The DQN model is the trained AI. If torch / the weights are
# unavailable, we transparently fall back to the rule-based
# engine below so the pipeline never fails to start.
try:
    from ai.dqn_model import DQNAgent
    _DQN_AVAILABLE = True
except Exception as _dqn_err:
    DQNAgent = None
    _DQN_AVAILABLE = False
    log.warning(f"[RUNNER] DQN unavailable ({_dqn_err}) — "
                f"using rule-based fallback")

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s [%(levelname)s] %(message)s",
    handlers = [
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log = logging.getLogger("PipelineRunner")

# ── Action Labels ──────────────────────────────────────────
ACTION_LABELS = {
    config.ACTION_IGNORE              : "IGNORED",
    config.ACTION_ALERT               : "ALERTED",
    config.ACTION_TERMINATE           : "TERMINATED",
    config.ACTION_TERMINATE_QUARANTINE: "TERMINATED+QUARANTINED",
}


# ============================================================
# DATABASE
# ============================================================

def init_db():
    """Create or migrate the shared events database schema."""
    return initialize_database()


def save_to_db(conn, event, action, status, outcome=None):
    """Save a processed event to the SQLite database."""
    try:
        proc     = event.get("process") or {}
        pid      = proc.get("pid")      if isinstance(proc, dict) else None
        procname = proc.get("name", "unknown") if isinstance(proc, dict) else "unknown"
        outcome = outcome or status

        conn.execute("""
            INSERT INTO events
            (timestamp, file_path, event_type, entropy,
             entropy_delta, pid, process_name, action, status,
             requested_action, outcome, dry_run)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            event.get("timestamp", datetime.now().isoformat()),
            event.get("file_path", ""),
            event.get("event_type", ""),
            event.get("entropy_overall") or 0.0,
            event.get("entropy_delta")   or 0.0,
            pid,
            procname,
            action,
            status,
            action,
            outcome,
            1 if config.DRY_RUN else 0,
        ))
        conn.commit()
    except Exception as e:
        log.error(f"[DB] Save failed: {e}")


# ============================================================
# DECISION ENGINE
# Rule-based for now — plug DQN here later
# ============================================================

def make_decision(event: dict) -> int:

    entropy   = event.get("entropy_overall") or 0.0
    delta     = abs(event.get("entropy_delta") or 0.0)
    fps       = event.get("events_per_sec")   or 0.0
    score     = event.get("threat_score")     or 0.0
    ext_chg   = event.get("ext_changed",      False)
    hi_speed  = event.get("is_suspicious_speed", False)

    # High entropy is not sufficient evidence: images, archives, videos and
    # encrypted user files are expected to be high entropy. Require a second
    # behavioral signal before taking a destructive action.
    delta_signal = delta >= config.ENTROPY_DELTA_THRESHOLD
    corroborated = ext_chg or hi_speed or delta_signal

    # Strong score plus corroborating ransomware behavior. The response layer
    # still performs its independent process-safety checks.
    if score >= 70 and corroborated:
        return config.ACTION_TERMINATE_QUARANTINE

    # A high score without corroboration is only an alert.
    if score >= 40:
        return config.ACTION_ALERT

    # Speed alone is useful for detection, but not enough for quarantine.
    if hi_speed:
        return config.ACTION_ALERT

    # Do not alert merely because a legitimate known file type is high
    # entropy. Unknown high-entropy files remain visible as alerts.
    extension = (event.get("file_extension") or "").lower()
    if entropy >= config.ENTROPY_THRESHOLD and (
        extension not in config.NORMAL_ENTROPY_RANGES
    ):
        return config.ACTION_ALERT

    return config.ACTION_IGNORE


# ============================================================
# RESPONSE EXECUTOR
# ============================================================

def execute_response(action: int,
                     event: dict,
                     bc: BlockchainConnector,
                     db_conn) -> str:

    file_path = event.get("file_path", "")
    proc      = event.get("process") or {}
    pid       = proc.get("pid")       if isinstance(proc, dict) else None
    procname  = proc.get("name", "unknown") if isinstance(proc, dict) else "unknown"

    # ── If whitelisted process, rename to simulator ──
    if procname in config.WHITELISTED_PROCESSES:
        procname = "ransomware_simulator"
        pid      = None

    entropy   = event.get("entropy_overall") or 0.0
    file_hash = event.get("file_hash", "")
    status    = ACTION_LABELS.get(action, "UNKNOWN")
    fname     = os.path.basename(file_path)
    outcome   = status

    # ── IGNORE ────────────────────────────────────
    if action == config.ACTION_IGNORE:
        log.info(f"  [OK]     {fname} | H={entropy:.2f}")
        save_to_db(db_conn, event, action, status, outcome)
        return status

    # ── ALERT ─────────────────────────────────────
    if action == config.ACTION_ALERT:
        log.warning(f"  [ALERT]  {fname} | H={entropy:.2f}")
        outcome = status

    # ── TERMINATE ─────────────────────────────────
    if action == config.ACTION_TERMINATE:
        log.warning(f"  [KILL]   {fname} | H={entropy:.2f}")
        killed = _terminate_process(pid, procname, proc)
        outcome = "DRY_RUN_TERMINATE" if config.DRY_RUN else (
            "TERMINATED" if killed else "TERMINATE_REFUSED"
        )

    # ── TERMINATE + QUARANTINE ────────────────────
    if action == config.ACTION_TERMINATE_QUARANTINE:
        log.warning(f"  [THREAT] {fname} | H={entropy:.2f}")
        killed = _terminate_process(pid, procname, proc)
        q_result = _quarantine_file(file_path, event=event, action=action)
        log.warning(f"  [ACTION] Quarantine result: {q_result}")
        outcome = q_result if isinstance(q_result, str) else status
        if config.DRY_RUN:
            outcome = "DRY_RUN_QUARANTINE"
        elif not killed and q_result != "QUARANTINED":
            outcome = "RESPONSE_PARTIAL"

    save_to_db(db_conn, event, action, status, outcome)

    # ── Blockchain log ────────────────────────────
    if action >= config.ACTION_ALERT:
        try:
            fingerprint = file_hash or hashlib.sha256(
                file_path.encode()
            ).hexdigest()

            bc.log_event({
                "fingerprint" : fingerprint[:64],
                "threat_type" : "ransomware",
                "pid"         : pid or 0,
                "entropy"     : entropy,
                "process"     : procname,
                "file_path"   : file_path,
                "action"      : str(action),
                "status"      : status
            })
        except Exception as e:
            log.error(f"  [BLOCKCHAIN] Failed: {e}")

    return status


def _terminate_process(pid, procname: str, process_info: dict | None = None):
    """Terminate only a freshly revalidated process identity.

    Filesystem attribution is best-effort. If the monitor cannot provide a
    process name, this function deliberately refuses to terminate anything.
    """
    if not isinstance(process_info, dict):
        log.warning("  [SAFE] No verified process identity; termination refused")
        return False

    expected_pid = process_info.get("pid")
    expected_name = process_info.get("name")
    expected_create_time = process_info.get("create_time")
    if not process_info.get("identity_verified", False):
        log.warning(
            "  [SAFE] Process attribution is best-effort; "
            "automatic termination refused"
        )
        return False
    if expected_pid != pid or not expected_name or expected_name != procname:
        log.warning("  [SAFE] Process identity changed; termination refused")
        return False

    try:
        result = ProcessTerminator().terminate(
            int(pid),
            process_name=expected_name,
            expected_create_time=expected_create_time,
        )
        if not result["success"]:
            log.warning("  [SAFE] Termination refused: %s", result["message"])
        return result["success"]
    except Exception as exc:
        log.error("  [TERMINATE] Safety layer failed: %s", exc)
        return False


def _quarantine_file(file_path: str, event: dict | None = None,
                     action: int | None = None):
    """Move a suspicious file and persist a complete sidecar record."""
    import shutil
    import stat

    if not os.path.isfile(file_path):
        log.warning(f"  [QUARANTINE] Already moved: {os.path.basename(file_path)}")
        return "FILE_ALREADY_MOVED"

    try:
        os.makedirs(config.QUARANTINE_DIR, exist_ok=True)
        file_stat = os.stat(file_path)
        sha256 = sha256_file(file_path)
        original_path = os.path.abspath(file_path)
        original_name = os.path.basename(file_path)
        q_name = f"{sha256[:16]}_{original_name}"
        q_path = os.path.join(config.QUARANTINE_DIR, q_name)

        if os.path.exists(q_path):
            q_name = f"{sha256[:16]}_{int(time.time_ns())}_{original_name}"
            q_path = os.path.join(config.QUARANTINE_DIR, q_name)

        shutil.move(file_path, q_path)
        os.chmod(q_path, stat.S_IRUSR)

        metadata = {
            "schema_version": 1,
            "quarantined_at": datetime.now().isoformat(),
            "original_path": original_path,
            "original_name": original_name,
            "quarantine_path": os.path.abspath(q_path),
            "fingerprint": sha256,
            "size_bytes": file_stat.st_size,
            "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "mode": stat.S_IMODE(file_stat.st_mode),
            "action": action,
            "event": event or {},
        }
        metadata_path = q_path + ".meta.json"
        temporary_path = metadata_path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
        os.replace(temporary_path, metadata_path)
        os.chmod(metadata_path, stat.S_IRUSR)

        log.warning(f"  [QUARANTINE] ✅ → {q_name}")
        return "QUARANTINED"

    except PermissionError:
        log.error("  [QUARANTINE] ❌ Permission denied")
        return "PERMISSION_DENIED"

    except Exception as e:
        log.error(f"  [QUARANTINE] ❌ {e}")
        return "FAILED"


# ============================================================
# DECISION ENGINE
# Combines the trained DQN (primary) with the rule-based engine
# (fallback). Both produce an action in the same 0-3 space.
# ============================================================

class DecisionEngine:
    """
    Wraps the trained DQN agent and falls back to the
    rule-based detector when the model cannot be loaded.
    """

    def __init__(self):
        self.agent = None
        self.using_dqn = False

        if _DQN_AVAILABLE and DQNAgent is not None:
            try:
                self.agent = DQNAgent()
                model_path = os.path.join(
                    config.AI_DIR, "dqn_weights.pth"
                )
                if os.path.exists(model_path):
                    if self.agent.load(model_path):
                        self.using_dqn = True
                        log.info("[DECISION] DQN model loaded ✅")
                    else:
                        log.warning("[DECISION] DQN load failed — "
                                    "falling back to rules")
                else:
                    log.warning("[DECISION] No dqn_weights.pth — "
                                "using rule-based engine")
            except Exception as e:
                log.warning(f"[DECISION] DQN init error ({e}) — rules")

    def decide(self, event: dict) -> dict:
        """
        Return a decision dict compatible with the response layer:
        { 'action', 'action_name', 'confidence', 'explanation' }
        """
        if self.using_dqn:
            try:
                decision = self.agent.decide(event)
                return {
                    "action"      : int(decision.get("action", 0)),
                    "action_name" : decision.get("action_name", "IGNORE"),
                    "confidence"  : float(decision.get("confidence", 0.0)),
                    "explanation" : decision.get("explanation", ""),
                }
            except Exception as e:
                log.warning(f"[DECISION] DQN inference error ({e}) — "
                            f"falling back to rules")

        action = make_decision(event)
        return {
            "action"      : action,
            "action_name" : ACTION_LABELS.get(action, "UNKNOWN"),
            "confidence"  : 1.0 if action >= config.ACTION_ALERT else 0.0,
            "explanation" : "Rule-based detector",
        }


# ============================================================
# PIPELINE RUNNER
# ============================================================

class PipelineRunner:
    """
    Connects all components and runs the full pipeline.
    """

    def __init__(self):
        log.info("[RUNNER] Initializing pipeline...")

        # Core pipeline
        self.pipeline = EventPipeline()

        # Decision engine (DQN + rule fallback)
        self.engine = DecisionEngine()

        # Database
        self.db = init_db()
        log.info("[RUNNER] Database ready ✅")

        # Blockchain
        self.bc = BlockchainConnector()

        # Stats
        self.stats = {
            "total"      : 0,
            "ignored"    : 0,
            "alerted"    : 0,
            "terminated" : 0,
            "quarantined": 0,
        }

    def start(self):
        """Start the full pipeline."""
        print()
        print("=" * 60)
        print("  ENTROPY - Full Pipeline Active")
        print("=" * 60)
        print(f"  Watching   : {len(config.WATCH_FOLDERS)} folders")
        print(f"  Dashboard  : http://localhost:{config.DASHBOARD_PORT}")
        print(f"  Blockchain : {config.GANACHE_URL}")
        print(f"  DB         : {config.DB_PATH}")
        print(f"  AI Engine  : "
              f"{'DQN (trained)' if self.engine.using_dqn else 'Rule-based'}")
        print(f"  Dry-run    : {config.DRY_RUN}")
        print("=" * 60)
        print()

        # Register our callback with the pipeline
        self.pipeline.register_ai_callback(self._on_analyzed_event)

        # Start the event pipeline
        self.pipeline.start()

        log.info("[RUNNER] Pipeline running — waiting for events...")

    def _on_analyzed_event(self, event: dict):
        """
        Called by the pipeline for every analyzed event.

        This is where detection + response happens.
        """
        self.stats["total"] += 1

        # ── Make decision ──────────────────────────
        decision = self.engine.decide(event)
        action   = decision["action"]

        # ── Execute response ───────────────────────
        status = execute_response(
            action, event, self.bc, self.db
        )

        # ── Update stats ───────────────────────────
        if action == config.ACTION_IGNORE:
            self.stats["ignored"] += 1
        elif action == config.ACTION_ALERT:
            self.stats["alerted"] += 1
        elif action == config.ACTION_TERMINATE:
            self.stats["terminated"] += 1
        elif action == config.ACTION_TERMINATE_QUARANTINE:
            self.stats["terminated"]  += 1
            self.stats["quarantined"] += 1

    def stop(self):
        self.pipeline.stop()
        # Give queued ledger writes a chance to complete before the runner
        # exits. This prevents daemon-thread writes from being silently lost.
        self.bc.flush(timeout=10.0)
        log.info("[RUNNER] Stopped.")

    def print_stats(self):
        print()
        print("=" * 40)
        print("  PIPELINE STATS")
        print("=" * 40)
        for k, v in self.stats.items():
            print(f"  {k:12} : {v}")
        print("=" * 40)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:
        import colorama
        colorama.init()
    except ImportError:
        pass

    runner = PipelineRunner()
    runner.start()

    try:
        while True:
            time.sleep(30)
            runner.print_stats()

    except KeyboardInterrupt:
        print()
        runner.stop()
        runner.print_stats()