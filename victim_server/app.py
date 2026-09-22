"""Read-only victim file explorer for the controlled ransomware lab."""
from __future__ import annotations
import os
import sys
import time
import secrets
from datetime import datetime
from pathlib import Path
from functools import wraps
from flask import Flask, jsonify, render_template, request, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, ROOT_DIR)
import config
from catalog import LOCK_EXTENSIONS, family_from_filename

# Paths
USER_FILES = os.path.join(BASE_DIR, "user_files")
# The quarantine folder is the install-time store created by the
# operator (config.QUARANTINE_DIR, overridable via ENTROPY_QUARANTINE_DIR).
QUARANTINE_FILES = getattr(config, "QUARANTINE_DIR",
                           os.path.join(ROOT_DIR, "quarantine_storage"))

os.makedirs(USER_FILES, exist_ok=True)
os.makedirs(QUARANTINE_FILES, exist_ok=True)

# Allowed UI Folders
ALLOWED_FOLDERS = frozenset({"Documents", "Downloads", "Desktop", "Pictures", "Quarantine"})

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = getattr(config, "SECRET_KEY", "entropy-local-development-only")

# Vault Config
VAULT_USER = getattr(config, "VAULT_USER", "victim_user")
VAULT_PIN = str(getattr(config, "VAULT_PIN", "1234"))
VAULT_SESSION_SECONDS = int(getattr(config, "VAULT_SESSION_HOURS", 8)) * 3600


# ── Vault Auth Helpers ───────────────────────────────────────
def _vault_unlocked() -> bool:
    exp = session.get("vault_expires_at")
    if not session.get("vault_auth"):
        return False
    if not exp or time.time() > float(exp):
        session.pop("vault_auth", None)
        session.pop("vault_expires_at", None)
        session.pop("vault_user", None)
        return False
    return True


# ── Folder Helpers ───────────────────────────────────────────
def _get_real_folder_path(folder_name: str) -> str | None:
    if folder_name == "Quarantine":
        return QUARANTINE_FILES
    if folder_name in ALLOWED_FOLDERS:
        return os.path.join(USER_FILES, folder_name)
    return None


def get_file_icon(filename: str) -> str:
    """Pick an icon from the extension only — exactly like a real file
    explorer. Unknown extensions (including anything an attacker may
    have renamed) get the generic icon; the explorer never labels a
    file as encrypted. Detection and labelling happen in the SOC."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".docx", ".doc"): return "doc"
    if ext in (".xlsx", ".xls"): return "xls"
    if ext == ".pdf": return "pdf"
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp"): return "img"
    if ext in (".zip", ".rar", ".7z"): return "zip"
    if ext in (".txt", ".log"): return "txt"
    if ext in (".exe", ".msi"): return "exe"
    return "unknown"


def get_folder_stats(folder_path: str, is_quarantine: bool = False):
    """Neutral folder stats: item count + total size (no attack intel)."""
    total_files = 0
    total_size = 0
    if not folder_path or not os.path.isdir(folder_path):
        return 0, 0
    for filename in os.listdir(folder_path):
        if filename.endswith(".meta.json"):
            continue
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        total_files += 1
        try:
            total_size += os.path.getsize(file_path)
        except OSError:
            continue
    return total_files, total_size


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024: return f"{size_bytes} B"
    if size_bytes < 1024 * 1024: return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _safe_file_path(folder: str, filename: str) -> Path | None:
    folder_path = _get_real_folder_path(folder)
    if not folder_path or not filename: return None
    if "/" in filename or "\\" in filename or ".." in filename:
        return None
    folder_root = Path(folder_path).resolve()
    candidate = (folder_root / filename).resolve()
    try:
        if candidate.parent != folder_root: return None
    except (OSError, RuntimeError):
        return None
    return candidate


def _file_family(filename: str):
    return family_from_filename(filename) if os.path.splitext(filename)[1].lower() in LOCK_EXTENSIONS else None


def _ransom_note_family(filename: str):
    family = family_from_filename(filename)
    if not family: return False
    if os.path.splitext(filename)[1].lower() in LOCK_EXTENSIONS: return False
    return family


# ── Routes ───────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("victim.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "victim"})


# ── Vault Auth Routes ────────────────────────────────────────
@app.route("/api/vault/status")
def vault_status():
    return jsonify({
        "unlocked": _vault_unlocked(),
        "user": session.get("vault_user"),
        "privileged": True,
        "scope": "quarantine_only",
    })


@app.route("/api/vault/login", methods=["POST"])
def vault_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    pin = (data.get("pin") or data.get("password") or "").strip()

    if username == VAULT_USER and secrets.compare_digest(pin, VAULT_PIN):
        session["vault_auth"] = True
        session["vault_user"] = username
        session["vault_expires_at"] = time.time() + VAULT_SESSION_SECONDS
        return jsonify({
            "ok": True,
            "message": "Privileged access granted",
            "user": username,
            "expires_in": VAULT_SESSION_SECONDS,
        })
    return jsonify({"ok": False, "error": "invalid_credentials",
                    "message": "Access denied. User only."}), 403


@app.route("/api/vault/logout", methods=["POST"])
def vault_logout():
    session.clear()
    return jsonify({"ok": True, "message": "Privileged session closed"})


# ── Folder / File Listing ────────────────────────────────────
# The victim explorer is deliberately a NEUTRAL "This PC" view:
# folders with item counts, files with name/size/modified. It never
# says how many files are encrypted, which family did it, or that
# the machine is compromised — a real file explorer can't. All
# attack assessment lives in the SOC dashboard.
@app.route("/api/folders")
def get_folders():
    folders = []
    unlocked = _vault_unlocked()
    for folder_name in ("Documents", "Downloads", "Desktop", "Pictures", "Quarantine"):
        folder_path = _get_real_folder_path(folder_name)
        is_q = (folder_name == "Quarantine")

        if is_q and not unlocked:
            # The vault exists but is locked: show it, hide its contents.
            actual_count = 0
            if os.path.isdir(folder_path):
                actual_count = len([f for f in os.listdir(folder_path) if not f.endswith(".meta.json")])
            folders.append({
                "name": folder_name,
                "file_count": actual_count,
                "size": "🔒 Locked",
                "locked": True,
                "privilege": "user_only",
            })
            continue

        files, size = get_folder_stats(folder_path, is_q)
        folders.append({
            "name": folder_name,
            "file_count": files,
            "size": format_size(size),
            "locked": False,
        })
    return jsonify(folders)


@app.route("/api/files/<folder>")
def get_files(folder):
    if folder not in ALLOWED_FOLDERS:
        return jsonify([])

    # Privileged gate for quarantine
    if folder == "Quarantine" and not _vault_unlocked():
        return jsonify({
            "error": "privileged_access_required",
            "message": "Quarantine Vault is restricted to the authorized user.",
            "auth_required": True,
            "files": [],
        }), 401

    folder_path = _get_real_folder_path(folder)
    if not folder_path or not os.path.isdir(folder_path):
        return jsonify([])

    # A real file explorer only knows: name, size, modified, icon.
    # No "encrypted" flags, no family attribution, no note markers —
    # a file renamed by an attacker simply appears under its new name.
    files = []
    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".meta.json"): continue
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path): continue
        try:
            file_stat = os.stat(file_path)
            extension = os.path.splitext(filename)[1].lower()
            files.append({
                "name": filename,
                "size": format_size(file_stat.st_size),
                "modified": datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "icon": get_file_icon(filename),
                "extension": extension,
            })
        except OSError:
            continue
    return jsonify(files)


@app.route("/api/status")
def status():
    total_files = 0
    total_encrypted = 0
    total_notes = 0
    quarantined = 0
    detected_family = None

    for folder_name in ("Documents", "Downloads", "Desktop", "Pictures"):
        folder_path = _get_real_folder_path(folder_name)
        if not folder_path or not os.path.isdir(folder_path): continue
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if not os.path.isfile(file_path): continue
            total_files += 1
            family = _file_family(filename)
            if family:
                total_encrypted += 1
                detected_family = family
            if _ransom_note_family(filename):
                total_notes += 1

    if os.path.isdir(QUARANTINE_FILES):
        quarantined = len([f for f in os.listdir(QUARANTINE_FILES) if not f.endswith(".meta.json")])

    if total_encrypted > 0:
        system_status = "COMPROMISED"
    elif quarantined > 0:
        system_status = "PROTECTED"
    else:
        system_status = "OPERATIONAL"

    return jsonify({
        "total_files": total_files,
        "encrypted_files": total_encrypted,
        "quarantined_files": quarantined,
        "ransom_notes": total_notes,
        "system_status": system_status,
        "detected_family": detected_family,
        "compromise_pct": round((total_encrypted / max(total_files, 1)) * 100, 1),
        "vault_unlocked": _vault_unlocked(),
    })


@app.route("/api/file/<folder>/<filename>")
def preview_file(folder, filename):
    if folder == "Quarantine" and not _vault_unlocked():
        return jsonify({
            "error": "privileged_access_required",
            "message": "Login required to open isolated files.",
            "auth_required": True,
        }), 401

    file_path = _safe_file_path(folder, filename)
    if file_path is None or not file_path.is_file():
        return jsonify({"error": "file not found"}), 404
    try:
        sample = file_path.read_bytes()[:65536]
        if b"\x00" in sample:
            content = "Binary fixture file\n\nHex preview: " + sample[:128].hex(" ")
            preview_type = "binary"
        else:
            try:
                content = sample.decode("utf-8")
                preview_type = "text"
            except UnicodeDecodeError:
                content = "Binary fixture file\n\nHex preview: " + sample[:128].hex(" ")
                preview_type = "binary"
        return jsonify({
            "name": filename,
            "preview_type": preview_type,
            "content": content,
            "truncated": file_path.stat().st_size > len(sample),
        })
    except OSError as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    host = getattr(config, "VICTIM_HOST", "127.0.0.1")
    port = getattr(config, "VICTIM_PORT", 5001)
    print("=" * 60)
    print("  VICTIM MACHINE — Web Server")
    print("=" * 60)
    print(f"  URL       : http://{host}:{port}")
    print(f"  User Files: {USER_FILES}")
    print(f"  Quarantine: {QUARANTINE_FILES} (privileged)")
    print(f"  Vault User: {VAULT_USER} | PIN: {VAULT_PIN}")
    print("=" * 60)
    app.run(host=host, port=port, debug=False)