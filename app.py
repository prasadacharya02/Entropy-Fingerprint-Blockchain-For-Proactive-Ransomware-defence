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
from flask import Flask, render_template, jsonify
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
    return render_template("dashboard.html")


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
        return jsonify({
            "connected"      : connected,
            "is_blockchain"  : status.get("is_blockchain", connected),
            "mode"           : status.get("mode", "none"),
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
    """Show reasoning for last threat"""
    try:
        db = get_db()
        row = db.execute("""
            SELECT * FROM events
            WHERE action >= 1
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        db.close()

        if not row:
            return jsonify({
                "decision": "STANDBY",
                "confidence": 0,
                "factors": []
            })

        entropy = row["entropy"] or 0
        delta   = row["entropy_delta"] or 0
        action  = row["action"] or 0
        path    = row["file_path"] or ""
        ext_chg = path.endswith(('.locked', '.encrypted', '.enc'))

        decisions = {
            0: "IGNORE",
            1: "ALERT",
            2: "TERMINATE",
            3: "TERMINATE + QUARANTINE"
        }

        # Factors that determined the decision
        factors = [
            {
                "name": "Entropy above threshold (7.5)",
                "value": f"{entropy:.2f}",
                "pass": entropy >= 7.5
            },
            {
                "name": "Entropy delta significant",
                "value": f"{abs(delta):.2f}",
                "pass": abs(delta) >= 1.5
            },
            {
                "name": "Extension changed",
                "value": "YES" if ext_chg else "NO",
                "pass": ext_chg
            },
            {
                "name": "File type suspicious",
                "value": path.split('.')[-1][:10] if '.' in path else '--',
                "pass": ext_chg
            },
            {
                "name": "Process unsigned",
                "value": "UNKNOWN",
                "pass": True
            }
        ]

        # Confidence based on how many factors triggered
        passed = sum(1 for f in factors if f["pass"])
        confidence = min(99, 60 + (passed * 10))

        return jsonify({
            "decision": decisions.get(action, "UNKNOWN"),
            "confidence": confidence,
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
    """Inject fake ransomware events for demo"""
    try:
        db = get_db()

        demo_files = [
            "financial_report_Q3.xlsx",
            "customer_database.db",
            "employee_records.docx",
            "product_designs.pdf",
            "source_code.zip"
        ]

        base_time = datetime.now()

        for i, fname in enumerate(demo_files):
            # Space events 1 second apart for a realistic timeline
            event_time = base_time + timedelta(seconds=i)
            fake_path  = f"C:\\Users\\demo\\Documents\\{fname}.locked"
            entropy    = round(random.uniform(7.85, 7.99), 4)
            delta      = round(random.uniform(2.5, 3.5), 4)
            fake_pid   = random.randint(1000, 9999)

            db.execute("""
                INSERT INTO events
                (timestamp, file_path, event_type, entropy, entropy_delta,
                 pid, process_name, action, status)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                event_time.isoformat(),
                fake_path,
                "RENAMED",
                entropy,
                delta,
                fake_pid,
                "ransomware_demo.exe",
                3,
                "TERMINATED+QUARANTINED"
            ))

        db.commit()
        db.close()

        return jsonify({"status": "ok", "injected": len(demo_files)})
    except Exception:
        log.exception("Demo trigger API failed")
        return _api_error("demo trigger failed")


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
        use_reloader = False
    )