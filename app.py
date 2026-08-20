# app.py
# ============================================================
# ENTROPY - Flask Dashboard Backend
# ============================================================

import sys
import os
import json
import hashlib
import random
import threading
import logging
import time
from datetime import datetime, timedelta

# ── Fix paths FIRST before anything else ──────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ── Now import config and other modules ───────────
import config
from storage.database import connect, init_db as initialize_database
from blockchain.connector import BlockchainConnector
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# ── App Setup ──────────────────────────────────────
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "dashboard", "templates"),
            static_folder=os.path.join(BASE_DIR, "dashboard", "static"))

app.config["SECRET_KEY"] = config.SECRET_KEY
log = logging.getLogger("Dashboard")


def _api_error(message="dashboard service unavailable", status=500):
    """Return a structured error instead of disguising failures as no data."""
    return jsonify({"error": message, "status": status}), status


# Socket.IO is same-origin by default; do not permit arbitrary websites to
# subscribe to live process/file telemetry.
socketio = SocketIO(app, cors_allowed_origins=[], async_mode="threading")
bc       = BlockchainConnector()


# ═══════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════

def get_db():
    return connect()


def init_db():
    conn = initialize_database()
    conn.close()
    print("[DASHBOARD] Database ready ✅")


# ── Action Labels ──────────────────────────────────
ACTION_MAP = {
    0: "IGNORE",
    1: "ALERT",
    2: "TERMINATE",
    3: "QUARANTINE"
}


# ═══════════════════════════════════════════════════
# CORE ROUTES
# ═══════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("platform.html")


@app.route("/legacy")
def legacy_dashboard():
    return render_template("dashboard.html")


@app.route("/api/platform")
def platform():
    status = bc.get_status()
    return jsonify({
        "product": "ENTROPY",
        "tagline": "Entropy fingerprinting with an auditable response ledger",
        "edition": "Command Platform",
        "version": "2.0.0",
        "dry_run": bool(config.DRY_RUN),
        "watch_folders": config.WATCH_FOLDERS,
        "ledger_mode": status.get("mode"),
        "is_blockchain": status.get("is_blockchain", False),
        "positioning": "Purple-team range for SOC training — not an EDR replacement",
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "dashboard"})


@app.route("/api/stats")
def stats():
    try:
        db  = get_db()
        row = db.execute("""
            SELECT
                COUNT(*)                    AS total,
                SUM(CASE WHEN action >= 1
                    THEN 1 ELSE 0 END)      AS threats,
                SUM(CASE WHEN action >= 2
                    THEN 1 ELSE 0 END)      AS terminated,
                SUM(CASE WHEN action = 3
                    THEN 1 ELSE 0 END)      AS quarantined,
                ROUND(AVG(entropy), 2)      AS avg_entropy,
                ROUND(MAX(entropy), 2)      AS max_entropy
            FROM events
        """).fetchone()
        db.close()

        bc_count = bc.get_event_count()

        return jsonify({
            "total"        : row["total"]       or 0,
            "threats"      : row["threats"]     or 0,
            "terminated"   : row["terminated"]  or 0,
            "quarantined"  : row["quarantined"] or 0,
            "avg_entropy"  : row["avg_entropy"] or 0,
            "max_entropy"  : row["max_entropy"] or 0,
            "blockchain_tx": bc_count
        })
    except Exception:
        log.exception("Stats API failed")
        return _api_error()


@app.route("/api/events")
def events():
    try:
        db   = get_db()
        rows = db.execute("""
            SELECT * FROM events
            ORDER BY id DESC
            LIMIT 50
        """).fetchall()
        db.close()
        return jsonify([dict(r) for r in rows])
    except Exception:
        log.exception("Events API failed")
        return _api_error()


@app.route("/api/entropy")
def entropy_data():
    try:
        db   = get_db()
        rows = db.execute("""
            SELECT timestamp, entropy, entropy_delta, file_path
            FROM events
            ORDER BY id DESC
            LIMIT 100
        """).fetchall()
        db.close()
        return jsonify([dict(r) for r in rows])
    except Exception:
        log.exception("Entropy API failed")
        return _api_error()


@app.route("/api/alerts")
def alerts():
    try:
        db   = get_db()
        rows = db.execute("""
            SELECT * FROM events
            WHERE action >= 1
            ORDER BY id DESC
            LIMIT 20
        """).fetchall()
        db.close()
        return jsonify([dict(r) for r in rows])
    except Exception:
        log.exception("Alerts API failed")
        return _api_error()


@app.route("/api/blockchain")
def blockchain_events():
    try:
        events = bc.get_all_events()
        return jsonify(events)
    except Exception:
        log.exception("Blockchain API failed")
        return _api_error("blockchain service unavailable")


@app.route("/api/blockchain/status")
def blockchain_status():
    try:
        connected = bc.verify_chain()
        count     = bc.get_event_count()
        status = bc.get_status()
        labels = {
            "ganache": "Ganache smart contract",
            "fallback": "Local SQLite ledger (not a blockchain)",
            "none": "Offline — no ledger",
        }
        mode = status.get("mode", "none")
        return jsonify({
            "connected"      : connected,
            "is_blockchain"  : status.get("is_blockchain", connected),
            "mode"           : mode,
            "mode_label"     : labels.get(mode, mode),
            "tx_count"       : count,
            "address"        : config.CONTRACT_ADDRESS,
            "network"        : config.GANACHE_URL
        })
    except Exception:
        log.exception("Blockchain status API failed")
        return _api_error("blockchain status unavailable")


@app.route("/api/quarantine")
def quarantine_files():
    try:
        files = []
        q_dir = config.QUARANTINE_DIR

        if os.path.exists(q_dir):
            for fname in os.listdir(q_dir):
                if fname.endswith(".meta.json") or fname.endswith(".tmp"):
                    continue
                fpath = os.path.join(q_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                fstat = os.stat(fpath)
                item = {
                    "name"     : fname,
                    "size"     : fstat.st_size,
                    "modified" : datetime.fromtimestamp(
                        fstat.st_mtime
                    ).isoformat()
                }
                metadata_path = fpath + ".meta.json"
                if os.path.isfile(metadata_path):
                    try:
                        with open(metadata_path, encoding="utf-8") as metadata_file:
                            item["metadata"] = json.load(metadata_file)
                    except (OSError, ValueError):
                        item["metadata_error"] = True
                files.append(item)

        return jsonify(files)
    except Exception:
        log.exception("Quarantine API failed")
        return _api_error("quarantine service unavailable")


@app.route("/api/live")
def live_stats():
    """Super fast endpoint — only reads counts"""
    try:
        db  = get_db()
        row = db.execute("""
            SELECT
                COUNT(*)                         AS total,
                SUM(CASE WHEN action >= 1 THEN 1 ELSE 0 END) AS threats,
                SUM(CASE WHEN action >= 2 THEN 1 ELSE 0 END) AS terminated,
                SUM(CASE WHEN action  = 3 THEN 1 ELSE 0 END) AS quarantined
            FROM events
        """).fetchone()
        db.close()
        return jsonify({
            "total"      : row["total"]       or 0,
            "threats"    : row["threats"]     or 0,
            "terminated" : row["terminated"]  or 0,
            "quarantined": row["quarantined"] or 0,
        })
    except Exception:
        log.exception("Live stats API failed")
        return _api_error("live statistics unavailable")


# ═══════════════════════════════════════════════════
# WEBSOCKET — Real Time Push
# ═══════════════════════════════════════════════════

@socketio.on("connect")
def handle_connect():
    print("[DASHBOARD] Client connected")
    emit("status", {"message": "Connected to Entropy Dashboard"})


def push_updates():
    """Background thread — pushes live data every 1 second"""
    while True:
        try:
            with app.app_context():
                db  = get_db()
                row = db.execute("""
                    SELECT COUNT(*) AS total,
                           SUM(CASE WHEN action >= 1
                               THEN 1 ELSE 0 END) AS threats
                    FROM events
                """).fetchone()
                db.close()

                socketio.emit("live_update", {
                    "total"   : row["total"]   or 0,
                    "threats" : row["threats"] or 0,
                    "time"    : datetime.now().strftime("%H:%M:%S")
                })
        except Exception:
            log.exception("Live update push failed")
        time.sleep(1)


# ═══════════════════════════════════════════════════
# DQN + PROCESSES + DEMO + THREAT LEVEL
# ═══════════════════════════════════════════════════

@app.route("/api/dqn/last")
def dqn_last_decision():
    """Show persisted decision metadata, not fabricated scores."""
    try:
        db = get_db()
        row = db.execute("""
            SELECT * FROM events
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        db.close()

        if not row:
            return jsonify({
                "decision": "STANDBY",
                "confidence": 0,
                "engine": "none",
                "explanation": "",
                "factors": []
            })

        keys = row.keys()
        entropy = row["entropy"] or 0
        delta   = row["entropy_delta"] or 0
        action  = row["action"] or 0
        engine  = row["engine"] if "engine" in keys and row["engine"] else "rules"
        explanation = row["explanation"] if "explanation" in keys else ""
        confidence = row["confidence"] if "confidence" in keys and row["confidence"] is not None else 0
        if isinstance(confidence, float) and confidence <= 1:
            confidence = round(confidence * 100, 1)

        decisions = {
            0: "IGNORE",
            1: "ALERT",
            2: "TERMINATE",
            3: "TERMINATE + QUARANTINE"
        }
        outcome = row["outcome"] if "outcome" in keys and row["outcome"] else row["status"]

        factors = [
            {"name": "Engine", "value": engine, "pass": engine == "dqn"},
            {"name": "Requested action", "value": decisions.get(action, "UNKNOWN"), "pass": action >= 1},
            {"name": "Outcome", "value": outcome or "--", "pass": True},
            {"name": "Entropy", "value": f"{entropy:.2f}", "pass": entropy >= config.ENTROPY_THRESHOLD},
            {"name": "Entropy delta", "value": f"{abs(delta):.2f}", "pass": abs(delta) >= config.ENTROPY_DELTA_THRESHOLD},
        ]
        if explanation:
            factors.append({"name": "Explanation", "value": explanation[:80], "pass": True})

        return jsonify({
            "decision": decisions.get(action, "UNKNOWN"),
            "confidence": confidence,
            "engine": engine,
            "explanation": explanation,
            "factors": factors
        })
    except Exception:
        log.exception("Decision API failed")
        return _api_error("decision service unavailable")


@app.route("/api/processes")
def flagged_processes():
    """Get processes flagged by our detection"""
    try:
        db = get_db()
        rows = db.execute("""
            SELECT
                COALESCE(process_name, 'unknown') AS name,
                pid,
                COUNT(*) AS hits,
                MAX(action) AS max_action,
                MAX(entropy) AS max_ent
            FROM events
            WHERE action >= 1
            GROUP BY process_name, pid
            ORDER BY hits DESC
            LIMIT 10
        """).fetchall()
        db.close()

        return jsonify([{
            "name": r["name"] or "unknown",
            "pid": r["pid"],
            "hits": r["hits"],
            "status": "killed" if r["max_action"] >= 2 else "watch",
            "entropy": r["max_ent"] or 0
        } for r in rows])
    except Exception:
        log.exception("Process summary API failed")
        return _api_error("process summary unavailable")


@app.route("/api/demo/trigger", methods=["POST"])
def demo_trigger():
    """Refuse fabricated events; the attacker lab generates real fixture activity."""
    return jsonify({
        "status": "rejected",
        "error": "synthetic event injection is disabled; use the attacker console",
    }), 409


@app.route("/api/threat-level")
def threat_level():
    """Calculate current threat severity"""
    try:
        db = get_db()
        row = db.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN action >= 2 THEN 1 ELSE 0 END) AS critical,
                SUM(CASE WHEN action >= 1 THEN 1 ELSE 0 END) AS threats
            FROM events
            WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
        """).fetchone()
        db.close()

        total    = row["total"] or 0
        critical = row["critical"] or 0
        threats  = row["threats"] or 0

        if total == 0:
            level, label = 0, "MINIMAL"
        else:
            score = min(100, int((critical / max(total, 1)) * 100 + threats * 3))
            if score < 20:
                level, label = score, "MINIMAL"
            elif score < 50:
                level, label = score, "ELEVATED"
            elif score < 80:
                level, label = score, "HIGH"
            else:
                level, label = score, "CRITICAL"

        return jsonify({
            "level": level,
            "label": label,
            "recent_threats": threats,
            "recent_critical": critical
        })
    except Exception:
        log.exception("Threat level API failed")
        return _api_error("threat level unavailable")


@app.route("/api/folders")
def platform_folders():
    sys.path.insert(0, os.path.join(BASE_DIR, "victim_server"))
    import importlib
    victim_app = importlib.import_module("victim_server.app")
    with victim_app.app.test_request_context():
        response = victim_app.get_folders()
    return response


@app.route("/api/lab/families")
def lab_families():
    from catalog import list_families
    return jsonify(list_families())


@app.route("/api/lab/status")
def lab_status():
    sys.path.insert(0, os.path.join(BASE_DIR, "attacker_server"))
    import ransomware_engines as engines
    from attacker_server.app import victim_snapshot
    stats = engines.current_stats()
    stats["victim"] = victim_snapshot()
    stats["dry_run"] = bool(config.DRY_RUN)
    return jsonify(stats)


@app.route("/api/lab/launch", methods=["POST"])
def lab_launch():
    sys.path.insert(0, os.path.join(BASE_DIR, "attacker_server"))
    import ransomware_engines as engines
    payload = request.get_json(silent=True) or {}
    family = str(payload.get("family") or "").strip().lower()
    if family not in engines.FAMILIES:
        return jsonify({"ok": False, "error": "unknown family"}), 400
    ok, engine = engines.start_attack(family)
    if not ok:
        return jsonify({"ok": False, "error": "engine refused to start"}), 500
    return jsonify({"ok": True, "family": engine.name, "stats": engine.get_stats()})


@app.route("/api/lab/stop", methods=["POST"])
def lab_stop():
    sys.path.insert(0, os.path.join(BASE_DIR, "attacker_server"))
    import ransomware_engines as engines
    return jsonify({"ok": True, "stopped": bool(engines.stop_attack())})


@app.route("/api/lab/reset", methods=["POST"])
def lab_reset():
    sys.path.insert(0, os.path.join(BASE_DIR, "attacker_server"))
    import ransomware_engines as engines
    engines.stop_attack()
    sys.path.insert(0, os.path.join(BASE_DIR, "victim_server"))
    from create_fake_files import restore_all_files
    restore_all_files()
    from attacker_server.app import victim_snapshot
    return jsonify({"ok": True, "victim": victim_snapshot()})


# ═══════════════════════════════════════════════════
# START
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()

    # Start background push thread
    t = threading.Thread(target=push_updates, daemon=True)
    t.start()

    print(f"\n[DASHBOARD] Starting...")
    print(f"            URL     → http://localhost:{config.FLASK_PORT}")
    print(f"            DB      → {config.DB_PATH}")
    print(f"            Chain   → {config.GANACHE_URL}\n")

    socketio.run(
        app,
        host   = config.FLASK_HOST,
        port   = config.FLASK_PORT,
        debug  = False,
        use_reloader = False,
        allow_unsafe_werkzeug = True,
    )