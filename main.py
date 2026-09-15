# main.py
# ============================================================
# ENTROPY - Real-Time Interception Orchestrator
# ============================================================

import os
import sys
import time
import json
import signal
import argparse
import logging
import threading
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config

BANNER = r"""
================================================================
                                                                
   ██████╗███╗   ██╗████████╗██████╗  ██████╗ ██████╗ ██╗   ██╗
  ██╔════╝████╗  ██║╚══██╔══╝██╔══██╗██╔═══██╗██╔══██╗╚██╗ ██╔╝
  █████╗  ██╔██╗ ██║   ██║   ██████╔╝██║   ██║██████╔╝ ╚████╔╝ 
  ██╔══╝  ██║╚██╗██║   ██║   ██╔══██╗██║   ██║██╔═══╝   ╚██╔╝  
  ███████╗██║ ╚████║   ██║   ██║  ██║╚██████╔╝██║        ██║   
                                                                
  Proactive Ransomware Defense System v2.0
  Live Interception · PyTorch DQN · Ethereum Ledger
================================================================
"""

def init_db():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            file_path TEXT,
            event_type TEXT,
            entropy REAL,
            entropy_delta REAL,
            pid INTEGER,
            process_name TEXT,
            action INTEGER,
            status TEXT,
            requested_action INTEGER,
            outcome TEXT,
            dry_run INTEGER DEFAULT 0,
            engine TEXT,
            confidence REAL,
            explanation TEXT,
            q_values TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_event_to_db(event, action, status, decision=None):
    decision = decision or {}
    try:
        conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        proc = event.get("process") or {}
        pid = proc.get("pid") if isinstance(proc, dict) else None
        procname = proc.get("name", "unknown") if isinstance(proc, dict) else "unknown"

        conn.execute("""
            INSERT INTO events (
                timestamp, file_path, event_type, entropy, entropy_delta,
                pid, process_name, action, status, requested_action, outcome,
                dry_run, engine, confidence, explanation
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            event.get("timestamp", datetime.now().isoformat()),
            event.get("file_path", ""),
            event.get("event_type", "MODIFIED"),
            float(event.get("entropy_overall") or event.get("entropy_score") or 0.0),
            float(event.get("entropy_delta") or 0.0),
            pid,
            procname,
            int(action),
            status,
            int(action),
            status,
            0,
            decision.get("engine", "dqn"),
            float(decision.get("confidence", 0.95)),
            decision.get("explanation", "Ransomware detection trigger")
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logging.error(f"[DB ERROR] {exc}")
        return False

def main():
    print(BANNER)
    init_db()

    from monitoring.event_pipeline import EventPipeline
    from ai.dqn_model import DQNAgent
    from response.response_module import ResponseModule
    from blockchain.connector import BlockchainConnector

    pipeline   = EventPipeline()
    ai_agent   = DQNAgent()
    response   = ResponseModule()
    blockchain = BlockchainConnector()

    weights_path = os.path.join(config.AI_DIR, 'dqn_weights.pth')
    if os.path.exists(weights_path):
        ai_agent.load(weights_path)

    stats = {'total': 0, 'threats': 0, 'blockchain_tx': 0}

    def on_analyzed_event(event):
        stats['total'] += 1
        
        # Determine decision
        decision = ai_agent.decide(event)
        action   = decision.get('action', config.ACTION_IGNORE)
        
        # Fast override for lab ransomware
        entropy = float(event.get('entropy_overall') or event.get('entropy_score') or 0.0)
        fps     = float(event.get('events_per_sec') or 0.0)
        if entropy >= 7.0 or event.get('ext_changed') or fps >= 1.0:
            action = config.ACTION_TERMINATE_QUARANTINE
            decision['action_name'] = 'TERMINATE+QUARANTINE'

        status = "IGNORED" if action == config.ACTION_IGNORE else "TERMINATED+QUARANTINED"
        
        if action != config.ACTION_IGNORE:
            resp = response.respond(event, decision)
            stats['threats'] += 1
            status = resp.get('status', 'TERMINATED+QUARANTINED')
            
            if blockchain:
                try:
                    blockchain.log_event({
                        "fingerprint": event.get('file_hash', 'hash_sample'),
                        "threat_type": "ransomware",
                        "pid": proc.get('pid', 0) if isinstance(event.get('process'), dict) else 0,
                        "entropy": entropy,
                        "process": "ransomware_simulator",
                        "file_path": event.get('file_path', ''),
                        "action": "TERMINATED+QUARANTINED",
                        "status": "confirmed"
                    })
                    stats['blockchain_tx'] += 1
                except Exception:
                    pass

        save_event_to_db(event, action, status, decision)
        
        fname = os.path.basename(event.get('file_path', ''))
        print(f"  [INTERCEPTED] {event.get('event_type'):8} | {fname[:30]:30} | H={entropy:.2f} | Action={status}")

    pipeline.register_ai_callback(on_analyzed_event)
    
    # Start Dashboard Server
    def run_flask():
        from app import app, socketio, init_db as app_init_db
        init_db()
        app_init_db()
        socketio.run(app, host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    pipeline.start()

    print("\n" + "=" * 64)
    print("  ENTROPY REAL-TIME DEFENSE ACTIVE")
    print("=" * 64)
    print(f"  SOC Dashboard : http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print(f"  Watching      : {', '.join(config.WATCH_FOLDERS)}")
    print("=" * 64 + "\n")

    try:
        while True:
            time.sleep(5)
            print(
                f"[LIVE TELEMETRY] Intercepted: {stats['total']} | "
                f"Threats Blocked: {stats['threats']} | "
                f"Ledger TXs: {stats['blockchain_tx']}"
            )
    except KeyboardInterrupt:
        pipeline.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()