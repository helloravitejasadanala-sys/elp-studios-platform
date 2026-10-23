#!/usr/bin/env python3
"""ELP Studio Console — reverse-proxy + static UI in front of PicPeak.

Talks to the existing PicPeak container. Does not store media, passwords,
or gallery databases. Bind-mounts brands/ read-only.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "public"
# Repo: apps/studio-console → apps/gallery. Container: /app → /gallery (bind mount).
_gallery_default = HERE.parent / "gallery"
if not _gallery_default.is_dir() and Path("/gallery").is_dir():
    _gallery_default = Path("/gallery")
GALLERY = Path(os.environ.get("ELP_GALLERY_DIR", _gallery_default))
sys.path.insert(0, str(GALLERY))
from elp_lib import (  # noqa: E402
    ARCHIVE_POLICY,
    BACKUP_POLICY,
    BRANDS_DIR,
    COST_CATEGORIES,
    STORAGE_ALERT_THRESHOLDS,
    STORAGE_VOLUME_NAME,
    TECHNICAL_LIMITS,
    build_storage_report,
    load_brands,
    load_dotenv,
)

load_dotenv(GALLERY / ".env")

LISTEN_HOST = os.environ.get("STUDIO_BIND", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("STUDIO_PORT", "3080"))
PICPEAK_ORIGIN = os.environ.get("PICPEAK_ORIGIN", "http://127.0.0.1:3000").rstrip("/")
PICPEAK_PUBLIC_ORIGIN = os.environ.get("PICPEAK_PUBLIC_ORIGIN", "http://localhost:3000").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@elp.local")


def _config() -> dict:
    return {
        "picpeakPublicOrigin": PICPEAK_PUBLIC_ORIGIN,
        "adminEmailDefault": ADMIN_EMAIL,
        "proxyPrefix": "/pp",
        "brands": load_brands(),
        "layouts": [
            {"id": "grid", "label": "Grid"},
            {"id": "masonry", "label": "Masonry"},
            {"id": "carousel", "label": "Carousel"},
            {"id": "timeline", "label": "Timeline"},
            {"id": "mosaic", "label": "Mosaic"},
            {"id": "gallery-premium", "label": "Gallery Premium"},
            {"id": "gallery-story", "label": "Gallery Story"},
        ],
        "accessModes": [
            {"id": "password", "label": "Password-protected", "require_password": True},
            {"id": "unlisted", "label": "Unlisted link (no password)", "require_password": False},
        ],
        "video": {
            "accept": ".jpg,.jpeg,.png,.webp,.gif,.heic,.mp4,.m4v,.mov,.webm",
            "priority": "mp4",
            "also": ["mov", "webm", "m4v"],
            "maxVideoMb": 500,
            "maxPhotoMb": 50,
            "note": "PicPeak plays the uploaded file. Prefer H.264 MP4 for mobile + desktop. Originals are not recompressed on download when original-resolution downloads are on.",
        },
        "storage": {
            "volumeName": STORAGE_VOLUME_NAME,
            "alerts": list(STORAGE_ALERT_THRESHOLDS),
            "costCategories": list(COST_CATEGORIES),
            "technicalLimits": list(TECHNICAL_LIMITS),
            "archivePolicy": ARCHIVE_POLICY,
            "backupPolicy": BACKUP_POLICY,
            "adminBackup": f"{PICPEAK_PUBLIC_ORIGIN}/admin/backup",
            "adminArchives": f"{PICPEAK_PUBLIC_ORIGIN}/admin/events/archives",
            "adminSettings": f"{PICPEAK_PUBLIC_ORIGIN}/admin/settings",
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ELPStudioConsole/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra:
            for k, v in extra:
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, obj) -> None:
        raw = json.dumps(obj).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self._file(PUBLIC / "index.html", "text/html; charset=utf-8")
            return
        if path == "/config.json":
            self._send_json(200, _config())
            return
        if path == "/elp/storage-report":
            self._storage_report()
            return
        if path.startswith("/brand-assets/"):
            self._brand_asset(path[len("/brand-assets/") :])
            return
        if path.startswith("/pp/"):
            self._proxy(parsed)
            return
        rel = path.lstrip("/")
        candidate = (PUBLIC / rel).resolve()
        if str(candidate).startswith(str(PUBLIC.resolve())) and candidate.is_file():
            ctype = {
                ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".json": "application/json",
            }.get(candidate.suffix.lower(), "application/octet-stream")
            self._file(candidate, ctype)
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        self._proxy(urlparse(self.path))

    def do_PUT(self):
        self._proxy(urlparse(self.path))

    def do_PATCH(self):
        self._proxy(urlparse(self.path))

    def do_DELETE(self):
        self._proxy(urlparse(self.path))

    def do_OPTIONS(self):
        self._proxy(urlparse(self.path))

    def _file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._send_json(404, {"error": "Missing file"})
            return
        self._send(200, path.read_bytes(), content_type)

    def _brand_asset(self, rel: str) -> None:
        # /brand-assets/<brand_id>/...
        target = (BRANDS_DIR / rel).resolve()
        if not str(target).startswith(str(BRANDS_DIR.resolve())) or not target.is_file():
            self._send_json(404, {"error": "Unknown brand asset"})
            return
        ctype = {
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(target.suffix.lower(), "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def _picpeak_json(self, path: str, timeout: int = 45) -> tuple[int, object]:
        dest = PICPEAK_ORIGIN + path
        headers = {"Accept": "application/json", "Origin": PICPEAK_ORIGIN}
        auth = self.headers.get("Authorization")
        if auth:
            headers["Authorization"] = auth
        cookie = self.headers.get("Cookie")
        if cookie:
            headers["Cookie"] = cookie
        req = Request(dest, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                return resp.status, json.loads(raw) if raw else {}
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {"error": str(exc)}
            except json.JSONDecodeError:
                parsed = {"error": raw or str(exc)}
            return exc.code, parsed
        except URLError as exc:
            return 502, {"error": str(exc.reason), "origin": PICPEAK_ORIGIN}

    def _storage_report(self) -> None:
        if not (self.headers.get("Authorization") or self.headers.get("Cookie")):
            self._send_json(401, {"error": "Sign in first. Storage report uses your PicPeak admin session."})
            return
        _code, info = self._picpeak_json("/api/admin/settings/storage/info")
        if _code >= 400:
            self._send_json(
                _code if _code != 502 else 502,
                {"error": "Could not read PicPeak storage/info", "detail": info},
            )
            return
        _code, settings = self._picpeak_json("/api/admin/settings")
        if _code >= 400:
            settings = {}
        _code, events_body = self._picpeak_json("/api/admin/events?page=1&limit=100")
        events = []
        if isinstance(events_body, dict):
            events = events_body.get("events") or events_body.get("data") or []
        elif isinstance(events_body, list):
            events = events_body
        backup = {}
        for path in ("/api/admin/backup/config", "/api/admin/backup/status", "/api/admin/backup"):
            code, body = self._picpeak_json(path)
            if code < 400 and isinstance(body, dict) and "error" not in body:
                backup = body
                break
        photos_by_event = {}
        for event in events[:40]:
            eid = event.get("id")
            if eid is None:
                continue
            code, body = self._picpeak_json(f"/api/admin/photos/{eid}/photos")
            if code >= 400:
                continue
            if isinstance(body, dict):
                photos_by_event[eid] = body.get("photos") or body.get("data") or []
            elif isinstance(body, list):
                photos_by_event[eid] = body
        report = build_storage_report(
            info=info if isinstance(info, dict) else {},
            events=events,
            photos_by_event=photos_by_event,
            settings=settings if isinstance(settings, dict) else {},
            backup=backup,
        )
        self._send_json(200, report)

    def _proxy(self, parsed) -> None:
        if not parsed.path.startswith("/pp/"):
            self._send_json(404, {"error": "Not a PicPeak proxy path"})
            return
        dest_path = parsed.path[len("/pp") :] or "/"
        dest = PICPEAK_ORIGIN + dest_path
        if parsed.query:
            dest += "?" + parsed.query
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {}
        for key in ("Authorization", "Content-Type", "Cookie", "Accept", "Origin"):
            val = self.headers.get(key)
            if val:
                headers[key] = val
        headers["Origin"] = PICPEAK_ORIGIN
        req = Request(dest, data=body, headers=headers, method=self.command)
        try:
            with urlopen(req, timeout=120) as resp:
                payload = resp.read()
                extra = []
                set_cookie = resp.headers.get("Set-Cookie")
                if set_cookie:
                    extra.append(("Set-Cookie", set_cookie))
                ctype = resp.headers.get("Content-Type") or "application/octet-stream"
                self._send(resp.status, payload, ctype, extra)
        except HTTPError as exc:
            payload = exc.read()
            ctype = exc.headers.get("Content-Type") if exc.headers else "application/json"
            self._send(exc.code, payload or json.dumps({"error": str(exc)}).encode(), ctype or "application/json")
        except URLError as exc:
            self._send_json(
                502,
                {
                    "error": "PicPeak is not reachable from the Studio Console.",
                    "detail": str(exc.reason),
                    "origin": PICPEAK_ORIGIN,
                },
            )


def main() -> int:
    if not PUBLIC.exists():
        print("public/ missing", file=sys.stderr)
        return 1
    httpd = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(f"ELP Studio Console  http://127.0.0.1:{LISTEN_PORT}")
    print(f"PicPeak proxy       {PICPEAK_ORIGIN}")
    print("Does not store galleries. Stop with Ctrl+C.")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
