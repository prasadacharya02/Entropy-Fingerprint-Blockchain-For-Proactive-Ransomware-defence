from __future__ import annotations

import hmac
import ipaddress
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
VICTIM_DIR = os.path.join(ROOT_DIR, "victim_server")
USER_FILES = os.path.join(VICTIM_DIR, "user_files")

HTML_PATH = os.path.join(
    BASE_DIR,
    "templates",
    "attacker.html",
)

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, VICTIM_DIR)

import config
import ransomware_engines as engines

try:
    from create_fake_files import restore_all_files
except Exception:
    restore_all_files = None


def victim_snapshot():
    total = 0
    locked = 0
    notes = 0

    lock_extensions = (
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
    )

    note_markers = (
        "@please_read_me@",
        "ryukreadme",
        "restore-my-files",
        "recover-",
        "maze-readme",
        "revil-readme",
        "akira-readme",
        "clop-readme",
        "qilin-readme",
    )

    if not os.path.isdir(USER_FILES):
        return {
            "exists": False,
            "total": 0,
            "locked": 0,
            "notes": 0,
        }

    for directory, _, filenames in os.walk(USER_FILES):
        for filename in filenames:
            total += 1

            extension = os.path.splitext(filename)[1].lower()
            lowercase_name = filename.lower()

            if extension in lock_extensions:
                locked += 1

            if (
                extension.startswith(".")
                and len(extension) == 8
            ):
                locked += 1

            if any(marker in lowercase_name for marker in note_markers):
                notes += 1

    return {
        "exists": True,
        "total": total,
        "locked": locked,
        "notes": notes,
    }


def read_json(handler):
    content_length = int(
        handler.headers.get("Content-Length") or 0
    )

    if content_length <= 0:
        return {}

    raw = handler.rfile.read(content_length)

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def send_json(handler, payload, status=200):
    body = json.dumps(payload).encode("utf-8")

    handler.send_response(status)
    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8",
    )
    handler.send_header(
        "Content-Length",
        str(len(body)),
    )
    handler.send_header(
        "Cache-Control",
        "no-store",
    )
    handler.end_headers()
    handler.wfile.write(body)


def send_text(
    handler,
    text,
    content_type="text/plain; charset=utf-8",
):
    body = text.encode("utf-8")

    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header(
        "Content-Disposition",
        "attachment; filename=campaign.log",
    )
    handler.end_headers()
    handler.wfile.write(body)


def send_html(handler):
    with open(HTML_PATH, "r", encoding="utf-8") as file:
        html = file.read()

    host_header = handler.headers.get(
        "Host",
        "127.0.0.1:8001",
    )

    host = host_header.split(":", 1)[0]

    forwarded_protocol = handler.headers.get(
        "X-Forwarded-Proto"
    )

    scheme = (
        "https"
        if forwarded_protocol == "https"
        else "http"
    )

    victim_url = (
        config.PUBLIC_VICTIM_URL
        or f"{scheme}://{host}:8002"
    )

    dashboard_url = (
        config.PUBLIC_DASHBOARD_URL
        or f"{scheme}://{host}:5000"
    )

    attacker_url = (
        config.PUBLIC_ATTACKER_URL
        or f"{scheme}://{host}:8001"
    )

    html = html.replace(
        "__VICTIM_URL__",
        victim_url,
    )

    html = html.replace(
        "__DASHBOARD_URL__",
        dashboard_url,
    )

    html = html.replace(
        "__ATTACKER_URL__",
        attacker_url,
    )

    body = html.encode("utf-8")

    handler.send_response(200)
    handler.send_header(
        "Content-Type",
        "text/html; charset=utf-8",
    )
    handler.send_header(
        "Content-Length",
        str(len(body)),
    )
    handler.send_header(
        "Cache-Control",
        "no-store",
    )
    handler.end_headers()
    handler.wfile.write(body)


def control_authorized(handler):
    """
    Localhost is allowed by default.

    If ENTROPY_CONTROL_TOKEN is configured,
    remote control requires:
    Authorization: Bearer <token>
    """
    configured_token = config.CONTROL_TOKEN

    if configured_token:
        supplied = handler.headers.get(
            "Authorization",
            "",
        )

        expected = f"Bearer {configured_token}"

        return hmac.compare_digest(
            supplied,
            expected,
        )

    try:
        address = ipaddress.ip_address(
            handler.client_address[0]
        )
        return address.is_loopback
    except ValueError:
        return False


def send_forbidden(handler):
    send_json(
        handler,
        {
            "ok": False,
            "error": (
                "control route requires local access "
                "or a valid bearer token"
            ),
        },
        status=403,
    )


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format_string, *args):
        sys.stderr.write(
            "[attacker] "
            + (format_string % args)
            + "\n"
        )

    def do_GET(self):
        path = urlparse(self.path).path

        if path in {
            "/",
            "/index.html",
            "/attacker.html",
        }:
            send_html(self)
            return

        if path == "/api/families":
            send_json(self, engines.list_families())
            return

        if path == "/api/stats":
            stats = engines.current_stats()
            stats["victim"] = victim_snapshot()
            send_json(self, stats)
            return

        if path == "/api/log":
            stats = engines.current_stats()
            lines = [
                entry.get("msg", "")
                for entry in stats.get("log", [])
            ]
            send_text(self, "\n".join(lines) + "\n")
            return

        self.send_error(404, "not found")

    def do_POST(self):
        path = urlparse(self.path).path

        protected_routes = {
            "/api/launch",
            "/api/stop",
            "/api/pause",
            "/api/resume",
            "/api/speed",
            "/api/reset",
        }

        if (
            path in protected_routes
            and not control_authorized(self)
        ):
            send_forbidden(self)
            return

        data = read_json(self)

        if path == "/api/launch":
            family = (
                data.get("family") or ""
            ).strip().lower()

            if family not in engines.FAMILIES:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": "unknown family",
                    },
                    status=400,
                )
                return

            snapshot = victim_snapshot()

            if (
                not snapshot["exists"]
                or snapshot["total"] == 0
            ):
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            "victim folder is empty — "
                            "hit RESET first"
                        ),
                    },
                    status=400,
                )
                return

            current = engines.current_stats()

            if current.get("active"):
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            f"{current.get('family')} "
                            "already running"
                        ),
                    },
                    status=409,
                )
                return

            ok, engine = engines.start_attack(family)

            if not ok:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": "engine refused to start",
                    },
                    status=500,
                )
                return

            send_json(
                self,
                {
                    "ok": True,
                    "family": engine.name,
                    "stats": engine.get_stats(),
                },
            )
            return

        if path == "/api/stop":
            stopped = engines.stop_attack()
            send_json(
                self,
                {
                    "ok": True,
                    "stopped": bool(stopped),
                },
            )
            return

        if path == "/api/pause":
            engine = engines._active_engine
            paused = bool(engine and engine.pause())

            send_json(
                self,
                {
                    "ok": paused,
                    "paused": paused,
                },
            )
            return

        if path == "/api/resume":
            engine = engines._active_engine
            resumed = bool(engine and engine.resume())

            send_json(
                self,
                {
                    "ok": resumed,
                    "paused": False,
                },
            )
            return

        if path == "/api/speed":
            engine = engines._active_engine

            try:
                factor = float(
                    data.get("factor", 1.0)
                )

                speed = (
                    engine.set_speed(factor)
                    if engine
                    else None
                )

                send_json(
                    self,
                    {
                        "ok": speed is not None,
                        "speed_factor": speed,
                    },
                )
            except (TypeError, ValueError):
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": "invalid speed",
                    },
                    status=400,
                )
            return

        if path == "/api/reset":
            current = engines.current_stats()

            if current.get("active"):
                engines.stop_attack()

                if engines._active_engine:
                    engines._active_engine.join(
                        timeout=4
                    )

            if restore_all_files is None:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": (
                            "create_fake_files.py "
                            "is unavailable"
                        ),
                    },
                    status=500,
                )
                return

            try:
                restore_all_files()

                send_json(
                    self,
                    {
                        "ok": True,
                        "victim": victim_snapshot(),
                    },
                )
            except Exception as exc:
                send_json(
                    self,
                    {
                        "ok": False,
                        "error": str(exc),
                    },
                    status=500,
                )
            return

        self.send_error(404, "not found")


if __name__ == "__main__":
    if not os.path.isfile(HTML_PATH):
        print(f"MISSING: {HTML_PATH}")
        raise SystemExit(1)

    print("=" * 60)
    print("  ATTACKER SITE")
    print("  http://0.0.0.0:8001")
    print("=" * 60)

    server = ThreadingHTTPServer(
        ("0.0.0.0", 8001),
        Handler,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAttacker server stopped")
        server.shutdown()
        server.server_close()