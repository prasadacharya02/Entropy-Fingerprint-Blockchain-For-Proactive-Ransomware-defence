from __future__ import annotations

import os
import random
import string
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread


ROOT_DIR = Path(__file__).resolve().parent.parent
VICTIM_ROOT = (ROOT_DIR / "victim_server" / "user_files").resolve()
VICTIM_BASE = str(VICTIM_ROOT)


def safe_path(path, allow_root=False):
    try:
        candidate = Path(path).resolve(strict=False)
        candidate.relative_to(VICTIM_ROOT)

        if not allow_root and candidate == VICTIM_ROOT:
            return None

        return candidate
    except (OSError, RuntimeError, ValueError, TypeError):
        return None


def victim_ready():
    return VICTIM_ROOT.is_dir() and not VICTIM_ROOT.is_symlink()


class BaseRansomware:
    name = "Demo"
    extension = ".locked"
    note_filename = "READ_ME.txt"
    workers = 1
    min_delay = 0.05
    max_delay = 0.15
    target_extensions = None

    def __init__(self):
        self.stop_event = Event()
        self.pause_event = Event()
        self.pause_event.set()

        self.lock = Lock()
        self.thread = None

        self.stats = {
            "family": self.name,
            "active": False,
            "paused": False,
            "phase": "IDLE",
            "targets": 0,
            "files_hit": 0,
            "files_skipped": 0,
            "bytes_encrypted": 0,
            "notes_dropped": 0,
            "speed_factor": 1.0,
            "started_at": None,
            "finished_at": None,
            "log": [],
        }

    def log(self, message):
        with self.lock:
            self.stats["log"].append({
                "time": time.strftime("%H:%M:%S"),
                "msg": message,
            })

            self.stats["log"] = self.stats["log"][-100:]

        print(f"[{self.name}] {message}", flush=True)

    def get_stats(self):
        with self.lock:
            result = dict(self.stats)
            result["log"] = list(self.stats["log"])

            targets = max(result["targets"], 1)
            result["progress"] = round(
                min(100, result["files_hit"] / targets * 100),
                1,
            )

            return result

    def collect_files(self):
        files = []
        folders = []

        if not victim_ready():
            return files, folders

        for directory, dirnames, filenames in os.walk(VICTIM_ROOT):
            safe_directory = safe_path(directory, allow_root=True)

            if safe_directory is None:
                continue

            folders.append(safe_directory)

            for filename in filenames:
                candidate = safe_path(
                    safe_directory / filename
                )

                if candidate is not None and candidate.is_file():
                    files.append(candidate)

        return files, folders

    def should_encrypt(self, file_path):
        file_path = Path(file_path)
        name = file_path.name.lower()
        extension = file_path.suffix.lower()

        if any(marker in name for marker in (
            "read_me",
            "please_read",
            "ryukreadme",
            "restore-my-files",
            "recover-",
            "desktop_wallpaper",
        )):
            return False

        if extension in {
            ".wncry",
            ".wncryt",
            ".ryk",
            ".maze",
            ".revil",
            ".lockbit",
            ".akira",
            ".clop",
            ".qilin",
            ".abcd",
        }:
            return False

        if self.target_extensions:
            if extension not in self.target_extensions:
                return False

        return safe_path(file_path) is not None

    def drop_note(self, folder):
        folder = safe_path(folder, allow_root=True)

        if folder is None or not folder.is_dir():
            return False

        note_path = safe_path(
            folder / self.note_filename
        )

        if note_path is None:
            return False

        content = (
            "ENTROPY SAFE LAB SIMULATION\n"
            "===========================\n\n"
            f"Simulated family: {self.name}\n\n"
            "This is not real ransomware.\n"
            "The file was created only for the demonstration.\n"
        )

        try:
            note_path.write_text(
                content,
                encoding="utf-8",
            )

            with self.lock:
                self.stats["notes_dropped"] += 1

            self.log(f"Note dropped: {note_path.name}")
            return True
        except OSError as exc:
            self.log(f"Note failed: {exc}")
            return False

    def modify_file(self, file_path):
        file_path = safe_path(file_path)

        if (
            not victim_ready()
            or file_path is None
            or not file_path.is_file()
        ):
            return False

        try:
            original_size = file_path.stat().st_size

            with file_path.open("wb") as handle:
                handle.write(
                    os.urandom(max(original_size, 1024))
                )

            new_path = safe_path(
                str(file_path) + self.extension
            )

            if new_path is None:
                return False

            if new_path.exists():
                new_path = safe_path(
                    str(file_path)
                    + "."
                    + str(time.time_ns())
                    + self.extension
                )

            if new_path is None:
                return False

            file_path.rename(new_path)

            with self.lock:
                self.stats["files_hit"] += 1
                self.stats["bytes_encrypted"] += original_size

            self.log(f"Encrypted: {new_path.name}")
            return True

        except OSError as exc:
            self.log(f"File failed: {exc}")
            return False

    def delay(self):
        while not self.pause_event.wait(0.1):
            if self.stop_event.is_set():
                return

        factor = max(
            0.1,
            float(self.stats["speed_factor"]),
        )

        delay = random.uniform(
            self.min_delay,
            self.max_delay,
        )

        time.sleep(delay / factor)

    def run(self):
        self.stats["active"] = True
        self.stats["phase"] = "SCANNING"
        self.stats["started_at"] = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.log(f"Attack started on {VICTIM_ROOT}")

        try:
            files, folders = self.collect_files()
            targets = [
                file_path
                for file_path in files
                if self.should_encrypt(file_path)
            ]

            with self.lock:
                self.stats["targets"] = len(targets)
                self.stats["files_skipped"] = (
                    len(files) - len(targets)
                )
                self.stats["phase"] = "DROPPING NOTES"

            self.log(
                f"Scan complete — {len(targets)} targets, "
                f"{len(files) - len(targets)} skipped"
            )

            for folder in folders:
                if self.stop_event.is_set():
                    break
                self.drop_note(folder)

            self.stats["phase"] = "MODIFYING FILES"

            for file_path in targets:
                if self.stop_event.is_set():
                    break

                if self.modify_file(file_path):
                    self.delay()

            self.stats["phase"] = "FINALIZING"

        except Exception as exc:
            self.log(f"Attack error: {exc}")

        finally:
            self.stats["active"] = False
            self.stats["paused"] = False
            self.stats["phase"] = (
                "STOPPED"
                if self.stop_event.is_set()
                else "COMPLETED"
            )
            self.stats["finished_at"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self.pause_event.set()

            self.log(
                f"Attack finished — "
                f"hit={self.stats['files_hit']} "
                f"skipped={self.stats['files_skipped']}"
            )

    def start(self):
        if self.thread and self.thread.is_alive():
            return False

        self.stop_event.clear()
        self.pause_event.set()
        self.stats["active"] = True
        self.thread = Thread(
            target=self.run,
            daemon=True,
        )
        self.thread.start()

        return True

    def stop(self):
        if not self.stats["active"]:
            return False

        self.stop_event.set()
        self.pause_event.set()
        return True

    def pause(self):
        if not self.stats["active"]:
            return False

        self.stats["paused"] = True
        self.stats["phase"] = "PAUSED"
        self.pause_event.clear()
        return True

    def resume(self):
        if not self.stats["active"]:
            return False

        self.stats["paused"] = False
        self.stats["phase"] = "MODIFYING FILES"
        self.pause_event.set()
        return True

    def set_speed(self, factor):
        self.stats["speed_factor"] = min(
            5.0,
            max(0.1, float(factor)),
        )
        return self.stats["speed_factor"]

    def join(self, timeout=None):
        if self.thread:
            self.thread.join(timeout)


class WannaCryEngine(BaseRansomware):
    name = "WannaCry"
    extension = ".WNCRY"
    note_filename = "@Please_Read_Me@.txt"
    min_delay = 0.02
    max_delay = 0.08


class RyukEngine(BaseRansomware):
    name = "Ryuk"
    extension = ".ryk"
    note_filename = "RyukReadMe.html"
    min_delay = 0.15
    max_delay = 0.35


class MazeEngine(BaseRansomware):
    name = "Maze"
    extension = ".maze"
    note_filename = "MAZE-README.txt"
    min_delay = 0.04
    max_delay = 0.12


class REvilEngine(BaseRansomware):
    name = "REvil"
    extension = ".revil"
    note_filename = "REVIL-README.txt"
    min_delay = 0.03
    max_delay = 0.10


class BlackCatEngine(BaseRansomware):
    name = "BlackCat"
    extension = ".abcd"
    note_filename = "RECOVER-blackcat-FILES.txt"
    min_delay = 0.02
    max_delay = 0.08


class ALPHVEngine(BaseRansomware):
    name = "ALPHV"
    extension = ".alphv"
    note_filename = "RECOVER-alphv-FILES.txt"
    min_delay = 0.02
    max_delay = 0.08


class AkiraEngine(BaseRansomware):
    name = "Akira"
    extension = ".akira"
    note_filename = "AKIRA-README.txt"
    min_delay = 0.05
    max_delay = 0.14


class Cl0pEngine(BaseRansomware):
    name = "Cl0p"
    extension = ".clop"
    note_filename = "CLOP-README.txt"
    min_delay = 0.06
    max_delay = 0.16


class QilinEngine(BaseRansomware):
    name = "Qilin"
    extension = ".qilin"
    note_filename = "QILIN-README.txt"
    min_delay = 0.03
    max_delay = 0.10


class LockBit5Engine(BaseRansomware):
    name = "LockBit 5.0"
    extension = ".lockbit"
    note_filename = "Restore-My-Files.txt"
    min_delay = 0.01
    max_delay = 0.05


FAMILIES = {
    "wannacry": WannaCryEngine,
    "ryuk": RyukEngine,
    "maze": MazeEngine,
    "revil": REvilEngine,
    "blackcat": BlackCatEngine,
    "alphv": ALPHVEngine,
    "akira": AkiraEngine,
    "cl0p": Cl0pEngine,
    "qilin": QilinEngine,
    "lockbit5": LockBit5Engine,
}


def list_families():
    return [
        {
            "id": "wannacry",
            "name": "WannaCry (2017)",
            "extension": ".WNCRY",
            "note": "@Please_Read_Me@.txt",
            "speed": "10-50 files/sec",
            "style": "Fast full-file simulation",
        },
        {
            "id": "ryuk",
            "name": "Ryuk (2019)",
            "extension": ".ryk",
            "note": "RyukReadMe.html",
            "speed": "2-5 files/sec",
            "style": "Slow selective simulation",
        },
        {
            "id": "maze",
            "name": "Maze (2020)",
            "extension": ".maze",
            "note": "MAZE-README.txt",
            "speed": "Moderate",
            "style": "Fixed extension simulation",
        },
        {
            "id": "revil",
            "name": "REvil (2021)",
            "extension": ".revil",
            "note": "REVIL-README.txt",
            "speed": "Fast",
            "style": "Parallel-style simulation",
        },
        {
            "id": "blackcat",
            "name": "BlackCat (2022)",
            "extension": ".abcd",
            "note": "RECOVER-blackcat-FILES.txt",
            "speed": "Fast",
            "style": "Random-extension simulation",
        },
        {
            "id": "alphv",
            "name": "ALPHV (2023)",
            "extension": ".alphv",
            "note": "RECOVER-alphv-FILES.txt",
            "speed": "Fast",
            "style": "Catalog training simulation",
        },
        {
            "id": "akira",
            "name": "Akira (2024)",
            "extension": ".akira",
            "note": "AKIRA-README.txt",
            "speed": "Moderate",
            "style": "Fixed extension simulation",
        },
        {
            "id": "cl0p",
            "name": "Cl0p (2025)",
            "extension": ".clop",
            "note": "CLOP-README.txt",
            "speed": "Selective",
            "style": "Document-style simulation",
        },
        {
            "id": "qilin",
            "name": "Qilin (2026)",
            "extension": ".qilin",
            "note": "QILIN-README.txt",
            "speed": "Fast",
            "style": "Fixed extension simulation",
        },
        {
            "id": "lockbit5",
            "name": "LockBit 5.0",
            "extension": ".lockbit",
            "note": "Restore-My-Files.txt",
            "speed": "Very fast",
            "style": "High-speed simulation",
        },
    ]


_active_engine = None
_active_lock = Lock()


def get_engine(family_id):
    key = (family_id or "").strip().lower()

    if key not in FAMILIES:
        raise ValueError(
            f"Unknown family: {family_id}"
        )

    return FAMILIES[key]()


def start_attack(family_id):
    global _active_engine

    with _active_lock:
        if _active_engine and _active_engine.stats.get("active"):
            _active_engine.stop()
            _active_engine.join(timeout=3)

        _active_engine = get_engine(family_id)
        ok = _active_engine.start()

        return ok, _active_engine


def stop_attack():
    with _active_lock:
        if not _active_engine:
            return False

        return _active_engine.stop()


def current_stats():
    with _active_lock:
        if not _active_engine:
            return {
                "active": False,
                "family": None,
                "phase": "IDLE",
                "progress": 0,
                "log": [],
            }

        return _active_engine.get_stats()