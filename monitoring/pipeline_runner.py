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
from response.response_module     import FileQuarantine, ProcessTerminator
from response.backup_manager     import BackupManager
from response.forensic_report    import generate_report
from storage.database             import init_db as initialize_database

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


# ============================================================
# FEDERATED THREAT-FINGERPRINT EXCHANGE
# ============================================================

# The node's shared view of the exchange. The canonical lazy singleton
# lives in blockchain.fingerprint_exchange so the flag collection in
# defense_guard and the response sharing here use the same store.
from blockchain.fingerprint_exchange import get_exchange  # noqa: F401


def save_to_db(conn, event, action, status, outcome=None, decision=None,
               restore_result=None):
    """Save a processed event to the SQLite database."""
    try:
        proc     = event.get("process") or {}
        pid      = proc.get("pid")      if isinstance(proc, dict) else None
        procname = proc.get("name", "unknown") if isinstance(proc, dict) else "unknown"
        outcome = outcome or status
        decision = decision or {}
        q_values = decision.get("q_values")
        conn.execute("""
            INSERT INTO events
            (timestamp, file_path, event_type, entropy,
             entropy_delta, pid, process_name, action, status,
             requested_action, outcome, restore_result, dry_run,
             engine, confidence, explanation, q_values)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            restore_result,
            1 if config.DRY_RUN else 0,
            decision.get("engine") or "rules",
            float(decision.get("confidence") or 0.0),
            decision.get("explanation") or "",
            json.dumps(q_values) if q_values is not None else None,
        ))
        conn.commit()
    except Exception as e:
        log.error(f"[DB] Save failed: {e}")


# ============================================================
# DECISION ENGINE
# Rule-based for now — plug DQN here later
# ============================================================

def make_decision(event: dict) -> int:

    # ── Hard-confirmation signals ────────────────────────────
    # A dropped ransom note, an attacker destroying the recovery
    # capability (backup store / Shadow Copies / services), or a
    # fingerprint that >= EXCHANGE_CONFIRM_THRESHOLD *independent*
    # nodes have already contained as a confirmed threat, is a
    # confirmed incident on its own — no local signal required.
    if (event.get("ransom_note") or event.get("defense_tamper")
            or event.get("known_threat_confirmed")):
        return config.ACTION_TERMINATE_QUARANTINE

    entropy   = event.get("entropy_overall") or 0.0
    delta     = abs(event.get("entropy_delta") or 0.0)
    fps       = event.get("events_per_sec")   or 0.0
    score     = event.get("threat_score")     or 0.0
    ext_chg   = event.get("ext_changed",      False)
    hi_speed  = event.get("is_suspicious_speed", False)

    # A fingerprint seen by a SINGLE node is corroboration, not
    # confirmation: it weighs the score but can never quarantine
    # alone (a poisoned or buggy node must not be able to seed the
    # exchange into destroying clean files everywhere).
    if event.get("known_threat"):
        score = min(100.0, score + 25.0)

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
                     db_conn, decision: dict | None = None,
                     backup: "BackupManager | None" = None,
                     exchange=None) -> str:

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

    terminate_result  = None
    quarantine_result = None
    restore_result    = None

    # ── IGNORE ───────────────────────────────────
    if action == config.ACTION_IGNORE:
        log.info(f"  [OK]     {fname} | H={entropy:.2f}")
        save_to_db(db_conn, event, action, status, outcome, decision)
        return status

    # ── ALERT ─────────────────────────────────────
    if action == config.ACTION_ALERT:
        log.warning(f"  [ALERT]  {fname} | H={entropy:.2f}")
        outcome = status

    # ── TERMINATE ─────────────────────────────────
    if action == config.ACTION_TERMINATE:
        log.warning(f"  [KILL]   {fname} | H={entropy:.2f}")
        killed = _terminate_process(pid, procname, proc)
        terminate_result = "TERMINATED" if killed else "TERMINATE_REFUSED"
        outcome = "DRY_RUN_TERMINATE" if config.DRY_RUN else (
            "TERMINATED" if killed else "TERMINATE_REFUSED"
        )

    # ── TERMINATE + QUARANTINE ────────────────────
    if action == config.ACTION_TERMINATE_QUARANTINE:
        log.warning(f"  [THREAT] {fname} | H={entropy:.2f}")
        killed = _terminate_process(pid, procname, proc)
        terminate_result = "TERMINATED" if killed else "TERMINATE_REFUSED"
        quarantine_result = _quarantine_file(file_path, event=event, action=action)
        log.warning(f"  [ACTION] Quarantine result: {quarantine_result}")
        outcome = quarantine_result if isinstance(quarantine_result, str) else status
        if config.DRY_RUN:
            outcome = "DRY_RUN_QUARANTINE"
        elif not killed and quarantine_result != "QUARANTINED":
            outcome = "RESPONSE_PARTIAL"

        # ── RECOVERY: restore the last known-good version ──
        # Dry-run: the lab attack engine is one-shot, so simulating the
        # restore is safe. Live mode: only restore once the file is
        # contained (quarantined or already gone) so the attacker cannot
        # re-encrypt the restored copy in place.
        if backup is not None:
            contained = config.DRY_RUN or quarantine_result in (
                "QUARANTINED", "FILE_ALREADY_MOVED", "DRY_RUN_QUARANTINE"
            )
            if not contained:
                restore_result = "RESTORE_SKIPPED"
                log.warning("  [RESTORE] Skipped: file not contained "
                            "(quarantine failed)")
            else:
                try:
                    r = backup.restore(file_path, event=event)
                    if r.get("success") and r.get("restored"):
                        restore_result = "RESTORED"
                    elif r.get("success") and r.get("dry_run"):
                        restore_result = "DRY_RUN_RESTORE"
                    else:
                        restore_result = "RESTORE_FAILED"
                    log.warning(f"  [RESTORE] {restore_result}: "
                                f"{r.get('message')}")
                except Exception as e:
                    restore_result = "RESTORE_FAILED"
                    log.error(f"  [RESTORE] {e}")
        if restore_result:
            outcome = f"{outcome}+{restore_result}"

    # ── FORENSIC REPORT for every incident ────────
    if action >= config.ACTION_ALERT:
        try:
            report_path = generate_report(
                event, decision or {}, {
                    "requested_action":     action,
                    "outcome":              outcome,
                    "dry_run":              bool(config.DRY_RUN),
                    "terminate":            terminate_result,
                    "quarantine":           quarantine_result,
                    "restore":              restore_result,
                    "blockchain_reference": file_hash or None,
                }
            )
            if report_path:
                log.info(f"  [REPORT] Forensic report → "
                         f"{os.path.basename(report_path)}")
        except Exception as e:
            log.error(f"  [REPORT] Generation failed: {e}")

    save_to_db(db_conn, event, action, status, outcome, decision,
               restore_result)

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

    # ── Federated exchange: share the confirmed threat ──────
    # Only CONFIRMED threats (quarantine) are shared — an alert is a
    # suspicion, not a shared fact. And only when we hold the file's
    # real content hash: a path hash or a missing file (e.g. the
    # already-deleted target of a defense-tamper event) must never be
    # published as a threat fingerprint.
    if action == config.ACTION_TERMINATE_QUARANTINE and file_hash:
        # An injected exchange (benchmark / multi-node simulation) is an
        # explicit opt-in and always registers. The canonical store is
        # gated by config.EXCHANGE_ENABLED (tests / single-node offline).
        if exchange is None and not config.EXCHANGE_ENABLED:
            store = None
        else:
            store = exchange if exchange is not None else get_exchange()
        if store is not None:
            try:
                rec = store.register(
                    file_hash,
                    threat_type="ransomware",
                    file_extension=os.path.splitext(file_path)[1].lower(),
                    file_size=event.get("file_size") or 0,
                    evidence=(decision or {}).get("explanation", ""),
                )
                log.warning(
                    f"  [EXCHANGE] fingerprint {file_hash[:12]}… shared "
                    f"(sightings={rec['sightings']}, "
                    f"sources={len(rec['sources'])})"
                )
            except Exception as e:
                log.error(f"  [EXCHANGE] Registration failed: {e}")

    # Return the detailed outcome (e.g. "DRY_RUN_QUARANTINE+DRY_RUN_RESTORE"),
    # not just the action label — callers and the dashboard rely on it.
    return outcome


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
                     action: int | None = None) -> str:
    """Quarantine a suspicious file via the shared response layer.

    Uses FileQuarantine (response/response_module.py) so the pipeline and
    the response tests share one dry-run-aware implementation. In dry-run
    mode the file is NEVER moved; the DRY_RUN outcome is recorded by the
    caller. Returns a string status: QUARANTINED, DRY_RUN_QUARANTINE,
    FILE_ALREADY_MOVED, PERMISSION_DENIED, or FAILED.
    """
    try:
        result = FileQuarantine().quarantine(file_path, event=event)
    except Exception as e:
        log.error(f"  [QUARANTINE] ❌ {e}")
        return "FAILED"

    if config.DRY_RUN and result.get("success"):
        log.info("  [DRY-RUN] Quarantine simulated — file left in place")
        return "DRY_RUN_QUARANTINE"

    if not result.get("success"):
        message = (result.get("message") or "").lower()
        if "not found" in message:
            log.warning(f"  [QUARANTINE] Already moved: {os.path.basename(file_path)}")
            return "FILE_ALREADY_MOVED"
        if "permission" in message or "denied" in message:
            log.error("  [QUARANTINE] ❌ Permission denied")
            return "PERMISSION_DENIED"
        log.error(f"  [QUARANTINE] ❌ {result.get('message')}")
        return "FAILED"

    log.warning(f"  [QUARANTINE] ✅ → {os.path.basename(result.get('quarantine_path') or file_path)}")
    return "QUARANTINED"


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
                    "q_values"    : decision.get("q_values"),
                    "engine"      : "dqn",
                }
            except Exception as e:
                log.warning(f"[DECISION] DQN inference error ({e}) — "
                            f"falling back to rules")

        action = make_decision(event)
        explanation = "Rule-based detector"
        if event.get("ransom_note"):
            explanation += " | RANSOM NOTE: " + "; ".join(
                event.get("ransom_note_evidence") or []
            )
        if event.get("defense_tamper"):
            explanation += " | DEFENSE TAMPER: " + "; ".join(
                event.get("defense_tamper_evidence") or []
            )
        if event.get("known_threat"):
            marker = "KNOWN THREAT (CONFIRMED BY EXCHANGE): " \
                if event.get("known_threat_confirmed") else \
                "KNOWN THREAT (CORROBORATED BY EXCHANGE): "
            explanation += " | " + marker + (
                event.get("known_threat_evidence") or ""
            )
        elif event.get("reason"):
            explanation += f" | {event['reason']}"
        return {
            "action"      : action,
            "action_name" : ACTION_LABELS.get(action, "UNKNOWN"),
            "confidence"  : 1.0 if action >= config.ACTION_ALERT else 0.0,
            "explanation" : explanation,
            "q_values"    : None,
            "engine"      : "rules",
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

        # Backup & recovery store
        self.backup = BackupManager()

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

        # ── Seed the backup store with the pre-watch state of the
        # protected estate so files that existed before monitoring
        # started are restorable after an attack. ──
        try:
            baselined = 0
            for folder in config.WATCH_FOLDERS:
                baselined += self.backup.snapshot_directory(
                    folder, source="startup_baseline"
                )
            backup_stats = self.backup.stats()
            log.info(f"[RUNNER] Backup baseline: {baselined} file(s) captured "
                     f"({backup_stats['files_restorable']} restorable)")
        except Exception as e:
            log.warning(f"[RUNNER] Backup baseline failed: {e}")

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

        # ── Capture the current file state for recovery ──
        # Additive (reads the file, writes only to backup_storage/),
        # so it runs in every mode. Clean versions (entropy below
        # threshold) become restore candidates; dirty ones are kept
        # for forensics but are never restorable.
        file_path = event.get("file_path", "")
        if file_path:
            try:
                self.backup.capture(file_path, event=event)
            except Exception as e:
                log.warning(f"[BACKUP] Capture failed for {file_path}: {e}")

        # ── Make decision ──────────────────────────
        decision = self.engine.decide(event)
        action   = decision["action"]

        # ── Execute response ───────────────────────
        status = execute_response(
            action, event, self.bc, self.db, decision, backup=self.backup
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