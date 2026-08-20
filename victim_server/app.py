"""Read-only victim file explorer for the controlled ransomware lab."""
from __future__ import annotations
import os
import sys
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, ROOT_DIR)
import config
from catalog import LOCK_EXTENSIONS, family_from_filename
USER_FILES = os.path.join(BASE_DIR, "user_files")
ALLOWED_FOLDERS = frozenset({"Documents", "Downloads", "Desktop", "Pictures"})
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
def get_file_icon(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".docx", ".doc"):
        return "doc"
    if ext in (".xlsx", ".xls"):
        return "xls"
    if ext == ".pdf":
        return "pdf"
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp"):
        return "img"
    if ext in (".zip", ".rar", ".7z"):
        return "zip"
    if ext in (".txt", ".log"):
        return "txt"
    if ext in (".exe", ".msi"):
        return "exe"
    if ext in (".wncry", ".wncryt", ".ryk", ".lockbit", ".abcd"):
        return "locked"
    if ext.startswith("."):
        return "locked" if len(ext) == 8 else "unknown"
    return "unknown"
def get_folder_stats(folder_path: str):
    total_files = 0
    total_size = 0
    encrypted = 0
    if not os.path.isdir(folder_path):
        return 0, 0, 0
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        total_files += 1
        try:
            total_size += os.path.getsize(file_path)
        except OSError:
            continue
        extension = os.path.splitext(filename)[1].lower()
        if extension in LOCK_EXTENSIONS or family_from_filename(filename):
            encrypted += 1
    return total_files, total_size, encrypted
def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"
def _safe_file_path(folder: str, filename: str) -> Path | None:
    """Resolve a direct child of a permitted fixture folder safely."""
    if folder not in ALLOWED_FOLDERS or not filename:
        return None
    folder_root = (Path(USER_FILES) / folder).resolve()
    candidate = (folder_root / filename).resolve()
    try:
        if candidate.parent != folder_root:
            return None
    except (OSError, RuntimeError):
        return None
    return candidate
def _file_family(filename: str):
    return family_from_filename(filename) if os.path.splitext(filename)[1].lower() in LOCK_EXTENSIONS else None
def _ransom_note_family(filename: str):
    family = family_from_filename(filename)
    if not family:
        return False
    if os.path.splitext(filename)[1].lower() in LOCK_EXTENSIONS:
        return False
    return family
@app.route("/")
def index():
    return render_template("victim.html")

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "victim"})
@app.route("/api/folders")
def get_folders():
    folders = []
    for folder_name in ("Documents", "Downloads", "Desktop", "Pictures"):
        folder_path = os.path.join(USER_FILES, folder_name)
        files, size, encrypted = get_folder_stats(folder_path)
        folders.append({
            "name": folder_name,
            "file_count": files,
            "size": format_size(size),
            "encrypted": encrypted,
            "status": "compromised" if encrypted else "safe",
        })
    return jsonify(folders)
@app.route("/api/files/<folder>")
def get_files(folder):
    if folder not in ALLOWED_FOLDERS:
        return jsonify([])
    folder_path = os.path.join(USER_FILES, folder)
    if not os.path.isdir(folder_path):
        return jsonify([])
    files = []
    for filename in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        try:
            file_stat = os.stat(file_path)
            extension = os.path.splitext(filename)[1].lower()
            family = _file_family(filename)
            files.append({
                "name": filename,
                "size": format_size(file_stat.st_size),
                "modified": datetime.fromtimestamp(file_stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "icon": get_file_icon(filename),
                "encrypted": family is not None,
                "family": family,
                "is_note": _ransom_note_family(filename),
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
    detected_family = None
    for folder_name in ALLOWED_FOLDERS:
        folder_path = os.path.join(USER_FILES, folder_name)
        if not os.path.isdir(folder_path):
            continue
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if not os.path.isfile(file_path):
                continue
            total_files += 1
            family = _file_family(filename)
            if family:
                total_encrypted += 1
                detected_family = family
            if _ransom_note_family(filename):
                total_notes += 1
    if total_encrypted == 0:
        system_status = "OPERATIONAL"
    elif total_encrypted < total_files * 0.3:
        system_status = "UNDER ATTACK"
    else:
        system_status = "COMPROMISED"
    return jsonify({
        "total_files": total_files,
        "encrypted_files": total_encrypted,
        "ransom_notes": total_notes,
        "system_status": system_status,
        "detected_family": detected_family,
        "compromise_pct": round(
            (total_encrypted / max(total_files, 1)) * 100, 1
        ),
    })
@app.route("/api/file/<folder>/<filename>")
def preview_file(folder, filename):
    """Return a bounded preview of a clean fixture file."""
    file_path = _safe_file_path(folder, filename)
    if file_path is None or not file_path.is_file():
        return jsonify({"error": "file not found or unavailable"}), 404
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
@app.route("/api/note/<folder>/<filename>")
def get_ransom_note(folder, filename):
    """Read a ransom note from the controlled fixture tree."""
    file_path = _safe_file_path(folder, filename)
    if file_path is None or not file_path.is_file():
        return jsonify({"error": "not found"}), 404
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return jsonify({"content": content})
    except OSError as exc:
        return jsonify({"error": str(exc)}), 500
if __name__ == "__main__":
    print("=" * 60)
    print("  VICTIM MACHINE — Web Server")
    print("=" * 60)
    print(f"  URL       : http://{config.VICTIM_HOST}:{config.VICTIM_PORT}")
    print(f"  User Files: {USER_FILES}")
    print("=" * 60)
    app.run(host=config.VICTIM_HOST, port=config.VICTIM_PORT, debug=False)